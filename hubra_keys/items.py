"""Each key is an inventory item of the type "Key".

Inventory lists, searches and shows the key with the club's other items;
Keys keeps what only a key has (number, kind, what it opens, deposit, who
holds it, the handover log) and is the one that changes its status. The two
stay in line through Inventory's contracts, never its code or tables:

- every change here goes to the item with ``inventory.items.save``
  (``push``), a deleted key deletes it with ``inventory.items.delete``;
- a key added or changed in Inventory comes back as ``inventory.item.saved``
  (``on_item_saved``): a new "Key" item gets its key here, a renamed one
  renames the key, and a status set by hand there is set back to the key's;
- a key item deleted in Inventory deletes the key (``on_item_deleted``);
- keys from before (and any whose item couldn't be made) get their item
  from the job ``keys-link-items`` (``link_missing``).
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from hubra.core.contracts import SYSTEM, ActionUnavailable, Refused, call, query
from hubra.core.extensions import db
from hubra.core.utils import log_audit

from .models import Key

log = logging.getLogger(__name__)

TYPE = "Key"
# A key's status as Inventory shows it. Handed out is "in use": a key isn't
# checked out with a due date like a tool.
STATUS_TO_ITEM = {
    "available": "available",
    "issued": "in_use",
    "lost": "lost",
    "retired": "retired",
}
# A key added in Inventory starts from the item's status where that means
# the same; "issued" needs a holder, so it is never taken from there.
ITEM_TO_STATUS = {"available": "available", "lost": "lost", "retired": "retired"}


def _fields(key: Key) -> dict:
    return {
        "name": key.label,
        "category": TYPE,
        "status": STATUS_TO_ITEM.get(key.status, "available"),
        "serial_number": key.number,
    }


def push(key: Key, actor_id: int | None = None) -> None:
    """Make or update the key's inventory item, in the caller's transaction."""
    fields = _fields(key)
    try:
        if key.item_id is not None:
            try:
                call(
                    "inventory.items.save",
                    item_id=key.item_id,
                    actor_id=actor_id,
                    actor=SYSTEM,
                    **fields,
                )
                return
            except Refused as exc:
                if exc.code != "NOT_FOUND":
                    raise
                key.item_id = None  # deleted under us: make a new one
        item = call("inventory.items.save", actor_id=actor_id, actor=SYSTEM, **fields)
    except ActionUnavailable:
        # Inventory is off or not loaded; the job links the key later.
        log.warning("keys: inventory unavailable, key %s not linked", key.id)
        return
    key.item_id = item["id"]
    db.session.flush()


def remove(key: Key, actor_id: int | None = None) -> None:
    """Delete the key's inventory item, if it has one."""
    if key.item_id is None:
        return
    try:
        call(
            "inventory.items.delete", item_id=key.item_id, actor_id=actor_id, actor=SYSTEM
        )
    except ActionUnavailable:
        log.warning("keys: inventory unavailable, item %s kept", key.item_id)


def link_missing(limit: int = 200) -> int:
    """Give keys without an inventory item one. Returns how many got one."""
    keys = db.session.scalars(
        select(Key).where(Key.item_id.is_(None)).order_by(Key.id).limit(limit)
    ).all()
    done = 0
    for key in keys:
        push(key)
        if key.item_id is not None:
            done += 1
    return done


def _key_for(item_id: int) -> Key | None:
    return db.session.scalar(select(Key).where(Key.item_id == item_id))


def _number_free(number: str | None, key_id: int | None) -> bool:
    if not number:
        return True
    clash = db.session.scalar(select(Key.id).where(Key.number == number))
    return clash is None or clash == key_id


def on_item_saved(tenant_id=None, item_id: int = 0, **_) -> None:
    """An item was added or changed in Inventory (or by ``push``).

    Reads the item as it is now rather than trusting the event, so an
    event that arrives late can't undo a newer change.
    """
    found = query("inventory.items.get", ids=[item_id], actor=SYSTEM)
    if not found:
        return
    item = found[0]
    key = _key_for(item_id)

    if item["category"] != TYPE:
        if key is None:
            return
        if key.status == "issued":
            # Someone holds it: it stays a key until it is taken back.
            push(key)
            return
        log_audit(None, "delete_key", "Key", key.id, f"{key.label} (no longer a key)")
        key.item_id = None
        db.session.delete(key)
        return

    number = (item.get("serial_number") or "").strip()[:100] or None
    if key is None:
        key = Key(
            label=item["name"][:120],
            number=number if _number_free(number, None) else None,
            kind="key",
            status=ITEM_TO_STATUS.get(item["status"], "available"),
            item_id=item_id,
        )
        db.session.add(key)
        db.session.flush()
        log_audit(None, "create_key", "Key", key.id, key.label)
    else:
        key.label = item["name"][:120]
        if number != key.number and _number_free(number, key.id):
            key.number = number
    db.session.flush()
    # The key says what its status is: put a status set by hand back, and a
    # number that is taken by another key.
    if item["status"] != STATUS_TO_ITEM.get(key.status) or (
        item.get("serial_number") or None
    ) != key.number:
        push(key)


def on_item_deleted(tenant_id=None, item_id: int = 0, **_) -> None:
    """A key's item was deleted in Inventory: the key and its log go too."""
    key = _key_for(item_id)
    if key is None:
        return
    log_audit(None, "delete_key", "Key", key.id, key.label)
    db.session.delete(key)
