"""Official exams table for Lebanese GS past exams.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "official_exams",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("session_label", sa.String(50), nullable=False),
        sa.Column("exam_content", JSONB(), nullable=False),
        sa.Column("answer_key", JSONB(), nullable=False),
        sa.Column("pdf_key", sa.String(200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("year", "session_label", name="uq_official_exams_year_session"),
    )


def downgrade() -> None:
    op.drop_table("official_exams")
