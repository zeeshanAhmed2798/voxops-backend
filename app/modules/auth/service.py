"""
app/modules/auth/service.py
===========================
Authentication business logic for VoxOps.

HOW IT WORKS:
- The "service" layer contains the actual logic (no HTTP stuff).
- Routers call service functions and convert results into HTTP responses.
- This separation keeps the code organized and easier to test.

WHAT THIS FILE DOES:
- register_org_and_admin()      → creates Org + Admin User atomically
- register_member_via_invite()  → validates invite token, creates member
- invite_member()               → admin creates invite token (logged to console)
- authenticate_user()           → check email/password, return JWT pair
- refresh_access_token()        → validate refresh token, issue new access token
- logout_user()                 → delete refresh token from DB (true revocation)
- forgot_password()             → generate password reset token (logged to console)
- reset_password()              → validate reset token, set new password
- change_password()             → verify current password, hash+save new one
"""

import re
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    generate_secure_token,
)
from app.models.organization import Organization
from app.models.user import User, UserRole, UserStatus
from app.models.refresh_token import RefreshToken
from app.models.password_reset_token import PasswordResetToken
from app.models.invite_token import InviteToken
from app.models.email_verification_token import EmailVerificationToken
from app.services.email_service import send_email
from app.schemas.auth import (
    RegisterOrgRequest,
    RegisterMemberRequest,
    InviteMemberRequest,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    InviteResponse,
    ForgotPasswordResponse,
    VerifyEmailRequest,
    ResendVerificationRequest,
)

logger = logging.getLogger(__name__)

# How long password reset tokens are valid (1 hour)
_RESET_TOKEN_EXPIRE_HOURS = 1

# How long invite tokens are valid (48 hours)
_INVITE_TOKEN_EXPIRE_HOURS = 48


# ── Helpers ───────────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    """
    Convert a string to a URL-safe slug.
    Example: "Acme Corp Ltd." → "acme-corp-ltd"
    """
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)   # Remove non-word chars (except spaces/dashes)
    slug = re.sub(r"[\s_]+", "-", slug)    # Replace spaces/underscores with dashes
    slug = re.sub(r"-+", "-", slug)        # Collapse multiple dashes
    slug = slug.strip("-")                  # Remove leading/trailing dashes
    return slug


def _make_token_pair(db: Session, user: User) -> TokenResponse:
    """
    Create an access token + refresh token for a user and persist the refresh token.

    Called after login or registration to create a full session.
    """
    # Create JWT access token
    access_token = create_access_token(
        user_id=str(user.id),
        organization_id=str(user.organization_id) if user.organization_id else None,
        role=user.role.value,
    )

    # Create opaque refresh token
    raw_refresh = create_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    # Persist refresh token in DB
    db_token = RefreshToken(
        user_id=user.id,
        token=raw_refresh,
        expires_at=expires_at,
    )
    db.add(db_token)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        token_type="bearer",
    )


def _send_verification_email(db: Session, user: User) -> None:
    """Generates a verification token and sends the verification email."""
    # Delete any existing unused tokens
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id,
        EmailVerificationToken.is_used == False  # noqa: E712
    ).delete()
    
    token = generate_secure_token(32)
    db_token = EmailVerificationToken(user_id=user.id, token=token)
    db.add(db_token)
    db.commit()
    
    verify_link = f"{settings.FRONTEND_ORIGIN}/verify-email?token={token}"
    
    send_email(
        to=user.email,
        subject="Verify your email - VoxOps",
        template_name="email_verification.html",
        context={"name": user.name, "link": verify_link}
    )


# ── Register: New Organization + Admin ───────────────────────────────────────

def register_org_and_admin(db: Session, request: RegisterOrgRequest) -> TokenResponse:
    """
    Create a new Organization and its first Admin User in a single atomic transaction.

    Steps:
    1. Validate that the email isn't already registered.
    2. Generate or validate the org slug (must be unique).
    3. Create the Organization row.
    4. Create the User row with role=ORG_ADMIN.
    5. Return a JWT token pair (logged in immediately after registration).

    Args:
        db:      Database session.
        request: RegisterOrgRequest with org details + admin credentials.

    Returns:
        TokenResponse with access_token + refresh_token.

    Raises:
        409 Conflict: Email already registered.
        409 Conflict: Org slug already taken.
        422 Unprocessable: Validation errors (password strength, email format).
    """

    # 1. Check email uniqueness
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An account with email '{request.email}' already exists.",
        )

    # 2. Generate slug if not provided, then check uniqueness
    slug = request.org_slug or _slugify(request.org_name)
    existing_org = db.query(Organization).filter(Organization.slug == slug).first()
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Organization slug '{slug}' is already taken. Choose a different name or provide a custom slug.",
        )

    try:
        # 3. Create the Organization
        org = Organization(
            name=request.org_name,
            slug=slug,
        )
        db.add(org)
        db.flush()  # flush to get org.id without committing yet

        # 4. Create the Admin User
        user = User(
            organization_id=org.id,
            name=request.full_name,
            email=request.email,
            password_hash=hash_password(request.password),
            role=UserRole.ORG_ADMIN,
            status=UserStatus.ACTIVE,
            is_email_verified=False,  # email verification is a future enhancement
        )
        db.add(user)
        db.flush()  # flush to get user.id

        # 5. Issue a token pair (and commit everything atomically via _make_token_pair)
        token_pair = _make_token_pair(db, user)
        # _make_token_pair does db.commit()
        
        _send_verification_email(db, user)

        logger.info(
            f"[REGISTER] New org '{org.name}' (slug={org.slug}) "
            f"with admin '{user.email}' created."
        )
        return token_pair

    except Exception:
        db.rollback()
        raise


# ── Invite Member (Admin sends invite) ───────────────────────────────────────

def invite_member(db: Session, request: InviteMemberRequest, admin: User) -> InviteResponse:
    """
    Generate an invite token for a new member to join the admin's organization.

    Simulates email delivery by logging the token to the console.
    In production, replace the logger.info call with an actual email send.

    Args:
        db:      Database session.
        request: InviteMemberRequest with email, name, and role.
        admin:   The current ORG_ADMIN user (from require_admin dependency).

    Returns:
        InviteResponse containing the token (for development/testing).

    Raises:
        400 Bad Request: Admin has no organization (shouldn't happen in normal flow).
        409 Conflict: That email is already a registered user.
        400 Bad Request: Invalid role string provided.
    """
    if admin.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin account has no organization.",
        )

    # Check if the email is already a registered user
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with email '{request.email}' already exists.",
        )

    # Validate role
    valid_member_roles = {r.value for r in UserRole} - {UserRole.SUPER_ADMIN.value}
    if request.role not in valid_member_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role '{request.role}'. Valid roles: {sorted(valid_member_roles)}",
        )

    # Expire any previous pending invites for this email+org
    db.query(InviteToken).filter(
        InviteToken.email == request.email,
        InviteToken.organization_id == admin.organization_id,
        InviteToken.is_used == False,  # noqa: E712
    ).delete()

    # Generate new invite token
    token = generate_secure_token(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=_INVITE_TOKEN_EXPIRE_HOURS)

    invite = InviteToken(
        organization_id=admin.organization_id,
        email=request.email,
        token=token,
        role=request.role,
        expires_at=expires_at,
    )
    db.add(invite)
    db.commit()

    org = db.query(Organization).filter(Organization.id == admin.organization_id).first()
    invite_link = f"{settings.FRONTEND_ORIGIN}/accept-invite?token={token}"

    send_email(
        to=request.email,
        subject=f"You've been invited to join {org.name} on VoxOps",
        template_name="organization_invite.html",
        context={
            "org_name": org.name,
            "inviter_name": admin.name,
            "link": invite_link
        }
    )

    return InviteResponse(
        message=f"Invite sent to {request.email}. "
                f"They can register using the token at POST /api/v1/auth/register-member.",
        invite_token=token if settings.APP_ENV == "development" else "",
        expires_in_hours=_INVITE_TOKEN_EXPIRE_HOURS,
    )


# ── Register: Member via Invite Token ─────────────────────────────────────────

def register_member_via_invite(
    db: Session, request: RegisterMemberRequest
) -> TokenResponse:
    """
    Allow an invited person to create their account using a valid invite token.

    Steps:
    1. Find the invite token in the DB.
    2. Validate: not expired, not already used.
    3. Check email uniqueness.
    4. Create the User with the role specified in the invite.
    5. Mark the invite as used.
    6. Return a JWT token pair.

    Args:
        db:      Database session.
        request: RegisterMemberRequest with invite_token, full_name, password.

    Returns:
        TokenResponse with access_token + refresh_token.

    Raises:
        400 Bad Request: Invalid, expired, or already-used invite token.
        409 Conflict:    Email already registered.
    """

    # 1. Find the invite token
    invite = db.query(InviteToken).filter(
        InviteToken.token == request.invite_token
    ).first()

    if invite is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invite token. Please ask your admin to send a new invite.",
        )

    # 2. Validate token
    if invite.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invite has already been used.",
        )
    if datetime.now(timezone.utc) > invite.expires_at.replace(tzinfo=timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invite has expired. Please ask your admin to send a new invite.",
        )

    # 3. Check email uniqueness
    existing = db.query(User).filter(User.email == invite.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An account with email '{invite.email}' already exists. Try logging in.",
        )

    try:
        # 4. Create the member user
        user = User(
            organization_id=invite.organization_id,
            name=request.full_name,
            email=invite.email,  # Use the invited email (not user-supplied — security)
            password_hash=hash_password(request.password),
            role=UserRole(invite.role),
            status=UserStatus.ACTIVE,
            is_email_verified=True,  # Automatically verified since they proved access via email
        )
        db.add(user)
        db.flush()

        # 5. Mark invite as used
        invite.is_used = True

        # 6. Issue token pair
        token_pair = _make_token_pair(db, user)

        logger.info(
            f"[REGISTER MEMBER] '{user.email}' joined org {invite.organization_id} "
            f"with role {user.role.value}."
        )
        return token_pair

    except Exception:
        db.rollback()
        raise


# ── Login ─────────────────────────────────────────────────────────────────────

def authenticate_user(db: Session, request: LoginRequest) -> TokenResponse:
    """
    Verify credentials and return a JWT access + refresh token pair.

    Steps:
    1. Find the user by email.
    2. Verify the password matches the stored hash.
    3. Check the account is ACTIVE.
    4. Create and return a JWT + refresh token.

    Security notes:
    - We use the SAME error message for "wrong email" and "wrong password".
      This prevents attackers from knowing which one was wrong (user enumeration).
    - Only ACTIVE users get a token.

    Args:
        db:      Database session.
        request: LoginRequest containing email and password.

    Returns:
        TokenResponse with access_token, refresh_token, and token_type.

    Raises:
        401 Unauthorized: Wrong email or password.
        403 Forbidden:    Account is inactive or suspended.
    """

    # Step 1: Find user by email
    user: User | None = db.query(User).filter(User.email == request.email).first()

    # Step 2: Verify password
    # IMPORTANT: Same error for "wrong email" and "wrong password" — prevents enumeration.
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

    if settings.REQUIRE_EMAIL_VERIFICATION and not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before logging in.",
        )

    # Step 4: Issue token pair
    return _make_token_pair(db, user)


# ── Refresh Access Token ──────────────────────────────────────────────────────

def refresh_access_token(db: Session, request: RefreshTokenRequest) -> TokenResponse:
    """
    Validate a refresh token and issue a new access token.

    Strategy: Token rotation — when a refresh token is used, we delete the
    old one and issue a brand new refresh + access pair. This limits the
    window of exposure if a refresh token is stolen.

    Args:
        db:      Database session.
        request: RefreshTokenRequest containing the refresh_token.

    Returns:
        New TokenResponse with fresh access_token + refresh_token.

    Raises:
        401 Unauthorized: Token not found, expired, or associated user is inactive.
    """
    _credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Look up the token in the DB
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token == request.refresh_token
    ).first()

    if db_token is None:
        raise _credentials_error

    # Check expiry
    if datetime.now(timezone.utc) > db_token.expires_at.replace(tzinfo=timezone.utc):
        db.delete(db_token)
        db.commit()
        raise _credentials_error

    # Fetch the user
    user = db.query(User).filter(User.id == db_token.user_id).first()
    if user is None or user.status != UserStatus.ACTIVE:
        db.delete(db_token)
        db.commit()
        raise _credentials_error

    # Token rotation: delete the old token, issue a new pair
    db.delete(db_token)
    db.flush()

    return _make_token_pair(db, user)


# ── Logout ────────────────────────────────────────────────────────────────────

def logout_user(db: Session, refresh_token: str) -> None:
    """
    Logout: delete the refresh token from the database.

    This immediately invalidates the session. The access token will still
    be valid until it expires (typically 60 minutes), but since it's
    short-lived this is an acceptable trade-off for a stateless architecture.

    Args:
        db:            Database session.
        refresh_token: The refresh token to revoke.
    """
    db.query(RefreshToken).filter(
        RefreshToken.token == refresh_token
    ).delete()
    db.commit()


# ── Forgot Password ───────────────────────────────────────────────────────────

def forgot_password(db: Session, email: str) -> ForgotPasswordResponse:
    """
    Generate a password reset token and simulate email delivery.

    Security: We always return the same response regardless of whether
    the email exists — this prevents user enumeration.

    Args:
        db:    Database session.
        email: The user's email address.

    Returns:
        ForgotPasswordResponse (same message whether email exists or not).
        In development: also returns the reset_token field for testing.
    """
    _generic_response = ForgotPasswordResponse()  # No token in production-mode response

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        # Don't reveal whether the email exists
        return _generic_response

    # Invalidate any existing reset tokens for this user
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.is_used == False,  # noqa: E712
    ).delete()

    # Generate new reset token
    token = generate_secure_token(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=_RESET_TOKEN_EXPIRE_HOURS)

    db_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=expires_at,
    )
    db.add(db_token)
    db.commit()

    reset_link = f"{settings.FRONTEND_ORIGIN}/reset-password?token={token}"
    send_email(
        to=email,
        subject="Reset your VoxOps password",
        template_name="password_reset.html",
        context={"link": reset_link}
    )

    # In DEV mode, also return the token in the response for easy testing
    return ForgotPasswordResponse(
        reset_token=token if settings.APP_ENV == "development" else None
    )


# ── Reset Password ────────────────────────────────────────────────────────────

def reset_password(db: Session, token: str, new_password: str) -> None:
    """
    Validate a reset token and set the user's new password.

    Steps:
    1. Find the token in the DB.
    2. Check it's not expired and not already used.
    3. Hash and save the new password.
    4. Mark the token as used.

    Args:
        db:           Database session.
        token:        The reset token from forgot_password().
        new_password: The new plain-text password (already validated by schema).

    Raises:
        400 Bad Request: Invalid, expired, or already-used token.
    """
    db_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token
    ).first()

    if db_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token.",
        )

    if db_token.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset token has already been used.",
        )

    if datetime.now(timezone.utc) > db_token.expires_at.replace(tzinfo=timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset token has expired. Please request a new one.",
        )

    user = db.query(User).filter(User.id == db_token.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found.",
        )

    # Update password and mark token as used
    user.password_hash = hash_password(new_password)
    db_token.is_used = True
    db.commit()

    logger.info(f"[PASSWORD RESET] User '{user.email}' successfully reset their password.")


# ── Change Password ───────────────────────────────────────────────────────────

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


# ── Verify Email ──────────────────────────────────────────────────────────────

def verify_email(db: Session, request: VerifyEmailRequest) -> dict:
    """
    Validate the email verification token and mark the user's email as verified.
    """
    db_token = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token == request.token
    ).first()

    if db_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token.",
        )

    if db_token.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This verification token has already been used.",
        )

    if db_token.is_expired():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This verification token has expired. Please request a new one.",
        )

    user = db.query(User).filter(User.id == db_token.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found.",
        )

    user.is_email_verified = True
    db_token.is_used = True
    db.commit()

    logger.info(f"[EMAIL VERIFICATION] User '{user.email}' successfully verified their email.")
    return {"message": "Email verified successfully."}


# ── Resend Verification Email ─────────────────────────────────────────────────

def resend_verification_email(db: Session, request: ResendVerificationRequest) -> dict:
    """
    Resend the verification email if the user is not already verified.
    """
    user = db.query(User).filter(User.email == request.email).first()
    
    # Do not reveal whether user exists for security, return success message anyway
    if user is not None and not user.is_email_verified:
        _send_verification_email(db, user)
        logger.info(f"[EMAIL VERIFICATION] Resent verification email to '{user.email}'.")

    return {"message": "If the email is registered and unverified, a new verification link has been sent."}
