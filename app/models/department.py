"""Department configuration models.

The Team module is intentionally not represented here.  Department roles are
operational labels used by routing and escalation; they are not authorization
roles and are not assigned to users until the Team module is implemented.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import GUID


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_department_org_name"),)

    # UUID keeps the public department identity stable across imports and clients.
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4, comment="Stable department UUID")
    # FK and index make ownership explicit and organization-scoped lists efficient.
    organization_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("organizations.id"), nullable=False, index=True, comment="Organization that owns this department")
    # Shown in the department directory; unique within an organization.
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="Department display name")
    # Optional explanation of the department's responsibility.
    description: Mapped[str | None] = mapped_column(String(500), comment="What work this department handles")
    # Audit when the department was created.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="When the department was created")
    # Audit when its details last changed.
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), comment="When the department was last changed")


class DepartmentCategory(Base):
    """A request category configured inside one department."""

    __tablename__ = "department_categories"
    __table_args__ = (
        UniqueConstraint("department_id", "name", name="uq_department_category_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id"), nullable=False, index=True
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true(), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DepartmentRole(Base):
    """A customizable operational role belonging to one department."""

    __tablename__ = "department_roles"
    __table_args__ = (
        UniqueConstraint("department_id", "name", name="uq_department_role_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id"), nullable=False, index=True
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true(), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DepartmentRoutingRule(Base):
    """Route a department category to a department role."""

    __tablename__ = "department_routing_rules"
    __table_args__ = (
        UniqueConstraint("department_id", "category_id", name="uq_department_routing_category"),
        CheckConstraint(
            "priority_override IS NULL OR priority_override IN ('LOW', 'NORMAL', 'HIGH')",
            name="ck_department_routing_priority",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id"), nullable=False, index=True
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("department_categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    department_role_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("department_roles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    priority_override: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true(), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class DepartmentEscalationPolicy(Base):
    """The single time-based escalation configuration for a department."""

    __tablename__ = "department_escalation_policies"
    __table_args__ = (
        UniqueConstraint("department_id", name="uq_department_escalation_department"),
        CheckConstraint("after_hours > 0", name="ck_department_escalation_hours"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("organizations.id"), nullable=False, index=True
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    after_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    escalate_to_role_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("department_roles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
