"""keys.code_id no longer has a foreign key to codes

Codes moved out of Hubra into its own plugin, so Keys must work in a club
where the codes table does not exist. Databases that created keys while
Codes was built into Hubra have the constraint; it is dropped here.

Revision ID: 5b1e0c0de1f2
Revises: 030760da547b
Create Date: 2026-11-02 14:00:00

"""

from alembic import op
import sqlalchemy as sa

from hubra.core.plugins.ops import current_schema, has_table


# revision identifiers, used by Alembic.
revision = "5b1e0c0de1f2"
down_revision = "030760da547b"
branch_labels = None
depends_on = None


def upgrade():
    if not has_table("keys"):
        return
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return  # SQLite (tests) does not enforce it without PRAGMA; nothing to do
    schema = current_schema()
    for fk in sa.inspect(bind).get_foreign_keys("keys", schema=schema):
        if fk["referred_table"] == "codes" and fk.get("name"):
            op.drop_constraint(fk["name"], "keys", type_="foreignkey", schema=schema)


def downgrade():
    pass  # the constraint is not put back: Codes may not be installed
