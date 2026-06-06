"""
src/api/routes/dashboard.py
Aggregate dashboard endpoints — returns all dashboard data in ONE query.
Eliminates multiple HTTP round trips from the frontend on page load.
"""
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from src.api.dependencies import require_roles
from src.database.connection import get_session
from src.models import (
    ApplicationAIAnalysis,
    CandidateApplication,
    JobPosting,
    Resume,
    User,
    EmployeeProfile,
    CandidateProfile,
    Employee,
    EmployeeDocument,
    CandidateDocument,
    EmployeeOnboarding,
    TrainingAssignment,
    TrainingProgram,
    InterviewSession,
)
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
    sessions_by_app: dict[int, InterviewSession] = {}

    if app_ids:
        for an in session.exec(
            select(ApplicationAIAnalysis).where(ApplicationAIAnalysis.application_id.in_(app_ids))
        ).all():
            analyses_by_app[an.application_id] = an
            
        for sess in session.exec(
            select(InterviewSession).where(InterviewSession.application_id.in_(app_ids)).order_by(InterviewSession.created_at.desc())
        ).all():
            # Keep the most recent session if multiple exist
            if sess.application_id not in sessions_by_app:
                sessions_by_app[sess.application_id] = sess

    # ── 4. Resume status ──────────────────────────────────────────────────────
    resume = session.exec(
        select(Resume).where(Resume.user_id == current_user.id)
    ).first()

    # ── Build payloads ────────────────────────────────────────────────────────
    apps_payload = []
    for app in my_apps:
        job = jobs_by_id.get(app.job_id)
        analysis = analyses_by_app.get(app.id)
        sess = sessions_by_app.get(app.id)
        
        apps_payload.append({
            "id": app.id,
            "job_id": app.job_id,
            "job_title": job.title if job else "",
            "department": job.department if job else "",
            "application_date": app.application_date.isoformat() if app.application_date else None,
            "status": app.status,
            "ai_analysis": analysis_payload(analysis) if analysis else None,
            "interview_status": sess.status if sess else None,
            "interview_session_id": sess.id if sess else None,
            "can_start_interview": sess is None,
            "can_resume_interview": sess is not None and sess.status == "active",
            "interview_completed": sess is not None and sess.status == "completed",
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


@router.get("/hr/reviews")
def get_hr_reviews(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr", "manager")),
):
    """
    Returns pending/overdue review queues for HR home widgets.
    """
    # 1. Pending Profile Reviews (completed but unverified profiles)
    cand_profiles = session.exec(
        select(CandidateProfile)
        .where(CandidateProfile.is_complete == True)
    ).all()
    emp_profiles = session.exec(
        select(EmployeeProfile)
        .where(EmployeeProfile.is_complete == True)
        .where(EmployeeProfile.verification_status == "Pending Review")
    ).all()
    
    users = {u.id: u for u in session.exec(select(User)).all()}
    employees = {e.id: e for e in session.exec(select(Employee)).all()}
    
    pending_profiles = []
    for cp in cand_profiles:
        user = users.get(cp.user_id)
        pending_profiles.append({
            "type": "Candidate",
            "id": cp.id,
            "user_id": cp.user_id,
            "name": cp.full_name or (user.username if user else "Candidate"),
            "completion_percent": cp.completion_percent,
            "updated_at": cp.updated_at.isoformat() if cp.updated_at else None,
        })
    for ep in emp_profiles:
        user = users.get(ep.user_id)
        emp = employees.get(ep.employee_id) if ep.employee_id else None
        pending_profiles.append({
            "type": "Employee",
            "id": ep.id,
            "user_id": ep.user_id,
            "name": emp.full_name if emp else (user.username if user else "Employee"),
            "completion_percent": ep.completion_percent,
            "updated_at": ep.updated_at.isoformat() if ep.updated_at else None,
        })
        
    # 2. Pending Document Verifications
    emp_docs = session.exec(
        select(EmployeeDocument)
        .where(EmployeeDocument.verification_status == "Pending Review")
    ).all()
    cand_docs = session.exec(
        select(CandidateDocument)
        .where(CandidateDocument.verification_status == "Pending Review")
    ).all()
    
    pending_docs = []
    for d in cand_docs:
        user = users.get(d.user_id)
        pending_docs.append({
            "kind": "candidate",
            "id": d.id,
            "user_id": d.user_id,
            "username": user.username if user else "",
            "document_type": d.document_type,
            "original_filename": d.original_filename,
            "uploaded_at": d.uploaded_at.isoformat() + "Z" if d.uploaded_at else None,
        })
    for d in emp_docs:
        user = users.get(d.user_id)
        pending_docs.append({
            "kind": "employee",
            "id": d.id,
            "user_id": d.user_id,
            "username": user.username if user else "",
            "document_type": d.document_type,
            "original_filename": d.original_filename,
            "uploaded_at": d.uploaded_at.isoformat() + "Z" if d.uploaded_at else None,
        })
        
    # 3. Pending Onboarding Assignments
    all_employees = session.exec(select(Employee)).all()
    all_plans = session.exec(select(EmployeeOnboarding)).all()
    has_any_plan_ids = {p.employee_id for p in all_plans}
    
    pending_onboarding = []
    for emp in all_employees:
        if emp.id not in has_any_plan_ids:
            user = users.get(emp.user_id)
            pending_onboarding.append({
                "employee_id": emp.id,
                "user_id": emp.user_id,
                "name": emp.full_name or (user.username if user else "Employee"),
                "employee_code": emp.employee_code,
                "department": emp.department,
                "joining_date": emp.joining_date.isoformat() if emp.joining_date else None,
            })
            
    # 4. Overdue Training Assignments
    overdue_trainings = session.exec(
        select(TrainingAssignment)
        .where(TrainingAssignment.status != "Completed")
        .where(TrainingAssignment.due_date < date.today())
    ).all()
    
    overdue_training_list = []
    for ta in overdue_trainings:
        emp = employees.get(ta.employee_id)
        user = users.get(emp.user_id) if emp else None
        prog = session.get(TrainingProgram, ta.program_id)
        overdue_training_list.append({
            "id": ta.id,
            "employee_id": ta.employee_id,
            "name": emp.full_name if emp else (user.username if user else "Employee"),
            "program_title": prog.title if prog else f"Program {ta.program_id}",
            "due_date": ta.due_date.isoformat() if ta.due_date else None,
            "status": ta.status,
            "progress_percent": ta.progress_percent,
        })
        
    # 5. Incomplete Candidate Profiles
    incomplete_cands = session.exec(
        select(CandidateProfile)
        .where(CandidateProfile.is_complete == False)
    ).all()
    incomplete_candidate_list = []
    for cp in incomplete_cands:
        user = users.get(cp.user_id)
        incomplete_candidate_list.append({
            "id": cp.id,
            "user_id": cp.user_id,
            "name": cp.full_name or (user.username if user else "Candidate"),
            "completion_percent": cp.completion_percent,
            "updated_at": cp.updated_at.isoformat() if cp.updated_at else None,
        })

    # 6. Incomplete Employee Profiles
    incomplete_emps = session.exec(
        select(EmployeeProfile)
        .where(EmployeeProfile.is_complete == False)
    ).all()
    incomplete_employee_list = []
    for ep in incomplete_emps:
        user = users.get(ep.user_id)
        emp = employees.get(ep.employee_id) if ep.employee_id else None
        incomplete_employee_list.append({
            "id": ep.id,
            "user_id": ep.user_id,
            "name": emp.full_name if emp else (user.username if user else "Employee"),
            "completion_percent": ep.completion_percent,
            "updated_at": ep.updated_at.isoformat() if ep.updated_at else None,
        })

    return {
        "pending_profiles": pending_profiles,
        "pending_documents": pending_docs,
        "pending_onboarding_assignments": pending_onboarding,
        "overdue_trainings": overdue_training_list,
        "incomplete_candidates": incomplete_candidate_list,
        "incomplete_employees": incomplete_employee_list,
    }
