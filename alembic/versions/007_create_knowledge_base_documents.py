"""Create knowledge_base_documents table

Revision ID: 007
Revises: 006
Create Date: 2026-09-23

The Knowledge Base documents table — org-scoped articles and SOPs.
Every document belongs to one organization. Access is controlled at
the application level (read=all members, write=admin only).

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
    """Create the knowledge_base_documents table."""
    op.create_table(
        "knowledge_base_documents",

        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
            comment="Unique document identifier",
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            comment="Organization this document belongs to",
        ),
        sa.Column(
            "title",
            sa.String(500),
            nullable=False,
            comment="Document title",
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
            comment="Document body in Markdown format",
        ),
        sa.Column(
            "category",
            sa.String(150),
            nullable=True,
            comment="Category tag, e.g. 'HR', 'SOPs', 'Policies'",
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            comment="Admin user who created this document",
        ),
        sa.Column(
            "is_published",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="True = visible to all members. False = draft (admin-only).",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Index for fast org-scoped queries (the primary access pattern)
    op.create_index(
        "ix_kb_documents_organization_id",
        "knowledge_base_documents",
        ["organization_id"],
    )

    # Index for category filtering
    op.create_index(
        "ix_kb_documents_category",
        "knowledge_base_documents",
        ["category"],
    )

    # Composite index for the most common query: org + published status
    op.create_index(
        "ix_kb_documents_org_published",
        "knowledge_base_documents",
        ["organization_id", "is_published"],
    )


def downgrade() -> None:
    """Drop the knowledge_base_documents table."""
    op.drop_index("ix_kb_documents_org_published", table_name="knowledge_base_documents")
    op.drop_index("ix_kb_documents_category", table_name="knowledge_base_documents")
    op.drop_index("ix_kb_documents_organization_id", table_name="knowledge_base_documents")
    op.drop_table("knowledge_base_documents")
