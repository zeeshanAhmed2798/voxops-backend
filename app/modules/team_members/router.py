"""Organization member directory, invitations, roles, and member management."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.department import Department
from app.models.user import AppRole, User, UserRole, UserStatus
from app.schemas.team_member import (
    AppRoleResponse,
    MemberDepartmentResponse,
    TeamMemberInvite,
    TeamMemberResponse,
    TeamMemberUpdate,
)
from app.shared.pagination import CursorPage, decode_cursor, encode_cursor
from app.shared.response import BaseResponse, ok


router = APIRouter(prefix="/team-members")
admin = require_roles(UserRole.ORG_ADMIN)

DIRECTORY_TAG = "Teams — Member Directory"
ROLES_TAG = "Teams — Application Roles"


def _org_id(user: User) -> uuid.UUID:
    if user.organization_id is None:
        raise HTTPException(status_code=403, detail="Your account is not assigned to an organization.")
    return user.organization_id


def _department(db: Session, user: User, department_id: uuid.UUID) -> Department:
    department = db.scalar(select(Department).where(
        Department.id == department_id,
        Department.organization_id == _org_id(user),
    ))
    if department is None:
        raise HTTPException(status_code=422, detail="Department must belong to your organization.")
    return department


def _role(db: Session, role_id: uuid.UUID, *, assignable: bool = True) -> AppRole:
    query = select(AppRole).where(AppRole.id == role_id, AppRole.is_active.is_(True))
    if assignable:
        query = query.where(AppRole.is_assignable.is_(True))
    role = db.scalar(query)
    if role is None:
        raise HTTPException(status_code=422, detail="Select an active assignable role.")
    return role


def _member(db: Session, user: User, member_id: uuid.UUID) -> User:
    member = db.scalar(select(User).where(
        User.id == member_id,
        User.organization_id == _org_id(user),
    ))
    if member is None:
        raise HTTPException(status_code=404, detail="Team member not found.")
    return member


def _member_response(member: User) -> TeamMemberResponse:
    return TeamMemberResponse(
        id=member.id,
        email=member.email,
        full_name=member.name,
        department=(
            MemberDepartmentResponse.model_validate(member.department)
            if member.department is not None else None
        ),
        role=AppRoleResponse.model_validate(member.user_role),
        status=member.status,
        job_title=member.job_title,
        created_at=member.created_at,
        updated_at=member.updated_at,
    )


@router.get(
    "/roles",
    response_model=BaseResponse[list[AppRoleResponse]],
    response_model_exclude_none=True,
    tags=[ROLES_TAG],
    summary="List assignable application roles",
)
def list_application_roles(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    roles = db.scalars(select(AppRole).where(
        AppRole.is_active.is_(True),
        AppRole.is_assignable.is_(True),
    ).order_by(AppRole.sort_order, AppRole.name)).all()
    return ok("Application roles retrieved successfully.", roles)


@router.get(
    "",
    response_model=BaseResponse[CursorPage[TeamMemberResponse]],
    response_model_exclude_none=True,
    tags=[DIRECTORY_TAG],
    summary="List organization team members",
)
def list_team_members(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=1000),
    search: str | None = Query(default=None, max_length=255),
    department_id: uuid.UUID | None = None,
    role_id: uuid.UUID | None = None,
    member_status: UserStatus | None = Query(default=None, alias="status"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(User).where(User.organization_id == _org_id(user))
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(or_(User.name.ilike(pattern), User.email.ilike(pattern)))
    if department_id:
        query = query.where(User.department_id == department_id)
    if role_id:
        query = query.where(User.user_role_id == role_id)
    if member_status:
        query = query.where(User.status == member_status)
    if cursor:
        try:
            cursor_data = decode_cursor(cursor)
            cursor_name = cursor_data["name"]
            cursor_id = uuid.UUID(cursor_data["id"])
        except (KeyError, ValueError):
            raise HTTPException(status_code=422, detail="Invalid pagination cursor.")
        query = query.where(or_(
            User.name > cursor_name,
            and_(User.name == cursor_name, User.id > cursor_id),
        ))

    members = list(db.scalars(query.order_by(User.name, User.id).limit(limit + 1)).unique().all())
    has_more = len(members) > limit
    members = members[:limit]
    next_cursor = None
    if has_more and members:
        last = members[-1]
        next_cursor = encode_cursor({"name": last.name, "id": str(last.id)})
    page = CursorPage(
        items=[_member_response(member) for member in members],
        next_cursor=next_cursor,
        has_more=has_more,
        limit=limit,
    )
    return ok("Team members retrieved successfully.", page)


@router.post(
    "",
    response_model=BaseResponse[TeamMemberResponse],
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    tags=[DIRECTORY_TAG],
    summary="Invite an organization team member",
)
def invite_team_member(
    request: TeamMemberInvite,
    user: User = Depends(admin),
    db: Session = Depends(get_db),
):
    department = _department(db, user, request.department_id)
    role = _role(db, request.role_id)
    member = User(
        organization_id=_org_id(user),
        department_id=department.id,
        user_role_id=role.id,
        user_role=role,
        name=request.full_name.strip(),
        email=str(request.email).lower(),
        password_hash=None,
        status=UserStatus.INVITED,
        timezone="UTC",
    )
    db.add(member)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A user with this email already exists.")
    db.refresh(member)
    return ok("Team member invited successfully.", _member_response(member))


@router.get(
    "/{member_id}",
    response_model=BaseResponse[TeamMemberResponse],
    response_model_exclude_none=True,
    tags=[DIRECTORY_TAG],
)
def get_team_member(
    member_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ok("Team member retrieved successfully.", _member_response(_member(db, user, member_id)))


@router.patch(
    "/{member_id}",
    response_model=BaseResponse[TeamMemberResponse],
    response_model_exclude_none=True,
    tags=[DIRECTORY_TAG],
    summary="Update a team member",
)
def update_team_member(
    member_id: uuid.UUID,
    request: TeamMemberUpdate,
    user: User = Depends(admin),
    db: Session = Depends(get_db),
):
    member = _member(db, user, member_id)
    changes = request.model_dump(exclude_unset=True)
    if "role_id" in changes:
        role = _role(db, changes.pop("role_id"))
        member.user_role_id = role.id
        member.user_role = role
    if "department_id" in changes:
        department = _department(db, user, changes.pop("department_id"))
        member.department_id = department.id
        member.department = department
    if "full_name" in changes:
        member.name = changes.pop("full_name").strip()
    if changes.get("status") == UserStatus.ACTIVE and member.password_hash is None:
        raise HTTPException(
            status_code=422,
            detail="An invited member must complete account activation before becoming active.",
        )
    for field, value in changes.items():
        setattr(member, field, value)
    db.commit()
    db.refresh(member)
    return ok("Team member updated successfully.", _member_response(member))


@router.delete(
    "/{member_id}",
    response_model=BaseResponse[None],
    response_model_exclude_none=True,
    tags=[DIRECTORY_TAG],
    summary="Deactivate a team member",
)
def deactivate_team_member(
    member_id: uuid.UUID,
    user: User = Depends(admin),
    db: Session = Depends(get_db),
):
    member = _member(db, user, member_id)
    if member.id == user.id:
        raise HTTPException(status_code=409, detail="You cannot deactivate your own account.")
    member.status = UserStatus.INACTIVE
    db.commit()
    return ok("Team member deactivated successfully.")
