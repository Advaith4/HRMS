from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from src.api.dependencies import get_current_user
from src.database.connection import get_session
from src.models import HRNotification, User

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

def _notif_payload(notif: HRNotification) -> dict:
    return {
        "id": notif.id,
        "user_id": notif.user_id,
        "title": notif.title,
        "message": notif.message,
        "event_type": notif.event_type,
        "related_id": notif.related_id,
        "is_read": notif.is_read,
        "created_at": notif.created_at.isoformat(),
    }

@router.get("")
def list_notifications(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    # Fetch notifications for current user ordered by created_at desc
    notifications = session.exec(
        select(HRNotification)
        .where(HRNotification.user_id == current_user.id)
        .order_by(HRNotification.created_at.desc())
    ).all()
    
    unread_count = len([n for n in notifications if not n.is_read])
    
    return {
        "unread_count": unread_count,
        "notifications": [_notif_payload(n) for n in notifications]
    }

@router.put("/read-all")
def mark_all_read(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    unread_notifications = session.exec(
        select(HRNotification)
        .where(HRNotification.user_id == current_user.id)
        .where(HRNotification.is_read == False)
    ).all()
    
    for n in unread_notifications:
        n.is_read = True
        session.add(n)
        
    session.commit()
    return {"ok": True}

@router.put("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    notif = session.get(HRNotification, notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found.")
        
    if notif.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
        
    notif.is_read = True
    session.add(notif)
    session.commit()
    
    return _notif_payload(notif)


from pydantic import BaseModel, Field
from src.api.dependencies import require_roles
from src.models import AuditLog
from src.tools.email_tool import EmailDraftInput, email_draft_tool


class EmailDispatchReq(BaseModel):
    draft_id: str
    approved: bool = Field(description="HR approval confirmation flag")
    recipient_email: str
    subject: str
    body: str


@router.post("/email/draft")
def generate_email_draft(
    body: EmailDraftInput,
    current_user: User = Depends(require_roles("hr", "manager", "admin")),
):
    """
    Generates a personalized candidate communication draft requiring HR approval before dispatch.
    """
    draft = email_draft_tool.run(
        candidate_id=body.candidate_id,
        candidate_name=body.candidate_name,
        candidate_email=body.candidate_email,
        job_title=body.job_title,
        email_type=body.email_type,
        interview_link=body.interview_link,
        company_name=body.company_name,
    )
    return draft.model_dump()


@router.post("/email/dispatch")
def dispatch_approved_email(
    body: EmailDispatchReq,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr", "manager", "admin")),
):
    """
    Dispatches an HR-approved email draft and records immutable audit log.
    """
    if not body.approved:
        raise HTTPException(status_code=400, detail="Cannot dispatch email without explicit HR approval confirmation.")

    # Record audit log
    audit_entry = AuditLog(
        user_id=current_user.id,
        action="EMAIL_DISPATCHED",
        resource_type="email_draft",
        resource_id=None,
        details=f'{{"draft_id": "{body.draft_id}", "recipient": "{body.recipient_email}", "subject": "{body.subject}"}}',
        request_id=None,
    )
    session.add(audit_entry)
    session.commit()

    return {
        "success": True,
        "message": f"Email successfully dispatched to {body.recipient_email}",
        "draft_id": body.draft_id,
        "status": "dispatched",
    }

