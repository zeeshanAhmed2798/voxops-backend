"""Create organizations table

Revision ID: 002
Revises: 001
Create Date: 2026-09-23

Creates the 'organizations' table — the top-level multi-tenant entity.
Every User, KnowledgeBaseDocument, etc. will reference organizations.id.

To apply:    alembic upgrade head
To roll back: alembic downgrade -1
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the organizations table."""
    op.create_table(
        "organizations",

        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
            comment="Unique organization identifier (UUID v4)",
        ),
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Display name, e.g. 'Acme Corporation'",
        ),
        sa.Column(
            "slug",
            sa.String(100),
            nullable=False,
            comment="URL-safe unique identifier, e.g. 'acme-corporation'",
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

    # Unique constraint on slug
    op.create_unique_constraint("uq_organizations_slug", "organizations", ["slug"])

    # Index for fast slug lookups
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)


def downgrade() -> None:
    """Drop the organizations table."""
    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_table("organizations")
