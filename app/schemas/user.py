"""
app/schemas/user.py
===================
Pydantic schemas for user profile API requests and responses.

HOW IT WORKS:
- UserResponse is what the API returns — safe fields only, NO password_hash.
- UpdateProfileRequest is what users can send to update their profile.
  It ONLY includes fields users are allowed to change themselves.
  Role, organization_id, status etc. are deliberately excluded.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole, UserStatus


# ── User Response ─────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    """
    Safe representation of a user returned by API endpoints.

    CRITICAL: password_hash is NEVER included here.
    All sensitive internal fields are excluded.

    Used by:
      - GET /api/v1/auth/me
      - GET /api/v1/users/me
    """

    # Pydantic v2: model_config replaces the old class Config
    model_config = ConfigDict(from_attributes=True)
    # from_attributes=True lets Pydantic read from SQLAlchemy model attributes directly
    # e.g. UserResponse.model_validate(user_db_object) works automatically

    id: uuid.UUID
    organization_id: Optional[uuid.UUID]
    department_id: Optional[uuid.UUID]
    user_role_id: uuid.UUID
    name: str
    email: EmailStr
    role: UserRole
    status: UserStatus

    # Profile fields
    job_title: Optional[str] = None
    phone: Optional[str] = None
    timezone: Optional[str] = None
    profile_picture: Optional[str] = None

    created_at: datetime
    updated_at: datetime


# ── Update Profile Request ─────────────────────────────────────────────────────

class UpdateProfileRequest(BaseModel):
    """
    Fields a user is allowed to update on their own profile.

    All fields are Optional — user can send only the fields they want to change.
    Fields NOT listed here cannot be changed through this endpoint.

    PROTECTED (excluded intentionally):
      - id
      - organization_id
      - department_id
      - role
      - status
      - password_hash
      - email (changing email needs verification flow — future feature)
    """

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Full display name",
        examples=["Jane Doe"],
    )
    job_title: Optional[str] = Field(
        default=None,
        max_length=150,
        description="Job title or position",
        examples=["Senior Support Agent"],
    )
    phone: Optional[str] = Field(
        default=None,
        max_length=30,
        description="Phone number in international format",
        examples=["+92-300-1234567"],
    )
    timezone: Optional[str] = Field(
        default=None,
        max_length=60,
        description="IANA timezone name",
        examples=["Asia/Karachi", "UTC", "America/New_York"],
    )
    profile_picture: Optional[str] = Field(
        default=None,
        max_length=500,
        description="URL to profile picture (uploaded externally)",
        examples=["https://cdn.example.com/avatars/jane.jpg"],
    )
