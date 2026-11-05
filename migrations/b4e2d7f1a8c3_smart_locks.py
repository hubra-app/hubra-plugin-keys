"""smart_locks and lock_access

Revision ID: b4e2d7f1a8c3
Revises: 8c3f5a1d9e47
Create Date: 2026-11-05 16:40:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b4e2d7f1a8c3"
down_revision = "8c3f5a1d9e47"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "smart_locks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("smartlock_id", sa.BigInteger(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=True),
        sa.Column("keypad", sa.Boolean(), nullable=False),
        sa.Column("app_open", sa.Boolean(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "lock_access",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lock_id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.Text(), nullable=True),
        sa.Column("auth_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error", sa.String(length=300), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lock_id"], ["smart_locks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lock_id", "member_id", name="uq_lock_access"),
    )


def downgrade():
    op.drop_table("lock_access")
    op.drop_table("smart_locks")
