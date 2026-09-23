"""
app/modules/auth/router.py
==========================
HTTP route handlers for all authentication endpoints.

ENDPOINTS:
  POST  /api/v1/auth/register          → create new org + admin
  POST  /api/v1/auth/register-member   → join org via invite token
  POST  /api/v1/auth/invite-member     → admin: invite someone to join [ADMIN ONLY]
  POST  /api/v1/auth/login             → login → JWT access + refresh token
  POST  /api/v1/auth/refresh           → get new access token from refresh token
  POST  /api/v1/auth/logout            → invalidate refresh token (true revocation)
  GET   /api/v1/auth/me                → get current user profile
  POST  /api/v1/auth/change-password   → change own password
  POST  /api/v1/auth/forgot-password   → request password reset token
  POST  /api/v1/auth/reset-password    → set new password using reset token
"""

from fastapi import APIRouter, Depends, Body, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.models.user import User
from app.modules.auth import service
from app.schemas.auth import (
    RegisterOrgRequest,
    RegisterMemberRequest,
    InviteMemberRequest,
    InviteResponse,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    LogoutResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    VerifyEmailRequest,
    ResendVerificationRequest,
)
from app.schemas.user import UserResponse


# Create the router for auth endpoints
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],  # Groups these endpoints in Swagger docs
)


# ── Register: New Organization + Admin ───────────────────────────────────────

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new organization and admin account",
    description=(
        "**First-time setup flow.** Creates a brand new Organization and its first Admin user "
        "in a single atomic transaction. The first user always receives the `ORG_ADMIN` role.\n\n"
        "Returns a token pair (access + refresh) so the admin is immediately logged in.\n\n"
        "**Password requirements:** min 8 chars, must include uppercase, lowercase, and a digit."
    ),
)
def register_org(
    request: RegisterOrgRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """POST /api/v1/auth/register"""
    return service.register_org_and_admin(db=db, request=request)


# ── Invite Member ─────────────────────────────────────────────────────────────

@router.post(
    "/invite-member",
    response_model=InviteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a new member to your organization [ADMIN ONLY]",
    description=(
        "**Admin only.** Generates a one-time invite token for the specified email address. "
        "In production this would send an email; in development, the token is returned in the "
        "response and logged to the server console.\n\n"
        "The invite expires after 48 hours. The invitee uses `POST /auth/register-member` "
        "with the token to create their account."
    ),
)
def invite_member(
    request: InviteMemberRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> InviteResponse:
    """POST /api/v1/auth/invite-member — requires ORG_ADMIN role"""
    return service.invite_member(db=db, request=request, admin=current_user)


# ── Register: Member via Invite ───────────────────────────────────────────────

@router.post(
    "/register-member",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Join an organization using an invite token",
    description=(
        "Complete your registration using the invite token sent by your organization's admin.\n\n"
        "Provide the `invite_token`, your `full_name`, and a `password`. "
        "The email is taken from the invite (cannot be changed for security).\n\n"
        "**Password requirements:** min 8 chars, must include uppercase, lowercase, and a digit."
    ),
)
def register_member(
    request: RegisterMemberRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """POST /api/v1/auth/register-member"""
    return service.register_member_via_invite(db=db, request=request)


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with email and password",
    description=(
        "Authenticate with your email and password.\n\n"
        "Returns:\n"
        "- `access_token`: Short-lived JWT (~60 min). Include in every request as "
        "`Authorization: Bearer <token>`\n"
        "- `refresh_token`: Long-lived opaque token (~7 days). Use **only** with "
        "`POST /auth/refresh` to get a new access token. Store securely.\n\n"
        "On each use of the refresh token, a new pair is issued (token rotation)."
    ),
)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """POST /api/v1/auth/login"""
    return service.authenticate_user(db=db, request=request)


# ── Refresh Token ─────────────────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a new access token using a refresh token",
    description=(
        "Use this endpoint when your access token expires.\n\n"
        "Send the `refresh_token` received at login. "
        "A new `access_token` and `refresh_token` pair is returned (token rotation — "
        "the old refresh token is invalidated).\n\n"
        "If the refresh token is invalid or expired, you must log in again."
    ),
)
def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """POST /api/v1/auth/refresh"""
    return service.refresh_access_token(db=db, request=request)


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout and invalidate refresh token",
    description=(
        "Invalidates your refresh token by deleting it from the database. "
        "Future refresh requests with the same token will be rejected.\n\n"
        "The access token remains valid until it expires (~60 min), but since "
        "it's short-lived, this is an acceptable trade-off.\n\n"
        "For immediate access token invalidation, reduce `ACCESS_TOKEN_EXPIRE_MINUTES` "
        "in your environment config."
    ),
)
def logout(
    request: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LogoutResponse:
    """POST /api/v1/auth/logout — requires valid access token"""
    service.logout_user(db=db, refresh_token=request.refresh_token)
    return LogoutResponse()


# ── Get Current User ──────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
    description=(
        "Returns the complete profile of the currently authenticated user. "
        "Requires a valid JWT access token in the Authorization header."
    ),
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """GET /api/v1/auth/me — requires Authorization: Bearer <token>"""
    return UserResponse.model_validate(current_user)


# ── Change Password ───────────────────────────────────────────────────────────

@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change your own password",
    description=(
        "Change the authenticated user's password. "
        "Must provide the correct current password for verification. "
        "The new password must meet strength requirements."
    ),
)
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """POST /api/v1/auth/change-password — requires Authorization: Bearer <token>"""
    service.change_password(
        db=db,
        current_user=current_user,
        current_password=request.current_password,
        new_password=request.new_password,
    )
    return {"message": "Password changed successfully."}


# ── Forgot Password ───────────────────────────────────────────────────────────

@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Request a password reset token",
    description=(
        "Generates a one-time password reset token for the given email.\n\n"
        "In production, the token would be emailed to the user. "
        "In development (`APP_ENV=development`), the token is also returned in "
        "the response body for easy testing.\n\n"
        "**Security:** The same response is returned whether the email exists or not, "
        "preventing user enumeration attacks.\n\n"
        "The token expires after 1 hour."
    ),
)
def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> ForgotPasswordResponse:
    """POST /api/v1/auth/forgot-password"""
    return service.forgot_password(db=db, email=request.email)


# ── Reset Password ────────────────────────────────────────────────────────────

@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Reset password using a reset token",
    description=(
        "Complete the password reset using the token received from `POST /auth/forgot-password`.\n\n"
        "The token is single-use and expires after 1 hour. "
        "After a successful reset, the token is invalidated."
    ),
)
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> dict:
    """POST /api/v1/auth/reset-password"""
    service.reset_password(db=db, token=request.token, new_password=request.new_password)
    return {"message": "Password reset successfully. You can now log in with your new password."}


# ── Verify Email ──────────────────────────────────────────────────────────────

@router.post(
    "/verify-email",
    status_code=status.HTTP_200_OK,
    summary="Verify user email address",
    description="Validates an email verification token and marks the user's email as verified.",
)
def verify_email(
    request: VerifyEmailRequest,
    db: Session = Depends(get_db),
) -> dict:
    """POST /api/v1/auth/verify-email"""
    return service.verify_email(db=db, request=request)


# ── Resend Verification Email ─────────────────────────────────────────────────

@router.post(
    "/resend-verification-email",
    status_code=status.HTTP_200_OK,
    summary="Resend email verification link",
    description="Resends the verification email if the user exists and is not already verified.",
)
def resend_verification_email(
    request: ResendVerificationRequest,
    db: Session = Depends(get_db),
) -> dict:
    """POST /api/v1/auth/resend-verification-email"""
    return service.resend_verification_email(db=db, request=request)
