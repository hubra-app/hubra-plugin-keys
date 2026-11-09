"""Codes are keys of the kind "code"; keys are public or assigned to
several members and groups, and show on those members' account page."""

from __future__ import annotations

import pytest

from hubra.core.models.group import Group
from hubra.core.models.member import Member, member_groups
from hubra_keys.models import Key


@pytest.fixture
def people(db, seeded_db):
    from hubra.core.models.user import User

    out = []
    for i, name in enumerate(("Ada", "Ben", "Cleo")):
        user = User(email=f"p{i}@test.ch", first_name=name, last_name="Test")
        user.set_password("password123")
        db.session.add(user)
        db.session.flush()
        m = Member(user_id=user.id, status="active", tier_id=seeded_db["tier"].id)
        db.session.add(m)
        out.append(m)
    group = Group(name="Werkstatt")
    db.session.add(group)
    db.session.flush()
    db.session.execute(member_groups.insert().values(member_id=out[2].id, group_id=group.id))
    db.session.commit()
    return out, group


def _mine(client, app, member):
    """GET /keys/mine as *member*."""
    from unittest.mock import patch

    with patch("hubra_keys.routes.get_current_member", return_value=member):
        return client.get("/api/v1/keys/mine").get_json()


def test_a_code_is_a_key_kept_encrypted(client, auth_headers, db):
    body = client.post(
        "/api/v1/keys/", json={"label": "Gate", "kind": "code", "code": " 4711 "}
    ).get_json()
    assert body["kind"] == "code" and body["hasCode"] is True
    row = db.session.get(Key, body["id"])
    assert row.secret and "4711" not in row.secret
    assert client.get(f"/api/v1/keys/{body['id']}/code").get_json() == {"code": "4711"}
    # A code isn't handed out.
    resp = client.post(f"/api/v1/keys/{body['id']}/issue", json={"member_id": 1})
    assert resp.status_code == 409 and resp.get_json()["error"] == "CODE_ASSIGNED"
    # Cleared with an empty code.
    client.patch(f"/api/v1/keys/{body['id']}", json={"code": ""})
    assert db.session.get(Key, body["id"]).secret is None


def test_assign_to_several_members_and_groups(client, auth_headers, people):
    (ada, ben, cleo), group = people
    body = client.post(
        "/api/v1/keys/",
        json={"label": "Hall", "member_ids": [ada.id, ben.id], "group_ids": [group.id]},
    ).get_json()
    assert sorted(m["id"] for m in body["members"]) == sorted([ada.id, ben.id])
    assert [g["name"] for g in body["groups"]] == ["Werkstatt"]
    # Replace the members, groups stay.
    body = client.patch(f"/api/v1/keys/{body['id']}", json={"member_ids": [ben.id]}).get_json()
    assert [m["id"] for m in body["members"]] == [ben.id]
    assert [g["id"] for g in body["groups"]] == [group.id]
    assert client.patch(
        f"/api/v1/keys/{body['id']}", json={"group_ids": [99999]}
    ).status_code == 404


def test_my_keys_follow_assignment(client, auth_headers, app, people):
    (ada, ben, cleo), group = people
    client.post("/api/v1/keys/", json={"label": "Ada's", "member_ids": [ada.id]})
    client.post("/api/v1/keys/", json={"label": "Workshop code", "kind": "code",
                                       "code": "1234", "group_ids": [group.id]})
    client.post("/api/v1/keys/", json={"label": "Wifi", "kind": "code", "code": "pw",
                                       "public": True})
    client.post("/api/v1/keys/", json={"label": "Nobody's"})

    assert [k["label"] for k in _mine(client, app, ada)] == ["Ada's", "Wifi"]
    assert [k["label"] for k in _mine(client, app, ben)] == ["Wifi"]
    cleo_keys = {k["label"]: k for k in _mine(client, app, cleo)}
    assert set(cleo_keys) == {"Workshop code", "Wifi"}
    assert cleo_keys["Workshop code"]["code"] == "1234"
    assert "members" not in cleo_keys["Wifi"] and "notes" not in cleo_keys["Wifi"]


def test_codes_from_the_codes_plugin_come_in(client, auth_headers, db, monkeypatch):
    from hubra_keys import items

    exported = [
        {"id": 7, "name": "Gate", "code": "4711", "description": "Back gate", "is_active": True},
        {"id": 8, "name": "Old", "code": "1", "description": None, "is_active": False},
    ]
    monkeypatch.setattr(items, "available", lambda name: name == "codes.codes.export")
    real_query = items.query
    monkeypatch.setattr(
        items, "query",
        lambda name, **kw: exported if name == "codes.codes.export" else real_query(name, **kw),
    )
    assert items.take_over_codes() == 2
    db.session.commit()
    assert items.take_over_codes() == 0
    gate = db.session.query(Key).filter_by(code_id=7).one()
    assert gate.kind == "code" and gate.notes == "Back gate" and gate.item_id
    assert client.get(f"/api/v1/keys/{gate.id}/code").get_json() == {"code": "4711"}
    assert db.session.query(Key).filter_by(code_id=8).one().status == "retired"
