"""Job API contracts and allowed workflow values."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


JobStatus = Literal["ASSIGNED", "IN_PROGRESS", "COMPLETED", "ESCALATED"]
JobPriority = Literal["LOW", "NORMAL", "HIGH"]


class JobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    department_id: uuid.UUID
    assigned_to_id: uuid.UUID
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    customer: str = Field(min_length=1, max_length=200)
    location: str = Field(min_length=1, max_length=200)
    equipment: str | None = Field(default=None, max_length=200)
    priority: JobPriority = "NORMAL"


class JobUpdate(JobCreate):
    pass


class JobResponse(JobCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    organization_id: uuid.UUID
    status: JobStatus
    created_at: datetime
    updated_at: datetime


class JobStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: JobStatus
