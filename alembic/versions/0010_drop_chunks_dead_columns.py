"""Drop dead chunks columns — subtopic always '', page_start/page_end always NULL
since textbook content stopped being chunked/embedded (see RAG-removal commit).

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("chunks", "subtopic")
    op.drop_column("chunks", "page_start")
    op.drop_column("chunks", "page_end")


def downgrade() -> None:
    op.add_column(
        "chunks",
        sa.Column("subtopic", sa.String(length=100), nullable=False, server_default=""),
    )
    op.add_column("chunks", sa.Column("page_start", sa.Integer(), nullable=True))
    op.add_column("chunks", sa.Column("page_end", sa.Integer(), nullable=True))
