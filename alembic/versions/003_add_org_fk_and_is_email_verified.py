"""Add org FK and is_email_verified to users table

Revision ID: 003
Revises: 002
Create Date: 2026-09-23

Two changes to the existing 'users' table:
1. Add is_email_verified boolean column (default false)
2. Add ForeignKey constraint on organization_id → organizations.id

Note: The organization_id column already exists from migration 001.
We're just adding the FK constraint now that the organizations table exists.

To apply:    alembic upgrade head
To roll back: alembic downgrade -1
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_email_verified column and organization FK constraint."""

    # 1. Add is_email_verified column
    op.add_column(
        "users",
        sa.Column(
            "is_email_verified",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether the user's email has been verified",
        ),
    )

    # 2. Add FK constraint on organization_id
    # The column already exists — we're just adding the constraint.
    op.create_foreign_key(
        constraint_name="fk_users_organization_id",
        source_table="users",
        referent_table="organizations",
        local_cols=["organization_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Remove is_email_verified and drop the FK constraint."""
    op.drop_constraint("fk_users_organization_id", "users", type_="foreignkey")
    op.drop_column("users", "is_email_verified")
