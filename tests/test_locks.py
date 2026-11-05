"""Smart locks: keypad codes follow membership and groups (Nuki faked)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from tests.helpers import set_modules
from tests.settings.test_settings_kv import _login, _make_role_and_member


class FakeNuki:
    def __init__(self):
        self.codes: dict[str, tuple[int, str, str]] = {}
        self.opened: list[int] = []
        self.down = False
        self._n = 0

    def add_code(self, token, smartlock_id, name, code):
        from hubra_keys.nuki import NukiError

        if self.down:
            raise NukiError("Nuki could not be reached.")
        assert token == "tok"
        assert len(code) == 6 and "0" not in code and not code.startswith("12")
        self._n += 1
        self.codes[str(self._n)] = (smartlock_id, name, code)
        return str(self._n)

    def remove_code(self, token, smartlock_id, auth_id):
        from hubra_keys.nuki import NukiError

        if self.down:
            raise NukiError("Nuki could not be reached.")
        self.codes.pop(auth_id, None)

    def unlock(self, token, smartlock_id):
        self.opened.append(smartlock_id)


@pytest.fixture
def nuki(monkeypatch):
    from hubra_keys import locks

    fake = FakeNuki()
    for name in ("add_code", "remove_code", "unlock"):
        monkeypatch.setattr(locks.nuki, name, getattr(fake, name))
    monkeypatch.setattr(locks, "_token", lambda: "tok")
    return fake


@pytest.fixture
def club(client, app, db, seeded_db, nuki):
    """Kim manages locks; Max is in the Werkstatt group, Ola is not."""
    from hubra.core.models.group import Group
    from hubra.core.models.member import Member

    set_modules(True, "inventory", "inventory.keys")
    app.test_cli_runner().invoke(args=["sync-permissions"])
    tier = seeded_db["tier"]
    kim = _make_role_and_member(
        db, tier, name="Kim", permission_keys=["keys.locks.manage"]
    )
    max_ = _make_role_and_member(db, tier, name="Max")
    ola = _make_role_and_member(db, tier, name="Ola")
    group = Group(name="Werkstatt")
    db.session.add(group)
    db.session.flush()
    db.session.get(Member, max_.id).groups.append(group)
    db.session.commit()
    return {"kim": kim.id, "max": max_.id, "ola": ola.id, "group": group.id}


def _lock(client, **extra):
    _login(client, "kim@test.ch")
    body = {"name": "Werkstatt", "smartlockId": 17, **extra}
    resp = client.post("/api/v1/keys/locks", json=body)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


def test_group_lock_gives_codes_to_the_group(client, db, club, nuki):
    lock = _lock(client, groupId=club["group"])
    assert lock["sync"] == {"added": 1, "removed": 0, "failed": 0}
    assert [a["memberId"] for a in lock["access"]] == [club["max"]]
    [(smartlock, name, code)] = nuki.codes.values()
    assert smartlock == 17 and name.startswith(f"Hubra {club['max']} ")

    _login(client, "max@test.ch")
    mine = client.get("/api/v1/keys/locks/mine").get_json()
    assert mine == [
        {"id": lock["id"], "name": "Werkstatt", "code": code, "appOpen": True}
    ]
    _login(client, "ola@test.ch")
    assert client.get("/api/v1/keys/locks/mine").get_json() == []
    assert client.post(f"/api/v1/keys/locks/{lock['id']}/open").status_code == 403


def test_code_is_stored_encrypted(client, db, club, nuki):
    from hubra_keys.models import LockAccess

    _lock(client, groupId=club["group"])
    row = db.session.query(LockAccess).one()
    [(_, _, code)] = nuki.codes.values()
    assert code not in row.code


def test_codes_go_when_membership_ends(client, db, club, nuki):
    from hubra.core.models.member import Member
    from hubra_keys.locks import sync_all

    _lock(client)  # everyone: the seeded admin, Kim, Max and Ola
    assert len(nuki.codes) == 4
    m = db.session.get(Member, club["max"])
    m.membership_until = date.today() - timedelta(days=1)
    db.session.get(Member, club["ola"]).status = "suspended"
    db.session.commit()
    assert sync_all() == {"added": 0, "removed": 2, "failed": 0}
    db.session.commit()
    names = sorted(n for _, n, _ in nuki.codes.values())
    assert [n.split()[1] for n in names] == sorted(
        str(i) for i in set(range(1, 5)) - {club["max"], club["ola"]}
    )


def test_leaving_the_group_removes_the_code(client, db, club, nuki):
    from hubra.core.models.member import Member
    from hubra_keys.locks import sync_all

    _lock(client, groupId=club["group"])
    db.session.get(Member, club["max"]).groups.clear()
    db.session.commit()
    sync_all()
    db.session.commit()
    assert nuki.codes == {}


def test_nuki_down_is_retried(client, db, club, nuki):
    from hubra_keys.locks import sync_all

    nuki.down = True
    lock = _lock(client, groupId=club["group"])
    assert lock["sync"]["failed"] == 1
    assert lock["access"][0]["status"] == "failed"
    nuki.down = False
    assert sync_all()["added"] == 1
    db.session.commit()
    assert len(nuki.codes) == 1


def test_open_from_the_app_logs_a_check_in(client, db, club, nuki):
    from hubra_keys.models import CheckIn

    lock = _lock(client, groupId=club["group"])
    _login(client, "max@test.ch")
    assert client.post(f"/api/v1/keys/locks/{lock['id']}/open").status_code == 200
    assert nuki.opened == [17]
    c = db.session.query(CheckIn).one()
    assert (c.member_id, c.place) == (club["max"], "Werkstatt")

    _login(client, "kim@test.ch")
    client.patch(f"/api/v1/keys/locks/{lock['id']}", json={"appOpen": False})
    _login(client, "max@test.ch")
    assert client.post(f"/api/v1/keys/locks/{lock['id']}/open").status_code == 403


def test_keypad_off_removes_codes_and_delete_cleans_up(client, db, club, nuki):
    lock = _lock(client)
    assert len(nuki.codes) == 4
    resp = client.patch(f"/api/v1/keys/locks/{lock['id']}", json={"keypad": False})
    assert resp.get_json()["sync"]["removed"] == 4 and nuki.codes == {}
    client.patch(f"/api/v1/keys/locks/{lock['id']}", json={"keypad": True})
    assert len(nuki.codes) == 4
    assert client.delete(f"/api/v1/keys/locks/{lock['id']}").status_code == 204
    assert nuki.codes == {}


def test_locks_need_the_right_and_validate(client, db, club):
    _login(client, "max@test.ch")
    assert client.get("/api/v1/keys/locks").status_code == 403
    assert client.post("/api/v1/keys/locks", json={}).status_code == 403
    _login(client, "kim@test.ch")
    for body in (
        {},
        {"name": "x"},
        {"name": "x", "smartlockId": "17"},
        {"name": "x", "smartlockId": 17, "groupId": 999},
        {"name": "x", "smartlockId": 17, "keypad": "yes"},
        {"name": "", "smartlockId": 17},
    ):
        assert client.post("/api/v1/keys/locks", json=body).status_code == 400, body


def test_new_code_rules():
    from hubra_keys.nuki import new_code

    for _ in range(200):
        code = new_code()
        assert len(code) == 6 and "0" not in code and not code.startswith("12")
