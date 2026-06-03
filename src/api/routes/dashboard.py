"""
src/api/routes/dashboard.py
Aggregate dashboard endpoints — returns all dashboard data in ONE query.
Eliminates multiple HTTP round trips from the frontend on page load.
"""
from typing import Any

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from src.api.dependencies import require_roles
from src.database.connection import get_session
from src.models import ApplicationAIAnalysis, CandidateApplication, JobPosting, Resume, User
from src.services.recruitment_ai import analysis_payload

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/hr")
def hr_dashboard(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr", "manager")),
):
    """
    Single endpoint that returns jobs + applications + candidates together.
    Replaces 3 separate API calls with 5 optimised batch queries.
    """
    # ── 1. Jobs ───────────────────────────────────────────────────────────────
    jobs = session.exec(select(JobPosting).order_by(JobPosting.created_at.desc())).all()

    # ── 2. Applications ───────────────────────────────────────────────────────
    applications = session.exec(
        select(CandidateApplication).order_by(CandidateApplication.application_date.desc())
    ).all()

    # ── 3. Batch-fetch related data (4 queries total, no N+1) ─────────────────
    job_ids = list({a.job_id for a in applications if a.job_id})
    cand_ids = list({a.candidate_user_id for a in applications if a.candidate_user_id})
    app_ids = [a.id for a in applications]

    jobs_by_id: dict[int, JobPosting] = {j.id: j for j in jobs}
    users_by_id: dict[int, User] = {}
    analyses_by_app: dict[int, ApplicationAIAnalysis] = {}

    if cand_ids:
        for u in session.exec(select(User).where(User.id.in_(cand_ids))).all():
            users_by_id[u.id] = u
    if app_ids:
        for an in session.exec(
            select(ApplicationAIAnalysis).where(ApplicationAIAnalysis.application_id.in_(app_ids))
        ).all():
            analyses_by_app[an.application_id] = an

    # ── 4. Candidates list ────────────────────────────────────────────────────
    all_candidates = session.exec(
        select(User).where(User.role == "candidate").order_by(User.created_at.desc())
    ).all()

    # ── Build payloads ────────────────────────────────────────────────────────
    apps_payload = []
    for app in applications:
        job = jobs_by_id.get(app.job_id)
        candidate = users_by_id.get(app.candidate_user_id)
        analysis = analyses_by_app.get(app.id)
        apps_payload.append({
            "id": app.id,
            "candidate_user_id": app.candidate_user_id,
            "candidate_username": candidate.username if candidate else "",
            "job_id": app.job_id,
            "job_title": job.title if job else "",
            "department": job.department if job else "",
            "application_date": app.application_date.isoformat() if app.application_date else None,
            "status": app.status,
            "ai_analysis": analysis_payload(analysis) if analysis else None,
        })

    jobs_payload = [_job_payload(j) for j in jobs]

    candidates_payload = [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "target_role": u.target_role,
            "location": u.location,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in all_candidates
    ]

    return {
        "jobs": jobs_payload,
        "applications": apps_payload,
        "candidates": candidates_payload,
    }


def _job_payload(job: JobPosting) -> dict[str, Any]:
    return {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "required_skills": job.required_skills,
        "department": job.department,
        "salary_range": job.salary_range,
        "experience_required": job.experience_required,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "created_by": job.created_by,
    }


@router.get("/candidate")
def candidate_dashboard(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("candidate")),
):
    """
    Single endpoint returning jobs + my applications + resume status.
    Replaces 3 separate API calls (listJobs, getMyApplications, getMyResume).
    """
    # ── 1. All active jobs ────────────────────────────────────────────────────
    jobs = session.exec(select(JobPosting).order_by(JobPosting.created_at.desc())).all()

    # ── 2. This candidate's applications ─────────────────────────────────────
    my_apps = session.exec(
        select(CandidateApplication)
        .where(CandidateApplication.candidate_user_id == current_user.id)
        .order_by(CandidateApplication.application_date.desc())
    ).all()

    # ── 3. Batch-fetch jobs + analyses for my applications (no N+1) ───────────
    app_job_ids = list({a.job_id for a in my_apps if a.job_id})
    app_ids = [a.id for a in my_apps]

    jobs_by_id: dict[int, JobPosting] = {j.id: j for j in jobs}
    analyses_by_app: dict[int, ApplicationAIAnalysis] = {}

    if app_ids:
        for an in session.exec(
            select(ApplicationAIAnalysis).where(ApplicationAIAnalysis.application_id.in_(app_ids))
        ).all():
            analyses_by_app[an.application_id] = an

    # ── 4. Resume status ──────────────────────────────────────────────────────
    resume = session.exec(
        select(Resume).where(Resume.user_id == current_user.id)
    ).first()

    # ── Build payloads ────────────────────────────────────────────────────────
    apps_payload = []
    for app in my_apps:
        job = jobs_by_id.get(app.job_id)
        analysis = analyses_by_app.get(app.id)
        apps_payload.append({
            "id": app.id,
            "job_id": app.job_id,
            "job_title": job.title if job else "",
            "department": job.department if job else "",
            "application_date": app.application_date.isoformat() if app.application_date else None,
            "status": app.status,
            "ai_analysis": analysis_payload(analysis) if analysis else None,
        })

    return {
        "jobs": [_job_payload(j) for j in jobs],
        "applications": apps_payload,
        "has_resume": resume is not None,
        "resume": {
            "id": resume.id,
            "raw_text": resume.raw_text[:500] if resume else "",
            "updated_at": resume.updated_at.isoformat() if resume and resume.updated_at else None,
        } if resume else None,
    }
