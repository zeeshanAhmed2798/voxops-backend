"""
app/db/seed.py
==============
Seed script for populating VoxOps database with initial test users and roles.

Seeded Accounts:
1. Super Admin:
   - Email: superadmin@voxops.com
   - Password: SuperAdmin123!
   - Role: SUPER_ADMIN

2. Organization Admin:
   - Email: admin@acme.com
   - Password: AdminPass123!
   - Role: ORG_ADMIN
   - Organization: Acme Corp

3. Member / Employee:
   - Email: bob@acme.com
   - Password: MemberPass123!
   - Role: EMPLOYEE
   - Organization: Acme Corp

Usage:
    python -m app.db.seed
    or
    python seed_users.py
"""

import sys
import os
from sqlalchemy.orm import Session

# Handle Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path if invoked directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.organization import Organization
from app.models.user import User, UserRole, UserStatus


def seed_data(db: Session) -> None:
    print("Starting VoxOps database seeding...")

    # 1. Ensure sample organization exists
    acme_org = db.query(Organization).filter(Organization.slug == "acme-corp").first()
    if not acme_org:
        acme_org = Organization(
            name="Acme Corp",
            slug="acme-corp",
        )
        db.add(acme_org)
        db.commit()
        db.refresh(acme_org)
        print(f"  [+] Created Organization: '{acme_org.name}' (ID: {acme_org.id})")
    else:
        print(f"  [-] Organization '{acme_org.name}' already exists.")

    # 2. Seed accounts
    users_to_seed = [
        {
            "name": "Super Admin",
            "email": "superadmin@voxops.com",
            "password": "SuperAdmin123!",
            "role": UserRole.SUPER_ADMIN,
            "organization_id": None,
            "job_title": "Platform Administrator",
        },
        {
            "name": "Acme Admin",
            "email": "admin@acme.com",
            "password": "AdminPass123!",
            "role": UserRole.ORG_ADMIN,
            "organization_id": acme_org.id,
            "job_title": "Organization Administrator",
        },
        {
            "name": "Bob Member",
            "email": "bob@acme.com",
            "password": "MemberPass123!",
            "role": UserRole.EMPLOYEE,
            "organization_id": acme_org.id,
            "job_title": "Staff Member",
        },
    ]

    for user_info in users_to_seed:
        existing_user = db.query(User).filter(User.email == user_info["email"]).first()
        if existing_user:
            print(f"  [-] User '{user_info['email']}' already exists — skipping.")
            continue

        user = User(
            name=user_info["name"],
            email=user_info["email"],
            password_hash=hash_password(user_info["password"]),
            role=user_info["role"],
            status=UserStatus.ACTIVE,
            is_email_verified=True,
            organization_id=user_info["organization_id"],
            job_title=user_info["job_title"],
        )
        db.add(user)
        print(f"  [+] Created User: {user.email} (Role: {user.role.value})")

    db.commit()
    print("Database seeding completed successfully!")


def main():
    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
