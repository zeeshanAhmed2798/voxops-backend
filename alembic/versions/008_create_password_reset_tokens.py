"""Create password_reset_tokens table

Revision ID: 006
Revises: 005
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


revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
            comment="Unique record identifier",
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            comment="The user requesting a password reset",
        ),
        sa.Column(
            "token",
            sa.String(128),
            nullable=False,
            unique=True,
            comment="URL-safe random token sent to user's email",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When this token expires (typically now + 1 hour)",
        ),
        sa.Column(
            "is_used",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="True once the token has been used — prevents replay attacks",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="When the reset was requested",
        ),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_token", "password_reset_tokens", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_token", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
