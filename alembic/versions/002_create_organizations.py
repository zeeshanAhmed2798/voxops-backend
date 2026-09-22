"""Create organization settings and preserve existing organization IDs.

Revision ID: 002
Revises: 001
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    # Existing users already carry organization IDs. Keep those IDs usable.
    op.execute(sa.text("""
        INSERT INTO organizations (id, name)
        SELECT DISTINCT organization_id, 'Organization ' || left(organization_id::text, 8)
        FROM users WHERE organization_id IS NOT NULL
    """))


def downgrade() -> None:
    op.drop_table("organizations")
