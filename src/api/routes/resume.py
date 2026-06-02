import os
import shutil
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session, select

from src.api.dependencies import require_roles
from src.database.connection import get_session
from src.models import Resume, User
from src.resume_lab import dumps_json, parse_resume
from utils.resume_parser import extract_text_from_pdf

router = APIRouter(prefix="/api/resume", tags=["resume"])

MAX_FILE_SIZE_MB = 5


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("candidate")),
):
    resume_text = await _extract_resume_text(file)
    parsed = parse_resume(resume_text)
    resume = session.exec(select(Resume).where(Resume.user_id == current_user.id)).first()
    now = datetime.utcnow()

    if resume:
        resume.raw_text = resume_text
        resume.original_text = resume_text
        resume.current_text = resume_text
        resume.parsed_resume = dumps_json(parsed)
        resume.last_analysis = None
        resume.applied_fixes = "[]"
        resume.updated_at = now
    else:
        resume = Resume(
            user_id=current_user.id,
            raw_text=resume_text,
            original_text=resume_text,
            current_text=resume_text,
            parsed_resume=dumps_json(parsed),
            applied_fixes="[]",
            created_at=now,
            updated_at=now,
        )
        session.add(resume)

    session.commit()
    session.refresh(resume)
    return {"success": True, "message": "Resume uploaded.", "resume": _resume_payload(resume, parsed)}


@router.get("/me")
def get_my_resume(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("candidate")),
):
    resume = session.exec(select(Resume).where(Resume.user_id == current_user.id)).first()
    if not resume:
        return {"success": True, "has_resume": False}
    parsed = parse_resume(resume.current_text or resume.raw_text)
    return {"success": True, "has_resume": True, "resume": _resume_payload(resume, parsed)}


async def _extract_resume_text(file: UploadFile) -> str:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    os.makedirs("data", exist_ok=True)
    temp_path = f"data/resume_{uuid.uuid4().hex}.pdf"

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


def _resume_payload(resume: Resume, parsed: dict[str, Any]) -> dict[str, Any]:
    text = resume.current_text or resume.raw_text
    return {
        "id": resume.id,
        "word_count": len(text.split()),
        "parsed_resume": parsed,
        "updated_at": resume.updated_at.isoformat() if resume.updated_at else None,
    }
