"""Keys blueprint: /api/v1/keys."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from sqlalchemy import select

from hubra.core.auth.helpers import get_current_member
from hubra.core.permissions import permission_required, require_member
from hubra.core.errors import api_error
from hubra.core.extensions import db

from .models import Key
from .services import KeyService, key_to_dict, keys_for, plain_code

keys_bp = Blueprint("keys_bp", __name__)


def _body() -> dict:
    return request.get_json(silent=True) or {}


def _done(key, status=200):
    db.session.commit()
    return jsonify(key_to_dict(key, with_history=True)), status


@keys_bp.get("/")
@permission_required("keys", "read", "View keys")
def list_keys():
    holder = request.args.get("holder_id", type=int)
    keys = KeyService.list(status=request.args.get("status"), holder_id=holder)
    return jsonify([key_to_dict(k) for k in keys]), 200


@keys_bp.get("/mine")
@require_member
def my_keys():
    """Keys and codes the signed-in member holds, may use (public) or is
    assigned to (directly or through a group); no permission needed. A
    code, or a key with a code, comes with the code itself."""
    me = get_current_member()
    # The member's view: no manager notes, no import marker, no other people.
    hidden = ("notes", "codeId", "holderId", "holderName", "members", "groups", "itemId")
    out = []
    for key in keys_for(me):
        row = {k: v for k, v in key_to_dict(key).items() if k not in hidden}
        row["mine"] = key.holder_id == me.id
        # A code key's code, or the code that goes with a key (a key safe,
        # the lock's combination).
        if key.secret:
            row["code"] = plain_code(key)
        out.append(row)
    return jsonify(out), 200


@keys_bp.get("/options")
@permission_required("keys", "read", "View keys")
def key_options():
    """The groups a key can be assigned to."""
    from hubra.core.models.group import Group

    groups = db.session.scalars(select(Group).order_by(Group.name)).all()
    return jsonify({"groups": [{"id": g.id, "name": g.name} for g in groups]}), 200


@keys_bp.get("/<int:key_id>/code")
@permission_required("keys", "read", "View keys")
def reveal_code(key_id: int):
    """A code key's code, for the managers; each look is in the audit log."""
    from hubra.core.utils import log_audit

    key = KeyService.get(key_id)
    log_audit(get_current_member().id, "reveal_code", "Key", key.id, key.label)
    db.session.commit()
    return jsonify({"code": plain_code(key)}), 200


@keys_bp.get("/<int:key_id>")
@permission_required("keys", "read", "View keys")
def get_key(key_id: int):
    return jsonify(key_to_dict(KeyService.get(key_id), with_history=True)), 200


@keys_bp.get("/by-item/<int:item_id>")
@permission_required("keys", "read", "View keys")
def get_key_by_item(item_id: int):
    """The key behind an inventory item, for the key panel on its page."""
    key = db.session.scalar(select(Key).where(Key.item_id == item_id))
    if key is None:
        return api_error("NOT_FOUND", f"No key for inventory item {item_id}", 404)
    return jsonify(key_to_dict(key, with_history=True)), 200


@keys_bp.post("/")
@permission_required("keys", "manage", "Manage keys")
def create_key():
    return _done(KeyService.create(_body(), get_current_member().id), 201)


@keys_bp.patch("/<int:key_id>")
@permission_required("keys", "manage", "Manage keys")
def update_key(key_id: int):
    return _done(KeyService.update(key_id, _body(), get_current_member().id))


@keys_bp.delete("/<int:key_id>")
@permission_required("keys", "manage", "Manage keys")
def delete_key(key_id: int):
    KeyService.delete(key_id, get_current_member().id)
    db.session.commit()
    return "", 204


@keys_bp.post("/<int:key_id>/issue")
@permission_required("keys", "manage", "Manage keys")
def issue_key(key_id: int):
    body = _body()
    if not isinstance(body.get("member_id"), int):
        return api_error("VALIDATION_ERROR", "member_id is required", 400)
    key = KeyService.issue(
        key_id, body["member_id"], get_current_member().id, body.get("note")
    )
    return _done(key)


@keys_bp.post("/<int:key_id>/return")
@permission_required("keys", "manage", "Manage keys")
def return_key(key_id: int):
    return _done(
        KeyService.take_back(key_id, get_current_member().id, _body().get("note"))
    )


@keys_bp.post("/<int:key_id>/lost")
@permission_required("keys", "manage", "Manage keys")
def lose_key(key_id: int):
    return _done(
        KeyService.mark_lost(key_id, get_current_member().id, _body().get("note"))
    )


@keys_bp.post("/<int:key_id>/found")
@permission_required("keys", "manage", "Manage keys")
def find_key(key_id: int):
    return _done(
        KeyService.mark_found(key_id, get_current_member().id, _body().get("note"))
    )


@keys_bp.post("/<int:key_id>/retire")
@permission_required("keys", "manage", "Manage keys")
def retire_key(key_id: int):
    return _done(
        KeyService.retire(key_id, get_current_member().id, _body().get("note"))
    )


from . import checkin, locks  # noqa: E402,F401  (register their routes)
