"""member_cards and checkins

Revision ID: 8c3f5a1d9e47
Revises: 5b1e0c0de1f2
Create Date: 2026-11-05 16:10:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8c3f5a1d9e47"
down_revision = "5b1e0c0de1f2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "member_cards",
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("member_id"),
        sa.UniqueConstraint("token"),
    )
    op.create_table(
        "checkins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=True),
        sa.Column("place", sa.String(length=120), nullable=True),
        sa.Column("by_id", sa.Integer(), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["club_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["by_id"], ["members.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("checkins", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_checkins_member_id"), ["member_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_checkins_event_id"), ["event_id"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_checkins_at"), ["at"], unique=False)


def downgrade():
    op.drop_table("checkins")
    op.drop_table("member_cards")
