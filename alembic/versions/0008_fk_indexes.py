"""Add indexes on foreign key columns used in WHERE/ORDER BY clauses.

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-18
"""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_index(
        "ix_messages_conversation_id_created_at", "messages", ["conversation_id", "created_at"]
    )
    op.create_index("ix_exam_sessions_user_id", "exam_sessions", ["user_id"])
    op.create_index("ix_exam_results_user_id", "exam_results", ["user_id"])
    op.create_index("ix_exam_results_session_id", "exam_results", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_exam_results_session_id", table_name="exam_results")
    op.drop_index("ix_exam_results_user_id", table_name="exam_results")
    op.drop_index("ix_exam_sessions_user_id", table_name="exam_sessions")
    op.drop_index("ix_messages_conversation_id_created_at", table_name="messages")
    op.drop_index("ix_conversations_user_id", table_name="conversations")
