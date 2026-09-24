"""
app/models/user.py
==================
SQLAlchemy model for the 'users' database table.

HOW IT WORKS:
- This class maps directly to a PostgreSQL table called 'users'.
- Each attribute (id, name, email, ...) maps to a column in that table.
- SQLAlchemy handles reading/writing rows as Python objects.

IMPORTANT FOR TEAM MEMBERS:
- Import User from here: from app.models.user import User
- Import enums from here: from app.models.user import UserRole, UserStatus
"""

import uuid
from datetime import datetime, timezone
from enum import Enum

# pyrefly: ignore [missing-import]
from sqlalchemy import (
    String,
    Boolean,
    DateTime,
    Enum as SAEnum,
    func,
)
# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import UUID
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# ── Enums ────────────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    """
    All possible roles in VoxOps.
    Stored as strings in the database (e.g. "ORG_ADMIN").

    Using str + Enum means: role.value == "ORG_ADMIN" AND role == "ORG_ADMIN" both work.
    This makes JSON serialization and comparisons much easier.
    """
    SUPER_ADMIN      = "SUPER_ADMIN"       # Full platform access
    ORG_ADMIN        = "ORG_ADMIN"         # Admin of one organization
    SUPERVISOR       = "SUPERVISOR"        # Manages teams within an org
    DEPARTMENT_AGENT = "DEPARTMENT_AGENT"  # Agent working in a department
    FIELD_WORKER     = "FIELD_WORKER"      # Field-based employee
    EMPLOYEE         = "EMPLOYEE"          # Standard employee


class UserStatus(str, Enum):
    """
    Account status. Only ACTIVE users can log in.
    """
    ACTIVE    = "ACTIVE"     # Can log in and use the system
    INACTIVE  = "INACTIVE"   # Disabled (e.g. left the company)
    SUSPENDED = "SUSPENDED"  # Temporarily blocked


# ── User Model ───────────────────────────────────────────────────────────────

class User(Base):
    """
    The User table — central to the entire VoxOps system.

    Every authenticated user in every organization is a row in this table.
    The organization_id field is what keeps organizations isolated from each other.

    NOTE: organization_id does NOT have a ForeignKey constraint yet because
    the Organization model will be built by another team member. We store the
    UUID value directly — this is intentional and avoids blocking our work.
    """

    __tablename__ = "users"

    # ── Identity ──────────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        comment="Unique user identifier (UUID v4)",
    )

    # ── Organization (Multi-Tenancy) ──────────────────────────────────────────
    # No ForeignKey here intentionally — org table is another team member's work.
    # Future: Add ForeignKey("organizations.id") when Organization model exists.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,   # SUPER_ADMIN may not belong to a specific org
        index=True,      # Index for fast org-level queries
        comment="Organization this user belongs to (multi-tenant isolation key)",
    )

    # ── Department (Optional Reference) ──────────────────────────────────────
    # No ForeignKey — departments table is another team member's work.
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Department this user belongs to (optional)",
    )

    # ── Basic Info ────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Full name of the user",
    )

    email: Mapped[str] = mapped_column(
        String(320),  # Max valid email length per RFC 5321
        unique=True,
        nullable=False,
        index=True,
        comment="Email address — unique across the entire system",
    )

    # ── Security ──────────────────────────────────────────────────────────────
    # NEVER store the plain password. Only the bcrypt hash goes here.
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="bcrypt hash of the user's password — NEVER store plain text",
    )

    # ── Role & Status ─────────────────────────────────────────────────────────
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="userrole", create_type=True),
        nullable=False,
        default=UserRole.EMPLOYEE,
        comment="User's role — controls what they can access",
    )

    status: Mapped[UserStatus] = mapped_column(
        SAEnum(UserStatus, name="userstatus", create_type=True),
        nullable=False,
        default=UserStatus.ACTIVE,
        comment="Account status — only ACTIVE users can log in",
    )

    is_email_verified: Mapped[bool] = mapped_column(
        Boolean(),
        nullable=False,
        default=False,
        server_default="false",
        comment="Whether the user's email has been verified",
    )

    # ── Profile Fields ────────────────────────────────────────────────────────
    job_title: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        comment="e.g. 'Senior Support Agent'",
    )

    phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        comment="Phone number (international format recommended)",
    )

    timezone: Mapped[str | None] = mapped_column(
        String(60),
        nullable=True,
        default="UTC",
        comment="IANA timezone string, e.g. 'Asia/Karachi'",
    )

    profile_picture: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="URL to profile image (stored externally, e.g. S3)",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this user account was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="When this user account was last modified",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
