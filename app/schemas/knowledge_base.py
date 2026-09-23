"""
app/schemas/knowledge_base.py
==============================
Pydantic schemas for Knowledge Base Document API endpoints.

THREE SCHEMA PATTERN:
  KBDocumentCreate  → what the client sends when creating a document
  KBDocumentUpdate  → what the client sends when updating (all fields optional)
  KBDocumentResponse → what the API returns (safe, read-only view)

WHY SEPARATE CREATE / UPDATE / RESPONSE?
- Create: required fields that must be provided.
- Update: all fields optional (PATCH semantics — only send what changes).
- Response: includes server-set fields (id, timestamps, org_id) the client
  should never send.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Create ─────────────────────────────────────────────────────────────────────

class KBDocumentCreate(BaseModel):
    """
    Body for POST /api/v1/knowledge-base  (ADMIN ONLY)

    Required: title, content
    Optional: category, is_published (defaults True = immediately visible)
    """
    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Document title shown in the Knowledge Base list",
        examples=["Employee Onboarding Guide"],
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Document body in Markdown format",
        examples=["# Welcome to VoxOps\n\nThis guide covers your first week..."],
    )
    category: Optional[str] = Field(
        default=None,
        max_length=150,
        description="Category tag for filtering, e.g. 'HR', 'SOPs', 'Policies'",
        examples=["HR Policies"],
    )
    is_published: bool = Field(
        default=True,
        description="True = visible to all members. False = draft (admin-only view).",
    )


# ── Update ─────────────────────────────────────────────────────────────────────

class KBDocumentUpdate(BaseModel):
    """
    Body for PUT /api/v1/knowledge-base/{id}  (ADMIN ONLY)

    All fields are optional — only send the fields you want to change.
    """
    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="Updated document title",
    )
    content: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Updated document body (Markdown)",
    )
    category: Optional[str] = Field(
        default=None,
        max_length=150,
        description="Updated category tag",
    )
    is_published: Optional[bool] = Field(
        default=None,
        description="Toggle published state",
    )


# ── Response ───────────────────────────────────────────────────────────────────

class KBDocumentResponse(BaseModel):
    """
    Full document representation returned by API endpoints.
    Includes server-managed fields (id, org, timestamps).
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    title: str
    content: str
    category: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    is_published: bool
    created_at: datetime
    updated_at: datetime


# ── List Item (lighter response for list endpoints) ────────────────────────────

class KBDocumentListItem(BaseModel):
    """
    Lightweight document summary for the GET /knowledge-base list endpoint.
    Excludes the full content body to reduce payload size.
    """
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    category: Optional[str] = None
    is_published: bool
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
