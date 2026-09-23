"""
app/schemas/auth.py
===================
Pydantic schemas for authentication-related API requests and responses.

HOW IT WORKS:
- Request schemas: validate what the client sends IN (input validation).
- Response schemas: define what we send OUT (never include password_hash!).
- Pydantic v2 raises clear validation errors automatically if input is wrong.

PASSWORD STRENGTH RULE:
  Minimum 8 characters with at least one uppercase letter, one lowercase
  letter, and one digit. Validated via a custom validator.
"""

import re
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ── Password Strength Validator ───────────────────────────────────────────────

def _validate_password_strength(v: str) -> str:
    """
    Enforce minimum password requirements:
    - At least 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 digit

    Raises ValueError on failure (Pydantic converts to 422 with clear message).
    """
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", v):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain at least one digit.")
    return v


# ── Register: New Organization + Admin ───────────────────────────────────────

class RegisterOrgRequest(BaseModel):
    """
    Body for POST /api/v1/auth/register

    Creates a brand new Organization and its first Admin user in one
    atomic transaction. The first user always gets the ORG_ADMIN role.

    Fields:
      org_name  : Display name of the organization
      org_slug  : URL-safe unique identifier (auto-generated if omitted)
      full_name : Admin's full name
      email     : Admin's email (must be unique system-wide)
      password  : Admin's password (must meet strength requirements)
    """
    org_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Your company / organization name",
        examples=["Acme Corporation"],
    )
    org_slug: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="URL-safe slug (auto-generated from org_name if omitted)",
        examples=["acme-corporation"],
    )
    full_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Your full name (as the admin user)",
        examples=["Jane Doe"],
    )
    email: EmailStr = Field(
        ...,
        description="Your work email — must be unique across the platform",
        examples=["jane@acmecorp.com"],
    )
    password: str = Field(
        ...,
        description="Password — min 8 chars, must include upper, lower, and digit",
        examples=["SecurePass123"],
    )

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


# ── Register: New Member via Invite Token ────────────────────────────────────

class RegisterMemberRequest(BaseModel):
    """
    Body for POST /api/v1/auth/register-member

    An invited user (who received an invite token from an admin)
    uses this endpoint to create their account.

    The invite_token encodes: which org, which email, which role.
    The invitee provides their name and chosen password.
    """
    invite_token: str = Field(
        ...,
        description="The invite token sent to your email by your organization's admin",
        examples=["abc123xyz..."],
    )
    full_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Your full name",
        examples=["John Smith"],
    )
    password: str = Field(
        ...,
        description="Password — min 8 chars, must include upper, lower, and digit",
        examples=["MyPassword456"],
    )

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


# ── Invite Member (Admin sends invite) ───────────────────────────────────────

class InviteMemberRequest(BaseModel):
    """
    Body for POST /api/v1/auth/invite-member  (ADMIN ONLY)

    Admin specifies who to invite and what role to assign them.
    A token is generated and logged (simulating email delivery).
    """
    email: EmailStr = Field(
        ...,
        description="Email address of the person to invite",
        examples=["bob@acmecorp.com"],
    )
    full_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the person being invited (for the welcome email)",
        examples=["Bob Johnson"],
    )
    role: str = Field(
        default="EMPLOYEE",
        description="Role to assign: EMPLOYEE, SUPERVISOR, DEPARTMENT_AGENT, FIELD_WORKER",
        examples=["EMPLOYEE"],
    )


class InviteResponse(BaseModel):
    """Response when an admin creates an invite."""
    message: str
    invite_token: str = Field(
        description="The invite token (in production this would be sent via email, not returned here)"
    )
    expires_in_hours: int


# ── Login ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """
    Body for POST /api/v1/auth/login
    Client sends email + password to get JWT tokens.
    """
    email: EmailStr = Field(
        ...,
        description="User's email address — must be a valid email format",
        examples=["jane@example.com"],
    )
    password: str = Field(
        ...,
        min_length=1,
        description="User's plain-text password (only ever sent over HTTPS, never stored)",
        examples=["ChangeMe123!"],
    )


# ── Token Responses ───────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """
    Response for POST /api/v1/auth/login — includes both access and refresh token.

    access_token : Short-lived JWT. Send in every API request header.
    refresh_token: Long-lived opaque token. Use ONLY to refresh the access token.
                   Store securely (httpOnly cookie or secure storage).
    """
    access_token: str = Field(..., description="JWT access token (short-lived, ~60 min)")
    refresh_token: str = Field(..., description="Opaque refresh token (long-lived, ~7 days)")
    token_type: str = Field(default="bearer", description="Always 'bearer'")


class RefreshTokenRequest(BaseModel):
    """Body for POST /api/v1/auth/refresh"""
    refresh_token: str = Field(
        ...,
        description="The refresh token received at login",
    )


# ── Logout Response ───────────────────────────────────────────────────────────

class LogoutResponse(BaseModel):
    """Response for POST /api/v1/auth/logout"""
    message: str = Field(
        default="Logged out successfully. Your session has been invalidated."
    )


# ── Password Reset ────────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    """
    Body for POST /api/v1/auth/forgot-password

    Security note: We always return the same response whether the email
    exists or not — this prevents user enumeration attacks.
    """
    email: EmailStr = Field(
        ...,
        description="The email address associated with your account",
        examples=["jane@example.com"],
    )


class ForgotPasswordResponse(BaseModel):
    """Response for POST /api/v1/auth/forgot-password"""
    message: str = Field(
        default=(
            "If an account with that email exists, a password reset link has been sent. "
            "Check your inbox (and spam folder). The link expires in 1 hour."
        )
    )
    # In production, we'd NOT return the token here. We return it for testing/demo purposes.
    reset_token: Optional[str] = Field(
        default=None,
        description="[DEV ONLY] The reset token (in production this is emailed, not returned)",
    )


class ResetPasswordRequest(BaseModel):
    """Body for POST /api/v1/auth/reset-password"""
    token: str = Field(
        ...,
        description="The reset token from the forgot-password step",
    )
    new_password: str = Field(
        ...,
        description="Your new password — min 8 chars, must include upper, lower, and digit",
        examples=["NewSecurePass789"],
    )

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class VerifyEmailRequest(BaseModel):
    """Body for GET /api/v1/auth/verify-email"""
    token: str = Field(
        ...,
        description="The verification token sent to the user's email",
    )


class ResendVerificationRequest(BaseModel):
    """Body for POST /api/v1/auth/resend-verification-email"""
    email: EmailStr = Field(
        ...,
        description="The email address to resend the verification link to",
        examples=["jane@example.com"],
    )


# ── Change Password ───────────────────────────────────────────────────────────

class ChangePasswordRequest(BaseModel):
    """
    Body for POST /api/v1/auth/change-password
    User must prove they know the current password before setting a new one.
    """
    current_password: str = Field(
        ...,
        min_length=1,
        description="The user's current password to verify identity",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        description="New password — must be at least 8 characters",
    )
