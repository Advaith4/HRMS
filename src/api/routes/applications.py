import os
import shutil
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from src.api.dependencies import require_roles
from src.database.connection import get_session
from src.models import CandidateApplication, JobPosting, User
from src.services.recruitment_ai import (
    analysis_payload,
    analyze_application,
    application_payload,
    rank_applications_for_job,
)
from utils.resume_parser import extract_text_from_pdf

router = APIRouter(prefix="/api/applications", tags=["applications"])

MAX_FILE_SIZE_MB = 5


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
