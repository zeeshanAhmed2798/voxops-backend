"""Create knowledge_base_documents table

Revision ID: 008
Revises: 007
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


revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
            comment="Organization this document belongs to — NEVER query without this filter",
        ),
        sa.Column(
            "title",
            sa.String(500),
            nullable=False,
            comment="Document title, shown in the KB list view",
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
            comment="Full document body (Markdown supported)",
        ),
        sa.Column(
            "category",
            sa.String(150),
            nullable=True,
            comment="Optional category tag, e.g. 'HR Policies', 'Onboarding', 'SOPs'",
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            comment="The admin user who created this document",
        ),
        sa.Column(
            "is_published",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="False = draft (visible to admins only). True = visible to all members.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="When the document was created",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="When the document was last edited",
        ),
    )
    op.create_index(
        "ix_knowledge_base_documents_organization_id",
        "knowledge_base_documents",
        ["organization_id"],
    )
    op.create_index(
        "ix_knowledge_base_documents_category",
        "knowledge_base_documents",
        ["category"],
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_base_documents_category", table_name="knowledge_base_documents")
    op.drop_index("ix_knowledge_base_documents_organization_id", table_name="knowledge_base_documents")
    op.drop_table("knowledge_base_documents")
