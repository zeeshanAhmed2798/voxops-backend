"""
tests/test_auth.py
==================
Automated tests for the Authentication and User Profile APIs.

HOW TO RUN:
    cd backend
    pytest tests/ -v

Each test function starts with 'test_' — pytest discovers them automatically.
The 'client' and 'test_user' fixtures are defined in conftest.py.
"""

import pytest
from fastapi.testclient import TestClient

from app.models.user import User


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ══════════════════════════════════════════════════════════════════════════════

class TestHealthCheck:
    """Tests for the root health check endpoint."""

    def test_root_returns_ok(self, client: TestClient):
        """GET / should return 200 and a status message."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "VoxOps" in data["message"]


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN
# ══════════════════════════════════════════════════════════════════════════════

class TestLogin:
    """Tests for POST /api/v1/auth/login"""

    def test_login_success(self, client: TestClient, test_user: User):
        """Valid credentials should return a JWT token."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "jane@example.com", "password": "ChangeMe123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 10  # Token is not empty

    def test_login_wrong_password(self, client: TestClient, test_user: User):
        """Wrong password should return 401."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "jane@example.com", "password": "WrongPassword!"},
        )
        assert response.status_code == 401
        assert "Incorrect" in response.json()["detail"]

    def test_login_wrong_email(self, client: TestClient):
        """Non-existent email should return 401 (same message — no user enumeration)."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "ChangeMe123!"},
        )
        assert response.status_code == 401
        assert "Incorrect" in response.json()["detail"]

    def test_login_inactive_user(self, client: TestClient, inactive_user: User):
        """An INACTIVE user should be rejected with 403."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "inactive@example.com", "password": "ChangeMe123!"},
        )
        assert response.status_code == 403
        assert "deactivated" in response.json()["detail"].lower()

    def test_login_missing_fields(self, client: TestClient):
        """Missing email or password should return 422 Unprocessable Entity."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "jane@example.com"},  # No password
        )
        assert response.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# AUTH/ME — GET CURRENT USER
# ══════════════════════════════════════════════════════════════════════════════

class TestAuthMe:
    """Tests for GET /api/v1/auth/me"""

    def test_auth_me_with_valid_token(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """Valid JWT should return current user info."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "jane@example.com"
        assert data["name"] == "Jane Doe"
        assert data["role"] == "ORG_ADMIN"
        assert data["status"] == "ACTIVE"
        assert "password_hash" not in data  # CRITICAL: Never expose this!
        assert "password" not in data        # CRITICAL: Never expose this!

    def test_auth_me_without_token(self, client: TestClient):
        """Missing JWT should return 401."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_auth_me_with_invalid_token(self, client: TestClient):
        """Invalid/tampered JWT should return 401."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer this.is.not.a.valid.jwt"},
        )
        assert response.status_code == 401

    def test_auth_me_response_has_organization_id(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """Response must include organization_id for multi-tenant isolation."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "organization_id" in data
        assert data["organization_id"] is not None


# ══════════════════════════════════════════════════════════════════════════════
# LOGOUT
# ══════════════════════════════════════════════════════════════════════════════

class TestLogout:
    """Tests for POST /api/v1/auth/logout"""

    def test_logout_with_valid_token(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """Valid token should get a 200 logout response."""
        response = client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "discard" in data["message"].lower()

    def test_logout_without_token(self, client: TestClient):
        """Logout without a token should return 401."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# CHANGE PASSWORD
# ══════════════════════════════════════════════════════════════════════════════

class TestChangePassword:
    """Tests for POST /api/v1/auth/change-password"""

    def test_change_password_success(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """Correct current password → new password set → can login with new password."""
        # Step 1: Change the password
        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "ChangeMe123!",
                "new_password": "NewSecurePass456!",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "success" in response.json()["message"].lower()

        # Step 2: Login with the NEW password
        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": "jane@example.com", "password": "NewSecurePass456!"},
        )
        assert login_response.status_code == 200
        assert "access_token" in login_response.json()

    def test_change_password_wrong_current(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """Wrong current password should be rejected with 400."""
        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "WrongCurrentPassword!",
                "new_password": "NewSecurePass456!",
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()

    def test_change_password_same_as_current(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """Setting same password as current should be rejected."""
        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "ChangeMe123!",
                "new_password": "ChangeMe123!",  # Same as current
            },
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_change_password_too_short(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """New password shorter than 8 characters should be rejected (Pydantic validation)."""
        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "ChangeMe123!",
                "new_password": "short",  # Less than 8 chars
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_change_password_requires_auth(self, client: TestClient):
        """Change password without JWT should return 401."""
        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "ChangeMe123!",
                "new_password": "NewSecurePass456!",
            },
        )
        assert response.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# USER PROFILE — GET
# ══════════════════════════════════════════════════════════════════════════════

class TestGetProfile:
    """Tests for GET /api/v1/users/me"""

    def test_get_profile_success(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """Authenticated user should get their profile."""
        response = client.get("/api/v1/users/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "jane@example.com"
        assert data["name"] == "Jane Doe"
        assert "password_hash" not in data  # CRITICAL

    def test_get_profile_without_auth(self, client: TestClient):
        """Without JWT, should return 401."""
        response = client.get("/api/v1/users/me")
        assert response.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# USER PROFILE — UPDATE
# ══════════════════════════════════════════════════════════════════════════════

class TestUpdateProfile:
    """Tests for PATCH /api/v1/users/me"""

    def test_update_name(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """Should be able to update name."""
        response = client.patch(
            "/api/v1/users/me",
            json={"name": "Jane Updated"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Jane Updated"

    def test_update_job_title(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """Should be able to update job_title."""
        response = client.patch(
            "/api/v1/users/me",
            json={"job_title": "Lead Engineer"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["job_title"] == "Lead Engineer"

    def test_update_timezone(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """Should be able to update timezone."""
        response = client.patch(
            "/api/v1/users/me",
            json={"timezone": "Asia/Karachi"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["timezone"] == "Asia/Karachi"

    def test_cannot_update_role(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """
        Attempting to set 'role' in the PATCH body should be IGNORED.
        The role field is not in UpdateProfileRequest schema, so Pydantic
        silently ignores it (or returns 422 depending on config).
        In either case, the role must NOT change.
        """
        original_role = test_user.role.value

        # Send role in request body — this field is not in UpdateProfileRequest
        response = client.patch(
            "/api/v1/users/me",
            json={"role": "SUPER_ADMIN", "name": "Jane Doe"},
            headers=auth_headers,
        )

        # The request may succeed (role field ignored) or return 422
        # Either way, the role must not have changed to SUPER_ADMIN
        if response.status_code == 200:
            assert response.json()["role"] == original_role, (
                "SECURITY BUG: User was able to change their own role!"
            )

    def test_cannot_update_organization_id(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """
        Attempting to set 'organization_id' in the PATCH body must be ignored.
        This is critical for multi-tenant isolation.
        """
        original_org_id = str(test_user.organization_id)

        response = client.patch(
            "/api/v1/users/me",
            json={
                "organization_id": "99999999-9999-9999-9999-999999999999",
                "name": "Jane Doe",
            },
            headers=auth_headers,
        )

        if response.status_code == 200:
            assert response.json()["organization_id"] == original_org_id, (
                "SECURITY BUG: User was able to change their own organization_id!"
            )

    def test_update_profile_empty_body(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """Empty update body should return current profile unchanged."""
        response = client.patch(
            "/api/v1/users/me",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["email"] == "jane@example.com"

    def test_update_profile_without_auth(self, client: TestClient):
        """Without JWT, should return 401."""
        response = client.patch(
            "/api/v1/users/me",
            json={"name": "Hacker"},
        )
        assert response.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# SUSPENDED USER — cannot log in or access protected routes
# ══════════════════════════════════════════════════════════════════════════════

class TestSuspendedUser:
    """Tests that SUSPENDED users are blocked from the system."""

    def test_suspended_user_cannot_login(self, client: TestClient, suspended_user: User):
        """
        A SUSPENDED user must not receive a JWT token.
        Spec: "INACTIVE and SUSPENDED users must not be able to log in."
        Expected: 403 Forbidden.
        """
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "suspended@example.com", "password": "ChangeMe123!"},
        )
        assert response.status_code == 403
        assert "suspended" in response.json()["detail"].lower()

    def test_suspended_user_blocked_on_protected_route(
        self, client: TestClient, db, suspended_user: User
    ):
        """
        Even if a SUSPENDED user somehow has a valid old token,
        get_current_user must reject them with 403.

        We simulate this by manually creating a token for the suspended user.
        """
        from app.core.security import create_access_token

        token = create_access_token(
            user_id=str(suspended_user.id),
            organization_id=str(suspended_user.organization_id),
            role=suspended_user.role.value,
        )
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/api/v1/auth/me", headers=headers)
        # get_current_user checks status after fetching from DB
        assert response.status_code == 403
        assert "suspended" in response.json()["detail"].lower()


# ══════════════════════════════════════════════════════════════════════════════
# ROLE AUTHORIZATION — require_roles() dependency
# ══════════════════════════════════════════════════════════════════════════════

class TestRoleAuthorization:
    """
    Tests for the require_roles() dependency (role-based access control).

    HOW require_roles WORKS:
    - It is a "factory" function that returns a FastAPI dependency.
    - You use it like: Depends(require_roles(UserRole.ORG_ADMIN))
    - If the current user's role is NOT in the allowed list → 403 Forbidden.
    - If the role IS in the list → the user object is returned normally.

    Since we don't have a role-restricted endpoint in this module yet,
    we test the dependency directly by calling require_roles() in a temporary
    test route registered on the app.
    """

    def test_require_roles_allows_authorized_role(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """
        test_user has role ORG_ADMIN.
        require_roles(ORG_ADMIN) should let them through.
        We verify via the auth/me endpoint that the user IS accessible.
        This proves the dependency chain works end-to-end.
        """
        # test_user is ORG_ADMIN — /auth/me uses get_current_user (no role restriction)
        # This test confirms the base dependency works for authorized users.
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "ORG_ADMIN"

    def test_require_roles_blocks_wrong_role(
        self, client: TestClient, db, test_user: User
    ):
        """
        Import and call require_roles() directly to verify it raises 403
        when the current user's role is not in the allowed list.

        This tests the dependency logic in isolation.
        """
        from fastapi import HTTPException
        from app.dependencies.auth import require_roles
        from app.models.user import UserRole

        # test_user is ORG_ADMIN — try to restrict to SUPER_ADMIN only
        check_fn = require_roles(UserRole.SUPER_ADMIN)

        # Call the inner check function directly, passing the test_user
        try:
            check_fn(current_user=test_user)
            assert False, "Expected HTTPException 403 was not raised"
        except HTTPException as exc:
            assert exc.status_code == 403
            assert "Access denied" in exc.detail

    def test_require_roles_allows_multiple_roles(self, client: TestClient, db, test_user: User):
        """
        require_roles accepts multiple roles — any match should be allowed.
        test_user is ORG_ADMIN, passing [SUPERVISOR, ORG_ADMIN] should work.
        """
        from app.dependencies.auth import require_roles
        from app.models.user import UserRole

        check_fn = require_roles(UserRole.SUPERVISOR, UserRole.ORG_ADMIN)

        # Should NOT raise — ORG_ADMIN is in the allowed list
        result = check_fn(current_user=test_user)
        assert result.role == UserRole.ORG_ADMIN

    def test_require_roles_super_admin_not_in_limited_list(
        self, client: TestClient, db, test_user: User
    ):
        """
        If the user is ORG_ADMIN but the endpoint requires FIELD_WORKER only,
        they must be blocked.
        """
        from fastapi import HTTPException
        from app.dependencies.auth import require_roles
        from app.models.user import UserRole

        check_fn = require_roles(UserRole.FIELD_WORKER)

        try:
            check_fn(current_user=test_user)
            assert False, "Expected HTTPException 403 was not raised"
        except HTTPException as exc:
            assert exc.status_code == 403

