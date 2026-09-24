"""
app/core/security.py
====================
Security utilities: password hashing and JWT token management.

HOW IT WORKS:
- Passwords: We use bcrypt (via passlib). It's slow on purpose — hard to brute-force.
- JWT: We encode user identity into a signed token. The signature uses JWT_SECRET.
  Anyone with the secret can verify the token is genuine (not tampered with).
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


# ── Password Hashing ────────────────────────────────────────────────────────
# CryptContext manages hashing schemes. 'bcrypt' is the algorithm.
# deprecated="auto" means old hashes get upgraded automatically.
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password using bcrypt.
    Store the result (password_hash) — NEVER store the original password.

    Example:
        hashed = hash_password("MySecret123!")
    """
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check if a plain-text password matches a stored bcrypt hash.
    Returns True if they match, False otherwise.

    Example:
        ok = verify_password("MySecret123!", stored_hash)
    """
    return _pwd_context.verify(plain_password, hashed_password)


# ── JWT Token Management ─────────────────────────────────────────────────────
def create_access_token(
    user_id: str,
    organization_id: Optional[str],
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a signed JWT access token containing the user's identity.

    The token encodes:
      - sub           : user's UUID (standard JWT 'subject' claim)
      - organization_id : which org this user belongs to (for isolation)
      - role          : user's role (for authorization checks)
      - exp           : expiration timestamp

    The token is SIGNED with JWT_SECRET — if someone tampers with the payload,
    the signature check will fail and the token will be rejected.

    Args:
        user_id: The user's UUID as a string.
        organization_id: The user's organization UUID (may be None for SUPER_ADMIN).
        role: The user's role string, e.g. "ORG_ADMIN".
        expires_delta: How long until the token expires (default: settings value).

    Returns:
        A signed JWT string to send to the client.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    payload = {
        "sub": user_id,                        # subject = user ID
        "organization_id": organization_id,    # for multi-tenant isolation
        "role": role,                          # for authorization
        "exp": expire,                         # expiration time
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token


import secrets


def create_refresh_token() -> str:
    """
    Generate an opaque, cryptographically secure random refresh token string.
    512-bit entropy (128-char hex string).
    """
    return secrets.token_hex(64)


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT access token.

    Raises:
        jose.JWTError: If the token is invalid, expired, or tampered with.

    Returns:
        The decoded payload dictionary (contains sub, organization_id, role, exp).
    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )
    return payload
