"""Job endpoints for field work in the signed-in organization."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.department import Department
from app.models.job import Job
from app.models.user import User, UserRole, UserStatus
from app.modules.departments.router import _org_id
from app.schemas.job import JobCreate, JobResponse, JobStatus, JobStatusUpdate, JobUpdate
from app.shared.response import BaseResponse, ok


router = APIRouter(prefix="/jobs", tags=["Jobs"])
manager = require_roles(UserRole.ORG_ADMIN, UserRole.SUPERVISOR)


def _job(db: Session, user: User, job_id: uuid.UUID) -> Job:
    job = db.scalar(select(Job).where(Job.id == job_id, Job.organization_id == _org_id(user)))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


def _validate_links(db: Session, user: User, request: JobCreate) -> None:
    if db.scalar(select(Department.id).where(
        Department.id == request.department_id, Department.organization_id == _org_id(user)
    )) is None:
        raise HTTPException(status_code=422, detail="Department must belong to your organization.")
    if db.scalar(select(User.id).where(
        User.id == request.assigned_to_id,
        User.organization_id == _org_id(user),
        User.status == UserStatus.ACTIVE,
    )) is None:
        raise HTTPException(status_code=422, detail="Technician must be an active user in your organization.")


@router.get("", response_model=BaseResponse[list[JobResponse]], response_model_exclude_none=True)
def list_jobs(
    status_filter: JobStatus | None = Query(default=None, alias="status"),
    department_id: uuid.UUID | None = None,
    assigned_to_me: bool = False,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    query = select(Job).where(Job.organization_id == _org_id(user))
    if status_filter:
        query = query.where(Job.status == status_filter)
    if department_id:
        query = query.where(Job.department_id == department_id)
    if assigned_to_me:
        query = query.where(Job.assigned_to_id == user.id)
    jobs = db.scalars(query.order_by(Job.created_at.desc(), Job.id.desc())).all()
    return ok("Jobs retrieved successfully.", jobs)


@router.post("", response_model=BaseResponse[JobResponse], response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
def create_job(request: JobCreate, user: User = Depends(manager), db: Session = Depends(get_db)):
    _validate_links(db, user, request)
    job = Job(organization_id=_org_id(user), **request.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return ok("Job created successfully.", job)


@router.get("/{job_id}", response_model=BaseResponse[JobResponse], response_model_exclude_none=True)
def get_job(job_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ok("Job retrieved successfully.", _job(db, user, job_id))


@router.put("/{job_id}", response_model=BaseResponse[JobResponse], response_model_exclude_none=True)
def update_job(job_id: uuid.UUID, request: JobUpdate, user: User = Depends(manager), db: Session = Depends(get_db)):
    job = _job(db, user, job_id)
    _validate_links(db, user, request)
    for field, value in request.model_dump().items():
        setattr(job, field, value)
    db.commit()
    db.refresh(job)
    return ok("Job updated successfully.", job)


@router.patch("/{job_id}/status", response_model=BaseResponse[JobResponse], response_model_exclude_none=True)
def update_job_status(job_id: uuid.UUID, request: JobStatusUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = _job(db, user, job_id)
    if user.role not in (UserRole.ORG_ADMIN, UserRole.SUPERVISOR) and job.assigned_to_id != user.id:
        raise HTTPException(status_code=403, detail="Only the assigned technician or a manager may update status.")
    allowed = {
        "ASSIGNED": {"IN_PROGRESS", "ESCALATED"},
        "IN_PROGRESS": {"COMPLETED", "ESCALATED"},
        "ESCALATED": {"IN_PROGRESS", "COMPLETED"},
        "COMPLETED": set(),
    }
    if request.status not in allowed[job.status]:
        raise HTTPException(status_code=409, detail=f"Cannot change job from {job.status} to {request.status}.")
    job.status = request.status
    db.commit()
    db.refresh(job)
    return ok("Job status updated successfully.", job)
