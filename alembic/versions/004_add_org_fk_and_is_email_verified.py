"""Add slug to orgs, FKs to users, and is_email_verified

Revision ID: 004
Revises: 003
Create Date: 2026-09-23

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "004"
down_revision = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add slug to organizations
    op.add_column('organizations', sa.Column('slug', sa.String(100), nullable=True))
    
    # 2. Populate slug for existing organizations using a simple generation strategy
    op.execute("UPDATE organizations SET slug = 'org-' || id::text WHERE slug IS NULL")
    
    # 3. Make slug not null
    op.alter_column('organizations', 'slug', existing_type=sa.String(100), nullable=False)
    op.create_unique_constraint("uq_organizations_slug", "organizations", ["slug"])
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)
    
    # 4. Add is_email_verified to users
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

    # 5. Add FK constraints on organization_id and department_id for users
    op.create_foreign_key(
        constraint_name="fk_users_organization_id",
        source_table="users",
        referent_table="organizations",
        local_cols=["organization_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )
    
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
