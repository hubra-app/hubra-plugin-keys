"""Each key is an inventory item of the type "Key", kept in line through
Inventory's contracts (hubra_keys.items)."""

from __future__ import annotations

import pytest

from hubra.core import contracts
from hubra.core.models.member import Member
from hubra_keys.items import link_missing
from hubra_keys.models import Key, KeyHandover


def _item(item_id: int) -> dict | None:
    found = contracts.query("inventory.items.get", ids=[item_id], actor=contracts.SYSTEM)
    return found[0] if found else None


@pytest.fixture
def holder(db, seeded_db):
    from hubra.core.models.user import User

    user = User(email="holder@test.ch", first_name="Hanna", last_name="Holder")
    user.set_password("password123")
    db.session.add(user)
    db.session.flush()
    m = Member(user_id=user.id, status="active", tier_id=seeded_db["tier"].id)
    db.session.add(m)
    db.session.commit()
    return m


def test_a_new_key_is_an_inventory_item(client, auth_headers):
    body = client.post(
        "/api/v1/keys/", json={"label": "Workshop", "number": "W-7", "kind": "card"}
    ).get_json()
    assert body["itemId"]
    item = _item(body["itemId"])
    assert item["name"] == "Workshop" and item["category"] == "Key"
    assert item["status"] == "available" and item["serial_number"] == "W-7"

    by_item = client.get(f"/api/v1/keys/by-item/{body['itemId']}")
    assert by_item.status_code == 200 and by_item.get_json()["id"] == body["id"]


def test_handovers_set_the_item_status(client, auth_headers, holder):
    key = client.post("/api/v1/keys/", json={"label": "Gate"}).get_json()
    item_id = key["itemId"]
    client.post(f"/api/v1/keys/{key['id']}/issue", json={"member_id": holder.id})
    assert _item(item_id)["status"] == "in_use"
    assert _item(item_id)["holder_id"] == holder.id
    client.post(f"/api/v1/keys/{key['id']}/return")
    assert _item(item_id)["status"] == "available"
    assert _item(item_id)["holder_id"] is None
    client.post(f"/api/v1/keys/{key['id']}/lost")
    assert _item(item_id)["status"] == "lost"
    client.post(f"/api/v1/keys/{key['id']}/found")
    client.post(f"/api/v1/keys/{key['id']}/retire")
    assert _item(item_id)["status"] == "retired"


def test_renaming_follows_both_ways(client, auth_headers, db):
    key = client.post("/api/v1/keys/", json={"label": "Gate"}).get_json()
    client.patch(f"/api/v1/keys/{key['id']}", json={"label": "Back gate", "number": "B-2"})
    item = _item(key["itemId"])
    assert item["name"] == "Back gate" and item["serial_number"] == "B-2"

    # Renamed in Inventory: the key follows.
    resp = client.patch(f"/api/v1/inventory/{key['itemId']}", json={"name": "Garden gate"})
    assert resp.status_code == 200
    db.session.expire_all()
    assert db.session.get(Key, key["id"]).label == "Garden gate"


def test_a_status_set_in_inventory_is_put_back(client, auth_headers, db, holder):
    key = client.post("/api/v1/keys/", json={"label": "Gate"}).get_json()
    client.post(f"/api/v1/keys/{key['id']}/issue", json={"member_id": holder.id})
    client.patch(f"/api/v1/inventory/{key['itemId']}", json={"status": "available"})
    db.session.expire_all()
    assert _item(key["itemId"])["status"] == "in_use"
    assert db.session.get(Key, key["id"]).status == "issued"


def test_a_key_added_in_inventory_gets_its_key(client, auth_headers, db):
    resp = client.post(
        "/api/v1/inventory/",
        json={"name": "Shed", "category": "Key", "serial_number": "S-1"},
    )
    assert resp.status_code == 201
    item_id = resp.get_json()["id"]
    db.session.expire_all()
    key = client.get(f"/api/v1/keys/by-item/{item_id}").get_json()
    assert key["label"] == "Shed" and key["number"] == "S-1"
    assert key["status"] == "available"
    # A tool is no key.
    tool = client.post("/api/v1/inventory/", json={"name": "Drill", "category": "Tool"})
    assert client.get(f"/api/v1/keys/by-item/{tool.get_json()['id']}").status_code == 404


def test_deleting_follows_both_ways(client, auth_headers, db):
    one = client.post("/api/v1/keys/", json={"label": "One"}).get_json()
    assert client.delete(f"/api/v1/keys/{one['id']}").status_code == 204
    assert _item(one["itemId"]) is None

    two = client.post("/api/v1/keys/", json={"label": "Two"}).get_json()
    assert client.delete(f"/api/v1/inventory/{two['itemId']}").status_code == 204
    db.session.expire_all()
    assert db.session.get(Key, two["id"]) is None


def test_no_longer_a_key(client, auth_headers, db, holder):
    key = client.post("/api/v1/keys/", json={"label": "Box"}).get_json()
    client.patch(f"/api/v1/inventory/{key['itemId']}", json={"category": "Item"})
    db.session.expire_all()
    assert db.session.get(Key, key["id"]) is None

    # One that somebody holds stays a key.
    held = client.post("/api/v1/keys/", json={"label": "Held"}).get_json()
    client.post(f"/api/v1/keys/{held['id']}/issue", json={"member_id": holder.id})
    client.patch(f"/api/v1/inventory/{held['itemId']}", json={"category": "Item"})
    db.session.expire_all()
    assert db.session.get(Key, held["id"]) is not None
    assert _item(held["itemId"])["category"] == "Key"


def test_keys_from_before_get_their_item(client, auth_headers, db, seeded_db, holder):
    from datetime import datetime, timezone

    old = [
        Key(label="Old 1", number="O-1", status="issued", holder_id=holder.id),
        Key(label="Old 2", status="lost"),
    ]
    db.session.add_all(old)
    db.session.flush()
    then = datetime(2025, 3, 1, 10, 0, tzinfo=timezone.utc)
    db.session.add(KeyHandover(key_id=old[0].id, action="issue", member_id=holder.id,
                               note="from before", at=then))
    db.session.commit()
    assert link_missing() == 2
    db.session.commit()
    first, second = (_item(k.item_id) for k in old)
    assert first["name"] == "Old 1" and first["category"] == "Key"
    assert first["status"] == "in_use" and first["holder_id"] == holder.id
    assert second["status"] == "lost"
    # The old handover moved into the item's history, with its date.
    history = client.get(f"/api/v1/inventory/{old[0].item_id}/history").get_json()
    assert [(h["action"], h["note"]) for h in history] == [("issue", "from before")]
    assert history[0]["at"].startswith("2025-03-01")
    assert db.session.query(KeyHandover).count() == 0
    assert link_missing() == 0
