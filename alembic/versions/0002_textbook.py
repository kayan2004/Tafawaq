"""Textbook ingestion schema: textbook_pages table + chunks extension.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "textbook_pages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("page_number", sa.Integer(), unique=True, nullable=False),
        sa.Column("chapter", sa.String(), nullable=False),
        sa.Column("section", sa.String(), nullable=False),
        sa.Column("page_type", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    # New nullable columns for textbook chunk page range tracking.
    # NULL for existing past-exam / answer-key chunks.
    op.add_column("chunks", sa.Column("page_start", sa.Integer(), nullable=True))
    op.add_column("chunks", sa.Column("page_end", sa.Integer(), nullable=True))

    # Textbook chunks have no year/session/exercise_id/question_type/marks —
    # relax NOT NULL so the shared chunks table can hold both source types.
    op.alter_column("chunks", "year", existing_type=sa.Integer(), nullable=True)
    op.alter_column("chunks", "session", existing_type=sa.Integer(), nullable=True)
    op.alter_column("chunks", "exercise_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column(
        "chunks",
        "question_type",
        existing_type=sa.Enum("proof", "calculation", "mcq", "sketch", name="questiontype"),
        nullable=True,
    )
    op.alter_column("chunks", "marks", existing_type=sa.Float(), nullable=True)


def downgrade() -> None:
    # Remove textbook rows before restoring NOT NULL constraints.
    op.execute("DELETE FROM chunks WHERE source_type LIKE 'textbook_%'")

    op.alter_column("chunks", "marks", existing_type=sa.Float(), nullable=False)
    op.alter_column(
        "chunks",
        "question_type",
        existing_type=sa.Enum("proof", "calculation", "mcq", "sketch", name="questiontype"),
        nullable=False,
    )
    op.alter_column("chunks", "exercise_id", existing_type=sa.Integer(), nullable=False)
    op.alter_column("chunks", "session", existing_type=sa.Integer(), nullable=False)
    op.alter_column("chunks", "year", existing_type=sa.Integer(), nullable=False)

    op.drop_column("chunks", "page_end")
    op.drop_column("chunks", "page_start")
    op.drop_table("textbook_pages")
