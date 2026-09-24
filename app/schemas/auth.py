"""
app/schemas/auth.py
===================
Pydantic schemas for authentication-related API requests and responses.

HOW IT WORKS:
- Request schemas: validate what the client sends IN (input validation).
- Response schemas: define what we send OUT (never include password_hash!).
- Pydantic v2 raises clear validation errors automatically if input is wrong.
"""

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, ConfigDict, Field


# ── Login ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """
    Body for POST /api/v1/auth/login
    Client sends email + password to get a JWT token.
    """
    email: str = Field(
        ...,
        description="User's email address",
        examples=["jane@example.com"],
    )
    password: str = Field(
        ...,
        min_length=1,
        description="User's plain-text password (only ever sent over HTTPS, never stored)",
        examples=["ChangeMe123!"],
    )


# ── Token Response ────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """
    Response for POST /api/v1/auth/login and POST /api/v1/auth/refresh
    The client stores these tokens and sends access_token in future requests.
    """
    access_token: str = Field(
        ...,
        description="Signed JWT access token",
    )
    refresh_token: str = Field(
        ...,
        description="Opaque refresh token for obtaining new access tokens",
    )
    token_type: str = Field(
        default="bearer",
        description="Always 'bearer' — standard OAuth2 token type",
    )
    expires_in: int = Field(
        default=1800,
        description="Access token expiration time in seconds (30 minutes)",
    )


class RefreshRequest(BaseModel):
    """
    Body for POST /api/v1/auth/refresh
    Client sends valid refresh_token to issue a new access_token.
    """
    refresh_token: str = Field(
        ...,
        min_length=1,
        description="Valid refresh token string previously received from login",
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
