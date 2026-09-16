"""
seed_dev.py
===========
⚠️  DEVELOPMENT ONLY — DO NOT RUN IN PRODUCTION ⚠️

This script creates a test organization ID and user in the database
so you can immediately test the login API.

WHAT IT CREATES:
  Organization (ID only — no org table yet):
    Name: CoolTech Services
    ID:   a1b2c3d4-0000-0000-0000-000000000001

  Test User:
    Name:     Jane Doe
    Email:    jane@example.com
    Password: ChangeMe123!   ← CHANGE THIS AFTER FIRST LOGIN
    Role:     ORG_ADMIN
    Status:   ACTIVE

HOW TO RUN:
  # Make sure your .env is set up and `alembic upgrade head` has been run first!
  cd backend
  python seed_dev.py

The script is safe to run multiple times — it checks if the user
already exists and skips creation if so.
"""

import sys
import os
import uuid

# Make sure 'app' is importable from this script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole, UserStatus


# ── Seed Data ─────────────────────────────────────────────────────────────────
# Hardcoded test organization ID (placeholder — real org table is another module)
TEST_ORG_ID = uuid.UUID("a1b2c3d4-0000-0000-0000-000000000001")

TEST_USER = {
    "id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
    "organization_id": TEST_ORG_ID,
    "name": "Jane Doe",
    "email": "jane@example.com",
    "password": "ChangeMe123!",  # Plain text — only used here for hashing
    "role": UserRole.ORG_ADMIN,
    "status": UserStatus.ACTIVE,
    "job_title": "Organization Administrator",
    "timezone": "UTC",
}


def seed() -> None:
    """Create the test user if it doesn't already exist."""
    print("=" * 60)
    print("VoxOps Development Seed Script")
    print("=" * 60)

    db = SessionLocal()

    try:
        # Check if user already exists
        existing = db.query(User).filter(User.email == TEST_USER["email"]).first()

        if existing:
            print(f"✓ User '{TEST_USER['email']}' already exists — skipping creation.")
            print(f"  ID:   {existing.id}")
            print(f"  Role: {existing.role.value}")
            print(f"  Status: {existing.status.value}")
        else:
            # Create the test user
            user = User(
                id=TEST_USER["id"],
                organization_id=TEST_USER["organization_id"],
                name=TEST_USER["name"],
                email=TEST_USER["email"],
                password_hash=hash_password(TEST_USER["password"]),
                role=TEST_USER["role"],
                status=TEST_USER["status"],
                job_title=TEST_USER["job_title"],
                timezone=TEST_USER["timezone"],
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            print(f"✓ Created test user:")
            print(f"  Name:    {user.name}")
            print(f"  Email:   {user.email}")
            print(f"  Role:    {user.role.value}")
            print(f"  Status:  {user.status.value}")
            print(f"  Org ID:  {user.organization_id}")
            print(f"  User ID: {user.id}")

        print()
        print("─" * 60)
        print("LOGIN CREDENTIALS FOR TESTING:")
        print(f"  Email:    {TEST_USER['email']}")
        print(f"  Password: {TEST_USER['password']}")
        print()
        print("Test via Swagger: http://127.0.0.1:8000/docs")
        print("─" * 60)
        print()
        print("⚠️  REMINDER: Change this password after first login!")
        print("    POST /api/v1/auth/change-password")

    except Exception as e:
        db.rollback()
        print(f"✗ Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
