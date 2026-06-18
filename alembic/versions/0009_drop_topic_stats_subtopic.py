"""Drop dead topic_stats.subtopic column — never read by any query.

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("topic_stats", "subtopic")


def downgrade() -> None:
    op.add_column(
        "topic_stats",
        sa.Column("subtopic", sa.String(length=100), nullable=False, server_default=""),
    )
