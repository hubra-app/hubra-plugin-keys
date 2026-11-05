"""Keys: physical keys, cards and fobs, who holds them, and every handover.
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
    schedule=(Schedule("keys-sync-locks", "hubra_keys.tasks.sync_locks", 900.0),),
    events={INVOICE_OVERDUE: "hubra_keys.hooks:on_invoice_overdue"},
    tables=(
        "keys",
        "key_handovers",
        "member_cards",
        "checkins",
        "smart_locks",
        "lock_access",
    ),
)
