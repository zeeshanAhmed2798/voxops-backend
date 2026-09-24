"""Organization member-directory and application-role API contracts."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserStatus


class AppRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    code: str
    name: str
    description: str | None
    is_assignable: bool
    is_active: bool
    sort_order: int


class MemberDepartmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str


class TeamMemberResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    department: MemberDepartmentResponse | None
    role: AppRoleResponse
    status: UserStatus
    job_title: str | None
    created_at: datetime
    updated_at: datetime


class TeamMemberInvite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role_id: uuid.UUID
    department_id: uuid.UUID


class TeamMemberUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    status: UserStatus | None = None
    job_title: str | None = Field(default=None, max_length=150)
