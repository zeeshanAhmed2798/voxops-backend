"""
app/models/invite_token.py
===========================
SQLAlchemy model for the 'invite_tokens' table.

INVITE MEMBER FLOW:
1. An ORG_ADMIN calls POST /auth/invite-member with the invitee's email + role.
2. We generate a secure random token, save it here with a 48-hour expiry,
   and log/print it (simulating an invite email).
3. The invitee opens the invite link (frontend) and calls
   POST /auth/register-member with: token + their name + chosen password.
4. We validate the token (not expired, not used, email matches),
   create the User, and mark the token as used.

SECURITY NOTES:
- Tokens expire after 48 hours.
- Tokens are single-use (is_used flag).
- The invite is tied to a specific email address — another person cannot
  use the same token to register with a different email.
- Only ORG_ADMIN can generate invite tokens (enforced in the router).
"""

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Boolean, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InviteToken(Base):
    """
    One-time tokens that allow a specific email address to join an organization.
    """

    __tablename__ = "invite_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique record identifier",
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Which organization the invitee is being added to",
    )

    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        index=True,
        comment="The email address this invite was sent to — must match on registration",
    )

    token: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        index=True,
        comment="URL-safe random token sent to the invitee",
    )

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="EMPLOYEE",
        comment="The role the invitee will receive upon registration",
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When this invite expires (typically now + 48 hours)",
    )

    is_used: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="True once the invitee has registered — prevents reuse",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When the invite was generated",
    )

    def __repr__(self) -> str:
        return f"<InviteToken email={self.email} org={self.organization_id} is_used={self.is_used}>"
