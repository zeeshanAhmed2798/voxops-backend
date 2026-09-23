"""
seed_dev.py
===========
⚠️  DEVELOPMENT ONLY — DO NOT RUN IN PRODUCTION ⚠️

This script creates demo data in the database so you can immediately test
all API endpoints without manually registering through the API.

WHAT IT CREATES:
  Organization:
    Name: Acme Corp
    Slug: acme-corp

  Admin User:
    Name:     Jane Doe (Admin)
    Email:    admin@acme.com
    Password: AdminPass123!
    Role:     ORG_ADMIN

  Member User:
    Name:     Bob Smith (Member)
    Email:    bob@acme.com
    Password: MemberPass123!
    Role:     EMPLOYEE

  Sample Knowledge Base Document:
    Title:   "Welcome to Acme Corp Knowledge Base"
    Category: "Onboarding"
    Published: True

HOW TO RUN:
  # Make sure your .env is set up and run migrations first!
  cd backend
  alembic upgrade head
  python seed_dev.py

The script is safe to run multiple times — it skips creation if data already exists.
"""

import sys
import os
import uuid

# Make sure 'app' is importable from this script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.organization import Organization
from app.models.user import User, UserRole, UserStatus
from app.models.knowledge_base import KnowledgeBaseDocument


# ── Seed Data ─────────────────────────────────────────────────────────────────

DEMO_ORG = {
    "id": uuid.UUID("a1b2c3d4-0000-0000-0000-000000000001"),
    "name": "Acme Corp",
    "slug": "acme-corp",
}

DEMO_ADMIN = {
    "id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
    "name": "Jane Doe (Admin)",
    "email": "admin@acme.com",
    "password": "AdminPass123!",
    "role": UserRole.ORG_ADMIN,
}

DEMO_MEMBER = {
    "id": uuid.UUID("00000000-0000-0000-0000-000000000002"),
    "name": "Bob Smith (Member)",
    "email": "bob@acme.com",
    "password": "MemberPass123!",
    "role": UserRole.EMPLOYEE,
}

DEMO_KB_DOC = {
    "id": uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001"),
    "title": "Welcome to Acme Corp Knowledge Base",
    "content": (
        "# Welcome to Acme Corp\n\n"
        "This is your company knowledge base. Here you will find:\n\n"
        "- **Onboarding guides** — Everything you need for your first week\n"
        "- **HR Policies** — Leave, benefits, code of conduct\n"
        "- **SOPs** — Standard operating procedures for field workers\n"
        "- **Technical docs** — Tools and systems we use\n\n"
        "## Getting Started\n\n"
        "1. Complete your profile in **Settings**\n"
        "2. Review the HR policies\n"
        "3. Connect with your team in the **Team** section\n\n"
        "> Questions? Contact your admin at admin@acme.com\n"
    ),
    "category": "Onboarding",
    "is_published": True,
}


def seed() -> None:
    """Create the demo organization, users, and a KB document."""
    print("=" * 60)
    print("VoxOps Development Seed Script")
    print("=" * 60)

    db = SessionLocal()

    try:
        # ── 1. Organization ──────────────────────────────────────────────────
        existing_org = db.query(Organization).filter(
            Organization.id == DEMO_ORG["id"]
        ).first()

        if existing_org:
            print(f"[OK] Organization '{existing_org.name}' already exists — skipping.")
            org = existing_org
        else:
            org = Organization(
                id=DEMO_ORG["id"],
                name=DEMO_ORG["name"],
                slug=DEMO_ORG["slug"],
            )
            db.add(org)
            db.flush()
            print(f"[OK] Created organization: {org.name} (slug={org.slug})")

        # ── 2. Admin User ────────────────────────────────────────────────────
        existing_admin = db.query(User).filter(
            User.email == DEMO_ADMIN["email"]
        ).first()

        if existing_admin:
            print(f"[OK] Admin user '{existing_admin.email}' already exists — skipping.")
            admin_id = existing_admin.id
        else:
            admin = User(
                id=DEMO_ADMIN["id"],
                organization_id=org.id,
                name=DEMO_ADMIN["name"],
                email=DEMO_ADMIN["email"],
                password_hash=hash_password(DEMO_ADMIN["password"]),
                role=DEMO_ADMIN["role"],
                status=UserStatus.ACTIVE,
                is_email_verified=True,
                job_title="Organization Administrator",
                timezone="UTC",
            )
            db.add(admin)
            db.flush()
            admin_id = admin.id
            print(f"[OK] Created admin: {admin.email} (role={admin.role.value})")

        # ── 3. Member User ───────────────────────────────────────────────────
        existing_member = db.query(User).filter(
            User.email == DEMO_MEMBER["email"]
        ).first()

        if existing_member:
            print(f"[OK] Member user '{existing_member.email}' already exists — skipping.")
        else:
            member = User(
                id=DEMO_MEMBER["id"],
                organization_id=org.id,
                name=DEMO_MEMBER["name"],
                email=DEMO_MEMBER["email"],
                password_hash=hash_password(DEMO_MEMBER["password"]),
                role=DEMO_MEMBER["role"],
                status=UserStatus.ACTIVE,
                is_email_verified=True,
                job_title="Field Worker",
                timezone="UTC",
            )
            db.add(member)
            print(f"[OK] Created member: {member.email} (role={member.role.value})")

        # ── 4. Knowledge Base Document ───────────────────────────────────────
        existing_doc = db.query(KnowledgeBaseDocument).filter(
            KnowledgeBaseDocument.id == DEMO_KB_DOC["id"]
        ).first()

        if existing_doc:
            print(f"[OK] KB document '{existing_doc.title}' already exists — skipping.")
        else:
            doc = KnowledgeBaseDocument(
                id=DEMO_KB_DOC["id"],
                organization_id=org.id,
                title=DEMO_KB_DOC["title"],
                content=DEMO_KB_DOC["content"],
                category=DEMO_KB_DOC["category"],
                created_by=admin_id,
                is_published=DEMO_KB_DOC["is_published"],
            )
            db.add(doc)
            print(f"[OK] Created KB document: '{doc.title}'")

        db.commit()

        # ── Summary ───────────────────────────────────────────────────────────
        print()
        print("─" * 60)
        print("DEMO CREDENTIALS:")
        print()
        print("  Admin User:")
        print(f"    Email:    {DEMO_ADMIN['email']}")
        print(f"    Password: {DEMO_ADMIN['password']}")
        print(f"    Role:     ORG_ADMIN (can create/edit/delete KB docs)")
        print()
        print("  Member User:")
        print(f"    Email:    {DEMO_MEMBER['email']}")
        print(f"    Password: {DEMO_MEMBER['password']}")
        print(f"    Role:     EMPLOYEE (read-only for KB docs)")
        print()
        print("  Test via Swagger: http://127.0.0.1:8000/docs")
        print("─" * 60)
        print()
        print("QUICK TEST FLOW:")
        print("  1. POST /api/v1/auth/login  (as admin or member)")
        print("  2. Copy access_token → Authorize in Swagger")
        print("  3. GET  /api/v1/knowledge-base  (both can read)")
        print("  4. POST /api/v1/knowledge-base  (admin only — member gets 403)")
        print("  5. POST /api/v1/auth/invite-member  (admin invites new user)")
        print("─" * 60)

    except Exception as e:
        db.rollback()
        print(f"\n[FAIL] Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
