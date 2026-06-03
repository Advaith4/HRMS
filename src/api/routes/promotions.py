from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from src.api.dependencies import require_roles
from src.database.connection import get_session
from src.models import PromotionHistory, Employee, User, HRNotification, EmployeeLifecycleEvent

router = APIRouter(prefix="/api/promotions", tags=["promotions"])

class PromotionCreate(BaseModel):
    new_designation: str = Field(max_length=120)
    promotion_date: date = Field(default_factory=date.today)
    reason: str = Field(default="", max_length=500)

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

def _promo_payload(promo: PromotionHistory, session: Session) -> dict:
    approved_user = session.get(User, promo.approved_by)
    approved_by_username = approved_user.username if approved_user else ""
    
    emp = session.get(Employee, promo.employee_id)
    employee_username = ""
    if emp:
        emp_user = session.get(User, emp.user_id)
        employee_username = emp_user.username if emp_user else ""
        
    return {
        "id": promo.id,
        "employee_id": promo.employee_id,
        "old_designation": promo.old_designation,
        "new_designation": promo.new_designation,
        "promotion_date": promo.promotion_date.isoformat(),
        "reason": promo.reason,
        "approved_by": promo.approved_by,
        "approved_by_username": approved_by_username,
        "employee_username": employee_username,
        "created_at": promo.created_at.isoformat(),
    }

@router.get("/recent")
def list_recent_promotions(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr"))
):
    promos = session.exec(
        select(PromotionHistory)
        .order_by(PromotionHistory.promotion_date.desc(), PromotionHistory.created_at.desc())
        .limit(10)
    ).all()
    return [_promo_payload(p, session) for p in promos]

@router.get("/employee/{employee_id}")
def get_promotion_history(
    employee_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr", "manager"))
):
    emp = session.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")
        
    promos = session.exec(
        select(PromotionHistory)
        .where(PromotionHistory.employee_id == employee_id)
        .order_by(PromotionHistory.promotion_date.desc(), PromotionHistory.created_at.desc())
    ).all()
    
    return {
        "current_designation": emp.designation,
        "history": [_promo_payload(p, session) for p in promos]
    }

@router.post("/employee/{employee_id}", status_code=201)
def add_promotion(
    employee_id: int,
    body: PromotionCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr"))
):
    emp = session.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")
        
    old_designation = emp.designation or "None"
    
    promo = PromotionHistory(
        employee_id=employee_id,
        old_designation=old_designation,
        new_designation=body.new_designation,
        promotion_date=body.promotion_date,
        reason=body.reason,
        approved_by=current_user.id
    )
    session.add(promo)
    
    # Update designation on Employee record
    emp.designation = body.new_designation
    session.add(emp)
    
    # Record lifecycle event
    lifecycle = EmployeeLifecycleEvent(
        employee_id=employee_id,
        event_type="Promoted",
        event_date=body.promotion_date,
        description=f"Promoted from {old_designation} to {body.new_designation}. Reason: {body.reason}",
        created_by=current_user.id
    )
    session.add(lifecycle)
    
    session.commit()
    session.refresh(promo)
    
    # Notify HR
    emp_user = session.get(User, emp.user_id)
    emp_name = emp_user.username if emp_user else f"Code {emp.employee_code}"
    _notify_hr(
        session,
        title="Employee Promotion",
        message=f"{emp_name} promoted from '{old_designation}' to '{body.new_designation}'",
        event_type="promotion",
        related_id=employee_id
    )
    session.commit()
    
    return _promo_payload(promo, session)
