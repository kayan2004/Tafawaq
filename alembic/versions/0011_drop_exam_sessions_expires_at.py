"""Drop exam_sessions.expires_at — hardcoded to a 2099 sentinel, never read by
any query. Exam sessions are permanent in Postgres, same as exam_results.

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("exam_sessions", "expires_at")


def downgrade() -> None:
    op.add_column(
        "exam_sessions",
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default="2099-12-31T00:00:00+00:00",
        ),
    )
