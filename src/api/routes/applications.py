import os
import shutil
import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from src.api.dependencies import require_roles
from src.database.connection import get_session
from src.models import CandidateApplication, Employee, JobPosting, User
from src.resume_lab import parse_resume
from src.services.recruitment_ai import (
    analysis_payload,
    analyze_application,
    application_payload,
    rank_applications_for_job,
)
from utils.resume_parser import extract_text_from_pdf

router = APIRouter(prefix="/api/applications", tags=["applications"])

MAX_FILE_SIZE_MB = 5


class HireApplicationReq(BaseModel):
    department: str = Field(default="", max_length=120)
    designation: str = Field(default="", max_length=120)
    salary: float | None = None
    joining_date: date | None = None
    employee_code: str | None = Field(default=None, max_length=40)


@router.post("/apply", status_code=201)
async def apply_to_job(
    job_id: int = Form(...),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("candidate")),
):
    job = session.get(JobPosting, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

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
    analysis = analyze_application(session, application.id)

    return {
        "success": True,
        "message": "Application submitted.",
        "application": application_payload(session, application),
        "ai_analysis": analysis_payload(analysis),
    }


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
    return [application_payload(session, application) for application in applications]


@router.get("")
def list_applications(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr", "manager")),
):
    applications = session.exec(
        select(CandidateApplication).order_by(CandidateApplication.application_date.desc())
    ).all()
    return [application_payload(session, application) for application in applications]


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

    session.add(candidate)
    session.add(application)
    session.add(employee)
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
