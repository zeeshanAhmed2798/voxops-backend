"""Field work owned by a department and assigned to a technician."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import GUID


class Job(Base):
    __tablename__ = "jobs"

    # UUID is the stable public identifier; the design's JOB #1042 is a separate future display number.
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4, comment="Stable job UUID")
    # Explicit owner prevents cross-organization reads and supports fast organization lists.
    organization_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("organizations.id"), nullable=False, index=True, comment="Organization that owns this job")
    # Every job belongs to one team responsible for the work.
    department_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("departments.id"), nullable=False, index=True, comment="Department responsible for this job")
    # Required technician matches the Assigned state used when a job is created.
    assigned_to_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id"), nullable=False, index=True, comment="User assigned to perform this job")
    # Short label shown on cards and detail pages.
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="Short job title")
    # Optional longer instructions or problem context.
    description: Mapped[str | None] = mapped_column(Text, comment="Job instructions or problem description")
    # Customer or site name appears on job cards and in the detail view.
    customer: Mapped[str] = mapped_column(String(200), nullable=False, comment="Customer or service site name")
    # City or address tells the technician where work occurs.
    location: Mapped[str] = mapped_column(String(200), nullable=False, comment="Where work occurs")
    # Optional equipment identifier or model shown in job details.
    equipment: Mapped[str | None] = mapped_column(String(200), comment="Equipment being serviced")
    # LOW/NORMAL/HIGH supports priority badges and filtering later.
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="NORMAL", comment="Urgency of the job")
    # ASSIGNED/IN_PROGRESS/COMPLETED/ESCALATED drives the workflow tabs.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ASSIGNED", comment="Current job workflow state")
    # Audit and chronological ordering for the Jobs list.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="When the job was created")
    # Audit and future synchronization after edits or status changes.
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), comment="When the job last changed")
