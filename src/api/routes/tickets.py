from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from src.api.dependencies import get_current_user, require_roles
from src.database.connection import get_session
from src.models import EmployeeTicket, Employee, User, HRNotification

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

class TicketCreate(BaseModel):
    title: str = Field(max_length=200)
    description: str = Field(max_length=3000)
    category: str = Field(max_length=60)
    priority: str = Field(default="Medium", max_length=20)

class TicketAssign(BaseModel):
    assigned_to: int

class TicketStatusUpdate(BaseModel):
    status: str = Field(max_length=30)
    resolution_note: Optional[str] = Field(default=None, max_length=2000)

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

def _ticket_payload(ticket: EmployeeTicket, session: Session) -> dict:
    assigned_to_username = ""
    if ticket.assigned_to:
        user_assigned = session.get(User, ticket.assigned_to)
        assigned_to_username = user_assigned.username if user_assigned else ""
        
    emp = session.get(Employee, ticket.employee_id)
    employee_username = ""
    if emp:
        emp_user = session.get(User, emp.user_id)
        employee_username = emp_user.username if emp_user else ""
        
    return {
        "id": ticket.id,
        "employee_id": ticket.employee_id,
        "user_id": ticket.user_id,
        "title": ticket.title,
        "description": ticket.description,
        "category": ticket.category,
        "priority": ticket.priority,
        "status": ticket.status,
        "assigned_to": ticket.assigned_to,
        "assigned_to_username": assigned_to_username,
        "employee_username": employee_username,
        "resolution_note": ticket.resolution_note,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat(),
    }

@router.post("", status_code=201)
def create_ticket(
    body: TicketCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    emp = session.exec(select(Employee).where(Employee.user_id == current_user.id)).first()
    if not emp:
        raise HTTPException(status_code=400, detail="Current user is not registered as an employee.")
        
    valid_categories = {"HR Issue", "Leave Issue", "Salary Issue", "Workplace Concern", "Manager Concern", "Other"}
    if body.category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(valid_categories)}")
        
    valid_priorities = {"Low", "Medium", "High", "Critical"}
    if body.priority not in valid_priorities:
        raise HTTPException(status_code=400, detail=f"Invalid priority. Must be one of: {', '.join(valid_priorities)}")
        
    ticket = EmployeeTicket(
        employee_id=emp.id,
        user_id=current_user.id,
        title=body.title,
        description=body.description,
        category=body.category,
        priority=body.priority,
        status="Open"
    )
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    
    # Notify HR
    _notify_hr(
        session,
        title="New Ticket Raised",
        message=f"New ticket '{ticket.title}' raised by {current_user.username} (Priority: {ticket.priority})",
        event_type="ticket_raised",
        related_id=ticket.id
    )
    session.commit()
    
    return _ticket_payload(ticket, session)

@router.get("")
def list_tickets(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role in ["hr", "manager", "admin"]:
        tickets = session.exec(select(EmployeeTicket).order_by(EmployeeTicket.created_at.desc())).all()
    else:
        tickets = session.exec(
            select(EmployeeTicket)
            .where(EmployeeTicket.user_id == current_user.id)
            .order_by(EmployeeTicket.created_at.desc())
        ).all()
        
    return [_ticket_payload(t, session) for t in tickets]

@router.get("/{ticket_id}")
def get_ticket(
    ticket_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    ticket = session.get(EmployeeTicket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")
        
    is_creator = ticket.user_id == current_user.id
    is_management = current_user.role in ["hr", "manager", "admin"]
    if not (is_creator or is_management):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
        
    return _ticket_payload(ticket, session)

@router.put("/{ticket_id}/assign")
def assign_ticket(
    ticket_id: int,
    body: TicketAssign,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr"))
):
    ticket = session.get(EmployeeTicket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")
        
    user_assign = session.get(User, body.assigned_to)
    if not user_assign or user_assign.role not in ["hr", "manager", "admin"]:
        raise HTTPException(status_code=400, detail="Assigned user must be an HR, Manager, or Admin user.")
        
    ticket.assigned_to = body.assigned_to
    ticket.status = "Assigned"
    ticket.updated_at = datetime.utcnow()
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    
    # Notify creator
    creator_notif = HRNotification(
        user_id=ticket.user_id,
        title="Ticket Assigned",
        message=f"Your ticket '{ticket.title}' has been assigned to {user_assign.username}.",
        event_type="ticket_status_change",
        related_id=ticket.id,
        is_read=False
    )
    session.add(creator_notif)
    session.commit()
    
    return _ticket_payload(ticket, session)

@router.put("/{ticket_id}/status")
def update_ticket_status(
    ticket_id: int,
    body: TicketStatusUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr"))
):
    ticket = session.get(EmployeeTicket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found.")
        
    valid_statuses = {"Open", "Assigned", "In Review", "Resolved", "Closed"}
    if body.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        
    ticket.status = body.status
    if body.resolution_note is not None:
        ticket.resolution_note = body.resolution_note
    ticket.updated_at = datetime.utcnow()
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    
    # Notify creator
    creator_notif = HRNotification(
        user_id=ticket.user_id,
        title="Ticket Status Updated",
        message=f"Your ticket '{ticket.title}' has been set to '{ticket.status}'.",
        event_type="ticket_status_change",
        related_id=ticket.id,
        is_read=False
    )
    session.add(creator_notif)
    session.commit()
    
    return _ticket_payload(ticket, session)
