"""Add slug to organizations, org/dept FKs on users, and is_email_verified

Revision ID: 004
Revises: 003
Create Date: 2026-09-23

Adds:
  - 'slug' column to organizations table (url-safe unique identifier)
  - FK constraint: users.organization_id -> organizations.id
  - FK constraint: users.department_id -> departments.id
  - 'is_email_verified' boolean column on users

To apply:    alembic upgrade head
To roll back: alembic downgrade -1
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add 'slug' to organizations
    op.add_column(
        "organizations",
        sa.Column("slug", sa.String(100), nullable=True, comment="URL-safe unique identifier"),
    )
    # Populate slug for any existing rows
    op.execute("UPDATE organizations SET slug = 'org-' || id::text WHERE slug IS NULL")
    op.alter_column("organizations", "slug", existing_type=sa.String(100), nullable=False)
    op.create_unique_constraint("uq_organizations_slug", "organizations", ["slug"])
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    # 2. Add 'is_email_verified' to users
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

    # 3. Add FK: users.organization_id -> organizations.id
    op.create_foreign_key(
        constraint_name="fk_users_organization_id",
        source_table="users",
        referent_table="organizations",
        local_cols=["organization_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )

    # 4. Add FK: users.department_id -> departments.id
    op.create_foreign_key(
        constraint_name="fk_users_department_id",
        source_table="users",
        referent_table="departments",
        local_cols=["department_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_department_id", "users", type_="foreignkey")
    op.drop_constraint("fk_users_organization_id", "users", type_="foreignkey")
    op.drop_column("users", "is_email_verified")
    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_constraint("uq_organizations_slug", "organizations", type_="unique")
    op.drop_column("organizations", "slug")
