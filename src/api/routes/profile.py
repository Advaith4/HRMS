import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from src.api.dependencies import get_current_user, require_roles
from src.database.connection import get_session
from src.models import (
    CandidateDocument,
    CandidateProfile,
    Employee,
    EmployeeDocument,
    EmployeeProfile,
    HRNotification,
    User,
    EmployeeLifecycleEvent,
)


router = APIRouter(prefix="/api/profile", tags=["profile"])
UPLOAD_ROOT = Path("data") / "profile_documents"
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


class CandidateProfileReq(BaseModel):
    full_name: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=30)
    date_of_birth: Optional[str] = None
    gender: str = Field(default="", max_length=40)
    location: str = Field(default="", max_length=100)
    address: str = Field(default="", max_length=500)
    linkedin_url: str = Field(default="", max_length=500)
    portfolio_url: str = Field(default="", max_length=500)
    current_status: str = Field(default="", max_length=60)
    current_company: str = Field(default="", max_length=200)
    current_role: str = Field(default="", max_length=200)
    years_of_experience: Optional[float] = None
    expected_salary: str = Field(default="", max_length=100)
    notice_period: str = Field(default="", max_length=100)
    degree: str = Field(default="", max_length=200)
    institution: str = Field(default="", max_length=200)
    graduation_year: str = Field(default="", max_length=20)
    cgpa_percentage: str = Field(default="", max_length=40)
    technical_skills: str = Field(default="", max_length=1000)
    soft_skills: str = Field(default="", max_length=1000)
    certifications: str = Field(default="", max_length=1000)


class EmployeeProfileReq(BaseModel):
    phone: str = Field(default="", max_length=30)
    address: str = Field(default="", max_length=500)
    emergency_contact: str = Field(default="", max_length=200)
    blood_group: str = Field(default="", max_length=20)
    marital_status: str = Field(default="", max_length=40)
    previous_experience: str = Field(default="", max_length=1000)
    skills: str = Field(default="", max_length=1000)
    certifications: str = Field(default="", max_length=1000)
    career_interests: str = Field(default="", max_length=1000)
    career_goals: str = Field(default="", max_length=1000)


class DocumentDecisionReq(BaseModel):
    status: str = Field(pattern="^(Approved|Rejected)$")
    rejection_comment: str = Field(default="", max_length=1000)


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        from datetime import date
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")


def _notify(session: Session, user_id: int, title: str, message: str, event_type: str, related_id: int | None = None) -> None:
    session.add(HRNotification(user_id=user_id, title=title, message=message, event_type=event_type, related_id=related_id))


def _required_missing(record, fields: list[str]) -> list[str]:
    missing = []
    for field in fields:
        value = getattr(record, field, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)
    return missing


def _completion(record, required_fields: list[str], required_doc_types: list[str], documents: list) -> tuple[int, list[str]]:
    missing = _required_missing(record, required_fields)
    uploaded_types = {doc.document_type for doc in documents}
    for doc_type in required_doc_types:
        if doc_type not in uploaded_types:
            missing.append(f"document:{doc_type}")
    total = len(required_fields) + len(required_doc_types)
    complete = max(total - len(missing), 0)
    return (round((complete / total) * 100) if total else 100), missing


def _candidate_profile(session: Session, user_id: int) -> CandidateProfile:
    profile = session.exec(select(CandidateProfile).where(CandidateProfile.user_id == user_id)).first()
    if profile:
        return profile
    profile = CandidateProfile(user_id=user_id)
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


def _employee_for_user(session: Session, user_id: int) -> Employee | None:
    return session.exec(select(Employee).where(Employee.user_id == user_id)).first()


def _employee_profile(session: Session, user_id: int) -> EmployeeProfile:
    employee = _employee_for_user(session, user_id)
    profile = session.exec(select(EmployeeProfile).where(EmployeeProfile.user_id == user_id)).first()
    if profile:
        if employee and profile.employee_id != employee.id:
            profile.employee_id = employee.id
            session.add(profile)
            session.commit()
        return profile
    profile = EmployeeProfile(user_id=user_id, employee_id=employee.id if employee else None)
    if employee:
        profile.phone = employee.phone or ""
        profile.address = employee.address or ""
        profile.emergency_contact = employee.emergency_contact or ""
        profile.skills = employee.skills or ""
        profile.certifications = employee.certifications or ""
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


def _doc_payload(doc) -> dict:
    return {
        "id": doc.id,
        "user_id": doc.user_id,
        "employee_id": getattr(doc, "employee_id", None),
        "document_type": doc.document_type,
        "original_filename": doc.original_filename,
        "verification_status": doc.verification_status,
        "rejection_comment": doc.rejection_comment,
        "uploaded_at": doc.uploaded_at.isoformat() + "Z" if doc.uploaded_at else None,
        "reviewed_at": doc.reviewed_at.isoformat() + "Z" if doc.reviewed_at else None,
    }


def _candidate_payload(session: Session, profile: CandidateProfile) -> dict:
    docs = session.exec(select(CandidateDocument).where(CandidateDocument.user_id == profile.user_id)).all()
    required = [
        "full_name", "phone", "date_of_birth", "gender", "location", "address",
        "current_status", "degree", "institution", "graduation_year", "technical_skills",
    ]
    percent, missing = _completion(profile, required, ["Resume"], docs)
    if profile.completion_percent != percent or profile.is_complete != (percent == 100):
        profile.completion_percent = percent
        profile.is_complete = percent == 100
        session.add(profile)
        session.commit()
    data = profile.model_dump()
    if profile.date_of_birth:
        data["date_of_birth"] = profile.date_of_birth.isoformat()
    data.update({
        "completion_percent": percent,
        "is_complete": percent == 100,
        "missing_information": missing,
        "documents": [_doc_payload(doc) for doc in docs],
    })
    return data


def _employee_payload(session: Session, profile: EmployeeProfile) -> dict:
    docs = session.exec(select(EmployeeDocument).where(EmployeeDocument.user_id == profile.user_id)).all()
    required = ["phone", "address", "emergency_contact", "blood_group", "marital_status", "skills", "career_goals"]
    percent, missing = _completion(profile, required, ["Government ID", "Resume"], docs)
    if profile.completion_percent != percent or profile.is_complete != (percent == 100):
        profile.completion_percent = percent
        profile.is_complete = percent == 100
        session.add(profile)
        session.commit()
    data = profile.model_dump()
    data.update({
        "completion_percent": percent,
        "is_complete": percent == 100,
        "missing_information": missing,
        "documents": [_doc_payload(doc) for doc in docs],
    })
    return data


@router.get("/me")
def get_my_profile(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    if current_user.role == "candidate":
        return {"role": "candidate", "profile": _candidate_payload(session, _candidate_profile(session, current_user.id))}
    if current_user.role == "employee":
        return {"role": "employee", "profile": _employee_payload(session, _employee_profile(session, current_user.id))}
    return {"role": current_user.role, "profile": {"is_complete": True, "completion_percent": 100, "missing_information": [], "documents": []}}


@router.put("/candidate")
def update_candidate_profile(body: CandidateProfileReq, session: Session = Depends(get_session), current_user: User = Depends(require_roles("candidate"))):
    profile = _candidate_profile(session, current_user.id)
    was_complete = profile.is_complete
    data = body.model_dump(exclude_unset=True)
    if "date_of_birth" in data:
        data["date_of_birth"] = _parse_date(data.pop("date_of_birth", None))
    for key, value in data.items():
        setattr(profile, key, value.strip() if isinstance(value, str) else value)
    profile.updated_at = datetime.utcnow()
    session.add(profile)
    session.commit()
    payload = _candidate_payload(session, profile)
    if payload["is_complete"] and not was_complete:
        _notify(session, current_user.id, "Profile Completed", "Your candidate career profile is complete.", "profile_completed", profile.id)
        session.commit()
    return payload


@router.put("/employee")
def update_employee_profile_completion(body: EmployeeProfileReq, session: Session = Depends(get_session), current_user: User = Depends(require_roles("employee"))):
    profile = _employee_profile(session, current_user.id)
    employee = _employee_for_user(session, current_user.id)
    was_complete = profile.is_complete
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, key, value.strip() if isinstance(value, str) else value)
        if employee and key in {"phone", "address", "emergency_contact", "skills", "certifications"}:
            setattr(employee, key, value.strip() if isinstance(value, str) else value)
    profile.updated_at = datetime.utcnow()
    session.add(profile)
    if employee:
        session.add(employee)
    session.commit()
    payload = _employee_payload(session, profile)
    if payload["is_complete"]:
        profile.pre_populated = False
        session.add(profile)
        session.commit()
        payload = _employee_payload(session, profile)
        if not was_complete:
            _notify(session, current_user.id, "Profile Completed", "Your employee profile is complete.", "profile_completed", profile.id)
            if employee:
                session.add(EmployeeLifecycleEvent(
                    employee_id=employee.id,
                    event_type="Profile Completed",
                    event_date=date.today(),
                    description="Completed personal and professional employee profile.",
                    created_by=current_user.id
                ))
            session.commit()
    return payload


@router.post("/documents", status_code=201)
def upload_document(
    document_type: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("candidate", "employee")),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported document type.")
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Document exceeds 8 MB upload limit.")
    folder = UPLOAD_ROOT / current_user.role / str(current_user.id)
    folder.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    stored_path = folder / stored_name
    with stored_path.open("wb") as dest:
        dest.write(content)

    from datetime import date
    if current_user.role == "candidate":
        doc = CandidateDocument(user_id=current_user.id, document_type=document_type, original_filename=file.filename or stored_name, stored_path=str(stored_path))
    else:
        employee = _employee_for_user(session, current_user.id)
        doc = EmployeeDocument(user_id=current_user.id, employee_id=employee.id if employee else None, document_type=document_type, original_filename=file.filename or stored_name, stored_path=str(stored_path))
        if employee:
            session.add(EmployeeLifecycleEvent(
                employee_id=employee.id,
                event_type="Documents Submitted",
                event_date=date.today(),
                description=f"Submitted compliance document: {document_type}.",
                created_by=current_user.id
            ))
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return _doc_payload(doc)


@router.get("/documents")
def list_documents(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    if current_user.role == "candidate":
        docs = session.exec(select(CandidateDocument).where(CandidateDocument.user_id == current_user.id)).all()
    elif current_user.role == "employee":
        docs = session.exec(select(EmployeeDocument).where(EmployeeDocument.user_id == current_user.id)).all()
    else:
        docs = session.exec(select(EmployeeDocument).order_by(EmployeeDocument.uploaded_at.desc())).all()
    
    users = {user.id: user for user in session.exec(select(User)).all()}
    payload = []
    for doc in docs:
        item = _doc_payload(doc)
        item["reviewer_username"] = users.get(doc.reviewed_by).username if doc.reviewed_by in users else ""
        payload.append(item)
    return payload


@router.get("/documents/{kind}/{document_id}/download")
def download_document(kind: str, document_id: int, session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    model = CandidateDocument if kind == "candidate" else EmployeeDocument
    doc = session.get(model, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    can_access = current_user.role in {"hr", "admin"} or doc.user_id == current_user.id
    if not can_access:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if not os.path.exists(doc.stored_path):
        raise HTTPException(status_code=404, detail="Stored file is missing.")
    return FileResponse(doc.stored_path, filename=doc.original_filename)


@router.get("/documents/review")
def list_review_documents(session: Session = Depends(get_session), current_user: User = Depends(require_roles("hr"))):
    employee_docs = session.exec(select(EmployeeDocument).order_by(EmployeeDocument.uploaded_at.desc())).all()
    candidate_docs = session.exec(select(CandidateDocument).order_by(CandidateDocument.uploaded_at.desc())).all()
    users = {user.id: user for user in session.exec(select(User)).all()}
    payload = []
    for kind, docs in (("employee", employee_docs), ("candidate", candidate_docs)):
        for doc in docs:
            item = _doc_payload(doc)
            item["kind"] = kind
            item["username"] = users.get(doc.user_id).username if doc.user_id in users else ""
            item["reviewer_username"] = users.get(doc.reviewed_by).username if doc.reviewed_by in users else ""
            payload.append(item)
    return sorted(payload, key=lambda item: item["uploaded_at"] or "", reverse=True)


@router.put("/documents/{kind}/{document_id}/decision")
def decide_document(kind: str, document_id: int, body: DocumentDecisionReq, session: Session = Depends(get_session), current_user: User = Depends(require_roles("hr"))):
    model = CandidateDocument if kind == "candidate" else EmployeeDocument
    doc = session.get(model, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    doc.verification_status = body.status
    doc.rejection_comment = body.rejection_comment.strip() if body.status == "Rejected" else ""
    doc.reviewed_at = datetime.utcnow()
    doc.reviewed_by = current_user.id
    session.add(doc)

    # Generate document verification lifecycle events for employee
    from datetime import date
    if kind == "employee" and doc.employee_id:
        if body.status == "Approved":
            evt_type = "Documents Verified"
            evt_desc = f"Verified compliance document: {doc.document_type}."
        else:
            evt_type = "Document Rejected"
            evt_desc = f"Rejected compliance document: {doc.document_type}. Reason: {doc.rejection_comment}"
        
        session.add(EmployeeLifecycleEvent(
            employee_id=doc.employee_id,
            event_type=evt_type,
            event_date=date.today(),
            description=evt_desc,
            created_by=current_user.id
        ))

    # Send Notification
    title = "Document Approved" if body.status == "Approved" else "Document Rejected"
    msg = f"{doc.document_type} was {body.status.lower()}."
    if doc.rejection_comment:
        msg += f" Reason: {doc.rejection_comment}"
    _notify(session, doc.user_id, title, msg, f"document_{body.status.lower()}", doc.id)
    session.commit()
    session.refresh(doc)
    
    payload = _doc_payload(doc)
    payload["reviewer_username"] = current_user.username
    return payload
