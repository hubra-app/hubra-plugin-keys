"""Celery tasks: keep the keypad codes on the club's smart locks in line,
and give keys without an inventory item one."""

from __future__ import annotations

from hubra.core.modules import per_tenant_job
from hubra.core.tasks import celery_app


@celery_app.task(name="hubra_keys.tasks.sync_locks")
@per_tenant_job("inventory.keys")
def sync_locks() -> dict:
    from hubra.core.extensions import db

    from .locks import sync_all

    done = sync_all()
    db.session.commit()
    return done


@celery_app.task(name="hubra_keys.tasks.link_items")
@per_tenant_job("inventory.keys")
def link_items() -> dict:
    """Keys from before get their inventory item, and the Codes plugin's
    codes come in as keys of the kind "code"."""
    from hubra.core.extensions import db

    from .items import link_missing, take_over_codes

    linked = link_missing()
    codes = take_over_codes()
    db.session.commit()
    return {"linked": linked, "codes": codes}
