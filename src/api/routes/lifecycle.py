from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from src.api.dependencies import get_current_user, require_roles
from src.database.connection import get_session
from src.models import EmployeeLifecycleEvent, Employee, User, HRNotification

router = APIRouter(prefix="/api/lifecycle", tags=["lifecycle"])

class LifecycleEventCreate(BaseModel):
    event_type: str = Field(max_length=60)
    event_date: date = Field(default_factory=date.today)
    description: str = Field(default="", max_length=1000)

def _notify_hr(session: Session, title: str, message: str, event_type: str, related_id: Optional[int] = None):
    hr_users = session.exec(select(User).where(User.role.in_(["hr", "admin"]))).all()
    for u in hr_users:
        notif = HRNotification(
            user_id=u.id,
            title=title,
            message=message,
            event_type=event_type,
            related_id=related_id,
            is_read=False
        )
        session.add(notif)

@router.get("/employee/{employee_id}")
def get_lifecycle_events(
    employee_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    emp = session.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")
    
    # Check permissions: HR/Admin/Manager, or the employee themselves
    is_self = current_user.id == emp.user_id
    is_management = current_user.role in ["hr", "manager", "admin"]
    if not (is_self or is_management):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
        
    events = session.exec(
        select(EmployeeLifecycleEvent)
        .where(EmployeeLifecycleEvent.employee_id == employee_id)
        .order_by(EmployeeLifecycleEvent.event_date.desc(), EmployeeLifecycleEvent.created_at.desc())
    ).all()
    
    # Batch-fetch creator usernames to avoid N+1
    creator_ids = list({evt.created_by for evt in events})
    creators_by_id = {}
    if creator_ids:
        for u in session.exec(select(User).where(User.id.in_(creator_ids))).all():
            creators_by_id[u.id] = u.username

    return [
        {
            "id": e.id,
            "employee_id": e.employee_id,
            "event_type": e.event_type,
            "event_date": e.event_date.isoformat(),
            "description": e.description,
            "created_by_username": creators_by_id.get(e.created_by, "Unknown"),
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]

@router.post("/employee/{employee_id}", status_code=201)
def add_lifecycle_event(
    employee_id: int,
    body: LifecycleEventCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr"))
):
    emp = session.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")
    
    valid_types = {"Joined", "Probation", "Confirmed", "Promoted", "Transferred", "Exited"}
    if body.event_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event_type. Must be one of: {', '.join(valid_types)}"
        )
        
    event = EmployeeLifecycleEvent(
        employee_id=employee_id,
        event_type=body.event_type,
        event_date=body.event_date,
        description=body.description,
        created_by=current_user.id
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    
    # Send notification
    emp_user = session.get(User, emp.user_id)
    emp_name = emp_user.username if emp_user else f"Code {emp.employee_code}"
    _notify_hr(
        session,
        title="Employee Lifecycle Updated",
        message=f"{emp_name} lifecycle updated to '{body.event_type}' on {body.event_date}",
        event_type="lifecycle_event",
        related_id=employee_id
    )
    session.commit()
    
    # Return payload
    return {
        "id": event.id,
        "employee_id": event.employee_id,
        "event_type": event.event_type,
        "event_date": event.event_date.isoformat(),
        "description": event.description,
        "created_by_username": current_user.username,
        "created_at": event.created_at.isoformat(),
    }
