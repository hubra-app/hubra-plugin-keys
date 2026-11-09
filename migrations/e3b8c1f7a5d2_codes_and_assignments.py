"""keys.secret, keys.public and key_assignments

A key of the kind "code" keeps its code encrypted in keys.secret (the Codes
plugin's codes move in as these). A key is public or assigned to several
members and groups.

Revision ID: e3b8c1f7a5d2
Revises: d7a1c4e9b2f6
Create Date: 2026-11-09 12:00:00

"""

from alembic import op
import sqlalchemy as sa

from hubra.core.plugins.ops import columns, has_table

revision = "e3b8c1f7a5d2"
down_revision = "d7a1c4e9b2f6"
branch_labels = None
depends_on = None


def upgrade():
    have = columns("keys")
    with op.batch_alter_table("keys", schema=None) as batch_op:
        if "secret" not in have:
            batch_op.add_column(sa.Column("secret", sa.Text(), nullable=True))
        if "public" not in have:
            batch_op.add_column(
                sa.Column("public", sa.Boolean(), nullable=False, server_default=sa.false())
            )
    if not has_table("key_assignments"):
        op.create_table(
            "key_assignments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("key_id", sa.Integer(), nullable=False),
            sa.Column("member_id", sa.Integer(), nullable=True),
            sa.Column("group_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["key_id"], ["keys.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("key_id", "member_id", name="uq_key_assignment_member"),
            sa.UniqueConstraint("key_id", "group_id", name="uq_key_assignment_group"),
        )
        op.create_index("ix_key_assignments_key_id", "key_assignments", ["key_id"])


def downgrade():
    op.drop_index("ix_key_assignments_key_id", "key_assignments")
    op.drop_table("key_assignments")
    with op.batch_alter_table("keys", schema=None) as batch_op:
        batch_op.drop_column("public")
        batch_op.drop_column("secret")
