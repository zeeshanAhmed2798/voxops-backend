"""
app/modules/users/service.py
============================
User profile business logic.

WHAT THIS FILE DOES:
- get_user_profile()    → fetch and return the current user's profile
- update_user_profile() → apply safe profile field updates

WHY SEPARATE SERVICE?
- Keeps HTTP handling (router.py) separate from database logic (service.py).
- Makes testing easier — you can test service functions without HTTP.
- Other modules can call these functions directly if needed.
"""

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UpdateProfileRequest, UserResponse


def get_user_profile(current_user: User) -> UserResponse:
    """
    Return the authenticated user's profile as a UserResponse schema.

    This is straightforward: convert the SQLAlchemy User object to the
    Pydantic UserResponse (which excludes password_hash automatically).

    Args:
        current_user: The authenticated User fetched from the DB.

    Returns:
        UserResponse with all safe profile fields.
    """
    return UserResponse.model_validate(current_user)


def update_user_profile(
    db: Session,
    current_user: User,
    update_data: UpdateProfileRequest,
) -> UserResponse:
    """
    Update allowed profile fields on the current user.

    WHAT CAN BE UPDATED:
        name, job_title, phone, timezone, profile_picture

    WHAT CANNOT BE UPDATED (protected by design — not in UpdateProfileRequest):
        id, organization_id, department_id, role, status, email, password_hash

    HOW IT WORKS:
    - We use model_dump(exclude_unset=True) to get only the fields the user
      actually sent. This means a PATCH request with just {"name": "Bob"}
      will ONLY update the name — all other fields stay unchanged.

    Args:
        db:           Database session.
        current_user: The authenticated User to update.
        update_data:  UpdateProfileRequest containing the fields to change.

    Returns:
        Updated UserResponse.
    """

    # exclude_unset=True: only includes fields the client explicitly sent
    # e.g. {"name": "Bob"} → only updates name, doesn't touch job_title etc.
    update_fields = update_data.model_dump(exclude_unset=True)

    if not update_fields:
        # Nothing to update — just return current profile
        return UserResponse.model_validate(current_user)

    # Apply each field to the SQLAlchemy model object
    for field_name, field_value in update_fields.items():
        setattr(current_user, field_name, field_value)

    # Persist changes to the database
    db.commit()
    db.refresh(current_user)  # Reload from DB to get updated timestamps

    return UserResponse.model_validate(current_user)
