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
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import UUID
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    INVITED   = "INVITED"    # Invited but has not activated the account
    ACTIVE    = "ACTIVE"     # Can log in and use the system
    INACTIVE  = "INACTIVE"   # Disabled (e.g. left the company)
    SUSPENDED = "SUSPENDED"  # Temporarily blocked


# ── Role Lookup Model ─────────────────────────────────────────────────────────

class AppRole(Base):
    """UUID-backed application role used by users and frontend dropdowns."""

    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("code", name="uq_user_roles_code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    is_assignable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


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
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Department this user belongs to (optional)",
    )
    department = relationship("Department", lazy="joined")

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
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="bcrypt hash of the user's password — NEVER store plain text",
    )

    # ── Role & Status ─────────────────────────────────────────────────────────
    user_role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_roles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Application role controlling API authorization",
    )
    user_role: Mapped[AppRole] = relationship(lazy="joined")

    status: Mapped[UserStatus] = mapped_column(
        SAEnum(UserStatus, name="userstatus", create_type=True),
        nullable=False,
        default=UserStatus.ACTIVE,
        comment="Account status — only ACTIVE users can log in",
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

    @property
    def role(self) -> UserRole:
        """Compatibility accessor used by authorization and JWT creation."""
        return UserRole(self.user_role.code)

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
