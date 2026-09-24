"""
seed_dev.py
===========
⚠️  DEVELOPMENT ONLY — DO NOT RUN IN PRODUCTION ⚠️

This script creates a test organization and user in the database
so you can immediately test the login API.

WHAT IT CREATES:
  Organization:
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
from app.models.user import AppRole, User, UserRole, UserStatus
from app.models.organization import Organization
from app.models.department import (
    Department,
    DepartmentCategory,
    DepartmentEscalationPolicy,
    DepartmentRole,
    DepartmentRoutingRule,
)


# ── Seed Data ─────────────────────────────────────────────────────────────────
# Stable development organization ID.
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


APP_ROLE_SEEDS = [
    (UserRole.SUPER_ADMIN, "Super Admin", "Platform-wide administration.", False, 0),
    (UserRole.EMPLOYEE, "Employee", "Standard organization member.", True, 10),
    (UserRole.FIELD_WORKER, "Field Worker", "Performs assigned field work.", True, 20),
    (UserRole.DEPARTMENT_AGENT, "Department Agent", "Handles department requests.", True, 30),
    (UserRole.SUPERVISOR, "Supervisor", "Supervises members and operational work.", True, 40),
    (UserRole.ORG_ADMIN, "Org Admin", "Manages the organization and its members.", True, 50),
]


TEAM_MEMBER_SEEDS = [
    {
        "name": "Ahmed Khan", "email": "ahmed@example.com", "role": UserRole.FIELD_WORKER,
        "department": "Maintenance", "status": UserStatus.ACTIVE, "job_title": "Field Worker",
    },
    {
        "name": "Sara Ali", "email": "sara@example.com", "role": UserRole.DEPARTMENT_AGENT,
        "department": "HR", "status": UserStatus.ACTIVE, "job_title": "HR Agent",
    },
    {
        "name": "Ali Raza", "email": "ali@example.com", "role": UserRole.EMPLOYEE,
        "department": "Maintenance", "status": UserStatus.ACTIVE, "job_title": "Technician",
    },
    {
        "name": "Bilal Ahmed", "email": "bilal@example.com", "role": UserRole.SUPERVISOR,
        "department": "IT", "status": UserStatus.ACTIVE, "job_title": "IT Supervisor",
    },
    {
        "name": "Fatima Noor", "email": "fatima@example.com", "role": UserRole.DEPARTMENT_AGENT,
        "department": "Finance", "status": UserStatus.INVITED, "job_title": "Finance Agent",
    },
]


def seed_application_roles(db) -> dict[UserRole, AppRole]:
    """Upsert UUID-backed application roles and return them by code."""
    existing = {item.code: item for item in db.query(AppRole).all()}
    roles: dict[UserRole, AppRole] = {}
    for code, name, description, assignable, sort_order in APP_ROLE_SEEDS:
        role = existing.get(code.value)
        if role is None:
            role = AppRole(
                id=uuid.uuid4(),
                code=code.value,
                name=name,
                description=description,
                is_assignable=assignable,
                is_active=True,
                sort_order=sort_order,
            )
            db.add(role)
        else:
            role.name = name
            role.description = description
            role.is_assignable = assignable
            role.is_active = True
            role.sort_order = sort_order
        roles[code] = role
    db.flush()
    return roles


# Each department has the complete configuration needed by the management UI:
# request categories, operational roles, category routing, and escalation.
DEPARTMENT_SEEDS = [
    {
        "name": "IT",
        "description": "Technical support for employees.",
        "categories": ["Hardware", "Software", "Network", "Access", "Security"],
        "roles": [
            ("IT Support", "Handles employee hardware and software support."),
            ("Network Team", "Owns connectivity and network infrastructure."),
            ("IT Admin", "Manages access, systems, and security."),
            ("IT Supervisor", "Escalation owner for unresolved IT requests."),
        ],
        "routes": [
            ("Hardware", "IT Support", "NORMAL"),
            ("Software", "IT Support", "NORMAL"),
            ("Network", "Network Team", "HIGH"),
            ("Access", "IT Admin", "NORMAL"),
            ("Security", "IT Admin", "HIGH"),
        ],
        "escalation": (24, "IT Supervisor"),
    },
    {
        "name": "HR",
        "description": "People operations and employee support.",
        "categories": ["Leave", "Payroll", "Benefits", "Recruitment", "Employee Concerns"],
        "roles": [
            ("HR Generalist", "Handles general employee requests."),
            ("Payroll Specialist", "Owns payroll and benefits questions."),
            ("Talent Partner", "Owns recruitment requests."),
            ("HR Supervisor", "Escalation owner for sensitive or delayed cases."),
        ],
        "routes": [
            ("Leave", "HR Generalist", "NORMAL"),
            ("Payroll", "Payroll Specialist", "HIGH"),
            ("Benefits", "Payroll Specialist", "NORMAL"),
            ("Recruitment", "Talent Partner", "NORMAL"),
            ("Employee Concerns", "HR Supervisor", "HIGH"),
        ],
        "escalation": (48, "HR Supervisor"),
    },
    {
        "name": "Finance",
        "description": "Financial operations, billing, and expense support.",
        "categories": ["Expenses", "Invoices", "Budget", "Reimbursements", "Payments"],
        "roles": [
            ("Finance Analyst", "Handles budgets and financial analysis."),
            ("Accounts Payable", "Handles invoices, payments, and reimbursements."),
            ("Finance Manager", "Escalation owner for finance requests."),
        ],
        "routes": [
            ("Expenses", "Finance Analyst", "NORMAL"),
            ("Invoices", "Accounts Payable", "NORMAL"),
            ("Budget", "Finance Analyst", "HIGH"),
            ("Reimbursements", "Accounts Payable", "NORMAL"),
            ("Payments", "Accounts Payable", "HIGH"),
        ],
        "escalation": (48, "Finance Manager"),
    },
    {
        "name": "Operations",
        "description": "Day-to-day business operations and service coordination.",
        "categories": ["Scheduling", "Process Issue", "Vendor Coordination", "Inventory", "Service Delivery"],
        "roles": [
            ("Operations Coordinator", "Coordinates schedules and daily operations."),
            ("Inventory Controller", "Owns inventory and supply requests."),
            ("Operations Manager", "Escalation owner for operational issues."),
        ],
        "routes": [
            ("Scheduling", "Operations Coordinator", "NORMAL"),
            ("Process Issue", "Operations Manager", "HIGH"),
            ("Vendor Coordination", "Operations Coordinator", "NORMAL"),
            ("Inventory", "Inventory Controller", "NORMAL"),
            ("Service Delivery", "Operations Manager", "HIGH"),
        ],
        "escalation": (24, "Operations Manager"),
    },
    {
        "name": "Maintenance",
        "description": "Equipment, building, and preventive maintenance support.",
        "categories": ["Equipment Repair", "Preventive Maintenance", "Electrical", "Plumbing", "HVAC"],
        "roles": [
            ("Maintenance Technician", "Handles general repairs and maintenance."),
            ("Facilities Engineer", "Handles specialist building systems."),
            ("Maintenance Supervisor", "Escalation owner for maintenance work."),
        ],
        "routes": [
            ("Equipment Repair", "Maintenance Technician", "HIGH"),
            ("Preventive Maintenance", "Maintenance Technician", "NORMAL"),
            ("Electrical", "Facilities Engineer", "HIGH"),
            ("Plumbing", "Facilities Engineer", "NORMAL"),
            ("HVAC", "Facilities Engineer", "HIGH"),
        ],
        "escalation": (12, "Maintenance Supervisor"),
    },
    {
        "name": "Facilities",
        "description": "Workplace facilities and office services.",
        "categories": ["Cleaning", "Workspace", "Utilities", "Parking", "Office Move"],
        "roles": [
            ("Facilities Coordinator", "Coordinates workplace service requests."),
            ("Site Services", "Handles utilities and on-site services."),
            ("Facilities Manager", "Escalation owner for facilities requests."),
        ],
        "routes": [
            ("Cleaning", "Site Services", "NORMAL"),
            ("Workspace", "Facilities Coordinator", "NORMAL"),
            ("Utilities", "Site Services", "HIGH"),
            ("Parking", "Facilities Coordinator", "LOW"),
            ("Office Move", "Facilities Coordinator", "NORMAL"),
        ],
        "escalation": (24, "Facilities Manager"),
    },
    {
        "name": "Security",
        "description": "Physical security, incidents, and site access.",
        "categories": ["Access Badge", "Visitor Access", "Security Incident", "Lost Property", "CCTV Review"],
        "roles": [
            ("Security Desk", "Handles access and visitor requests."),
            ("Security Officer", "Responds to incidents and investigations."),
            ("Security Supervisor", "Escalation owner for security requests."),
        ],
        "routes": [
            ("Access Badge", "Security Desk", "NORMAL"),
            ("Visitor Access", "Security Desk", "NORMAL"),
            ("Security Incident", "Security Officer", "HIGH"),
            ("Lost Property", "Security Officer", "LOW"),
            ("CCTV Review", "Security Supervisor", "HIGH"),
        ],
        "escalation": (4, "Security Supervisor"),
    },
    {
        "name": "Procurement",
        "description": "Purchasing, suppliers, and purchase-order support.",
        "categories": ["Purchase Request", "Supplier Onboarding", "Purchase Order", "Contract Renewal", "Delivery Issue"],
        "roles": [
            ("Procurement Specialist", "Handles purchasing and supplier requests."),
            ("Contract Coordinator", "Handles contracts and renewals."),
            ("Procurement Manager", "Escalation owner for procurement requests."),
        ],
        "routes": [
            ("Purchase Request", "Procurement Specialist", "NORMAL"),
            ("Supplier Onboarding", "Procurement Specialist", "NORMAL"),
            ("Purchase Order", "Procurement Specialist", "HIGH"),
            ("Contract Renewal", "Contract Coordinator", "NORMAL"),
            ("Delivery Issue", "Procurement Manager", "HIGH"),
        ],
        "escalation": (48, "Procurement Manager"),
    },
    {
        "name": "Customer Support",
        "description": "Customer questions, incidents, and service follow-up.",
        "categories": ["General Inquiry", "Product Issue", "Service Complaint", "Account Help", "Feedback"],
        "roles": [
            ("Support Agent", "Handles general customer requests."),
            ("Technical Support", "Handles product and technical issues."),
            ("Support Supervisor", "Escalation owner for customer cases."),
        ],
        "routes": [
            ("General Inquiry", "Support Agent", "NORMAL"),
            ("Product Issue", "Technical Support", "HIGH"),
            ("Service Complaint", "Support Supervisor", "HIGH"),
            ("Account Help", "Support Agent", "NORMAL"),
            ("Feedback", "Support Agent", "LOW"),
        ],
        "escalation": (8, "Support Supervisor"),
    },
    {
        "name": "Legal & Compliance",
        "description": "Legal review, policy, privacy, and compliance support.",
        "categories": ["Contract Review", "Policy Question", "Compliance Concern", "Data Privacy", "Legal Notice"],
        "roles": [
            ("Legal Counsel", "Handles contracts and legal matters."),
            ("Compliance Officer", "Handles policy, compliance, and privacy."),
            ("Legal Manager", "Escalation owner for legal requests."),
        ],
        "routes": [
            ("Contract Review", "Legal Counsel", "NORMAL"),
            ("Policy Question", "Compliance Officer", "NORMAL"),
            ("Compliance Concern", "Compliance Officer", "HIGH"),
            ("Data Privacy", "Compliance Officer", "HIGH"),
            ("Legal Notice", "Legal Manager", "HIGH"),
        ],
        "escalation": (24, "Legal Manager"),
    },
]


def seed_departments(db) -> None:
    """Upsert the complete ten-department demo configuration."""
    existing_departments = {
        department.name.casefold(): department
        for department in db.query(Department).filter_by(organization_id=TEST_ORG_ID).all()
    }

    for definition in DEPARTMENT_SEEDS:
        department = existing_departments.get(definition["name"].casefold())
        if department is None:
            department = Department(
                organization_id=TEST_ORG_ID,
                name=definition["name"],
                description=definition["description"],
            )
            db.add(department)
            db.flush()
            existing_departments[department.name.casefold()] = department
        else:
            department.description = definition["description"]

        categories = {
            item.name.casefold(): item
            for item in db.query(DepartmentCategory).filter_by(department_id=department.id).all()
        }
        for name in definition["categories"]:
            if name.casefold() not in categories:
                category = DepartmentCategory(
                    organization_id=TEST_ORG_ID, department_id=department.id, name=name
                )
                db.add(category)
                db.flush()
                categories[name.casefold()] = category

        roles = {
            item.name.casefold(): item
            for item in db.query(DepartmentRole).filter_by(department_id=department.id).all()
        }
        for name, description in definition["roles"]:
            role = roles.get(name.casefold())
            if role is None:
                role = DepartmentRole(
                    organization_id=TEST_ORG_ID,
                    department_id=department.id,
                    name=name,
                    description=description,
                )
                db.add(role)
                db.flush()
                roles[name.casefold()] = role
            else:
                role.description = description

        rules = {
            item.category_id: item
            for item in db.query(DepartmentRoutingRule).filter_by(department_id=department.id).all()
        }
        for category_name, role_name, priority in definition["routes"]:
            category = categories[category_name.casefold()]
            role = roles[role_name.casefold()]
            rule = rules.get(category.id)
            if rule is None:
                rule = DepartmentRoutingRule(
                    organization_id=TEST_ORG_ID,
                    department_id=department.id,
                    category_id=category.id,
                    department_role_id=role.id,
                    priority_override=priority,
                )
                db.add(rule)
            else:
                rule.department_role_id = role.id
                rule.priority_override = priority
                rule.is_active = True

        after_hours, escalation_role_name = definition["escalation"]
        escalation_role = roles[escalation_role_name.casefold()]
        policy = db.query(DepartmentEscalationPolicy).filter_by(
            department_id=department.id
        ).first()
        if policy is None:
            db.add(DepartmentEscalationPolicy(
                organization_id=TEST_ORG_ID,
                department_id=department.id,
                after_hours=after_hours,
                escalate_to_role_id=escalation_role.id,
            ))
        else:
            policy.after_hours = after_hours
            policy.escalate_to_role_id = escalation_role.id
            policy.is_enabled = True

    db.commit()
    print(f"✓ Seeded {len(DEPARTMENT_SEEDS)} departments with categories, roles, routing, and escalation.")


def seed_team_members(db, roles: dict[UserRole, AppRole]) -> None:
    """Create representative members used by the Teams frontend."""
    departments = {
        item.name.casefold(): item
        for item in db.query(Department).filter_by(organization_id=TEST_ORG_ID).all()
    }
    for definition in TEAM_MEMBER_SEEDS:
        member = db.query(User).filter_by(email=definition["email"]).first()
        role = roles[definition["role"]]
        department = departments[definition["department"].casefold()]
        if member is None:
            member = User(
                organization_id=TEST_ORG_ID,
                department_id=department.id,
                user_role_id=role.id,
                user_role=role,
                name=definition["name"],
                email=definition["email"],
                password_hash=(
                    hash_password(TEST_USER["password"])
                    if definition["status"] == UserStatus.ACTIVE else None
                ),
                status=definition["status"],
                job_title=definition["job_title"],
                timezone="UTC",
            )
            db.add(member)
        else:
            member.department_id = department.id
            member.user_role_id = role.id
            member.user_role = role
            member.name = definition["name"]
            member.status = definition["status"]
            member.job_title = definition["job_title"]
    db.commit()
    print(f"✓ Seeded {len(TEAM_MEMBER_SEEDS)} representative team members.")


def seed() -> None:
    """Create the test user if it doesn't already exist."""
    print("=" * 60)
    print("VoxOps Development Seed Script")
    print("=" * 60)

    db = SessionLocal()

    try:
        organization = db.get(Organization, TEST_ORG_ID)
        if organization is None:
            organization = Organization(id=TEST_ORG_ID, name="CoolTech Services")
            db.add(organization)
            db.commit()
            print("✓ Created development organization: CoolTech Services")
        elif organization.name.startswith("Organization "):
            # The migration gives existing IDs a placeholder name.
            organization.name = "CoolTech Services"
            db.commit()

        roles = seed_application_roles(db)

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
                user_role_id=roles[TEST_USER["role"]].id,
                user_role=roles[TEST_USER["role"]],
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

        seed_departments(db)
        seed_team_members(db, roles)

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
