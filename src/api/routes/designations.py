from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from src.api.dependencies import get_current_user, require_roles
from src.database.connection import get_session
from src.models import Designation, Department, User

router = APIRouter(prefix="/api/designations", tags=["designations"])

class DesignationCreate(BaseModel):
    name: str = Field(max_length=120)
    department_id: Optional[int] = None
    level: int = Field(default=1)
    description: str = Field(default="", max_length=500)

class DesignationUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    department_id: Optional[int] = None
    level: Optional[int] = None
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None

def _desig_payload(desig: Designation, session: Session) -> dict:
    dept_name = ""
    if desig.department_id:
        dept = session.get(Department, desig.department_id)
        dept_name = dept.name if dept else ""
    return {
        "id": desig.id,
        "name": desig.name,
        "department_id": desig.department_id,
        "department_name": dept_name,
        "level": desig.level,
        "description": desig.description,
        "is_active": desig.is_active,
        "created_at": desig.created_at.isoformat(),
    }

@router.get("")
def list_designations(
    department_id: Optional[int] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    query = select(Designation)
    if department_id is not None:
        query = query.where(Designation.department_id == department_id)
    desigs = session.exec(query.order_by(Designation.name)).all()
    return [_desig_payload(d, session) for d in desigs]

@router.post("", status_code=201)
def create_designation(
    body: DesignationCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr"))
):
    desig = Designation(**body.model_dump())
    session.add(desig)
    session.commit()
    session.refresh(desig)
    return _desig_payload(desig, session)

@router.put("/{desig_id}")
def update_designation(
    desig_id: int,
    body: DesignationUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr"))
):
    desig = session.get(Designation, desig_id)
    if not desig:
        raise HTTPException(status_code=404, detail="Designation not found.")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(desig, k, v)
    desig.updated_at = datetime.utcnow()
    session.add(desig)
    session.commit()
    session.refresh(desig)
    return _desig_payload(desig, session)

@router.delete("/{desig_id}")
def archive_designation(
    desig_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr"))
):
    desig = session.get(Designation, desig_id)
    if not desig:
        raise HTTPException(status_code=404, detail="Designation not found.")
    desig.is_active = False
    desig.updated_at = datetime.utcnow()
    session.add(desig)
    session.commit()
    return {"ok": True}
