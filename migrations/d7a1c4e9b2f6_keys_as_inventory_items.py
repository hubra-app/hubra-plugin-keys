"""keys.item_id: each key is an inventory item of the type "Key"

The item itself is made through Inventory's contract (inventory.items.save),
not here: a plugin doesn't write another plugin's tables. Keys from before
get theirs from the job keys-link-items within a few minutes.

Revision ID: d7a1c4e9b2f6
Revises: b4e2d7f1a8c3
Create Date: 2026-11-09 10:00:00

"""

from alembic import op
import sqlalchemy as sa

from hubra.core.plugins.ops import columns


# revision identifiers, used by Alembic.
revision = "d7a1c4e9b2f6"
down_revision = "b4e2d7f1a8c3"
branch_labels = None
depends_on = None


def upgrade():
    if "item_id" in columns("keys"):
        return
    with op.batch_alter_table("keys", schema=None) as batch_op:
        batch_op.add_column(sa.Column("item_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_keys_item_id", ["item_id"], unique=True)


def downgrade():
    with op.batch_alter_table("keys", schema=None) as batch_op:
        batch_op.drop_index("ix_keys_item_id")
        batch_op.drop_column("item_id")
