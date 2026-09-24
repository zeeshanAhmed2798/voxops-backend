"""Database constraints for complete department configuration."""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.department import (
    Department,
    DepartmentCategory,
    DepartmentEscalationPolicy,
    DepartmentRole,
    DepartmentRoutingRule,
)
from app.models.organization import Organization


def _department(db):
    organization = Organization(id=uuid.uuid4(), name="Department Test Org")
    department = Department(
        id=uuid.uuid4(),
        organization_id=organization.id,
        name="HR",
        description="People operations",
    )
    db.add_all([organization, department])
    db.commit()
    return organization, department


def test_department_configuration_records_can_be_persisted(db):
    organization, department = _department(db)
    category = DepartmentCategory(
        organization_id=organization.id,
        department_id=department.id,
        name="Payroll",
    )
    role = DepartmentRole(
        organization_id=organization.id,
        department_id=department.id,
        name="Payroll Admin",
    )
    db.add_all([category, role])
    db.flush()

    rule = DepartmentRoutingRule(
        organization_id=organization.id,
        department_id=department.id,
        category_id=category.id,
        department_role_id=role.id,
        priority_override="HIGH",
    )
    policy = DepartmentEscalationPolicy(
        organization_id=organization.id,
        department_id=department.id,
        after_hours=48,
        escalate_to_role_id=role.id,
    )
    db.add_all([rule, policy])
    db.commit()

    assert category.is_active is True
    assert role.is_active is True
    assert rule.is_active is True
    assert policy.is_enabled is True


@pytest.mark.parametrize(
    ("model_factory", "expected_constraint"),
    [
        (
            lambda org, dept: DepartmentCategory(
                organization_id=org.id, department_id=dept.id, name="Leave"
            ),
            "uq_department_category_name",
        ),
        (
            lambda org, dept: DepartmentRole(
                organization_id=org.id, department_id=dept.id, name="HR Generalist"
            ),
            "uq_department_role_name",
        ),
    ],
)
def test_category_and_role_names_are_unique_per_department(db, model_factory, expected_constraint):
    organization, department = _department(db)
    db.add(model_factory(organization, department))
    db.commit()
    db.add(model_factory(organization, department))

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    constraint_names = {constraint.name for constraint in model_factory(organization, department).__table__.constraints}
    assert expected_constraint in constraint_names


def test_only_one_routing_rule_per_category_and_escalation_policy_per_department(db):
    organization, department = _department(db)
    category = DepartmentCategory(
        organization_id=organization.id, department_id=department.id, name="Leave"
    )
    role = DepartmentRole(
        organization_id=organization.id, department_id=department.id, name="HR Generalist"
    )
    db.add_all([category, role])
    db.flush()
    db.add_all([
        DepartmentRoutingRule(
            organization_id=organization.id,
            department_id=department.id,
            category_id=category.id,
            department_role_id=role.id,
        ),
        DepartmentEscalationPolicy(
            organization_id=organization.id,
            department_id=department.id,
            after_hours=48,
            escalate_to_role_id=role.id,
        ),
    ])
    db.commit()

    db.add(DepartmentRoutingRule(
        organization_id=organization.id,
        department_id=department.id,
        category_id=category.id,
        department_role_id=role.id,
    ))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    db.add(DepartmentEscalationPolicy(
        organization_id=organization.id,
        department_id=department.id,
        after_hours=24,
        escalate_to_role_id=role.id,
    ))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


@pytest.mark.parametrize(
    "record_factory",
    [
        lambda org, dept, category, role: DepartmentRoutingRule(
            organization_id=org.id,
            department_id=dept.id,
            category_id=category.id,
            department_role_id=role.id,
            priority_override="URGENT",
        ),
        lambda org, dept, category, role: DepartmentEscalationPolicy(
            organization_id=org.id,
            department_id=dept.id,
            after_hours=0,
            escalate_to_role_id=role.id,
        ),
    ],
)
def test_invalid_priority_and_escalation_hours_are_rejected(db, record_factory):
    organization, department = _department(db)
    category = DepartmentCategory(
        organization_id=organization.id, department_id=department.id, name="Leave"
    )
    role = DepartmentRole(
        organization_id=organization.id, department_id=department.id, name="HR Generalist"
    )
    db.add_all([category, role])
    db.flush()
    db.add(record_factory(organization, department, category, role))

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
