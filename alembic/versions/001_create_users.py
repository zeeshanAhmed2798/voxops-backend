"""Initial migration: create users table

Revision ID: 001_create_users
Revises: 
Create Date: 2026-09-16

This migration creates the 'users' table with all required columns,
enums (userrole, userstatus), and indexes.

To apply:    alembic upgrade head
To roll back: alembic downgrade -1
"""

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# ── Revision Identifiers ──────────────────────────────────────────────────────
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Upgrade: Create Tables ───────────────────────────────────────────────────
def upgrade() -> None:
    """
    Create the 'users' table and its supporting enums.
    This runs when you do: alembic upgrade head
    """

    # Create the UserRole enum type in PostgreSQL
    userrole_enum = postgresql.ENUM(
        "SUPER_ADMIN",
        "ORG_ADMIN",
        "SUPERVISOR",
        "DEPARTMENT_AGENT",
        "FIELD_WORKER",
        "EMPLOYEE",
        name="userrole",
    )
    userrole_enum.create(op.get_bind(), checkfirst=True)

    # Create the UserStatus enum type in PostgreSQL
    userstatus_enum = postgresql.ENUM(
        "ACTIVE",
        "INACTIVE",
        "SUSPENDED",
        name="userstatus",
    )
    userstatus_enum.create(op.get_bind(), checkfirst=True)

    # Create the 'users' table
    op.create_table(
        "users",

        # ── Primary Key ──────────────────────────────────────────────────────
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
            comment="Unique user identifier (UUID v4)",
        ),

        # ── Organization (Multi-Tenancy) ──────────────────────────────────
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Organization this user belongs to",
        ),

        # ── Department ────────────────────────────────────────────────────
        sa.Column(
            "department_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Department this user belongs to",
        ),

        # ── Basic Info ────────────────────────────────────────────────────
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Full name",
        ),
        sa.Column(
            "email",
            sa.String(320),
            nullable=False,
            comment="Email address — unique",
        ),

        # ── Security ──────────────────────────────────────────────────────
        sa.Column(
            "password_hash",
            sa.String(255),
            nullable=False,
            comment="bcrypt hash — NEVER plain text",
        ),

        # ── Role & Status ─────────────────────────────────────────────────
        sa.Column(
            "role",
            postgresql.ENUM(
                "SUPER_ADMIN",
                "ORG_ADMIN",
                "SUPERVISOR",
                "DEPARTMENT_AGENT",
                "FIELD_WORKER",
                "EMPLOYEE",
                name="userrole",
                create_type=False,  # Already created above
            ),
            nullable=False,
            server_default="EMPLOYEE",
            comment="User role",
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "ACTIVE",
                "INACTIVE",
                "SUSPENDED",
                name="userstatus",
                create_type=False,  # Already created above
            ),
            nullable=False,
            server_default="ACTIVE",
            comment="Account status",
        ),

        # ── Profile Fields ────────────────────────────────────────────────
        sa.Column("job_title", sa.String(150), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("timezone", sa.String(60), nullable=True, server_default="UTC"),
        sa.Column("profile_picture", sa.String(500), nullable=True),

        # ── Timestamps ────────────────────────────────────────────────────
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

    # ── Constraints ──────────────────────────────────────────────────────────

    # Unique constraint on email
    op.create_unique_constraint(
        "uq_users_email",
        "users",
        ["email"],
    )

    # ── Indexes ───────────────────────────────────────────────────────────────

    # Index on email for fast login lookups
    op.create_index(
        "ix_users_email",
        "users",
        ["email"],
        unique=True,
    )

    # Index on organization_id for fast org-level queries (multi-tenancy)
    op.create_index(
        "ix_users_organization_id",
        "users",
        ["organization_id"],
    )


# ── Downgrade: Drop Tables ───────────────────────────────────────────────────
def downgrade() -> None:
    """
    Undo the upgrade — drop the users table and its enums.
    This runs when you do: alembic downgrade -1
    """
    # Drop indexes first
    op.drop_index("ix_users_organization_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")

    # Drop the table
    op.drop_table("users")

    # Drop the enum types
    op.execute("DROP TYPE IF EXISTS userstatus")
    op.execute("DROP TYPE IF EXISTS userrole")
