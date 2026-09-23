"""
app/core/security.py
====================
Security utilities: password hashing and JWT token management.

HOW IT WORKS:
- Passwords: We use bcrypt (via passlib). It's slow on purpose — hard to brute-force.
- JWT: We encode user identity into a signed token. The signature uses JWT_SECRET.
  Anyone with the secret can verify the token is genuine (not tampered with).
- Refresh tokens: Opaque random strings stored in the DB (not JWTs). This lets us
  truly revoke them on logout by deleting the DB row.
- Secure tokens: Random URL-safe strings for password reset and invite emails.
"""

import secrets
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
      - token_type    : "access" to distinguish from other token types
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
        "token_type": "access",                # distinguish from refresh JWT
        "exp": expire,                         # expiration time
    }

    token = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return token


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


# ── Refresh Token (Opaque) ───────────────────────────────────────────────────

def create_refresh_token() -> str:
    """
    Generate a cryptographically secure random refresh token.

    This is an OPAQUE token (not a JWT). It is stored in the database and
    looked up on each refresh request. On logout, the DB row is deleted,
    which immediately invalidates the token.

    Returns:
        A 64-character URL-safe random hex string.

    Why not a JWT?
        JWTs are self-contained and cannot be revoked before expiry.
        Storing the refresh token in the DB gives us true revocation.
    """
    return secrets.token_hex(64)  # 128 characters, 512 bits of entropy


# ── Secure One-Time Tokens ───────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 32) -> str:
    """
    Generate a URL-safe secure random token for password resets and invites.

    These tokens are stored in the DB with an expiry. Once used, they are
    marked as `is_used=True` and cannot be reused.

    Args:
        nbytes: Number of random bytes (default 32 → 43-char URL-safe string).

    Returns:
        A URL-safe base64-encoded random string.

    Example:
        token = generate_secure_token()
        # → "abc123xyz..." (43 chars, URL-safe)
    """
    return secrets.token_urlsafe(nbytes)
