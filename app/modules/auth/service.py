"""
app/modules/auth/service.py
===========================
Authentication business logic for VoxOps.

HOW IT WORKS:
- The "service" layer contains the actual logic (no HTTP stuff).
- Routers call service functions and convert results into HTTP responses.
- This separation keeps the code organized and easier to test.

WHAT THIS FILE DOES:
- authenticate_user()  → check email/password, return JWT
- change_password()    → verify current password, hash+save new password
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.security import verify_password, hash_password, create_access_token
from app.models.user import User, UserStatus
from app.schemas.auth import LoginRequest, TokenResponse


def authenticate_user(db: Session, request: LoginRequest) -> TokenResponse:
    """
    Verify credentials and return a JWT token.

    Steps:
    1. Find the user by email.
    2. Verify the password matches the stored hash.
    3. Check the account is ACTIVE.
    4. Create and return a JWT containing user identity.

    Security notes:
    - We use the SAME error message for "wrong email" and "wrong password".
      This prevents attackers from knowing which one was wrong (user enumeration).
    - Only ACTIVE users get a token.

    Args:
        db:      Database session (injected by FastAPI).
        request: LoginRequest containing email and password.

    Returns:
        TokenResponse with access_token and token_type.

    Raises:
        401 Unauthorized: Wrong email or password.
        403 Forbidden:    Account is inactive or suspended.
    """

    # Step 1: Find user by email
    user: User | None = db.query(User).filter(User.email == request.email).first()

    # Step 2: Verify password
    # IMPORTANT: We check BOTH "user not found" AND "wrong password" with the same error.
    # This prevents user enumeration attacks.
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Step 3: Check account status
    if user.status == UserStatus.INACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Contact your administrator.",
        )
    if user.status == UserStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been suspended. Contact your administrator.",
        )

    # Step 4: Create JWT token
    # Convert UUIDs to strings for JWT (JWT doesn't support UUID type natively)
    token = create_access_token(
        user_id=str(user.id),
        organization_id=str(user.organization_id) if user.organization_id else None,
        role=user.role.value,
    )

    return TokenResponse(access_token=token, token_type="bearer")


def change_password(
    db: Session,
    current_user: User,
    current_password: str,
    new_password: str,
) -> None:
    """
    Change a user's password after verifying the current one.

    Steps:
    1. Verify the current password matches stored hash.
    2. Hash the new password.
    3. Save the new hash to the database.

    Args:
        db:               Database session.
        current_user:     The authenticated User object.
        current_password: Plain-text current password for verification.
        new_password:     Plain-text new password to set.

    Raises:
        400 Bad Request: If current password is wrong.
        400 Bad Request: If new password is same as current.
    """

    # Verify the current password
    if not verify_password(current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    # Prevent setting the same password
    if verify_password(new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password.",
        )

    # Hash and save the new password
    current_user.password_hash = hash_password(new_password)
    db.commit()
