"""
app/dependencies/auth.py
========================
FastAPI dependencies for authentication and authorization.

HOW DEPENDENCIES WORK IN FASTAPI:
- A "dependency" is a function FastAPI calls automatically before your route runs.
- You declare it with: Depends(some_function)
- FastAPI injects the return value into your route handler.
- If the dependency raises an HTTPException, the request is rejected before
  your route code even runs.

WHAT THIS FILE PROVIDES:
1. get_current_user()     → extracts user from JWT, checks status
2. require_roles(*roles)  → factory for role-based access control
3. require_admin          → shortcut: require_roles(ORG_ADMIN, SUPER_ADMIN)
4. get_current_org()      → fetches the current user's Organization from DB

FOR TEAM MEMBERS:
- Use get_current_user for any protected route (any logged-in user).
- Use require_admin for admin-only routes (KB write, invite member, etc.).
- Use require_roles(...) for fine-grained multi-role access control.
- Use get_current_org when you need the Organization object (slug, name, etc.).
- current_user.organization_id is always available for multi-tenant scoping.
"""

import uuid as uuid_module
from typing import Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole, UserStatus
from app.models.organization import Organization


# ── HTTP Bearer scheme ─────────────────────────────────────────────────────────
# This tells FastAPI/Swagger that endpoints expect:
# Authorization: Bearer <token>
# auto_error=False means we get None instead of auto-reject, so we can give
# a clearer error message ourselves.
_bearer_scheme = HTTPBearer(auto_error=False)


# ── get_current_user ───────────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency: extract and validate the current authenticated user.

    Flow:
        Request
          ↓
        Authorization: Bearer <token>   ← extracted by HTTPBearer
          ↓
        decode_access_token(token)      ← verifies signature + expiry
          ↓
        extract user_id from payload
          ↓
        fetch User from database
          ↓
        check user.status == ACTIVE
          ↓
        return User object

    Usage in a route:
        @router.get("/protected")
        def protected_route(current_user: User = Depends(get_current_user)):
            return {"user_id": str(current_user.id)}

    Raises:
        401 Unauthorized — if token is missing, invalid, or expired
        403 Forbidden    — if user exists but is INACTIVE or SUSPENDED
    """

    # 1. Check that the Authorization header was provided
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Provide a Bearer token in the Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # 2. Decode and verify the JWT
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Extract the user ID from the token payload
    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is malformed — missing subject (user ID).",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 4. Look up the user in the database
    # We must convert the string user_id back to a UUID object.
    # The JWT stores user_id as a string; the DB column expects a UUID.
    try:
        user_uuid = uuid_module.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload contains an invalid user ID format.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_uuid).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with this token no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 5. Check account status — inactive/suspended users cannot access the system
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

    # 6. Return the fully validated User object
    return user


# ── require_roles ──────────────────────────────────────────────────────────────

def require_roles(*allowed_roles: UserRole) -> Callable:
    """
    Factory function that creates a role-checking dependency.

    This is the foundation for role-based access control (RBAC).
    It returns a FastAPI dependency function you can plug into any route.

    Usage example:
        from app.dependencies.auth import require_roles
        from app.models.user import UserRole

        @router.get("/admin-only")
        def admin_route(
            current_user: User = Depends(
                require_roles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
            )
        ):
            return {"message": "Welcome, admin!"}

    How it works:
        1. First, get_current_user() runs (it's a dependency of this dependency).
        2. Then, check if current_user.role is in the allowed_roles list.
        3. If not, raise 403 Forbidden.

    Args:
        *allowed_roles: One or more UserRole values that are permitted.

    Returns:
        A FastAPI dependency function that returns the current user if authorized.
    """

    def _check_roles(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. "
                    f"Required role(s): {[r.value for r in allowed_roles]}. "
                    f"Your role: {current_user.role.value}."
                ),
            )
        return current_user

    return _check_roles


# ── require_admin ──────────────────────────────────────────────────────────────

# Pre-built dependency: restricts an endpoint to ORG_ADMIN or SUPER_ADMIN.
# Usage:
#   @router.post("/admin-only")
#   def admin_route(current_user: User = Depends(require_admin)):
#       ...
require_admin = require_roles(UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)


# ── get_current_org ────────────────────────────────────────────────────────────

def get_current_org(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Organization:
    """
    FastAPI dependency: fetch the Organization for the current authenticated user.

    This ensures every org-level query is automatically scoped to the right tenant.
    Use this dependency when you need access to Organization fields (name, slug, etc.)

    Usage in a route:
        @router.get("/org-info")
        def org_info(org: Organization = Depends(get_current_org)):
            return {"org_name": org.name}

    Raises:
        400 Bad Request — if the user has no organization_id (e.g. SUPER_ADMIN
                          calling an org-scoped endpoint without context)
        404 Not Found   — if the organization doesn't exist (data integrity issue)
    """
    if current_user.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint requires an organization context. "
                   "Your account is not associated with any organization.",
        )

    org = db.query(Organization).filter(
        Organization.id == current_user.organization_id
    ).first()

    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found. Please contact support.",
        )

    return org
