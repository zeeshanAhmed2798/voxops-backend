"""Departments and jobs for one-organization field work.

Revision ID: 003
Revises: 002
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "name", name="uq_department_org_name"),
    )
    op.create_index("ix_departments_organization_id", "departments", ["organization_id"])
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id"), nullable=False),
        sa.Column("assigned_to_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("customer", sa.String(200), nullable=False),
        sa.Column("location", sa.String(200), nullable=False),
        sa.Column("equipment", sa.String(200)),
        sa.Column("priority", sa.String(20), nullable=False, server_default="NORMAL"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ASSIGNED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("priority IN ('LOW', 'NORMAL', 'HIGH')", name="ck_jobs_priority"),
        sa.CheckConstraint("status IN ('ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'ESCALATED')", name="ck_jobs_status"),
    )
    op.create_index("ix_jobs_organization_id", "jobs", ["organization_id"])
    op.create_index("ix_jobs_department_id", "jobs", ["department_id"])
    op.create_index("ix_jobs_assigned_to_id", "jobs", ["assigned_to_id"])


def downgrade() -> None:
    op.drop_index("ix_jobs_assigned_to_id", table_name="jobs")
    op.drop_index("ix_jobs_department_id", table_name="jobs")
    op.drop_index("ix_jobs_organization_id", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("ix_departments_organization_id", table_name="departments")
    op.drop_table("departments")
