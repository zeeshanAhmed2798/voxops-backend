"""
app/modules/knowledge_base/router.py
=====================================
HTTP route handlers for Knowledge Base endpoints.

ENDPOINTS:
  GET    /api/v1/knowledge-base          → list all documents [ANY MEMBER]
  GET    /api/v1/knowledge-base/{id}     → view single document [ANY MEMBER]
  POST   /api/v1/knowledge-base          → create document [ADMIN ONLY]
  PUT    /api/v1/knowledge-base/{id}     → update document [ADMIN ONLY]
  DELETE /api/v1/knowledge-base/{id}     → delete document [ADMIN ONLY]

ACCESS CONTROL:
  - GET endpoints: any authenticated member of the organization.
  - POST/PUT/DELETE: require ORG_ADMIN or SUPER_ADMIN role.
    Non-admin users attempting write operations will receive 403 Forbidden.

MULTI-TENANCY:
  The service layer always filters by current_user.organization_id.
  Users can only see/modify documents belonging to their organization.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.models.user import User
from app.modules.knowledge_base import service
from app.schemas.knowledge_base import (
    KBDocumentCreate,
    KBDocumentUpdate,
    KBDocumentResponse,
    KBDocumentListItem,
)


router = APIRouter(
    prefix="/knowledge-base",
    tags=["Knowledge Base"],
)


# ── List Documents ─────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=List[KBDocumentListItem],
    status_code=status.HTTP_200_OK,
    summary="List all Knowledge Base documents",
    description=(
        "Returns all Knowledge Base documents for the authenticated user's organization.\n\n"
        "**Access:** Any authenticated member can read published documents. "
        "Admins can also see drafts (`is_published=false`).\n\n"
        "**Pagination:** Use `skip` and `limit` query params (max 100 per page).\n\n"
        "**Filtering:** Use `category` to filter by tag. Use `search` for title substring search."
    ),
)
def list_documents(
    category: Optional[str] = Query(None, description="Filter by category tag"),
    search: Optional[str] = Query(None, description="Search by document title (partial match)"),
    skip: int = Query(0, ge=0, description="Number of records to skip (pagination)"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return (max 100)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[KBDocumentListItem]:
    """GET /api/v1/knowledge-base"""
    return service.list_documents(
        db=db,
        current_user=current_user,
        category=category,
        search=search,
        skip=skip,
        limit=limit,
    )


# ── Get Single Document ────────────────────────────────────────────────────────

@router.get(
    "/{document_id}",
    response_model=KBDocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single Knowledge Base document",
    description=(
        "Returns the full content of a Knowledge Base document.\n\n"
        "**Access:** Any authenticated member can read published documents. "
        "Draft documents are only visible to admins.\n\n"
        "Returns 404 if the document doesn't exist, belongs to another organization, "
        "or is a draft being accessed by a non-admin."
    ),
)
def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KBDocumentResponse:
    """GET /api/v1/knowledge-base/{document_id}"""
    return service.get_document(db=db, document_id=document_id, current_user=current_user)


# ── Create Document ────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=KBDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Knowledge Base document [ADMIN ONLY]",
    description=(
        "**Admin only.** Creates a new Knowledge Base document for your organization.\n\n"
        "Set `is_published=false` to save as a draft (visible to admins only). "
        "Set `is_published=true` (default) to make it immediately visible to all members.\n\n"
        "Returns **403 Forbidden** if called by a non-admin user."
    ),
)
def create_document(
    data: KBDocumentCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> KBDocumentResponse:
    """POST /api/v1/knowledge-base — requires ORG_ADMIN role"""
    return service.create_document(db=db, data=data, current_user=current_user)


# ── Update Document ────────────────────────────────────────────────────────────

@router.put(
    "/{document_id}",
    response_model=KBDocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a Knowledge Base document [ADMIN ONLY]",
    description=(
        "**Admin only.** Updates a Knowledge Base document.\n\n"
        "You only need to include the fields you want to change (PATCH semantics). "
        "Omitted fields will not be modified.\n\n"
        "Returns **403 Forbidden** if called by a non-admin user.\n"
        "Returns **404 Not Found** if the document doesn't exist in your organization."
    ),
)
def update_document(
    document_id: uuid.UUID,
    data: KBDocumentUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> KBDocumentResponse:
    """PUT /api/v1/knowledge-base/{document_id} — requires ORG_ADMIN role"""
    return service.update_document(
        db=db,
        document_id=document_id,
        data=data,
        current_user=current_user,
    )


# ── Delete Document ────────────────────────────────────────────────────────────

@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Knowledge Base document [ADMIN ONLY]",
    description=(
        "**Admin only.** Permanently deletes a Knowledge Base document.\n\n"
        "This action cannot be undone.\n\n"
        "Returns **403 Forbidden** if called by a non-admin user.\n"
        "Returns **404 Not Found** if the document doesn't exist in your organization."
    ),
)
def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    """DELETE /api/v1/knowledge-base/{document_id} — requires ORG_ADMIN role"""
    service.delete_document(db=db, document_id=document_id, current_user=current_user)
