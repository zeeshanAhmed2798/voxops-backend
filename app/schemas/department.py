"""Department API contracts."""

import uuid
from datetime import datetime

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, ConfigDict, Field


class DepartmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class DepartmentUpdate(DepartmentCreate):
    pass


class DepartmentResponse(DepartmentCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
