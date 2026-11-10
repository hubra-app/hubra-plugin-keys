"""The keys plugin: keys, handovers and the overdue-invoice hook."""

from __future__ import annotations

import pytest

from tests.helpers import set_modules
from hubra.core.models.member import Member
from hubra.core.models.notification import Notification
from hubra_keys.models import Key


@pytest.fixture
def other_member(db, seeded_db):
    from hubra.core.models.user import User

    user = User(email="holder@test.ch", first_name="Hanna", last_name="Holder")
    user.set_password("password123")
    db.session.add(user)
    db.session.flush()
    m = Member(user_id=user.id, status="active", tier_id=seeded_db["tier"].id)
    db.session.add(m)
    db.session.commit()
    return m


@pytest.fixture
def key(db, seeded_db):
    k = Key(label="Front door", number="A-1", kind="key", opens="Main entrance")
    db.session.add(k)
    db.session.commit()
    return k


# ── Keys ─────────────────────────────────────────────────────────────────────


def test_create_and_list_keys(client, auth_headers):
    resp = client.post(
        "/api/v1/keys/",
        json={"label": "Workshop", "number": "W-7", "kind": "card", "deposit_chf": 20},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["status"] == "available"
    assert body["depositChf"] == "20.00" or body["depositChf"] == "20"
    listed = client.get("/api/v1/keys/").get_json()
    assert [k["label"] for k in listed] == ["Workshop"]


def test_create_key_validates(client, auth_headers, key):
    assert client.post("/api/v1/keys/", json={}).status_code == 400
    assert (
        client.post("/api/v1/keys/", json={"label": "x", "kind": "laser"}).status_code
        == 400
    )
    for body in (
        {"label": 5},
        {"label": "x", "notes": ["a"]},
        {"label": "x", "public": "yes"},
        {"label": "x", "member_ids": "1"},
        {"label": "x", "code": 1234},
        {"label": "x", "deposit_chf": "NaN"},
    ):
        assert client.post("/api/v1/keys/", json=body).status_code == 400, body
    dup = client.post("/api/v1/keys/", json={"label": "Copy", "number": "A-1"})
    assert dup.status_code == 409


def _now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


def test_keys_has_no_foreign_key_to_codes():
    from hubra_keys.models import Key

    assert not Key.__table__.c.code_id.foreign_keys


def test_issue_and_return_key_logs_history(client, auth_headers, key, other_member):
    resp = client.post(
        f"/api/v1/keys/{key.id}/issue", json={"member_id": other_member.id}
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "issued"
    assert body["holderName"] == "Hanna Holder"

    # Cannot issue twice or delete while issued.
    again = client.post(
        f"/api/v1/keys/{key.id}/issue", json={"member_id": other_member.id}
    )
    assert again.status_code == 409
    assert client.delete(f"/api/v1/keys/{key.id}").status_code == 409

    resp = client.post(f"/api/v1/keys/{key.id}/return", json={"note": "ok"})
    body = resp.get_json()
    assert body["status"] == "available" and body["holderId"] is None
    # The handovers are the history of the key's item in Inventory.
    history = client.get(f"/api/v1/inventory/{body['itemId']}/history").get_json()
    assert [h["action"] for h in history] == ["return", "issue"]
    assert history[0]["note"] == "ok" and history[1]["member_name"] == "Hanna Holder"


def test_lost_and_found(client, auth_headers, key):
    assert client.post(f"/api/v1/keys/{key.id}/lost").get_json()["status"] == "lost"
    assert client.post(f"/api/v1/keys/{key.id}/lost").status_code == 409
    assert (
        client.post(f"/api/v1/keys/{key.id}/found").get_json()["status"] == "available"
    )


def test_my_keys(client, db, auth_headers, key, seeded_db):
    key.status = "issued"
    key.holder_id = seeded_db["admin"].id
    key.notes = "Depot noch offen, nachfragen"
    db.session.commit()
    mine = client.get("/api/v1/keys/mine").get_json()
    assert [k["id"] for k in mine] == [key.id]
    # Manager notes stay with the managers.
    assert "notes" not in mine[0] and "codeId" not in mine[0]

    key.status = "retired"
    db.session.commit()
    assert client.get("/api/v1/keys/mine").get_json() == []


def test_key_with_a_code(client, db, auth_headers, key, seeded_db):
    """A physical key can carry a code (key safe); its holder sees it."""
    resp = client.patch(f"/api/v1/keys/{key.id}", json={"code": "4711"})
    assert resp.status_code == 200 and resp.get_json()["hasCode"] is True
    assert resp.get_json()["kind"] == "key"
    key.status = "issued"
    key.holder_id = seeded_db["admin"].id
    db.session.commit()
    mine = client.get("/api/v1/keys/mine").get_json()
    assert mine[0]["code"] == "4711"
    # "" removes it again.
    resp = client.patch(f"/api/v1/keys/{key.id}", json={"code": ""})
    assert resp.get_json()["hasCode"] is False
    assert "code" not in client.get("/api/v1/keys/mine").get_json()[0]


def test_keys_need_inventory(client, db, auth_headers):
    set_modules(False, "inventory")
    resp = client.get("/api/v1/keys/")
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "MODULE_DISABLED"


def test_overdue_invoice_notifies_key_managers(db, seeded_db, key, other_member):
    from hubra.core.modules import emit

    key.status = "issued"
    key.holder_id = other_member.id
    db.session.commit()
    called = emit(
        "invoice.overdue", tenant_id=None, member_id=other_member.id, invoice_id=1
    )
    assert "inventory.keys" in called
    # Plugin handlers run after the commit (Hubra >= the plugin boundaries).
    db.session.commit()
    notes = (
        db.session.query(Notification).filter_by(member_id=seeded_db["admin"].id).all()
    )
    assert any("Front door" in n.msg for n in notes)


# ── Dashboard widgets ───────────────────────────────────────────────────────


def test_widgets(db, key, other_member):
    from hubra.core import contracts

    key.status, key.holder_id = "issued", other_member.id
    db.session.add_all([
        Key(label="Shared code", kind="code", public=True),
        Key(label="Back door", number="B-2", status="lost"),
        Key(label="Old", status="retired", public=True),
    ])
    db.session.commit()

    mine = contracts.widget_data("inventory.keys.mine", {}, actor=other_member)
    # Held first, then usable; retired keys and the codes themselves never.
    assert [i["label"] for i in mine["items"]] == ["Front door", "Shared code"]
    assert mine["items"][0]["sub"] == "A-1 · Main entrance"
    assert "code" not in str(mine).lower().replace("shared code", "")

    issued = contracts.widget_data("inventory.keys.issued", {}, actor=contracts.SYSTEM)
    assert issued["value"] == 1 and issued["sub"] in ("1 verloren", "1 lost")

    offered = [o.contract.name for o in contracts.widgets(actor=other_member)]
    assert "inventory.keys.issued" not in offered
