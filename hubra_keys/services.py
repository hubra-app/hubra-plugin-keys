"""Key service: CRUD plus issue, return, lost and found with a handover log."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from hubra.core.utils import log_audit
from hubra.core.errors import raise_error
from hubra.core.extensions import db
from hubra.core.models.member import Member

from . import items
from .models import KEY_KINDS, KEY_STATUSES, Key, KeyAssignment

_EDITABLE = ("label", "number", "kind", "opens", "deposit_chf", "notes", "public")
SECRET_PURPOSE = "keys.secret"
# Longest text each field takes (the column sizes; notes and the code are
# capped so one request can't store megabytes).
_MAX_LEN = {"label": 120, "number": 100, "opens": 255, "notes": 10000}
_MAX_CODE = 200
# deposit_chf is NUMERIC(10, 2).
_MAX_DEPOSIT = Decimal("99999999.99")


def key_to_dict(key: Key, with_history: bool = False) -> dict:
    """A key as the app sees it. Its history is the item's in Inventory
    (``with_history`` is kept for older callers and adds nothing)."""
    data = {
        "id": key.id,
        "label": key.label,
        "number": key.number,
        "kind": key.kind,
        "opens": key.opens,
        "status": key.status,
        "holderId": key.holder_id,
        "holderName": key.holder.name if key.holder else None,
        "depositChf": str(key.deposit_chf) if key.deposit_chf is not None else None,
        "codeId": key.code_id,
        "hasCode": bool(key.secret),
        "public": bool(key.public),
        "members": [
            {"id": a.member_id, "name": a.member.name if a.member else None}
            for a in key.assignments
            if a.member_id is not None
        ],
        "groups": [
            {"id": a.group_id, "name": a.group.name if a.group else None}
            for a in key.assignments
            if a.group_id is not None
        ],
        "itemId": key.item_id,
        "notes": key.notes,
        "updatedAt": key.updated_at.isoformat() if key.updated_at else None,
    }
    return data


def _clean(data: dict, partial: bool) -> dict:
    out = {k: data[k] for k in _EDITABLE if k in data}
    for k, most in _MAX_LEN.items():
        if out.get(k) is not None and not isinstance(out[k], str):
            raise_error(400, "VALIDATION_ERROR", f"{k} must be text")
        if out.get(k) is not None and len(out[k].strip()) > most:
            raise_error(400, "VALIDATION_ERROR", f"{k} can be up to {most} characters")
    if "public" in out and not isinstance(out["public"], bool):
        raise_error(400, "VALIDATION_ERROR", "public must be true or false")
    if not partial and not (data.get("label") or "").strip():
        raise_error(400, "VALIDATION_ERROR", "label is required")
    if "label" in out:
        out["label"] = (out["label"] or "").strip()
        if not out["label"]:
            raise_error(400, "VALIDATION_ERROR", "label cannot be empty")
    if "kind" in out and out["kind"] not in KEY_KINDS:
        raise_error(400, "VALIDATION_ERROR", f"kind must be one of {KEY_KINDS}")
    if "number" in out:
        out["number"] = (out["number"] or "").strip() or None
    if out.get("deposit_chf") not in (None, ""):
        try:
            out["deposit_chf"] = Decimal(str(out["deposit_chf"]))
        except InvalidOperation:
            raise_error(400, "VALIDATION_ERROR", "deposit_chf must be a number")
        if not out["deposit_chf"].is_finite() or not (
            0 <= out["deposit_chf"] <= _MAX_DEPOSIT
        ):
            raise_error(400, "VALIDATION_ERROR", "deposit_chf must be a number")
    elif "deposit_chf" in out:
        out["deposit_chf"] = None
    return out


def _ids(data: dict, field: str) -> list[int] | None:
    if field not in data:
        return None
    raw = data[field]
    if not isinstance(raw, list) or not all(
        isinstance(i, int) and not isinstance(i, bool) for i in raw
    ):
        raise_error(400, "VALIDATION_ERROR", f"{field} must be a list of ids")
    return list(dict.fromkeys(raw))


def _replace(key: Key, field: str, ids: list[int]) -> None:
    """Assign the key to exactly *ids* (members or groups): keep the rows
    that stay, add the new ones, drop the rest."""
    keep = [a for a in key.assignments if getattr(a, field) is None or getattr(a, field) in ids]
    have = {getattr(a, field) for a in keep}
    key.assignments = keep + [KeyAssignment(**{field: i}) for i in ids if i not in have]


def _apply_extras(key: Key, data: dict) -> None:
    """The code (of a code key, or one that goes with a key), and who the
    key is assigned to."""
    from hubra.core.crypto import encrypt_code
    from hubra.core.models.group import Group

    if "code" in data:
        code = data["code"]
        if code is not None and not isinstance(code, str):
            raise_error(400, "VALIDATION_ERROR", "code must be text")
        code = (code or "").strip()
        if len(code) > _MAX_CODE:
            raise_error(400, "VALIDATION_ERROR", f"code can be up to {_MAX_CODE} characters")
        key.secret = encrypt_code(code, SECRET_PURPOSE) if code else None
    member_ids = _ids(data, "member_ids")
    group_ids = _ids(data, "group_ids")
    if member_ids is not None:
        for mid in member_ids:
            m = db.session.get(Member, mid)
            if m is None or m.archived_at is not None:
                raise_error(404, "NOT_FOUND", f"Member {mid} not found")
        _replace(key, "member_id", member_ids)
    if group_ids is not None:
        for gid in group_ids:
            if db.session.get(Group, gid) is None:
                raise_error(404, "NOT_FOUND", f"Group {gid} not found")
        _replace(key, "group_id", group_ids)


def plain_code(key: Key) -> str | None:
    """The key's code in clear text; "" when it no longer opens."""
    from cryptography.fernet import InvalidToken

    from hubra.core.crypto import decrypt_code

    if not key.secret:
        return None
    try:
        return decrypt_code(key.secret, SECRET_PURPOSE)
    except InvalidToken:
        return ""


def keys_for(member: Member) -> list[Key]:
    """Keys the member holds, may use (public) or is assigned to, directly
    or through a group. Retired ones left out."""
    from sqlalchemy import or_

    from hubra.core.models.member import member_groups

    my_groups = select(member_groups.c.group_id).where(
        member_groups.c.member_id == member.id
    )
    assigned = select(KeyAssignment.key_id).where(
        or_(KeyAssignment.member_id == member.id, KeyAssignment.group_id.in_(my_groups))
    )
    return list(
        db.session.scalars(
            select(Key)
            .where(Key.status != "retired")
            .where(or_(Key.holder_id == member.id, Key.public.is_(True), Key.id.in_(assigned)))
            .order_by(Key.label)
        ).all()
    )


def _check_number_free(number: str | None, key_id: int | None = None) -> None:
    if not number:
        return
    clash = db.session.scalar(select(Key).where(Key.number == number))
    if clash is not None and clash.id != key_id:
        raise_error(409, "CONFLICT", f"Key number {number} is already used")


class KeyService:
    @staticmethod
    def list(status: str | None = None, holder_id: int | None = None) -> list[Key]:
        stmt = select(Key).options(selectinload(Key.holder)).order_by(Key.label)
        if status:
            if status not in KEY_STATUSES:
                raise_error(400, "VALIDATION_ERROR", f"Unknown status {status}")
            stmt = stmt.where(Key.status == status)
        if holder_id is not None:
            stmt = stmt.where(Key.holder_id == holder_id)
        return list(db.session.scalars(stmt).all())

    @staticmethod
    def get(key_id: int) -> Key:
        key = db.session.get(Key, key_id)
        if key is None:
            raise_error(404, "NOT_FOUND", f"Key {key_id} not found")
        return key

    @staticmethod
    def create(data: dict, actor_id: int | None) -> Key:
        values = _clean(data, partial=False)
        _check_number_free(values.get("number"))
        key = Key(**values)
        db.session.add(key)
        _apply_extras(key, data)
        db.session.flush()
        log_audit(actor_id, "create_key", "Key", key.id, key.label)
        items.push(key, actor_id)
        return key

    @staticmethod
    def update(key_id: int, data: dict, actor_id: int | None) -> Key:
        key = KeyService.get(key_id)
        values = _clean(data, partial=True)
        if "number" in values:
            _check_number_free(values["number"], key.id)
        for field, value in values.items():
            setattr(key, field, value)
        _apply_extras(key, data)
        db.session.flush()
        log_audit(actor_id, "update_key", "Key", key.id, key.label)
        items.push(key, actor_id)
        return key

    @staticmethod
    def delete(key_id: int, actor_id: int | None) -> None:
        key = KeyService.get(key_id)
        if key.status == "issued":
            raise_error(409, "CONFLICT", "Take the key back before deleting it")
        log_audit(actor_id, "delete_key", "Key", key.id, key.label)
        items.remove(key, actor_id)
        db.session.delete(key)
        db.session.flush()

    # ── Handovers ──────────────────────────────────────────────────────────

    @staticmethod
    def _log(key: Key, action: str, member_id, actor_id, note) -> None:
        """Into the history of the key's item in Inventory."""
        items.record(key, action, member_id, actor_id, note)

    @staticmethod
    def issue(key_id: int, member_id: int, actor_id: int | None, note=None) -> Key:
        key = KeyService.get(key_id)
        if key.kind == "code":
            raise_error(409, "CODE_ASSIGNED", "A code isn't handed out: assign it instead")
        if key.status != "available":
            raise_error(409, "CONFLICT", f"Key is {key.status}, not available")
        member = db.session.get(Member, member_id)
        if member is None or member.archived_at is not None:
            raise_error(404, "NOT_FOUND", f"Member {member_id} not found")
        key.status = "issued"
        key.holder_id = member_id
        KeyService._log(key, "issue", member_id, actor_id, note)
        log_audit(actor_id, "issue_key", "Key", key.id, f"{key.label} → {member.name}")
        db.session.flush()
        items.push(key, actor_id)
        return key

    @staticmethod
    def take_back(key_id: int, actor_id: int | None, note=None) -> Key:
        key = KeyService.get(key_id)
        if key.status != "issued":
            raise_error(409, "CONFLICT", "Key is not issued")
        KeyService._log(key, "return", key.holder_id, actor_id, note)
        log_audit(actor_id, "return_key", "Key", key.id, key.label)
        key.status = "available"
        key.holder_id = None
        db.session.flush()
        items.push(key, actor_id)
        return key

    @staticmethod
    def mark_lost(key_id: int, actor_id: int | None, note=None) -> Key:
        key = KeyService.get(key_id)
        if key.status in ("lost", "retired"):
            raise_error(409, "CONFLICT", f"Key is already {key.status}")
        KeyService._log(key, "lost", key.holder_id, actor_id, note)
        log_audit(actor_id, "lose_key", "Key", key.id, key.label)
        key.status = "lost"
        db.session.flush()
        items.push(key, actor_id)
        return key

    @staticmethod
    def mark_found(key_id: int, actor_id: int | None, note=None) -> Key:
        key = KeyService.get(key_id)
        if key.status != "lost":
            raise_error(409, "CONFLICT", "Key is not lost")
        KeyService._log(key, "found", None, actor_id, note)
        log_audit(actor_id, "find_key", "Key", key.id, key.label)
        key.status = "available"
        key.holder_id = None
        db.session.flush()
        items.push(key, actor_id)
        return key

    @staticmethod
    def retire(key_id: int, actor_id: int | None, note=None) -> Key:
        key = KeyService.get(key_id)
        if key.status == "issued":
            raise_error(409, "CONFLICT", "Take the key back before retiring it")
        KeyService._log(key, "retire", None, actor_id, note)
        key.status = "retired"
        db.session.flush()
        items.push(key, actor_id)
        return key
