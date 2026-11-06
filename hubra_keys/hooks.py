"""Event handlers for the keys module."""

from __future__ import annotations

from sqlalchemy import select

from hubra.core.extensions import db
from hubra.core.models.member import Member

from .models import Key


def on_invoice_overdue(tenant_id, member_id: int, invoice_id: int, **_):
    """Tell the key managers when someone with an overdue invoice holds keys.

    A physical key cannot be switched off like an RFID tag, so the club
    decides whether to ask for it back.
    """
    from hubra.core.notifications.services import create_notification
    from hubra.core.permissions import member_has_permission

    keys = db.session.scalars(
        select(Key).where(Key.holder_id == member_id, Key.status == "issued")
    ).all()
    if not keys:
        return
    member = db.session.get(Member, member_id)
    labels = ", ".join(k.label for k in keys)
    managers = [
        m
        for m in db.session.scalars(
            select(Member).where(Member.archived_at.is_(None))
        ).all()
        if member_has_permission(m, "keys.keys.manage")
    ]
    for manager in managers:
        create_notification(
            manager.id,
            kind="warning",
            title="Overdue invoice, keys issued",
            msg=f"{member.name if member else member_id} holds {labels}"[:255],
        )
