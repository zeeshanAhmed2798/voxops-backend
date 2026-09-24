"""Complete department configuration tables.

Revision ID: 004
Revises: 003
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "department_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("department_id", "name", name="uq_department_category_name"),
    )
    op.create_index("ix_department_categories_organization_id", "department_categories", ["organization_id"])
    op.create_index("ix_department_categories_department_id", "department_categories", ["department_id"])
    op.create_index("ix_department_categories_is_active", "department_categories", ["is_active"])

    op.create_table(
        "department_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("department_id", "name", name="uq_department_role_name"),
    )
    op.create_index("ix_department_roles_organization_id", "department_roles", ["organization_id"])
    op.create_index("ix_department_roles_department_id", "department_roles", ["department_id"])
    op.create_index("ix_department_roles_is_active", "department_roles", ["is_active"])

    op.create_table(
        "department_routing_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("department_categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("department_role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("department_roles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("priority_override", sa.String(20)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("department_id", "category_id", name="uq_department_routing_category"),
        sa.CheckConstraint(
            "priority_override IS NULL OR priority_override IN ('LOW', 'NORMAL', 'HIGH')",
            name="ck_department_routing_priority",
        ),
    )
    op.create_index("ix_department_routing_rules_organization_id", "department_routing_rules", ["organization_id"])
    op.create_index("ix_department_routing_rules_department_id", "department_routing_rules", ["department_id"])
    op.create_index("ix_department_routing_rules_category_id", "department_routing_rules", ["category_id"])
    op.create_index("ix_department_routing_rules_department_role_id", "department_routing_rules", ["department_role_id"])
    op.create_index("ix_department_routing_rules_is_active", "department_routing_rules", ["is_active"])

    op.create_table(
        "department_escalation_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("after_hours", sa.Integer(), nullable=False),
        sa.Column("escalate_to_role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("department_roles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("department_id", name="uq_department_escalation_department"),
        sa.CheckConstraint("after_hours > 0", name="ck_department_escalation_hours"),
    )
    op.create_index("ix_department_escalation_policies_organization_id", "department_escalation_policies", ["organization_id"])
    op.create_index("ix_department_escalation_policies_department_id", "department_escalation_policies", ["department_id"])
    op.create_index("ix_department_escalation_policies_escalate_to_role_id", "department_escalation_policies", ["escalate_to_role_id"])


def downgrade() -> None:
    op.drop_index("ix_department_escalation_policies_escalate_to_role_id", table_name="department_escalation_policies")
    op.drop_index("ix_department_escalation_policies_department_id", table_name="department_escalation_policies")
    op.drop_index("ix_department_escalation_policies_organization_id", table_name="department_escalation_policies")
    op.drop_table("department_escalation_policies")

    op.drop_index("ix_department_routing_rules_is_active", table_name="department_routing_rules")
    op.drop_index("ix_department_routing_rules_department_role_id", table_name="department_routing_rules")
    op.drop_index("ix_department_routing_rules_category_id", table_name="department_routing_rules")
    op.drop_index("ix_department_routing_rules_department_id", table_name="department_routing_rules")
    op.drop_index("ix_department_routing_rules_organization_id", table_name="department_routing_rules")
    op.drop_table("department_routing_rules")

    op.drop_index("ix_department_roles_is_active", table_name="department_roles")
    op.drop_index("ix_department_roles_department_id", table_name="department_roles")
    op.drop_index("ix_department_roles_organization_id", table_name="department_roles")
    op.drop_table("department_roles")

    op.drop_index("ix_department_categories_is_active", table_name="department_categories")
    op.drop_index("ix_department_categories_department_id", table_name="department_categories")
    op.drop_index("ix_department_categories_organization_id", table_name="department_categories")
    op.drop_table("department_categories")
