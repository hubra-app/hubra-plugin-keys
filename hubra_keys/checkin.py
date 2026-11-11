"""Check-in with the member badge: /api/v1/keys/checkins.

Every member has one member badge on My Account (and in Google Wallet): a
badge number such as ``HB-7K3M-Q9TX`` with its QR code, the same in every
club (Hubra core, ``members.badge.lookup``). Whoever checks people in (a
trainer at training, someone at the door) scans it with a scanner or the
check-in screen's camera; the check-in is kept, and at an event the member
is marked present on the event's attendance roll.

The club's own member cards are gone: their table ``member_cards`` is
dropped, so an old printed or photographed card code no longer checks
anyone in (it could not be renewed or revoked any more).

GET    /checkins/lookup        ?card=<badge number>: who it is, before checking in
GET    /checkins/events        today's events to check people in to
GET    /checkins               ?date=YYYY-MM-DD&eventId=<id>: that day's check-ins
POST   /checkins               {card, eventId?, place?}
DELETE /checkins/<id>          undo a check-in (not the attendance mark)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from flask import jsonify, request
from sqlalchemy import func, select

from hubra.core.auth.helpers import get_current_member
from hubra.core.contracts import SYSTEM, ActionUnavailable, Refused, query
from hubra.core.errors import api_error
from hubra.core.permissions import permission_required
from hubra.core.extensions import db
from hubra.core.models.event import ClubEvent, EventAttendance
from hubra.core.models.member import Member

from .models import CheckIn
from .routes import keys_bp

LABEL = "Check members in with their member badge"
# The same member at the same place within this time counts once.
REPEAT = timedelta(minutes=10)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value) -> str | None:
    return value.isoformat() if value else None


def _blocked(member: Member) -> str | None:
    """Why this member may not be checked in, or None."""
    if member.deleted_at or member.archived_at:
        return "This member has left the club."
    if member.is_blocked:
        return "This member is suspended."
    return None


def _expired(member: Member) -> bool:
    until = member.membership_until
    return bool(until and until < date.today())


def _member_out(member: Member) -> dict:
    user = getattr(member, "user", None)
    return {
        "memberId": member.id,
        "name": member.name,
        "status": member.status,
        "avatar": getattr(user, "avatar", None),
        "until": _iso(member.membership_until),
        "expired": _expired(member),
        "blocked": _blocked(member),
    }


class BadgeLookupMissing(Exception):
    """This Hubra has no ``members.badge.lookup`` (older than the release
    after 0.2.5): say so instead of calling every badge unknown."""


def _by_token(token) -> Member | None:
    """The member behind a scanned member badge number."""
    if not isinstance(token, str) or not token.strip() or len(token) > 64:
        return None
    try:
        found = query("members.badge.lookup", code=token, actor=SYSTEM)
    except Refused:
        return None
    except ActionUnavailable:
        raise BadgeLookupMissing() from None
    return db.session.get(Member, found["member_id"])


def _no_lookup():
    return api_error(
        "BADGE_LOOKUP_MISSING",
        "This Hubra can't look up member badges yet. Update Hubra to check members in.",
        503,
    )


def _checkin_out(c: CheckIn, names: dict[int, str], already=False) -> dict:
    return {
        "id": c.id,
        "memberId": c.member_id,
        "name": names.get(c.member_id) or (c.member.name if c.member else None),
        "eventId": c.event_id,
        "place": c.place,
        "at": _iso(c.at),
        "already": already,
    }


def _today_events():
    today = date.today()
    return db.session.scalars(
        select(ClubEvent)
        .where(ClubEvent.date <= today)
        .where(func.coalesce(ClubEvent.end_date, ClubEvent.date) >= today)
        .order_by(ClubEvent.time, ClubEvent.title)
    )


# ── Check-in ─────────────────────────────────────────────────────────────────


@keys_bp.get("/checkins/lookup")
@permission_required("checkins", "create", LABEL)
def lookup():
    try:
        member = _by_token(request.args.get("card"))
    except BadgeLookupMissing:
        return _no_lookup()
    if member is None:
        return api_error("CARD_UNKNOWN", "No member of the club has this badge.", 404)
    return jsonify(_member_out(member))


@keys_bp.get("/checkins/events")
@permission_required("checkins", "create", LABEL)
def events_today():
    return jsonify(
        [
            {"id": e.id, "title": e.title, "time": e.time, "location": e.location}
            for e in _today_events()
        ]
    )


@keys_bp.get("/checkins")
@permission_required("checkins", "create", LABEL)
def list_checkins():
    raw = request.args.get("date")
    try:
        day = date.fromisoformat(raw) if raw else date.today()
    except ValueError:
        return api_error("VALIDATION_ERROR", "date must be YYYY-MM-DD", 400)
    start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
    q = (
        select(CheckIn)
        .where(CheckIn.at >= start - timedelta(hours=14))
        .where(CheckIn.at < start + timedelta(days=1, hours=14))
        .order_by(CheckIn.at.desc())
    )
    event_id = request.args.get("eventId", type=int)
    if event_id:
        q = q.where(CheckIn.event_id == event_id)
    rows = [c for c in db.session.scalars(q) if _local_day(c.at) == day]
    names = _names({c.member_id for c in rows})
    return jsonify([_checkin_out(c, names) for c in rows])


def _local_day(at: datetime) -> date:
    """The club's day of a check-in (the server's local time)."""
    return at.astimezone().date()


def _names(ids) -> dict[int, str]:
    if not ids:
        return {}
    return {
        m.id: m.name
        for m in db.session.scalars(select(Member).where(Member.id.in_(ids)))
    }


@keys_bp.post("/checkins")
@permission_required("checkins", "create", LABEL)
def check_in():
    body = request.get_json(silent=True) or {}
    try:
        member = _by_token(body.get("card"))
    except BadgeLookupMissing:
        return _no_lookup()
    if member is None:
        return api_error("CARD_UNKNOWN", "No member of the club has this badge.", 404)
    reason = _blocked(member)
    if reason:
        return api_error("CARD_BLOCKED", reason, 409)

    event = None
    event_id = body.get("eventId")
    if event_id is not None:
        if not isinstance(event_id, int) or isinstance(event_id, bool):
            return api_error("VALIDATION_ERROR", "eventId must be an event id", 400)
        event = db.session.get(ClubEvent, event_id)
        if event is None:
            return api_error("VALIDATION_ERROR", "eventId must be an event", 400)
    place = body.get("place")
    if place is not None and (not isinstance(place, str) or len(place) > 120):
        return api_error("VALIDATION_ERROR", "place must be text up to 120", 400)
    place = (place or "").strip() or None
    if event is not None:
        place = None

    by = get_current_member()
    now = _now()
    same = select(CheckIn).where(CheckIn.member_id == member.id)
    if event is not None:
        same = same.where(CheckIn.event_id == event.id)
    else:
        same = (
            same.where(CheckIn.event_id.is_(None))
            .where(CheckIn.place.is_(None) if place is None else CheckIn.place == place)
            .where(CheckIn.at >= now - REPEAT)
        )
    earlier = db.session.scalar(same.order_by(CheckIn.at.desc()).limit(1))
    out = _member_out(member)
    if earlier is not None:
        out["checkIn"] = _checkin_out(earlier, {member.id: member.name}, True)
        return jsonify(out)

    checkin = CheckIn(
        member_id=member.id,
        event_id=event.id if event else None,
        place=place,
        by_id=by.id,
        at=now,
    )
    db.session.add(checkin)
    if event is not None:
        mark = db.session.scalar(
            select(EventAttendance)
            .where(EventAttendance.event_id == event.id)
            .where(EventAttendance.member_id == member.id)
        )
        if mark is None:
            db.session.add(
                EventAttendance(
                    event_id=event.id,
                    member_id=member.id,
                    status="present",
                    marked_by=by.id,
                    marked_at=now,
                )
            )
        elif mark.status != "present":
            mark.status, mark.marked_by, mark.marked_at = "present", by.id, now
    db.session.flush()
    out["checkIn"] = _checkin_out(checkin, {member.id: member.name})
    db.session.commit()
    return jsonify(out), 201


@keys_bp.delete("/checkins/<int:checkin_id>")
@permission_required("checkins", "create", LABEL)
def undo(checkin_id: int):
    checkin = db.session.get(CheckIn, checkin_id)
    if checkin is None:
        return api_error("NOT_FOUND", "No such check-in.", 404)
    # Check-ins are also the log of doors opened from the app: an undo is
    # kept in the audit log so that log can't be emptied without a trace.
    from hubra.core.utils import log_audit

    log_audit(
        get_current_member().id,
        "keys.checkin.undo",
        "CheckIn",
        checkin.id,
        f"member {checkin.member_id} at {_iso(checkin.at)}"
        + (f" ({checkin.place})" if checkin.place else ""),
    )
    db.session.delete(checkin)
    db.session.commit()
    return "", 204
