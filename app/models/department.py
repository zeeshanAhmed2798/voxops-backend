"""Departments group work inside an organization."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
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
