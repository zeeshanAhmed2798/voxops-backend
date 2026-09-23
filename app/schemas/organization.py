"""
app/schemas/organization.py
============================
Pydantic schemas for Organization API responses.
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class OrganizationResponse(BaseModel):
    """Safe representation of an Organization returned by API endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime
