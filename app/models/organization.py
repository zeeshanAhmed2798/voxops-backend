"""Organization model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import GUID


class Organization(Base):
    __tablename__ = "organizations"

    # Stable UUID matches the organization_id already stored on User.
    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        comment="Stable organization UUID used by users, departments, and jobs",
    )
    # Human-readable name for the workspace and administrator screens.
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Organization display name")
    slug: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True, comment="URL-safe unique identifier")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="When this organization was created")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), comment="When this organization was last changed")
