"""Conversations: add subject + cleared_at; unique(user_id, subject).

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # subject is nullable so existing exam-session conversations keep NULL.
    # PostgreSQL UNIQUE treats NULLs as distinct, so multiple NULL rows are fine.
    op.add_column("conversations", sa.Column("subject", sa.String(100), nullable=True))
    op.add_column("conversations", sa.Column("cleared_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint(
        "uq_conversations_user_subject", "conversations", ["user_id", "subject"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_conversations_user_subject", "conversations", type_="unique")
    op.drop_column("conversations", "cleared_at")
    op.drop_column("conversations", "subject")
