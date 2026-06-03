from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from src.api.dependencies import get_current_user, require_roles
from src.database.connection import get_session
from src.models import Department, User

router = APIRouter(prefix="/api/departments", tags=["departments"])

class DepartmentCreate(BaseModel):
    name: str = Field(max_length=120)
    description: str = Field(default="", max_length=500)
    head_user_id: Optional[int] = None

class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    description: Optional[str] = Field(default=None, max_length=500)
    head_user_id: Optional[int] = None
    is_active: Optional[bool] = None

def _dept_payload(dept: Department, session: Session) -> dict:
    head_name = ""
    if dept.head_user_id:
        user = session.get(User, dept.head_user_id)
        head_name = user.username if user else ""
    # count employees
    from src.models import Employee
    count = len(session.exec(select(Employee).where(Employee.department_id == dept.id)).all())
    return {
        "id": dept.id,
        "name": dept.name,
        "description": dept.description,
        "head_user_id": dept.head_user_id,
        "head_name": head_name,
        "is_active": dept.is_active,
        "employee_count": count,
        "created_at": dept.created_at.isoformat(),
    }

@router.get("")
def list_departments(session: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    depts = session.exec(select(Department).order_by(Department.name)).all()
    return [_dept_payload(d, session) for d in depts]

@router.post("", status_code=201)
def create_department(body: DepartmentCreate, session: Session = Depends(get_session), current_user: User = Depends(require_roles("hr"))):
    existing = session.exec(select(Department).where(Department.name == body.name)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Department already exists.")
    dept = Department(**body.model_dump())
    session.add(dept)
    session.commit()
    session.refresh(dept)
    return _dept_payload(dept, session)

@router.put("/{dept_id}")
def update_department(dept_id: int, body: DepartmentUpdate, session: Session = Depends(get_session), current_user: User = Depends(require_roles("hr"))):
    dept = session.get(Department, dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found.")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(dept, k, v)
    dept.updated_at = datetime.utcnow()
    session.add(dept)
    session.commit()
    session.refresh(dept)
    return _dept_payload(dept, session)

@router.delete("/{dept_id}")
def deactivate_department(dept_id: int, session: Session = Depends(get_session), current_user: User = Depends(require_roles("hr"))):
    dept = session.get(Department, dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found.")
    dept.is_active = False
    dept.updated_at = datetime.utcnow()
    session.add(dept)
    session.commit()
    return {"ok": True}
