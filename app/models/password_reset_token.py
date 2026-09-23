"""
app/models/password_reset_token.py
====================================
SQLAlchemy model for the 'password_reset_tokens' table.

FLOW:
1. User calls POST /auth/forgot-password with their email.
2. We generate a secure random token, save it here with a 1-hour expiry,
   and log/print it (simulating an email send).
3. User calls POST /auth/reset-password with the token + new password.
4. We look up the token, check it's not expired and not already used,
   then set the new password and mark the token as used.

SECURITY NOTES:
- Tokens expire after 1 hour (RESET_TOKEN_EXPIRE_MINUTES = 60).
- Tokens are single-use — is_used prevents replay attacks.
- We use a URL-safe random string (not a JWT) so the token can be
  embedded directly in a reset link URL.
"""

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Boolean, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PasswordResetToken(Base):
    """
    One-time tokens for the password reset flow.
    """

    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique record identifier",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="The user requesting a password reset",
    )

    token: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
        comment="URL-safe random token sent to the user's email",
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When this token expires (typically now + 1 hour)",
    )

    is_used: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="True once the token has been used — prevents replay attacks",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When the reset was requested",
    )

    def __repr__(self) -> str:
        return f"<PasswordResetToken user_id={self.user_id} is_used={self.is_used}>"
