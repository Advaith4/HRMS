import logging
import os
import shutil
import uuid
from datetime import date, datetime
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from src.api.dependencies import require_roles
from src.database.connection import get_session
from src.models import (
    ApplicationAIAnalysis,
    CandidateApplication,
    Employee,
    JobPosting,
    User,
    CandidateProfile,
    CandidateDocument,
    EmployeeProfile,
    EmployeeDocument,
    EmployeeOnboarding,
    EmployeeOnboardingTask,
    OnboardingTemplate,
    OnboardingTask,
    HRNotification,
    EmployeeLifecycleEvent,
)
from src.resume_lab import parse_resume
from src.services.recruitment_ai import (
    analysis_payload,
    analyze_application,
    application_payload,
    rank_applications_for_job,
)
from utils.resume_parser import extract_text_from_pdf

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/applications", tags=["applications"])

MAX_FILE_SIZE_MB = 5


class HireApplicationReq(BaseModel):
    department: str = Field(default="", max_length=120)
    designation: str = Field(default="", max_length=120)
    salary: float | None = None
    joining_date: date | None = None
    employee_code: str | None = Field(default=None, max_length=40)
    onboarding_template_id: Optional[int] = None


@router.post("/apply", status_code=201)
async def apply_to_job(
    job_id: int = Form(...),
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("candidate")),
):
    job = session.get(JobPosting, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing = session.exec(
        select(CandidateApplication)
        .where(CandidateApplication.candidate_user_id == current_user.id)
        .where(CandidateApplication.job_id == job_id)
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="You have already submitted an application for this job opening."
        )

    resume_text = await _extract_resume_text(file)
    application = CandidateApplication(
        candidate_user_id=current_user.id,
        job_id=job.id,
        resume_text=resume_text,
        application_date=datetime.utcnow(),
        status="Applied",
    )
    session.add(application)
    session.commit()
    session.refresh(application)

    # Run AI analysis in the background — don't make the candidate wait for the LLM
    app_id = application.id
    background_tasks.add_task(_run_analysis_background, app_id)

    return {
        "success": True,
        "message": "Application submitted. AI analysis is running in the background.",
        "application": application_payload(session, application),
        "ai_analysis": None,
    }


def _run_analysis_background(application_id: int) -> None:
    """Background task — runs AI analysis after the HTTP response is already sent."""
    from src.database.connection import engine
    with Session(engine) as bg_session:
        try:
            analyze_application(bg_session, application_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Background analysis failed for application %s: %s", application_id, exc)


@router.get("/me")
def my_applications(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("candidate")),
):
    applications = session.exec(
        select(CandidateApplication)
        .where(CandidateApplication.candidate_user_id == current_user.id)
        .order_by(CandidateApplication.application_date.desc())
    ).all()
    return _bulk_application_payloads(session, applications, include_resume=False)


@router.get("")
def list_applications(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr", "manager")),
):
    applications = session.exec(
        select(CandidateApplication).order_by(CandidateApplication.application_date.desc())
    ).all()
    return _bulk_application_payloads(session, applications)


@router.post("/{application_id}/analyze")
def reanalyze_application(
    application_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr", "manager")),
):
    application = session.get(CandidateApplication, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    analyze_application(session, application_id, force=True)
    return {"success": True, "application": application_payload(session, application)}


@router.post("/{application_id}/hire", status_code=201)
def hire_application(
    application_id: int,
    req: HireApplicationReq,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr")),
):
    application = session.get(CandidateApplication, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    candidate = session.get(User, application.candidate_user_id)
    job = session.get(JobPosting, application.job_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate user not found")
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")

    employee = session.exec(select(Employee).where(Employee.user_id == candidate.id)).first()
    parsed = parse_resume(application.resume_text)
    skills = ", ".join(parsed.get("skills", [])) or job.required_skills or ""
    now = datetime.utcnow()

    candidate.role = "employee"
    candidate.target_role = req.designation.strip() or job.title
    application.status = "Hired"

    # Retrieve candidate profile and documents
    candidate_profile = session.exec(select(CandidateProfile).where(CandidateProfile.user_id == candidate.id)).first()

    if employee is None:
        employee = Employee(
            user_id=candidate.id,
            employee_code=(req.employee_code or _next_employee_code(session)).strip(),
            department=req.department.strip() or job.department,
            designation=req.designation.strip() or job.title,
            salary=req.salary,
            joining_date=req.joining_date or date.today(),
            skills=skills,
        )
    else:
        employee.department = req.department.strip() or employee.department or job.department
        employee.designation = req.designation.strip() or employee.designation or job.title
        employee.salary = req.salary if req.salary is not None else employee.salary
        employee.joining_date = req.joining_date or employee.joining_date or date.today()
        employee.skills = employee.skills or skills
        if req.employee_code:
            employee.employee_code = req.employee_code.strip()

    # Pre-populate Employee fields if candidate profile exists
    if candidate_profile:
        employee.full_name = candidate_profile.full_name or employee.full_name or candidate.username
        employee.phone = candidate_profile.phone or employee.phone
        employee.address = candidate_profile.address or employee.address
        employee.date_of_birth = candidate_profile.date_of_birth or employee.date_of_birth
        employee.years_of_experience = candidate_profile.years_of_experience or employee.years_of_experience
        employee.certifications = candidate_profile.certifications or employee.certifications

    session.add(candidate)
    session.add(application)
    session.add(employee)
    session.flush()

    # Create/update employee profile with pre_populated=True
    employee_profile = session.exec(select(EmployeeProfile).where(EmployeeProfile.user_id == candidate.id)).first()
    if employee_profile is None:
        employee_profile = EmployeeProfile(
            user_id=candidate.id,
            employee_id=employee.id,
            pre_populated=True,
        )
    else:
        employee_profile.pre_populated = True
        employee_profile.employee_id = employee.id

    if candidate_profile:
        employee_profile.phone = candidate_profile.phone or employee_profile.phone
        employee_profile.address = candidate_profile.address or employee_profile.address
        employee_profile.skills = candidate_profile.technical_skills or employee_profile.skills
        employee_profile.certifications = candidate_profile.certifications or employee_profile.certifications
        # Pre-populate previous experience combining previous work details and education
        exp_parts = []
        if candidate_profile.current_role or candidate_profile.current_company:
            exp_parts.append(f"Previous Role: {candidate_profile.current_role} at {candidate_profile.current_company} ({candidate_profile.years_of_experience or 0} years experience)")
        if candidate_profile.degree or candidate_profile.institution:
            exp_parts.append(f"Education: {candidate_profile.degree} from {candidate_profile.institution} (Graduated: {candidate_profile.graduation_year or 'N/A'}, CGPA: {candidate_profile.cgpa_percentage or 'N/A'})")
        if exp_parts:
            employee_profile.previous_experience = "\n".join(exp_parts)

    session.add(employee_profile)

    # Record Joined lifecycle event
    joined_event = EmployeeLifecycleEvent(
        employee_id=employee.id,
        event_type="Joined",
        event_date=date.today(),
        description=f"Joined the company as {employee.designation} in {employee.department}.",
        created_by=current_user.id
    )
    session.add(joined_event)

    # Migrate candidate documents to employee documents without duplicating file
    cand_docs = session.exec(select(CandidateDocument).where(CandidateDocument.user_id == candidate.id)).all()
    for c_doc in cand_docs:
        existing_emp_doc = session.exec(
            select(EmployeeDocument)
            .where(EmployeeDocument.user_id == candidate.id)
            .where(EmployeeDocument.document_type == c_doc.document_type)
        ).first()
        if not existing_emp_doc:
            emp_doc = EmployeeDocument(
                user_id=candidate.id,
                employee_id=employee.id,
                document_type=c_doc.document_type,
                original_filename=c_doc.original_filename,
                stored_path=c_doc.stored_path,
                verification_status=c_doc.verification_status,
                rejection_comment=c_doc.rejection_comment,
                uploaded_at=c_doc.uploaded_at,
                reviewed_at=c_doc.reviewed_at,
                reviewed_by=c_doc.reviewed_by,
            )
            session.add(emp_doc)

    # Smart Onboarding Template Assignment (by department if not manually provided)
    onboard_tmpl_id = req.onboarding_template_id
    if not onboard_tmpl_id:
        dept = req.department.strip() or job.department or ""
        templates = session.exec(select(OnboardingTemplate).where(OnboardingTemplate.is_active == True)).all()
        for t in templates:
            if dept.lower() in t.name.lower() or t.name.lower() in dept.lower():
                onboard_tmpl_id = t.id
                break

    # Automatically trigger onboarding assignment if template ID is provided or determined
    if onboard_tmpl_id:
        template = session.get(OnboardingTemplate, onboard_tmpl_id)
        if template and template.is_active:
            tasks = session.exec(
                select(OnboardingTask)
                .where(OnboardingTask.template_id == template.id)
                .order_by(OnboardingTask.order_index, OnboardingTask.id)
            ).all()
            if tasks:
                # Check for active duplicate onboarding plans
                duplicate = session.exec(
                    select(EmployeeOnboarding)
                    .where(EmployeeOnboarding.employee_id == employee.id)
                    .where(EmployeeOnboarding.template_id == template.id)
                    .where(EmployeeOnboarding.status != "Completed")
                ).first()
                if not duplicate:
                    plan = EmployeeOnboarding(
                        employee_id=employee.id,
                        template_id=template.id,
                        assigned_by=current_user.id,
                        status="Active",
                        due_date=None,
                        started_at=now,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(plan)
                    session.flush()

                    for task in tasks:
                        session.add(
                            EmployeeOnboardingTask(
                                employee_onboarding_id=plan.id,
                                task_title=task.title,
                                task_description=task.description,
                                order_index=task.order_index,
                                is_required=task.is_required,
                            )
                        )
                    # Notify employee
                    session.add(
                        HRNotification(
                            user_id=employee.user_id,
                            title="Onboarding Assigned",
                            message=f"You have been assigned the {template.name} onboarding plan.",
                            event_type="onboarding_assigned",
                            related_id=plan.id,
                            is_read=False,
                        )
                    )
                    # Record Onboarding Started event
                    onboarding_event = EmployeeLifecycleEvent(
                        employee_id=employee.id,
                        event_type="Onboarding Started",
                        event_date=date.today(),
                        description=f"Onboarding started with plan: '{template.name}'.",
                        created_by=current_user.id
                    )
                    session.add(onboarding_event)

    try:
        session.commit()
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail=f"Could not create employee record: {exc}") from exc

    session.refresh(employee)
    session.refresh(application)

    return {
        "success": True,
        "message": "Candidate hired and employee profile created.",
        "application": application_payload(session, application),
        "employee": _employee_payload(session, employee),
        "hired_at": now.isoformat(),
    }


@router.get("/rankings/{job_id}")
def get_job_rankings(
    job_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr", "manager")),
):
    job = session.get(JobPosting, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job": {"id": job.id, "title": job.title}, "rankings": rank_applications_for_job(session, job_id)}


async def _extract_resume_text(file: UploadFile) -> str:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    os.makedirs("data", exist_ok=True)
    temp_path = f"data/application_resume_{uuid.uuid4().hex}.pdf"

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        size_mb = os.path.getsize(temp_path) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            raise HTTPException(status_code=400, detail=f"File exceeds {MAX_FILE_SIZE_MB}MB limit.")

        resume_text = extract_text_from_pdf(temp_path)
        if not resume_text or len(resume_text.strip()) < 50:
            raise HTTPException(status_code=400, detail="Could not extract text from PDF. Is it a scanned image?")
        return resume_text
    finally:
        await file.close()
        if os.path.exists(temp_path):
            os.remove(temp_path)


def _next_employee_code(session: Session) -> str:
    existing_count = len(session.exec(select(Employee)).all())
    for offset in range(existing_count + 1, existing_count + 1000):
        code = f"TF-{offset:05d}"
        if not session.exec(select(Employee).where(Employee.employee_code == code)).first():
            return code
    return f"TF-{uuid.uuid4().hex[:8].upper()}"


def _employee_payload(session: Session, employee: Employee) -> dict[str, Any]:
    user = session.get(User, employee.user_id)
    return {
        "id": employee.id,
        "user_id": employee.user_id,
        "username": user.username if user else "",
        "employee_code": employee.employee_code,
        "department": employee.department,
        "designation": employee.designation,
        "salary": employee.salary,
        "joining_date": employee.joining_date.isoformat() if employee.joining_date else None,
        "skills": employee.skills,
    }


def _bulk_application_payloads(
    session: Session,
    applications: list[CandidateApplication],
    include_resume: bool = True,
) -> list[dict[str, Any]]:
    """
    Build application payloads with batch DB lookups — no N+1 queries.
    Fetches all Jobs, Users, and AI Analyses in 3 queries regardless of list size.
    """
    if not applications:
        return []

    job_ids = list({a.job_id for a in applications if a.job_id})
    user_ids = list({a.candidate_user_id for a in applications if a.candidate_user_id})
    app_ids = [a.id for a in applications]

    jobs_by_id: dict[int, JobPosting] = {}
    users_by_id: dict[int, User] = {}
    analyses_by_app_id: dict[int, ApplicationAIAnalysis] = {}

    if job_ids:
        for j in session.exec(select(JobPosting).where(JobPosting.id.in_(job_ids))).all():
            jobs_by_id[j.id] = j
    if user_ids:
        for u in session.exec(select(User).where(User.id.in_(user_ids))).all():
            users_by_id[u.id] = u
    if app_ids:
        for an in session.exec(
            select(ApplicationAIAnalysis).where(ApplicationAIAnalysis.application_id.in_(app_ids))
        ).all():
            analyses_by_app_id[an.application_id] = an

    result = []
    for app in applications:
        job = jobs_by_id.get(app.job_id)
        candidate = users_by_id.get(app.candidate_user_id)
        analysis = analyses_by_app_id.get(app.id)
        payload = {
            "id": app.id,
            "candidate_user_id": app.candidate_user_id,
            "candidate_username": candidate.username if candidate else "",
            "job_id": app.job_id,
            "job_title": job.title if job else "",
            "department": job.department if job else "",
            "application_date": app.application_date.isoformat() if app.application_date else None,
            "status": app.status,
            "ai_analysis": analysis_payload(analysis) if analysis else None,
        }
        if include_resume:
            payload["resume_text"] = app.resume_text
        result.append(payload)
    return result
