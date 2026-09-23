"""
app/models/refresh_token.py
============================
SQLAlchemy model for the 'refresh_tokens' table.

HOW IT WORKS:
- On login, we generate an opaque random refresh token and store it here.
- On POST /auth/refresh, we look up the token row. If valid and not expired,
  we issue a new access token (and optionally rotate the refresh token).
- On POST /auth/logout, we DELETE the row — this immediately revokes the token.

WHY STORE IN DB (not JWT)?
  JWTs are stateless — you cannot "delete" a JWT. If a refresh JWT is stolen,
  an attacker can use it until it expires.
  A DB-stored opaque token can be deleted immediately on logout, giving us
  true session revocation.

SECURITY NOTES:
- Each user can have MULTIPLE refresh tokens (one per device/session).
- Tokens are hashed? No — they're already 512-bit random strings, which are
  computationally infeasible to brute-force. Hashing adds little value here
  and complicates rotation. (For maximum security in high-risk apps, hash them.)
"""

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RefreshToken(Base):
    """
    Stores active refresh tokens for each user session.
    Deleting a row = logging out that session.
    """

    __tablename__ = "refresh_tokens"

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
        comment="The user this token belongs to",
    )

    token: Mapped[str] = mapped_column(
        String(256),
        unique=True,
        nullable=False,
        index=True,
        comment="The opaque refresh token string (128-char hex, 512-bit entropy)",
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When this refresh token expires",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this token was created (= login time)",
    )

    def __repr__(self) -> str:
        return f"<RefreshToken user_id={self.user_id} expires_at={self.expires_at}>"
