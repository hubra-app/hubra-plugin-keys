"""Keys: physical keys, cards and fobs, who holds them, and every handover.
Also the member card in the app, and checking members in with it."""

from hubra.core.modules import Blueprint, Module, NavItem
from hubra.core.modules.events import INVOICE_OVERDUE

module = Module(
    code="inventory.keys",
    name="Keys",
    description=(
        "Physical keys, cards and fobs: who holds which, with a handover log. "
        "Member cards with a QR code to check members in"
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
    ),
    events={INVOICE_OVERDUE: "hubra_keys.hooks:on_invoice_overdue"},
    tables=("keys", "key_handovers", "member_cards", "checkins"),
)
