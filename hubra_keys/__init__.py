"""Keys: physical keys, cards and fobs, who holds them, and every handover.
Each key is an inventory item of the type "Key" (hubra_keys.items).
Also the member card in the app, checking members in with it, and Nuki
smart locks whose keypad codes follow membership."""

from hubra.core.modules import Blueprint, Module, NavItem, Schedule, SettingField
from hubra.core.modules.events import INVOICE_OVERDUE

module = Module(
    code="inventory.keys",
    name="Keys",
    description=(
        "Physical keys, cards and fobs: who holds which, with a handover log. "
        "Member cards with a QR code to check members in. "
        "Nuki smart locks that follow membership"
    ),
    default_enabled=False,
    depends_on=("inventory",),
    blueprints=(
        Blueprint(
            "hubra_keys.routes",
            "keys_bp",
            "/api/v1/keys",
        ),
    ),
    nav=(
        NavItem(
            "/app/inventory/keys",
            "shell.nav.keys",
            "key",
            order=31,
            perms=("keys.keys.read",),
        ),
        NavItem(
            "/app/inventory/checkin",
            "shell.nav.checkin",
            "qrcode",
            order=32,
            perms=("keys.checkins.create",),
        ),
        NavItem(
            "/app/inventory/locks",
            "shell.nav.locks",
            "lock",
            order=33,
            perms=("keys.locks.manage",),
        ),
    ),
    settings=(
        SettingField(
            "nuki_token",
            "secret",
            label="Nuki API token",
            description="Nuki Web → API → API token, for the smart locks",
        ),
    ),
    tasks=("hubra_keys.tasks",),
    schedule=(
        Schedule("keys-sync-locks", "hubra_keys.tasks.sync_locks", 900.0),
        Schedule("keys-link-items", "hubra_keys.tasks.link_items", 300.0),
    ),
    events={
        INVOICE_OVERDUE: "hubra_keys.hooks:on_invoice_overdue",
        "inventory.item.saved": "hubra_keys.items:on_item_saved",
        "inventory.item.deleted": "hubra_keys.items:on_item_deleted",
    },
    # Each key is an inventory item of the type "Key" (hubra_keys.items).
    consumes={
        "inventory.items.get": ">=1,<2",
        "inventory.items.save": ">=1,<2",
        "inventory.items.delete": ">=1,<2",
        "inventory.item.saved": ">=1,<2",
        "inventory.item.deleted": ">=1,<2",
    },
    tables=(
        "keys",
        "key_handovers",
        "member_cards",
        "checkins",
        "smart_locks",
        "lock_access",
    ),
)
