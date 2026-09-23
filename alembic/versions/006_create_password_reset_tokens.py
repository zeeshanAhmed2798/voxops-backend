"""Create password_reset_tokens table

Revision ID: 005
Revises: 004
Create Date: 2026-09-23

Stores one-time password reset tokens for the forgot/reset password flow.
Tokens expire after 1 hour and are single-use (is_used flag).

To apply:    alembic upgrade head
To roll back: alembic downgrade -1
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "006"
down_revision = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the password_reset_tokens table."""
    op.create_table(
        "password_reset_tokens",

        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "token",
            sa.String(128),
            nullable=False,
            comment="URL-safe random token sent to the user's email",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "is_used",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Marks token as consumed — prevents replay attacks",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_unique_constraint(
        "uq_password_reset_tokens_token", "password_reset_tokens", ["token"]
    )
    op.create_index(
        "ix_password_reset_tokens_token", "password_reset_tokens", ["token"], unique=True
    )
    op.create_index(
        "ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"]
    )


def downgrade() -> None:
    """Drop the password_reset_tokens table."""
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_token", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
