"""
app/modules/users/router.py
===========================
HTTP route handlers for user profile endpoints.

ENDPOINTS:
  GET   /api/v1/users/me   → get own profile
  PATCH /api/v1/users/me   → update own profile (safe fields only)

Both endpoints require a valid JWT (via get_current_user dependency).
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.modules.users import service
from app.schemas.user import UserResponse, UpdateProfileRequest
from app.shared.response import BaseResponse, ok


router = APIRouter(
    prefix="/users",
    tags=["User Profile"],  # Groups these in Swagger docs
)


@router.get(
    "/me",
    response_model=BaseResponse[UserResponse],
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
    summary="Get my profile",
    description=(
        "Returns the complete profile of the currently authenticated user. "
        "Requires a valid JWT bearer token."
    ),
)
def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> BaseResponse[UserResponse]:
    """GET /api/v1/users/me"""
    return ok("Profile retrieved successfully.", service.get_user_profile(current_user=current_user))


@router.patch(
    "/me",
    response_model=BaseResponse[UserResponse],
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
    summary="Update my profile",
    description=(
        "Update your own profile fields. "
        "Only send the fields you want to change (PATCH semantics). "
        "You cannot change: id, organization_id, role, status, email, or password_hash. "
        "Role and organization changes require administrator action."
    ),
)
def update_my_profile(
    update_data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BaseResponse[UserResponse]:
    """PATCH /api/v1/users/me"""
    profile = service.update_user_profile(
        db=db,
        current_user=current_user,
        update_data=update_data,
    )
    return ok("Profile updated successfully.", profile)
