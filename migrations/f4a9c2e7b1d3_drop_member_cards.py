"""drop member_cards: the club's own member cards are gone

Check-in scans the member badge (Hubra core). Old card codes could no
longer be renewed or revoked, so they no longer check anyone in.

Revision ID: f4a9c2e7b1d3
Revises: e3b8c1f7a5d2
Create Date: 2026-11-11 12:00:00

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f4a9c2e7b1d3"
down_revision = "e3b8c1f7a5d2"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DROP TABLE IF EXISTS member_cards")


def downgrade():
    op.create_table(
        "member_cards",
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("member_id"),
        sa.UniqueConstraint("token"),
    )
