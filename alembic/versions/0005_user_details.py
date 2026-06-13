"""Add user_details table for profile (language, grade, branch).

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_details",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "language",
            sa.Enum("en", "fr", name="language"),
            nullable=False,
        ),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column(
            "branch",
            sa.Enum("general_science", "life_science", name="branch"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", name="uq_user_details_user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_details")
    op.execute("DROP TYPE IF EXISTS branch")
    op.execute("DROP TYPE IF EXISTS language")
