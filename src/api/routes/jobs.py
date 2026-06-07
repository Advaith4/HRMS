import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from src.api.dependencies import require_roles
from src.database.connection import get_session
from src.models import CandidateApplication, JobPosting, User
from src.services.rag.sync_service import RAGSyncService

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
logger = logging.getLogger(__name__)

JOB_STATUS_OPEN = "OPEN"
JOB_STATUS_CLOSED = "CLOSED"
JOB_STATUS_ARCHIVED = "ARCHIVED"
JOB_DELETE_BLOCKED_MESSAGE = "This job contains applicant history and cannot be deleted. Close or archive the job instead."


class JobCreateReq(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=20000)
    required_skills: str = Field(default="", max_length=2000)
    department: str = Field(default="", max_length=120)
    salary_range: str = Field(default="", max_length=120)
    experience_required: str = Field(default="", max_length=120)


class JobUpdateReq(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=20000)
    required_skills: str | None = Field(default=None, max_length=2000)
    department: str | None = Field(default=None, max_length=120)
    salary_range: str | None = Field(default=None, max_length=120)
    experience_required: str | None = Field(default=None, max_length=120)


@router.get("")
def list_jobs(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("candidate", "hr", "manager")),
):
    query = select(JobPosting)
    if current_user.role == "candidate":
        query = query.where(JobPosting.status != JOB_STATUS_ARCHIVED)
    jobs = session.exec(query.order_by(JobPosting.created_at.desc())).all()
    return [_job_payload(job) for job in jobs]


@router.get("/{job_id}")
def get_job(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("candidate", "hr", "manager")),
):
    job = session.get(JobPosting, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if current_user.role == "candidate" and job.status == JOB_STATUS_ARCHIVED:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_payload(job)


@router.post("", status_code=201)
def create_job(
    req: JobCreateReq,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr")),
):
    job = JobPosting(
        title=req.title.strip(),
        description=req.description.strip(),
        required_skills=req.required_skills.strip(),
        department=req.department.strip(),
        salary_range=req.salary_range.strip(),
        experience_required=req.experience_required.strip(),
        status=JOB_STATUS_OPEN,
        created_by=current_user.id,
        created_at=datetime.utcnow(),
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    _sync_job_to_rag(job)
    return _job_payload(job)


@router.put("/{job_id}")
def update_job(
    job_id: int,
    req: JobUpdateReq,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr")),
):
    job = session.get(JobPosting, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(job, field, value.strip() if isinstance(value, str) else value)

    session.add(job)
    session.commit()
    session.refresh(job)
    _sync_job_to_rag(job)
    return _job_payload(job)


@router.delete("/{job_id}")
def delete_job(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr", "manager")),
):
    job = session.get(JobPosting, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    application = session.exec(
        select(CandidateApplication).where(CandidateApplication.job_id == job_id)
    ).first()
    if application:
        raise HTTPException(status_code=409, detail=JOB_DELETE_BLOCKED_MESSAGE)
    session.delete(job)
    session.commit()
    _delete_job_from_rag(job_id)
    return {"success": True, "message": "Job deleted"}


@router.post("/{job_id}/close")
def close_job(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr", "manager")),
):
    job = session.get(JobPosting, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status == JOB_STATUS_ARCHIVED:
        raise HTTPException(status_code=409, detail="Archived jobs cannot be reopened or closed.")
    job.status = JOB_STATUS_CLOSED
    session.add(job)
    session.commit()
    session.refresh(job)
    _sync_job_to_rag(job)
    return _job_payload(job)


@router.post("/{job_id}/archive")
def archive_job(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr", "manager")),
):
    job = session.get(JobPosting, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = JOB_STATUS_ARCHIVED
    session.add(job)
    session.commit()
    session.refresh(job)
    _sync_job_to_rag(job)
    return _job_payload(job)


def _sync_job_to_rag(job: JobPosting) -> None:
    try:
        RAGSyncService().sync_job(job)
    except Exception as exc:  # noqa: BLE001
        logger.warning("RAG job sync failed job_id=%s error=%s", job.id, exc)


def _delete_job_from_rag(job_id: int) -> None:
    try:
        RAGSyncService().delete_job(job_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("RAG job delete sync failed job_id=%s error=%s", job_id, exc)


def _job_payload(job: JobPosting) -> dict[str, Any]:
    return {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "required_skills": job.required_skills,
        "department": job.department,
        "salary_range": job.salary_range,
        "experience_required": job.experience_required,
        "status": job.status or JOB_STATUS_OPEN,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "created_by": job.created_by,
    }
