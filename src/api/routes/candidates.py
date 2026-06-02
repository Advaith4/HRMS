from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from src.api.dependencies import require_roles
from src.database.connection import get_session
from src.models import CandidateApplication, User

router = APIRouter(prefix="/api/candidates", tags=["candidates"])


@router.get("")
def list_candidates(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr", "manager")),
):
    candidates = session.exec(
        select(User).where(User.role == "candidate").order_by(User.created_at.desc())
    ).all()
    return [_candidate_payload(session, candidate) for candidate in candidates]


@router.get("/{candidate_id}")
def get_candidate(
    candidate_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr", "manager")),
):
    candidate = session.get(User, candidate_id)
    if not candidate or candidate.role != "candidate":
        raise HTTPException(status_code=404, detail="Candidate not found")
    return _candidate_payload(session, candidate, include_applications=True)


def _candidate_payload(session: Session, candidate: User, include_applications: bool = False) -> dict[str, Any]:
    applications = session.exec(
        select(CandidateApplication)
        .where(CandidateApplication.candidate_user_id == candidate.id)
        .order_by(CandidateApplication.application_date.desc())
    ).all()
    payload = {
        "id": candidate.id,
        "username": candidate.username,
        "role": candidate.role,
        "target_role": candidate.target_role,
        "location": candidate.location,
        "experience": candidate.experience,
        "created_at": candidate.created_at.isoformat() if candidate.created_at else None,
        "application_count": len(applications),
    }
    if include_applications:
        payload["applications"] = [
            {
                "id": application.id,
                "job_id": application.job_id,
                "status": application.status,
                "application_date": application.application_date.isoformat()
                if application.application_date
                else None,
            }
            for application in applications
        ]
    return payload
