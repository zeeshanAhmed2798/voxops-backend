"""Department CRUD scoped to the authenticated organization."""

import uuid

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, Query, status
# pyrefly: ignore [missing-import, parse-error]
from sqlalchemy import and_, or_, select
# pyrefly: ignore [missing-import]
from sqlalchemy.exc import IntegrityError
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.department import (
    Department,
    DepartmentCategory,
    DepartmentEscalationPolicy,
    DepartmentRole,
    DepartmentRoutingRule,
)
from app.models.job import Job
from app.models.user import User, UserRole
from app.schemas.department import (
    DepartmentCategoryResponse,
    DepartmentCategoryCreate,
    DepartmentCategoryUpdate,
    DepartmentConfigurationResponse,
    DepartmentCreate,
    DepartmentCreateResponse,
    DepartmentEscalationPolicyResponse,
    DepartmentEscalationPolicyWrite,
    DepartmentResponse,
    DepartmentRoleCreate,
    DepartmentRoleResponse,
    DepartmentRoleUpdate,
    DepartmentRoutingRuleCreate,
    DepartmentRoutingRuleResponse,
    DepartmentUpdate,
    DepartmentWithCategoriesResponse,
)
# pyrefly: ignore [missing-import]
from app.shared.pagination import CursorPage, decode_cursor, encode_cursor
from app.shared.response import BaseResponse, ok


router = APIRouter(prefix="/departments")
admin = require_roles(UserRole.ORG_ADMIN)

DIRECTORY_TAG = "Departments — Directory"
CATEGORIES_TAG = "Departments — Categories"
ROLES_TAG = "Departments — Roles"
ROUTING_TAG = "Departments — Routing"
ESCALATION_TAG = "Departments — Escalation"


def _org_id(user: User) -> uuid.UUID:
    if user.organization_id is None:
        raise HTTPException(status_code=403, detail="Your account is not assigned to an organization.")
    return user.organization_id


def get_department_for_user(db: Session, user: User, department_id: uuid.UUID) -> Department:
    department = db.scalar(select(Department).where(
        Department.id == department_id, Department.organization_id == _org_id(user)
    ))
    if department is None:
        raise HTTPException(status_code=404, detail="Department not found.")
    return department


def _get_category(
    db: Session, user: User, department_id: uuid.UUID, category_id: uuid.UUID
) -> DepartmentCategory:
    get_department_for_user(db, user, department_id)
    category = db.scalar(select(DepartmentCategory).where(
        DepartmentCategory.id == category_id,
        DepartmentCategory.department_id == department_id,
        DepartmentCategory.organization_id == _org_id(user),
    ))
    if category is None:
        raise HTTPException(status_code=404, detail="Department category not found.")
    return category


def _get_role(
    db: Session, user: User, department_id: uuid.UUID, role_id: uuid.UUID
) -> DepartmentRole:
    get_department_for_user(db, user, department_id)
    role = db.scalar(select(DepartmentRole).where(
        DepartmentRole.id == role_id,
        DepartmentRole.department_id == department_id,
        DepartmentRole.organization_id == _org_id(user),
    ))
    if role is None:
        raise HTTPException(status_code=404, detail="Department role not found.")
    return role


def _get_rule(
    db: Session, user: User, department_id: uuid.UUID, rule_id: uuid.UUID
) -> DepartmentRoutingRule:
    get_department_for_user(db, user, department_id)
    rule = db.scalar(select(DepartmentRoutingRule).where(
        DepartmentRoutingRule.id == rule_id,
        DepartmentRoutingRule.department_id == department_id,
        DepartmentRoutingRule.organization_id == _org_id(user),
    ))
    if rule is None:
        raise HTTPException(status_code=404, detail="Department routing rule not found.")
    return rule


def _rule_response(
    rule: DepartmentRoutingRule,
    category: DepartmentCategory,
    role: DepartmentRole,
) -> DepartmentRoutingRuleResponse:
    return DepartmentRoutingRuleResponse(
        id=rule.id,
        category_id=rule.category_id,
        category_name=category.name,
        department_role_id=rule.department_role_id,
        department_role_name=role.name,
        priority_override=rule.priority_override,
        is_active=rule.is_active,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


def _policy_response(
    policy: DepartmentEscalationPolicy, role: DepartmentRole
) -> DepartmentEscalationPolicyResponse:
    return DepartmentEscalationPolicyResponse(
        id=policy.id,
        after_hours=policy.after_hours,
        escalate_to_role_id=policy.escalate_to_role_id,
        escalate_to_role_name=role.name,
        is_enabled=policy.is_enabled,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


@router.get(
    "",
    response_model=BaseResponse[CursorPage[DepartmentWithCategoriesResponse]],
    response_model_exclude_none=True,
    tags=[DIRECTORY_TAG],
    summary="List departments with categories",
)
def list_departments(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=1000),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    organization_id = _org_id(user)
    query = select(Department).where(Department.organization_id == organization_id)
    if cursor:
        try:
            cursor_data = decode_cursor(cursor)
            cursor_name = cursor_data["name"]
            cursor_id = uuid.UUID(cursor_data["id"])
        except (KeyError, ValueError):
            raise HTTPException(status_code=422, detail="Invalid pagination cursor.")
        query = query.where(or_(
            Department.name > cursor_name,
            and_(Department.name == cursor_name, Department.id > cursor_id),
        ))

    departments = list(db.scalars(
        query.order_by(Department.name, Department.id).limit(limit + 1)
    ).all())
    has_more = len(departments) > limit
    departments = departments[:limit]
    department_ids = [department.id for department in departments]
    categories_by_department: dict[uuid.UUID, list[DepartmentCategory]] = {
        department_id: [] for department_id in department_ids
    }
    if department_ids:
        categories = db.scalars(select(DepartmentCategory).where(
            DepartmentCategory.organization_id == organization_id,
            DepartmentCategory.department_id.in_(department_ids),
        ).order_by(DepartmentCategory.name, DepartmentCategory.id)).all()
        for category in categories:
            categories_by_department[category.department_id].append(category)

    items = [
        DepartmentWithCategoriesResponse(
            **DepartmentResponse.model_validate(department).model_dump(),
            categories=[
                DepartmentCategoryResponse.model_validate(category)
                for category in categories_by_department[department.id]
            ],
        )
        for department in departments
    ]
    next_cursor = None
    if has_more and departments:
        last = departments[-1]
        next_cursor = encode_cursor({"name": last.name, "id": str(last.id)})
    return ok(
        "Departments retrieved successfully.",
        CursorPage(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
            limit=limit,
        ),
    )


@router.post("", response_model=BaseResponse[DepartmentCreateResponse], response_model_exclude_none=True, status_code=status.HTTP_201_CREATED, tags=[DIRECTORY_TAG])
def create_department(request: DepartmentCreate, user: User = Depends(admin), db: Session = Depends(get_db)):
    organization_id = _org_id(user)
    department_data = request.model_dump(exclude={"categories"})
    department = Department(organization_id=organization_id, **department_data)
    db.add(department)
    try:
        db.flush()
        categories = [
            DepartmentCategory(
                organization_id=organization_id,
                department_id=department.id,
                name=name,
            )
            for name in request.categories
        ]
        db.add_all(categories)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A department or category with this name already exists.",
        )
    db.refresh(department)
    for category in categories:
        db.refresh(category)
    response = DepartmentCreateResponse(
        **DepartmentResponse.model_validate(department).model_dump(),
        categories=[DepartmentCategoryResponse.model_validate(category) for category in categories],
    )
    return ok("Department created successfully.", response)


@router.get("/{department_id}", response_model=BaseResponse[DepartmentResponse], response_model_exclude_none=True, tags=[DIRECTORY_TAG])
def get_department(department_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok("Department retrieved successfully.", get_department_for_user(db, user, department_id))


@router.put("/{department_id}", response_model=BaseResponse[DepartmentResponse], response_model_exclude_none=True, tags=[DIRECTORY_TAG])
def update_department(department_id: uuid.UUID, request: DepartmentUpdate, user: User = Depends(admin), db: Session = Depends(get_db)):
    department = get_department_for_user(db, user, department_id)
    for field, value in request.model_dump().items():
        setattr(department, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A department with this name already exists.")
    db.refresh(department)
    return ok("Department updated successfully.", department)


@router.delete("/{department_id}", response_model=BaseResponse[None], response_model_exclude_none=True, tags=[DIRECTORY_TAG])
def delete_department(department_id: uuid.UUID, user: User = Depends(admin), db: Session = Depends(get_db)):
    department = get_department_for_user(db, user, department_id)
    if db.scalar(select(Job.id).where(Job.department_id == department_id).limit(1)):
        raise HTTPException(status_code=409, detail="Move this department's jobs before deleting it.")
    if db.scalar(select(User.id).where(User.department_id == department_id).limit(1)):
        raise HTTPException(status_code=409, detail="Move this department's users before deleting it.")
    db.delete(department)
    db.commit()
    return ok("Department deleted successfully.")


@router.get(
    "/{department_id}/configuration",
    response_model=BaseResponse[DepartmentConfigurationResponse],
    response_model_exclude_none=True,
    tags=[DIRECTORY_TAG],
    summary="Get complete department configuration",
)
def get_department_configuration(
    department_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    department = get_department_for_user(db, user, department_id)
    categories = db.scalars(select(DepartmentCategory).where(
        DepartmentCategory.department_id == department_id,
        DepartmentCategory.organization_id == _org_id(user),
    ).order_by(DepartmentCategory.name)).all()
    roles = db.scalars(select(DepartmentRole).where(
        DepartmentRole.department_id == department_id,
        DepartmentRole.organization_id == _org_id(user),
    ).order_by(DepartmentRole.name)).all()
    rules = db.scalars(select(DepartmentRoutingRule).where(
        DepartmentRoutingRule.department_id == department_id,
        DepartmentRoutingRule.organization_id == _org_id(user),
    ).order_by(DepartmentRoutingRule.created_at)).all()
    category_by_id = {category.id: category for category in categories}
    role_by_id = {role.id: role for role in roles}
    policy = db.scalar(select(DepartmentEscalationPolicy).where(
        DepartmentEscalationPolicy.department_id == department_id,
        DepartmentEscalationPolicy.organization_id == _org_id(user),
    ))
    response = DepartmentConfigurationResponse(
        department=DepartmentResponse.model_validate(department),
        categories=[DepartmentCategoryResponse.model_validate(item) for item in categories],
        roles=[DepartmentRoleResponse.model_validate(item) for item in roles],
        routing_rules=[
            _rule_response(rule, category_by_id[rule.category_id], role_by_id[rule.department_role_id])
            for rule in rules
        ],
        escalation_policy=(
            _policy_response(policy, role_by_id[policy.escalate_to_role_id]) if policy else None
        ),
    )
    return ok("Department configuration retrieved successfully.", response)


@router.get(
    "/{department_id}/categories",
    response_model=BaseResponse[list[DepartmentCategoryResponse]],
    response_model_exclude_none=True,
    tags=[CATEGORIES_TAG],
)
def list_department_categories(
    department_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_department_for_user(db, user, department_id)
    categories = db.scalars(select(DepartmentCategory).where(
        DepartmentCategory.department_id == department_id,
        DepartmentCategory.organization_id == _org_id(user),
    ).order_by(DepartmentCategory.name)).all()
    return ok("Department categories retrieved successfully.", categories)


@router.post(
    "/{department_id}/categories",
    response_model=BaseResponse[DepartmentCategoryResponse],
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    tags=[CATEGORIES_TAG],
)
def create_department_category(
    department_id: uuid.UUID,
    request: DepartmentCategoryCreate,
    user: User = Depends(admin),
    db: Session = Depends(get_db),
):
    get_department_for_user(db, user, department_id)
    category = DepartmentCategory(
        organization_id=_org_id(user), department_id=department_id, name=request.name
    )
    db.add(category)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A category with this name already exists.")
    db.refresh(category)
    return ok("Department category created successfully.", category)


@router.put(
    "/{department_id}/categories/{category_id}",
    response_model=BaseResponse[DepartmentCategoryResponse],
    response_model_exclude_none=True,
    tags=[CATEGORIES_TAG],
)
def update_department_category(
    department_id: uuid.UUID,
    category_id: uuid.UUID,
    request: DepartmentCategoryUpdate,
    user: User = Depends(admin),
    db: Session = Depends(get_db),
):
    category = _get_category(db, user, department_id, category_id)
    category.name = request.name
    category.is_active = request.is_active
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A category with this name already exists.")
    db.refresh(category)
    return ok("Department category updated successfully.", category)


@router.delete(
    "/{department_id}/categories/{category_id}",
    response_model=BaseResponse[None],
    response_model_exclude_none=True,
    tags=[CATEGORIES_TAG],
)
def delete_department_category(
    department_id: uuid.UUID,
    category_id: uuid.UUID,
    user: User = Depends(admin),
    db: Session = Depends(get_db),
):
    category = _get_category(db, user, department_id, category_id)
    db.delete(category)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Remove this category's routing rule first.")
    return ok("Department category deleted successfully.")


@router.get(
    "/{department_id}/roles",
    response_model=BaseResponse[list[DepartmentRoleResponse]],
    response_model_exclude_none=True,
    tags=[ROLES_TAG],
)
def list_department_roles(
    department_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_department_for_user(db, user, department_id)
    roles = db.scalars(select(DepartmentRole).where(
        DepartmentRole.department_id == department_id,
        DepartmentRole.organization_id == _org_id(user),
    ).order_by(DepartmentRole.name)).all()
    return ok("Department roles retrieved successfully.", roles)


@router.post(
    "/{department_id}/roles",
    response_model=BaseResponse[DepartmentRoleResponse],
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    tags=[ROLES_TAG],
)
def create_department_role(
    department_id: uuid.UUID,
    request: DepartmentRoleCreate,
    user: User = Depends(admin),
    db: Session = Depends(get_db),
):
    get_department_for_user(db, user, department_id)
    role = DepartmentRole(
        organization_id=_org_id(user), department_id=department_id, **request.model_dump()
    )
    db.add(role)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A department role with this name already exists.")
    db.refresh(role)
    return ok("Department role created successfully.", role)


@router.put(
    "/{department_id}/roles/{role_id}",
    response_model=BaseResponse[DepartmentRoleResponse],
    response_model_exclude_none=True,
    tags=[ROLES_TAG],
)
def update_department_role(
    department_id: uuid.UUID,
    role_id: uuid.UUID,
    request: DepartmentRoleUpdate,
    user: User = Depends(admin),
    db: Session = Depends(get_db),
):
    role = _get_role(db, user, department_id, role_id)
    for field, value in request.model_dump().items():
        setattr(role, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A department role with this name already exists.")
    db.refresh(role)
    return ok("Department role updated successfully.", role)


@router.delete(
    "/{department_id}/roles/{role_id}",
    response_model=BaseResponse[None],
    response_model_exclude_none=True,
    tags=[ROLES_TAG],
)
def delete_department_role(
    department_id: uuid.UUID,
    role_id: uuid.UUID,
    user: User = Depends(admin),
    db: Session = Depends(get_db),
):
    role = _get_role(db, user, department_id, role_id)
    db.delete(role)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Remove routing rules and escalation policies using this role first.",
        )
    return ok("Department role deleted successfully.")


@router.get(
    "/{department_id}/routing-rules",
    response_model=BaseResponse[list[DepartmentRoutingRuleResponse]],
    response_model_exclude_none=True,
    tags=[ROUTING_TAG],
)
def list_department_routing_rules(
    department_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_department_for_user(db, user, department_id)
    categories = {item.id: item for item in db.scalars(select(DepartmentCategory).where(
        DepartmentCategory.department_id == department_id
    )).all()}
    roles = {item.id: item for item in db.scalars(select(DepartmentRole).where(
        DepartmentRole.department_id == department_id
    )).all()}
    rules = db.scalars(select(DepartmentRoutingRule).where(
        DepartmentRoutingRule.department_id == department_id,
        DepartmentRoutingRule.organization_id == _org_id(user),
    ).order_by(DepartmentRoutingRule.created_at)).all()
    return ok(
        "Department routing rules retrieved successfully.",
        [_rule_response(rule, categories[rule.category_id], roles[rule.department_role_id]) for rule in rules],
    )


@router.post(
    "/{department_id}/routing-rules",
    response_model=BaseResponse[DepartmentRoutingRuleResponse],
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    tags=[ROUTING_TAG],
)
def create_department_routing_rule(
    department_id: uuid.UUID,
    request: DepartmentRoutingRuleCreate,
    user: User = Depends(admin),
    db: Session = Depends(get_db),
):
    category = _get_category(db, user, department_id, request.category_id)
    role = _get_role(db, user, department_id, request.department_role_id)
    rule = DepartmentRoutingRule(
        organization_id=_org_id(user), department_id=department_id, **request.model_dump()
    )
    db.add(rule)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This category already has a routing rule.")
    db.refresh(rule)
    return ok("Department routing rule created successfully.", _rule_response(rule, category, role))


@router.put(
    "/{department_id}/routing-rules/{rule_id}",
    response_model=BaseResponse[DepartmentRoutingRuleResponse],
    response_model_exclude_none=True,
    tags=[ROUTING_TAG],
)
def update_department_routing_rule(
    department_id: uuid.UUID,
    rule_id: uuid.UUID,
    request: DepartmentRoutingRuleCreate,
    user: User = Depends(admin),
    db: Session = Depends(get_db),
):
    rule = _get_rule(db, user, department_id, rule_id)
    category = _get_category(db, user, department_id, request.category_id)
    role = _get_role(db, user, department_id, request.department_role_id)
    for field, value in request.model_dump().items():
        setattr(rule, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This category already has a routing rule.")
    db.refresh(rule)
    return ok("Department routing rule updated successfully.", _rule_response(rule, category, role))


@router.delete(
    "/{department_id}/routing-rules/{rule_id}",
    response_model=BaseResponse[None],
    response_model_exclude_none=True,
    tags=[ROUTING_TAG],
)
def delete_department_routing_rule(
    department_id: uuid.UUID,
    rule_id: uuid.UUID,
    user: User = Depends(admin),
    db: Session = Depends(get_db),
):
    db.delete(_get_rule(db, user, department_id, rule_id))
    db.commit()
    return ok("Department routing rule deleted successfully.")


@router.get(
    "/{department_id}/escalation",
    response_model=BaseResponse[DepartmentEscalationPolicyResponse | None],
    response_model_exclude_none=True,
    tags=[ESCALATION_TAG],
)
def get_department_escalation(
    department_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_department_for_user(db, user, department_id)
    policy = db.scalar(select(DepartmentEscalationPolicy).where(
        DepartmentEscalationPolicy.department_id == department_id,
        DepartmentEscalationPolicy.organization_id == _org_id(user),
    ))
    if policy is None:
        return ok("Department escalation policy is not configured.")
    role = _get_role(db, user, department_id, policy.escalate_to_role_id)
    return ok("Department escalation policy retrieved successfully.", _policy_response(policy, role))


@router.put(
    "/{department_id}/escalation",
    response_model=BaseResponse[DepartmentEscalationPolicyResponse],
    response_model_exclude_none=True,
    tags=[ESCALATION_TAG],
)
def upsert_department_escalation(
    department_id: uuid.UUID,
    request: DepartmentEscalationPolicyWrite,
    user: User = Depends(admin),
    db: Session = Depends(get_db),
):
    get_department_for_user(db, user, department_id)
    role = _get_role(db, user, department_id, request.escalate_to_role_id)
    policy = db.scalar(select(DepartmentEscalationPolicy).where(
        DepartmentEscalationPolicy.department_id == department_id,
        DepartmentEscalationPolicy.organization_id == _org_id(user),
    ))
    if policy is None:
        policy = DepartmentEscalationPolicy(
            organization_id=_org_id(user), department_id=department_id, **request.model_dump()
        )
        db.add(policy)
    else:
        for field, value in request.model_dump().items():
            setattr(policy, field, value)
    db.commit()
    db.refresh(policy)
    return ok("Department escalation policy saved successfully.", _policy_response(policy, role))


@router.delete(
    "/{department_id}/escalation",
    response_model=BaseResponse[None],
    response_model_exclude_none=True,
    tags=[ESCALATION_TAG],
)
def delete_department_escalation(
    department_id: uuid.UUID,
    user: User = Depends(admin),
    db: Session = Depends(get_db),
):
    get_department_for_user(db, user, department_id)
    policy = db.scalar(select(DepartmentEscalationPolicy).where(
        DepartmentEscalationPolicy.department_id == department_id,
        DepartmentEscalationPolicy.organization_id == _org_id(user),
    ))
    if policy is None:
        raise HTTPException(status_code=404, detail="Department escalation policy not found.")
    db.delete(policy)
    db.commit()
    return ok("Department escalation policy deleted successfully.")
