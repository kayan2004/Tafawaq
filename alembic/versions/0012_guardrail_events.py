"""Add guardrail_events table for the guardrails redesign; drop messages.guardrails_score
(confirmed dead since baseline — never written anywhere — now superseded by this table).

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guardrail_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("conversation_id", UUID(as_uuid=True), sa.ForeignKey("conversations.id"), nullable=True),
        sa.Column(
            "source",
            sa.Enum("chat", "exam_generation", name="guardrailsource"),
            nullable=False,
        ),
        sa.Column(
            "direction",
            sa.Enum("input", "output", name="guardraildirection"),
            nullable=False,
        ),
        sa.Column(
            "category",
            sa.Enum("off_topic", "prompt_injection", "harmful_content", name="guardrailcategory"),
            nullable=True,
        ),
        sa.Column(
            "level",
            sa.Enum("warned", "blocked", name="guardraillevel"),
            nullable=False,
        ),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("text_hash", sa.String(64), nullable=False),
        sa.Column("text_preview", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_guardrail_events_user_id", "guardrail_events", ["user_id"])
    op.create_index("ix_guardrail_events_created_at", "guardrail_events", ["created_at"])

    op.drop_column("messages", "guardrails_score")


def downgrade() -> None:
    op.add_column("messages", sa.Column("guardrails_score", sa.Float(), nullable=True))

    op.drop_index("ix_guardrail_events_created_at", table_name="guardrail_events")
    op.drop_index("ix_guardrail_events_user_id", table_name="guardrail_events")
    op.drop_table("guardrail_events")
    op.execute("DROP TYPE IF EXISTS guardraillevel")
    op.execute("DROP TYPE IF EXISTS guardrailcategory")
    op.execute("DROP TYPE IF EXISTS guardraildirection")
    op.execute("DROP TYPE IF EXISTS guardrailsource")
