from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from src.api.dependencies import require_roles
from src.database.connection import get_session
from src.models import SalaryHistory, Employee, User, HRNotification, EmployeeLifecycleEvent

router = APIRouter(prefix="/api/salary", tags=["salary"])

class SalaryRevisionCreate(BaseModel):
    new_salary: float = Field(gt=0)
    reason: str = Field(default="", max_length=500)
    effective_date: date = Field(default_factory=date.today)

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

def _salary_payload(history: SalaryHistory, session: Session) -> dict:
    approved_user = session.get(User, history.approved_by)
    approved_by_username = approved_user.username if approved_user else ""
    return {
        "id": history.id,
        "employee_id": history.employee_id,
        "previous_salary": history.previous_salary,
        "new_salary": history.new_salary,
        "increment_percent": history.increment_percent,
        "reason": history.reason,
        "approved_by": history.approved_by,
        "approved_by_username": approved_by_username,
        "effective_date": history.effective_date.isoformat(),
        "created_at": history.created_at.isoformat(),
    }

@router.get("/employee/{employee_id}")
def get_salary_history(
    employee_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr"))
):
    emp = session.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")
        
    history = session.exec(
        select(SalaryHistory)
        .where(SalaryHistory.employee_id == employee_id)
        .order_by(SalaryHistory.effective_date.desc(), SalaryHistory.created_at.desc())
    ).all()
    
    return {
        "current_salary": emp.salary,
        "history": [_salary_payload(h, session) for h in history]
    }

@router.post("/employee/{employee_id}", status_code=201)
def add_salary_revision(
    employee_id: int,
    body: SalaryRevisionCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr"))
):
    emp = session.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")
        
    prev_salary = emp.salary
    increment_percent = None
    if prev_salary and prev_salary > 0:
        increment_percent = round(((body.new_salary - prev_salary) / prev_salary) * 100, 2)
        
    history = SalaryHistory(
        employee_id=employee_id,
        previous_salary=prev_salary,
        new_salary=body.new_salary,
        increment_percent=increment_percent,
        reason=body.reason,
        effective_date=body.effective_date,
        approved_by=current_user.id
    )
    session.add(history)
    
    # Update employee's current salary
    emp.salary = body.new_salary
    session.add(emp)

    # Record lifecycle event
    session.add(
        EmployeeLifecycleEvent(
            employee_id=employee_id,
            event_type="Salary Revision",
            event_date=body.effective_date,
            description=f"Salary revised from {prev_salary or 0} to {body.new_salary} (+{increment_percent or 0}%). Reason: {body.reason}",
            created_by=current_user.id
        )
    )
    
    session.commit()
    session.refresh(history)
    
    # Notify HR
    emp_user = session.get(User, emp.user_id)
    emp_name = emp_user.username if emp_user else f"Code {emp.employee_code}"
    _notify_hr(
        session,
        title="Salary Revision",
        message=f"Salary revised for {emp_name} from {prev_salary or 0} to {body.new_salary} (+{increment_percent or 0}%)",
        event_type="salary_revision",
        related_id=employee_id
    )
    session.commit()
    
    return _salary_payload(history, session)
