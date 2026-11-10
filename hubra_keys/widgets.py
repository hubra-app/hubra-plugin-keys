"""Dashboard widgets of Keys (docs/dashboards.md in hubra-app/hubra).

inventory.keys.mine    list  keys and codes the viewer holds or may use (no code shown)
inventory.keys.issued  stat  how many keys are handed out, and how many are lost

They read as the viewing member.
"""

from __future__ import annotations

from sqlalchemy import func, select

from hubra.core.extensions import db

from .models import Key
from .services import keys_for


def _german(member) -> bool:
    return (getattr(member, "language", None) or "de").lower().startswith("de")


def _count(config: dict) -> int:
    try:
        return max(1, min(int(config.get("count") or 5), 20))
    except (TypeError, ValueError):
        return 5


def mine(ctx, config: dict) -> dict:
    """What the viewer holds first, then what they may use."""
    if ctx.actor is None:
        return {"items": [], "total": 0}
    keys = sorted(keys_for(ctx.actor), key=lambda k: (k.holder_id != ctx.actor.id, k.label))
    items = [
        {"label": k.label, "sub": " · ".join(p for p in (k.number, k.opens) if p) or None}
        for k in keys[: _count(config)]
    ]
    return {"items": items, "total": len(keys)}


def issued(ctx, config: dict) -> dict:
    """Keys handed out to someone, with the lost ones beside."""
    counts = dict(
        db.session.execute(
            select(Key.status, func.count())
            .where(Key.status.in_(("issued", "lost")))
            .group_by(Key.status)
        ).all()
    )
    lost = counts.get("lost", 0)
    sub = None
    if lost:
        sub = f"{lost} verloren" if _german(ctx.actor) else f"{lost} lost"
    return {"value": counts.get("issued", 0), "sub": sub, "path": "/app/inventory"}
