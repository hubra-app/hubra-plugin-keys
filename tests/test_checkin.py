"""Member cards and check-in: the card's code, scanning it, attendance."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from tests.helpers import set_modules
from tests.settings.test_settings_kv import _login, _make_role_and_member

LINK = "https://club.test/demo/app/inventory/checkin?card="


@pytest.fixture
def club(client, app, db, seeded_db):
    """Tom checks people in; Max and Ola are members without that right."""
    set_modules(True, "inventory", "inventory.keys")
    app.test_cli_runner().invoke(args=["sync-permissions"])
    tier = seeded_db["tier"]
    tom = _make_role_and_member(
        db, tier, name="Tom", permission_keys=["keys.checkins.create"]
    )
    max_ = _make_role_and_member(db, tier, name="Max")
    ola = _make_role_and_member(db, tier, name="Ola")
    return {"tom": tom.id, "max": max_.id, "ola": ola.id}


def _card(client, who: str) -> str:
    _login(client, f"{who}@test.ch")
    resp = client.get(f"/api/v1/keys/card?link={LINK}")
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["qr"].startswith("data:image/svg+xml;base64,")
    return body["token"]


def _event(db, **extra):
    from hubra.core.models.event import ClubEvent

    e = ClubEvent(
        title="Training", date=date.today(), time="18:00", type="training", **extra
    )
    db.session.add(e)
    db.session.commit()
    return e


def test_my_card_stays_until_renewed(client, club):
    token = _card(client, "max")
    assert _card(client, "max") == token
    renewed = client.post(f"/api/v1/keys/card/renew?link={LINK}").get_json()
    assert renewed["token"] != token
    # The old code no longer works.
    _login(client, "tom@test.ch")
    old = client.post("/api/v1/keys/checkins", json={"card": token})
    assert old.status_code == 404
    assert old.get_json()["error"] == "CARD_UNKNOWN"


def test_check_in_at_an_event_marks_present(client, db, club):
    from hubra.core.models.event import EventAttendance

    event = _event(db)
    token = _card(client, "max")
    _login(client, "tom@test.ch")
    events = client.get("/api/v1/keys/checkins/events").get_json()
    assert [e["id"] for e in events] == [event.id]

    who = client.get(f"/api/v1/keys/checkins/lookup?card={token}").get_json()
    assert who["memberId"] == club["max"] and who["blocked"] is None

    resp = client.post(
        "/api/v1/keys/checkins", json={"card": token, "eventId": event.id}
    )
    assert resp.status_code == 201, resp.get_json()
    assert resp.get_json()["checkIn"]["already"] is False
    mark = db.session.query(EventAttendance).filter_by(event_id=event.id).one()
    assert (mark.member_id, mark.status, mark.marked_by) == (
        club["max"],
        "present",
        club["tom"],
    )

    # Scanned twice: one check-in.
    again = client.post(
        "/api/v1/keys/checkins", json={"card": token, "eventId": event.id}
    )
    assert again.status_code == 200 and again.get_json()["checkIn"]["already"]
    listed = client.get(f"/api/v1/keys/checkins?eventId={event.id}").get_json()
    assert [c["memberId"] for c in listed] == [club["max"]]

    # Undo removes the check-in but keeps the roll as it is.
    assert client.delete(f"/api/v1/keys/checkins/{listed[0]['id']}").status_code == 204
    assert client.get("/api/v1/keys/checkins").get_json() == []
    assert db.session.query(EventAttendance).count() == 1


def test_excused_becomes_present(client, db, club):
    from hubra.core.models.event import EventAttendance

    event = _event(db)
    db.session.add(
        EventAttendance(event_id=event.id, member_id=club["max"], status="excused")
    )
    db.session.commit()
    token = _card(client, "max")
    _login(client, "tom@test.ch")
    client.post("/api/v1/keys/checkins", json={"card": token, "eventId": event.id})
    db.session.expire_all()
    assert db.session.query(EventAttendance).one().status == "present"


def test_door_check_in_with_a_place(client, db, club):
    token = _card(client, "ola")
    _login(client, "tom@test.ch")
    first = client.post(
        "/api/v1/keys/checkins", json={"card": token, "place": "Werkstatt"}
    )
    assert first.status_code == 201
    assert first.get_json()["checkIn"]["place"] == "Werkstatt"
    # Within ten minutes at the same place it counts once; elsewhere it counts.
    same = client.post(
        "/api/v1/keys/checkins", json={"card": token, "place": "Werkstatt"}
    )
    assert same.get_json()["checkIn"]["already"]
    other = client.post("/api/v1/keys/checkins", json={"card": token})
    assert other.status_code == 201


def test_suspended_or_expired(client, db, club):
    from hubra.core.models.member import Member

    token = _card(client, "max")
    member = db.session.get(Member, club["max"])
    member.membership_until = date.today() - timedelta(days=1)
    db.session.commit()
    _login(client, "tom@test.ch")
    ok = client.post("/api/v1/keys/checkins", json={"card": token})
    assert ok.status_code == 201 and ok.get_json()["expired"] is True

    member.status = "suspended"
    db.session.commit()
    who = client.get(f"/api/v1/keys/checkins/lookup?card={token}").get_json()
    assert who["blocked"]
    refused = client.post("/api/v1/keys/checkins", json={"card": token})
    assert refused.status_code == 409
    assert refused.get_json()["error"] == "CARD_BLOCKED"


def test_check_in_needs_the_right(client, db, club):
    token = _card(client, "max")
    _login(client, "ola@test.ch")
    assert client.post("/api/v1/keys/checkins", json={"card": token}).status_code == 403
    assert client.get(f"/api/v1/keys/checkins/lookup?card={token}").status_code == 403
    assert client.get("/api/v1/keys/checkins").status_code == 403


def test_check_in_validates(client, db, club):
    token = _card(client, "max")
    _login(client, "tom@test.ch")
    for body in (
        {},
        {"card": 5},
        {"card": "x" * 65},
    ):
        resp = client.post("/api/v1/keys/checkins", json=body)
        assert resp.status_code == 404, body
    for body in (
        {"card": token, "eventId": "1"},
        {"card": token, "eventId": 999},
        {"card": token, "place": ["a"]},
        {"card": token, "place": "x" * 121},
    ):
        resp = client.post("/api/v1/keys/checkins", json=body)
        assert resp.status_code == 400, body
    assert client.get("/api/v1/keys/checkins?date=gestern").status_code == 400


def test_card_link_must_be_http(client, club):
    _login(client, "max@test.ch")
    body = client.get("/api/v1/keys/card?link=javascript:alert(1)//").get_json()
    # Without a usable link the code holds just the token.
    assert body["qr"] and body["token"]
