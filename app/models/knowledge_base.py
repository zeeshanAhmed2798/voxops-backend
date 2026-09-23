"""
app/models/knowledge_base.py
=============================
SQLAlchemy model for the 'knowledge_base_documents' table.

MULTI-TENANCY:
- Every document is scoped to one organization via organization_id.
- All queries MUST filter by organization_id to prevent data leakage.

ACCESS CONTROL (enforced in the router):
- Any authenticated member of the org can READ documents.
- Only ORG_ADMIN (and SUPER_ADMIN) can CREATE, UPDATE, or DELETE documents.

CONTENT FORMAT:
- The 'content' field stores Markdown text.
- The frontend renders it as formatted text.
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KnowledgeBaseDocument(Base):
    """
    A single knowledge base article/document belonging to one organization.
    """

    __tablename__ = "knowledge_base_documents"

    # ── Primary Key ──────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Unique document identifier",
    )

    # ── Multi-Tenancy ─────────────────────────────────────────────────────────
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Organization this document belongs to — NEVER query without this filter",
    )

    # ── Content ───────────────────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Document title, shown in the KB list view",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Document body in Markdown format",
    )

    category: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        index=True,
        comment="Optional category tag, e.g. 'HR Policies', 'Onboarding', 'SOPs'",
    )

    # ── Authorship ────────────────────────────────────────────────────────────
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="The admin user who created this document",
    )

    # ── Publishing ────────────────────────────────────────────────────────────
    is_published: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="False = draft (visible to admins only). True = visible to all members.",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="When the document was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="When the document was last edited",
    )

    def __repr__(self) -> str:
        return f"<KBDocument id={self.id} title={self.title!r} org={self.organization_id}>"
