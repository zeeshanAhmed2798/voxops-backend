"""Department CRUD scoped to the authenticated organization."""

import uuid

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, status
# pyrefly: ignore [missing-import, parse-error]
from sqlalchemy import select
# pyrefly: ignore [missing-import]
from sqlalchemy.exc import IntegrityError
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.department import Department
from app.models.job import Job
from app.models.user import User, UserRole
from app.schemas.department import DepartmentCreate, DepartmentResponse, DepartmentUpdate
from app.shared.response import BaseResponse, ok


router = APIRouter(prefix="/departments", tags=["Departments"])
admin = require_roles(UserRole.ORG_ADMIN)


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


@router.get("", response_model=BaseResponse[list[DepartmentResponse]], response_model_exclude_none=True)
def list_departments(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    departments = db.scalars(select(Department).where(Department.organization_id == _org_id(user)).order_by(Department.name)).all()
    return ok("Departments retrieved successfully.", departments)


@router.post("", response_model=BaseResponse[DepartmentResponse], response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
def create_department(request: DepartmentCreate, user: User = Depends(admin), db: Session = Depends(get_db)):
    department = Department(organization_id=_org_id(user), **request.model_dump())
    db.add(department)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A department with this name already exists.")
    db.refresh(department)
    return ok("Department created successfully.", department)


@router.get("/{department_id}", response_model=BaseResponse[DepartmentResponse], response_model_exclude_none=True)
def get_department(department_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok("Department retrieved successfully.", get_department_for_user(db, user, department_id))


@router.put("/{department_id}", response_model=BaseResponse[DepartmentResponse], response_model_exclude_none=True)
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


@router.delete("/{department_id}", response_model=BaseResponse[None], response_model_exclude_none=True)
def delete_department(department_id: uuid.UUID, user: User = Depends(admin), db: Session = Depends(get_db)):
    department = get_department_for_user(db, user, department_id)
    if db.scalar(select(Job.id).where(Job.department_id == department_id).limit(1)):
        raise HTTPException(status_code=409, detail="Move this department's jobs before deleting it.")
    if db.scalar(select(User.id).where(User.department_id == department_id).limit(1)):
        raise HTTPException(status_code=409, detail="Move this department's users before deleting it.")
    db.delete(department)
    db.commit()
    return ok("Department deleted successfully.")
