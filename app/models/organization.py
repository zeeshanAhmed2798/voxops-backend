"""Minimal organization anchor for department and job ownership."""

import uuid
from datetime import datetime

# pyrefly: ignore [missing-import]
from sqlalchemy import DateTime, String, func
# pyrefly: ignore [missing-import]
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
    # Creation time supports audit and future organization lifecycle work.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="When this organization was created")
    # Last change time supports audit and cache refresh.
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), comment="When this organization was last changed")
