"""conversations: drop unique(user_id, subject), add title.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF EXISTS: the unique constraint was absent on some installations where
    # migration 0004 ran but the constraint creation was not committed.
    op.execute("ALTER TABLE conversations DROP CONSTRAINT IF EXISTS uq_conversations_user_subject")
    op.add_column("conversations", sa.Column("title", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("conversations", "title")
    op.create_unique_constraint(
        "uq_conversations_user_subject", "conversations", ["user_id", "subject"]
    )
