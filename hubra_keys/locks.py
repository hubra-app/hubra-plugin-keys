"""Smart locks: who may open which door follows membership and groups.

GET    /locks                   the club's locks with who has access (keys.locks.manage)
POST   /locks                   {name, smartlockId, groupId?, keypad, appOpen}
PATCH  /locks/<id>              same fields
DELETE /locks/<id>              removes the lock and its codes on Nuki
POST   /locks/<id>/sync         brings Nuki in line now
GET    /locks/mine              doors I may open, with my keypad code
POST   /locks/<id>/open         opens the door from the app (logged as a check-in)

A sync (every 15 minutes, and after each change) gives each member who may
open a lock a keypad code there, and takes it away from those who no longer
may: who left, is suspended, whose membership ended, or who left the group.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from flask import jsonify, request
from sqlalchemy import select

from hubra.api.auth.helpers import get_current_member
from hubra.api.permissions import permission_required, require_member
from hubra.api.utils import log_audit
from hubra.core.crypto import decrypt_code, encrypt_code
from hubra.core.errors import api_error
from hubra.core.extensions import db
from hubra.core.models.group import Group
from hubra.core.models.member import Member, member_groups

from . import nuki
from .models import CheckIn, LockAccess, SmartLock
from .routes import keys_bp

LABEL = "Manage smart locks"
PURPOSE = "lock_access.code"
MODULE = "inventory.keys"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _token() -> str:
    from hubra.core.modules import get_config

    return str(get_config(MODULE).get("nuki_token") or "").strip()


def may_open(member: Member) -> bool:
    if member.deleted_at or member.archived_at or member.is_blocked:
        return False
    if member.status == "inactive":
        return False
    until = member.membership_until
    return not (until and until < date.today())


def allowed(lock: SmartLock) -> dict[int, Member]:
    """Members who may open *lock*."""
    q = select(Member)
    if lock.group_id:
        q = q.join(member_groups, member_groups.c.member_id == Member.id).where(
            member_groups.c.group_id == lock.group_id
        )
    return {m.id: m for m in db.session.scalars(q) if may_open(m)}


def _auth_name(member: Member) -> str:
    return f"Hubra {member.id} {member.name}"[:32]


def sync(lock: SmartLock) -> dict:
    """Adds and removes keypad codes on Nuki. Returns counts."""
    token = _token()
    who = allowed(lock) if lock.keypad else {}
    rows = {a.member_id: a for a in lock.access}
    out = {"added": 0, "removed": 0, "failed": 0}
    for member_id, row in list(rows.items()):
        if member_id in who:
            continue
        try:
            if row.auth_id:
                nuki.remove_code(token, lock.smartlock_id, row.auth_id)
        except nuki.NukiError as exc:
            row.status, row.error, row.updated_at = "failed", str(exc), _now()
            out["failed"] += 1
            continue
        db.session.delete(row)
        out["removed"] += 1
    for member_id, member in who.items():
        row = rows.get(member_id)
        if row is None:
            row = LockAccess(lock_id=lock.id, member_id=member_id)
            db.session.add(row)
        if row.status == "active":
            continue
        code = decrypt_code(row.code, PURPOSE) if row.code else nuki.new_code()
        row.code = encrypt_code(code, PURPOSE)
        try:
            row.auth_id = nuki.add_code(
                token, lock.smartlock_id, _auth_name(member), code
            )
        except nuki.NukiError as exc:
            row.status, row.error, row.updated_at = "failed", str(exc), _now()
            out["failed"] += 1
            continue
        row.status, row.error, row.updated_at = "active", None, _now()
        out["added"] += 1
    lock.synced_at = _now()
    db.session.flush()
    return out


def sync_all() -> dict:
    total = {"added": 0, "removed": 0, "failed": 0}
    for lock in db.session.scalars(select(SmartLock)):
        for k, v in sync(lock).items():
            total[k] += v
    return total


# ── Routes ───────────────────────────────────────────────────────────────────


def _lock_out(lock: SmartLock, names: dict[int, str] | None = None) -> dict:
    out = {
        "id": lock.id,
        "name": lock.name,
        "smartlockId": lock.smartlock_id,
        "groupId": lock.group_id,
        "keypad": lock.keypad,
        "appOpen": lock.app_open,
        "syncedAt": lock.synced_at.isoformat() if lock.synced_at else None,
    }
    if names is not None:
        out["access"] = sorted(
            (
                {
                    "memberId": a.member_id,
                    "name": names.get(a.member_id),
                    "status": a.status,
                    "error": a.error,
                }
                for a in lock.access
            ),
            key=lambda a: a["name"] or "",
        )
    return out


def _read(lock: SmartLock, data: dict) -> str | None:
    name = data.get("name", lock.name)
    if not isinstance(name, str) or not name.strip() or len(name) > 120:
        return "name is required (up to 120 characters)"
    sid = data.get("smartlockId", lock.smartlock_id)
    if not isinstance(sid, int) or isinstance(sid, bool) or not 0 < sid < 2**53:
        return "smartlockId must be the lock's Nuki id"
    group_id = data.get("groupId", lock.group_id)
    if group_id is not None and (
        not isinstance(group_id, int) or db.session.get(Group, group_id) is None
    ):
        return "groupId must be a group"
    flags = {}
    for field, attr in (("keypad", "keypad"), ("appOpen", "app_open")):
        value = data.get(field, getattr(lock, attr))
        if value is None:
            value = True
        if not isinstance(value, bool):
            return f"{field} must be true or false"
        flags[attr] = value
    lock.name, lock.smartlock_id, lock.group_id = name.strip(), sid, group_id
    lock.keypad, lock.app_open = flags["keypad"], flags["app_open"]
    return None


def _names(ids) -> dict[int, str]:
    ids = set(ids)
    if not ids:
        return {}
    return {
        m.id: m.name
        for m in db.session.scalars(select(Member).where(Member.id.in_(ids)))
    }


def _saved(lock: SmartLock, status: int = 200):
    """Commit, then try Nuki; the lock is kept even when Nuki fails."""
    db.session.commit()
    result = sync(lock)
    db.session.commit()
    out = _lock_out(lock, _names(a.member_id for a in lock.access))
    out["sync"] = result
    return jsonify(out), status


@keys_bp.get("/locks")
@permission_required("locks", "manage", LABEL)
def list_locks():
    locks = list(db.session.scalars(select(SmartLock).order_by(SmartLock.name)))
    names = _names(a.member_id for lock in locks for a in lock.access)
    return jsonify(
        {
            "configured": bool(_token()),
            "locks": [_lock_out(lock, names) for lock in locks],
            "groups": [
                {"id": g.id, "name": g.name}
                for g in db.session.scalars(select(Group).order_by(Group.name))
            ],
        }
    )


@keys_bp.post("/locks")
@permission_required("locks", "manage", LABEL)
def create_lock():
    lock = SmartLock(name="", smartlock_id=0)
    error = _read(lock, request.get_json(silent=True) or {})
    if error:
        return api_error("VALIDATION_ERROR", error, 400)
    db.session.add(lock)
    db.session.flush()
    log_audit(
        get_current_member().id, "keys.lock.create", "SmartLock", lock.id, lock.name
    )
    return _saved(lock, 201)


@keys_bp.patch("/locks/<int:lock_id>")
@permission_required("locks", "manage", LABEL)
def update_lock(lock_id: int):
    lock = db.session.get(SmartLock, lock_id)
    if lock is None:
        return api_error("NOT_FOUND", "No such lock.", 404)
    before = lock.smartlock_id
    error = _read(lock, request.get_json(silent=True) or {})
    if error:
        db.session.rollback()
        return api_error("VALIDATION_ERROR", error, 400)
    if lock.smartlock_id != before:
        # Codes on the old lock stay there; the club removes them in Nuki.
        for row in list(lock.access):
            db.session.delete(row)
    log_audit(
        get_current_member().id, "keys.lock.update", "SmartLock", lock.id, lock.name
    )
    return _saved(lock)


@keys_bp.delete("/locks/<int:lock_id>")
@permission_required("locks", "manage", LABEL)
def delete_lock(lock_id: int):
    lock = db.session.get(SmartLock, lock_id)
    if lock is None:
        return api_error("NOT_FOUND", "No such lock.", 404)
    token = _token()
    for row in lock.access:
        if row.auth_id:
            try:
                nuki.remove_code(token, lock.smartlock_id, row.auth_id)
            except nuki.NukiError as exc:
                return api_error(
                    "NUKI_ERROR",
                    f"{exc} The lock is kept so its codes can be removed.",
                    502,
                )
    log_audit(
        get_current_member().id, "keys.lock.delete", "SmartLock", lock.id, lock.name
    )
    db.session.delete(lock)
    db.session.commit()
    return "", 204


@keys_bp.post("/locks/<int:lock_id>/sync")
@permission_required("locks", "manage", LABEL)
def sync_lock(lock_id: int):
    lock = db.session.get(SmartLock, lock_id)
    if lock is None:
        return api_error("NOT_FOUND", "No such lock.", 404)
    return _saved(lock)


@keys_bp.get("/locks/mine")
@require_member
def my_locks():
    member = get_current_member()
    out = []
    if not may_open(member):
        return jsonify(out)
    for lock in db.session.scalars(select(SmartLock).order_by(SmartLock.name)):
        if member.id not in allowed(lock):
            continue
        row = next((a for a in lock.access if a.member_id == member.id), None)
        code = (
            decrypt_code(row.code, PURPOSE)
            if lock.keypad and row and row.status == "active" and row.code
            else None
        )
        if code is None and not lock.app_open:
            continue
        out.append(
            {"id": lock.id, "name": lock.name, "code": code, "appOpen": lock.app_open}
        )
    return jsonify(out)


@keys_bp.post("/locks/<int:lock_id>/open")
@require_member
def open_lock(lock_id: int):
    member = get_current_member()
    lock = db.session.get(SmartLock, lock_id)
    if lock is None or not lock.app_open or member.id not in allowed(lock):
        return api_error("FORBIDDEN", "You may not open this door.", 403)
    try:
        nuki.unlock(_token(), lock.smartlock_id)
    except nuki.NukiError as exc:
        return api_error("NUKI_ERROR", str(exc), 502)
    db.session.add(
        CheckIn(member_id=member.id, place=lock.name[:120], by_id=member.id, at=_now())
    )
    db.session.commit()
    return jsonify({"opened": True})
