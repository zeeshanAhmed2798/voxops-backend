"""
app/models/organization.py
===========================
SQLAlchemy model for the 'organizations' table.

HOW IT WORKS:
- Every company that signs up for VoxOps becomes one Organization row.
- All other tables (users, knowledge_base_documents, etc.) reference
  organization_id to enforce strict data isolation between tenants.

MULTI-TENANCY RULE:
  Every query on a tenant-specific table MUST filter by organization_id.
  Never return data from multiple organizations in a single response.
"""

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Organization(Base):
    """
    The Organization table — top of the multi-tenant hierarchy.

    One Organization = one company/team using VoxOps.
    Every user, document, job, request, etc. belongs to exactly one Organization.
    """

    __tablename__ = "organizations"

    # ── Primary Key ──────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        comment="Unique organization identifier (UUID v4)",
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Display name of the organization, e.g. 'Acme Corp'",
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="URL-safe unique identifier, e.g. 'acme-corp'. Auto-generated from name.",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When this organization was registered",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="When this organization was last updated",
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id} slug={self.slug}>"
