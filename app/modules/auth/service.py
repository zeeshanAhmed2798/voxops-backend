"""
app/modules/auth/service.py
===========================
Authentication business logic for VoxOps.

HOW IT WORKS:
- The "service" layer contains the actual logic (no HTTP stuff).
- Routers call service functions and convert results into HTTP responses.
- This separation keeps the code organized and easier to test.

WHAT THIS FILE DOES:
- authenticate_user()   → check email/password, return access & refresh JWT tokens
- refresh_tokens_flow() → validate refresh token, issue new tokens
- change_password()     → verify current password, hash+save new password
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import verify_password, hash_password, create_access_token, create_refresh_token
from app.models.user import User, UserStatus
from app.models.token import RefreshToken
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest


def authenticate_user(db: Session, request: LoginRequest) -> TokenResponse:
    """
    Verify credentials and return access and refresh tokens.

    Steps:
    1. Find the user by email.
    2. Verify the password matches the stored hash.
    3. Check the account is ACTIVE.
    4. Create JWT access token and opaque refresh token.
    5. Save refresh token in database (table refresh_tokens).
    """

    # Step 1: Find user by email
    user: User | None = db.query(User).filter(User.email == request.email).first()

    # Step 2: Verify password
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

    # Step 4: Create access token
    access_token = create_access_token(
        user_id=str(user.id),
        organization_id=str(user.organization_id) if user.organization_id else None,
        role=user.role.value,
    )

    # Step 5: Create and store refresh token (expires in 7 days by default)
    refresh_token_str = create_refresh_token()
    refresh_days = getattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7) or 7
    expires_at = datetime.now(timezone.utc) + timedelta(days=refresh_days)

    db_refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        expires_at=expires_at,
    )
    db.add(db_refresh_token)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def refresh_tokens_flow(db: Session, request: RefreshRequest) -> TokenResponse:
    """
    Validate a refresh token and issue a new pair of access & refresh tokens.
    Single-use refresh token rotation for maximum security.
    """
    token_record: RefreshToken | None = (
        db.query(RefreshToken)
        .filter(RefreshToken.token == request.refresh_token)
        .first()
    )

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check expiration (handle naive datetimes from SQLite in tests)
    now = datetime.now(timezone.utc)
    expires_at = token_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= now:
        db.delete(token_record)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Fetch user & check active status
    user: User | None = db.query(User).filter(User.id == token_record.user_id).first()
    if not user or user.status != UserStatus.ACTIVE:
        db.delete(token_record)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account associated with token is inactive or suspended.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Single-use: delete consumed refresh token
    db.delete(token_record)

    # Generate new token pair
    new_access_token = create_access_token(
        user_id=str(user.id),
        organization_id=str(user.organization_id) if user.organization_id else None,
        role=user.role.value,
    )
    new_refresh_str = create_refresh_token()
    refresh_days = getattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7) or 7
    new_expires_at = datetime.now(timezone.utc) + timedelta(days=refresh_days)

    new_token_record = RefreshToken(
        user_id=user.id,
        token=new_refresh_str,
        expires_at=new_expires_at,
    )
    db.add(new_token_record)
    db.commit()

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_str,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def change_password(
    db: Session,
    current_user: User,
    current_password: str,
    new_password: str,
) -> None:
    """
    Change a user's password after verifying the current one.
    """
    if not verify_password(current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    if verify_password(new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password.",
        )

    current_user.password_hash = hash_password(new_password)
    db.commit()
