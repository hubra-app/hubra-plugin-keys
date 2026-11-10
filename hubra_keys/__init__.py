"""Keys: physical keys, cards and fobs, who holds them, and every handover.
Each key is an inventory item of the type "Key" (hubra_keys.items).
Also the member card in the app, checking members in with it, and Nuki
smart locks whose keypad codes follow membership."""

from hubra.core.contracts import WidgetField, widget_contract
from hubra.core.modules import Blueprint, Module, NavItem, Schedule, SettingField
from hubra.core.modules.events import INVOICE_OVERDUE

module = Module(
    code="inventory.keys",
    # Access the standard roles get when a club first switches it on
    # (docs/roles.md in hubra-app/hubra).
    role_defaults={"board": "view"},
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
        # Check-in scans the member badge (Hubra core).
        "members.badge.lookup": ">=1,<2",
        "inventory.items.get": ">=1,<2",
        "inventory.items.save": ">=1,<2",
        "inventory.items.delete": ">=1,<2",
        "inventory.items.history.add": ">=1,<2",
        # Optional: the Codes plugin's codes move in as keys of kind "code".
        "codes.codes.export": ">=1,<2",
        "inventory.item.saved": ">=1,<2",
        "inventory.item.deleted": ">=1,<2",
    },
    # Key rotation re-encrypts these (FERNET_KEY / club keys).
    encrypted_columns=(
        ("keys", "id", "secret", " AND secret IS NOT NULL"),
        ("lock_access", "id", "code", " AND code IS NOT NULL"),
    ),
    tables=(
        "keys",
        "key_assignments",
        "key_handovers",
        "member_cards",
        "checkins",
        "smart_locks",
        "lock_access",
    ),
    # Dashboard widgets (hubra_keys/widgets.py).
    provides=(
        widget_contract(
            "inventory.keys.mine",
            "hubra_keys.widgets:mine",
            label="keys.widget.mine",
            description="keys.widget.mineHint",
            size="s",
            view="list",
            fields=(WidgetField("count", "keys.widget.count", "number", 5),),
        ),
        widget_contract(
            "inventory.keys.issued",
            "hubra_keys.widgets:issued",
            label="keys.widget.issued",
            description="keys.widget.issuedHint",
            size="s",
            view="stat",
            perm="keys.keys.read",
        ),
    ),
)
