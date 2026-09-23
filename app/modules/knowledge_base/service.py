"""
app/modules/knowledge_base/service.py
======================================
Knowledge Base business logic for VoxOps.

MULTI-TENANCY RULE:
  Every function in this file MUST filter by organization_id.
  Never return documents from another organization — data isolation is critical.

ACCESS CONTROL (enforced here AND in the router):
  READ   → any authenticated org member (is_published=True only for regular members)
  CREATE → ORG_ADMIN only
  UPDATE → ORG_ADMIN only
  DELETE → ORG_ADMIN only

NOTE ON DRAFTS:
  Documents with is_published=False are "drafts". Regular members only see
  published documents. Admins can see all documents (published + drafts).
"""

import uuid
import logging
from typing import List, Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.knowledge_base import KnowledgeBaseDocument
from app.models.user import User, UserRole
from app.schemas.knowledge_base import (
    KBDocumentCreate,
    KBDocumentUpdate,
    KBDocumentResponse,
    KBDocumentListItem,
)

logger = logging.getLogger(__name__)


# ── List Documents ─────────────────────────────────────────────────────────────

def list_documents(
    db: Session,
    current_user: User,
    category: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[KBDocumentListItem]:
    """
    List all Knowledge Base documents for the current user's organization.

    MULTI-TENANT ISOLATION:
        Documents are always filtered by current_user.organization_id.

    ACCESS CONTROL:
        - Admins see all documents (published + drafts).
        - Regular members only see published documents (is_published=True).

    Args:
        db:           Database session.
        current_user: Authenticated user (determines org + role).
        category:     Optional filter by category tag.
        search:       Optional title substring search.
        skip:         Pagination offset (number of records to skip).
        limit:        Pagination limit (max records to return, capped at 100).

    Returns:
        List of KBDocumentListItem (without content body for performance).
    """
    limit = min(limit, 100)  # Hard cap to prevent abuse

    query = db.query(KnowledgeBaseDocument).filter(
        KnowledgeBaseDocument.organization_id == current_user.organization_id
    )

    # Non-admin users only see published documents
    is_admin = current_user.role in (UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
    if not is_admin:
        query = query.filter(KnowledgeBaseDocument.is_published == True)  # noqa: E712

    # Optional filters
    if category:
        query = query.filter(KnowledgeBaseDocument.category == category)

    if search:
        query = query.filter(
            KnowledgeBaseDocument.title.ilike(f"%{search}%")
        )

    # Order by newest first, paginate
    documents = (
        query
        .order_by(KnowledgeBaseDocument.updated_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [KBDocumentListItem.model_validate(doc) for doc in documents]


# ── Get Single Document ────────────────────────────────────────────────────────

def get_document(
    db: Session,
    document_id: uuid.UUID,
    current_user: User,
) -> KBDocumentResponse:
    """
    Fetch a single Knowledge Base document by ID.

    MULTI-TENANT ISOLATION:
        We filter by BOTH document_id AND organization_id — this ensures
        users cannot access documents from other organizations even if they
        guess a valid UUID.

    ACCESS CONTROL:
        - Admins can view any document (including drafts).
        - Members can only view published documents.

    Args:
        db:          Database session.
        document_id: UUID of the document to retrieve.
        current_user: Authenticated user.

    Returns:
        KBDocumentResponse with full content.

    Raises:
        404 Not Found: Document doesn't exist in the user's org, or member
                       tried to access a draft.
    """
    query = db.query(KnowledgeBaseDocument).filter(
        KnowledgeBaseDocument.id == document_id,
        KnowledgeBaseDocument.organization_id == current_user.organization_id,
    )

    # Non-admins cannot view drafts
    is_admin = current_user.role in (UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
    if not is_admin:
        query = query.filter(KnowledgeBaseDocument.is_published == True)  # noqa: E712

    document = query.first()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge Base document with id '{document_id}' was not found.",
        )

    return KBDocumentResponse.model_validate(document)


# ── Create Document ────────────────────────────────────────────────────────────

def create_document(
    db: Session,
    data: KBDocumentCreate,
    current_user: User,
) -> KBDocumentResponse:
    """
    Create a new Knowledge Base document.

    The document is automatically scoped to the admin's organization.
    The `created_by` field is set to the current admin's user ID.

    Args:
        db:           Database session.
        data:         KBDocumentCreate with title, content, etc.
        current_user: The ORG_ADMIN creating the document.

    Returns:
        KBDocumentResponse of the newly created document.

    Raises:
        400 Bad Request: Admin has no organization.
    """
    if current_user.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create document: your account has no organization.",
        )

    document = KnowledgeBaseDocument(
        organization_id=current_user.organization_id,
        title=data.title,
        content=data.content,
        category=data.category,
        created_by=current_user.id,
        is_published=data.is_published,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    logger.info(
        f"[KB] Admin '{current_user.email}' created document '{document.title}' "
        f"in org {current_user.organization_id}."
    )

    return KBDocumentResponse.model_validate(document)


# ── Update Document ────────────────────────────────────────────────────────────

def update_document(
    db: Session,
    document_id: uuid.UUID,
    data: KBDocumentUpdate,
    current_user: User,
) -> KBDocumentResponse:
    """
    Update an existing Knowledge Base document.

    MULTI-TENANT ISOLATION:
        Finds the document by ID + organization_id — admins cannot edit
        documents from other organizations.

    PATCH semantics:
        Only fields explicitly provided in `data` are updated.
        Omitted fields remain unchanged.

    Args:
        db:          Database session.
        document_id: UUID of the document to update.
        data:        KBDocumentUpdate with fields to change (all optional).
        current_user: The ORG_ADMIN making the update.

    Returns:
        Updated KBDocumentResponse.

    Raises:
        404 Not Found: Document not found in the admin's organization.
    """
    document = db.query(KnowledgeBaseDocument).filter(
        KnowledgeBaseDocument.id == document_id,
        KnowledgeBaseDocument.organization_id == current_user.organization_id,
    ).first()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge Base document with id '{document_id}' was not found.",
        )

    # Apply only the fields the client sent (exclude_unset = true PATCH semantics)
    update_fields = data.model_dump(exclude_unset=True)
    for field_name, field_value in update_fields.items():
        setattr(document, field_name, field_value)

    db.commit()
    db.refresh(document)

    logger.info(
        f"[KB] Admin '{current_user.email}' updated document '{document.title}' "
        f"(id={document_id})."
    )

    return KBDocumentResponse.model_validate(document)


# ── Delete Document ────────────────────────────────────────────────────────────

def delete_document(
    db: Session,
    document_id: uuid.UUID,
    current_user: User,
) -> None:
    """
    Permanently delete a Knowledge Base document.

    MULTI-TENANT ISOLATION:
        Deletes only within the admin's organization.

    Args:
        db:          Database session.
        document_id: UUID of the document to delete.
        current_user: The ORG_ADMIN performing the delete.

    Raises:
        404 Not Found: Document not found in the admin's organization.
    """
    document = db.query(KnowledgeBaseDocument).filter(
        KnowledgeBaseDocument.id == document_id,
        KnowledgeBaseDocument.organization_id == current_user.organization_id,
    ).first()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge Base document with id '{document_id}' was not found.",
        )

    title = document.title
    db.delete(document)
    db.commit()

    logger.info(
        f"[KB] Admin '{current_user.email}' deleted document '{title}' (id={document_id})."
    )
