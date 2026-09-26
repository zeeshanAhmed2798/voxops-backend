"""Create refresh_tokens table

Revision ID: 005
Revises: 004
Create Date: 2026-09-23

Stores refresh tokens for JWT-based authentication.
Each token is linked to a user and expires after REFRESH_TOKEN_EXPIRE_DAYS.
Tokens are single-use — revoked on refresh, logout, or expiry.

To apply:    alembic upgrade head
To roll back: alembic downgrade -1
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
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
            comment="The user this token belongs to",
        ),
        sa.Column(
            "token",
            sa.String(256),
            nullable=False,
            unique=True,
            comment="The opaque refresh token string (128-char hex, 512-bit entropy)",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When this refresh token expires",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="When this token was created (= login time)",
        ),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token", "refresh_tokens", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_token", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
