"""Import every ORM model so SQLAlchemy's shared metadata is complete.

Importing any ``app.models`` submodule first executes this package module. That
ensures string-based foreign keys such as ``organizations.id`` can always be
resolved, regardless of which API router happens to load first.
"""

from app.models.organization import Organization
from app.models.user import AppRole, User, UserRole, UserStatus
from app.models.department import (
    Department,
    DepartmentCategory,
    DepartmentEscalationPolicy,
    DepartmentRole,
    DepartmentRoutingRule,
)
from app.models.job import Job

__all__ = [
    "Organization",
    "User",
    "AppRole",
    "UserRole",
    "UserStatus",
    "Department",
    "DepartmentCategory",
    "DepartmentRole",
    "DepartmentRoutingRule",
    "DepartmentEscalationPolicy",
    "Job",
]
