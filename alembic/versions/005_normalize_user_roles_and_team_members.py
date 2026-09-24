"""Normalize user roles and prepare the organization member directory.

Revision ID: 005
Revises: 004
"""

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


ROLE_ROWS = [
    ("SUPER_ADMIN", "Super Admin", "Platform-wide administration.", False, 0),
    ("EMPLOYEE", "Employee", "Standard organization member.", True, 10),
    ("FIELD_WORKER", "Field Worker", "Performs assigned field work.", True, 20),
    ("DEPARTMENT_AGENT", "Department Agent", "Handles department requests.", True, 30),
    ("SUPERVISOR", "Supervisor", "Supervises members and operational work.", True, 40),
    ("ORG_ADMIN", "Org Admin", "Manages the organization and its members.", True, 50),
]


def upgrade() -> None:
    # PostgreSQL enums can be extended safely; invited users are created after
    # this migration commits, so the new value is not used in this transaction.
    op.execute("ALTER TYPE userstatus ADD VALUE IF NOT EXISTS 'INVITED'")

    op.create_table(
        "user_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500)),
        sa.Column("is_assignable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("code", name="uq_user_roles_code"),
    )
    roles_table = sa.table(
        "user_roles",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
        sa.column("is_assignable", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
        sa.column("sort_order", sa.Integer()),
    )
    op.bulk_insert(roles_table, [
        {
            "id": uuid.uuid4(),
            "code": code,
            "name": name,
            "description": description,
            "is_assignable": assignable,
            "is_active": True,
            "sort_order": sort_order,
        }
        for code, name, description, assignable, sort_order in ROLE_ROWS
    ])

    op.add_column("users", sa.Column("user_role_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(
        """
        UPDATE users
        SET user_role_id = user_roles.id
        FROM user_roles
        WHERE user_roles.code = users.role::text
        """
    )
    op.alter_column("users", "user_role_id", nullable=False)
    op.create_foreign_key(
        "fk_users_user_role_id_user_roles", "users", "user_roles", ["user_role_id"], ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_users_user_role_id", "users", ["user_role_id"])

    op.create_foreign_key(
        "fk_users_department_id_departments", "users", "departments", ["department_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_users_department_id", "users", ["department_id"])
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)
    op.drop_column("users", "role")
    op.execute("DROP TYPE IF EXISTS userrole")


def downgrade() -> None:
    userrole_enum = postgresql.ENUM(
        "SUPER_ADMIN", "ORG_ADMIN", "SUPERVISOR", "DEPARTMENT_AGENT", "FIELD_WORKER", "EMPLOYEE",
        name="userrole",
    )
    userrole_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "users",
        sa.Column("role", postgresql.ENUM(name="userrole", create_type=False), nullable=True),
    )
    op.execute(
        """
        UPDATE users
        SET role = user_roles.code::userrole
        FROM user_roles
        WHERE user_roles.id = users.user_role_id
        """
    )
    op.alter_column("users", "role", nullable=False)
    op.drop_index("ix_users_department_id", table_name="users")
    op.drop_constraint("fk_users_department_id_departments", "users", type_="foreignkey")
    op.drop_index("ix_users_user_role_id", table_name="users")
    op.drop_constraint("fk_users_user_role_id_user_roles", "users", type_="foreignkey")
    op.drop_column("users", "user_role_id")
    op.drop_table("user_roles")
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)
