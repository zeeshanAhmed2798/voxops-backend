"""
tests/conftest.py
==================
pytest fixtures shared across all test files.

HOW TESTING WORKS IN FASTAPI:
- We use TestClient (from httpx) to send HTTP requests to the app IN MEMORY.
- We use an in-memory SQLite database instead of PostgreSQL for tests.
  This means tests run fast and don't need a real database server.
- We override FastAPI's get_db dependency to use the test database.

IMPORTANT: Tests use SQLite, not PostgreSQL.
  - This is standard practice for unit tests.
  - SQLite doesn't support all PostgreSQL features (e.g., UUID type, ENUM types).
  - We handle this by configuring SQLAlchemy to use String for UUIDs in tests.
"""

import os
import pytest
import uuid
from typing import Generator

# Tests replace the database dependency with SQLite, but Settings is loaded
# while importing the app. Supply test-only values so no .env is required.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_voxops.db")
os.environ.setdefault("JWT_SECRET", "test-only-secret-do-not-use-in-production")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.models.user import AppRole, User, UserRole, UserStatus
from app.models.organization import Organization
from app.models.department import Department
from app.models.job import Job


# ── Test Database Setup ───────────────────────────────────────────────────────
# Use SQLite in-memory database for tests (fast, no external server needed)
SQLITE_TEST_URL = "sqlite:///./test_voxops.db"

test_engine = create_engine(
    SQLITE_TEST_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite + threading
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
)


# ── Create/Drop Tables ────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def create_test_tables():
    """Give each test fresh tables, including tests that exercise DB rollbacks."""
    # SQLite doesn't support PostgreSQL ENUM types natively.
    # SQLAlchemy handles this gracefully by using VARCHAR for ENUM columns in SQLite.
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    for index, role in enumerate(UserRole):
        session.add(AppRole(
            id=uuid.uuid4(),
            code=role.value,
            name=role.value.replace("_", " ").title(),
            is_assignable=role != UserRole.SUPER_ADMIN,
            is_active=True,
            sort_order=index,
        ))
    session.commit()
    session.close()
    yield
    Base.metadata.drop_all(bind=test_engine)


# ── Database Session Fixture ───────────────────────────────────────────────────
@pytest.fixture()
def db() -> Generator[Session, None, None]:
    """Provide a session for the disposable per-test database."""
    session = TestingSessionLocal()

    yield session

    session.close()


# ── Override FastAPI's get_db ─────────────────────────────────────────────────
@pytest.fixture()
def client(db: Session) -> Generator[TestClient, None, None]:
    """
    HTTP test client with the database overridden to use the test DB.

    This is the key trick: we tell FastAPI to use our test DB session
    instead of the real PostgreSQL session.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass  # Session cleanup handled by the db fixture

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ── Test User Fixtures ────────────────────────────────────────────────────────
@pytest.fixture()
def test_user(db: Session) -> User:
    """Create an active test user in the test database."""
    role = db.query(AppRole).filter_by(code=UserRole.ORG_ADMIN.value).one()
    user = User(
        id=uuid.uuid4(),
        organization_id=uuid.UUID("a1b2c3d4-0000-0000-0000-000000000001"),
        name="Jane Doe",
        email="jane@example.com",
        password_hash=hash_password("ChangeMe123!"),
        user_role_id=role.id,
        status=UserStatus.ACTIVE,
        job_title="Test Admin",
        timezone="UTC",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def inactive_user(db: Session) -> User:
    """Create an INACTIVE test user (should not be able to log in)."""
    role = db.query(AppRole).filter_by(code=UserRole.EMPLOYEE.value).one()
    user = User(
        id=uuid.uuid4(),
        organization_id=uuid.UUID("a1b2c3d4-0000-0000-0000-000000000001"),
        name="Inactive User",
        email="inactive@example.com",
        password_hash=hash_password("ChangeMe123!"),
        user_role_id=role.id,
        status=UserStatus.INACTIVE,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture()
def auth_headers(client: TestClient, test_user: User) -> dict:
    """Log in as the test user and return Authorization headers."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "jane@example.com", "password": "ChangeMe123!"},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
