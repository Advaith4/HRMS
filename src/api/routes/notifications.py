from datetime import datetime
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
