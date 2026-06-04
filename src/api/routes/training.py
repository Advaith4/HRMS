from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from src.api.dependencies import get_current_user, require_roles
from src.database.connection import get_session
from src.models import Employee, HRNotification, TrainingAssignment, TrainingProgram, User


router = APIRouter(prefix="/api/training", tags=["training"])


class TrainingProgramCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    category: str = Field(default="General", max_length=100)
    skills_covered: str = Field(default="", max_length=500)
    duration_hours: int = Field(default=1, ge=1)
    difficulty: str = Field(default="Beginner", pattern="^(Beginner|Intermediate|Advanced)$")
    status: str = Field(default="Draft", pattern="^(Draft|Active|Archived)$")


class TrainingProgramUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    category: Optional[str] = Field(default=None, max_length=100)
    skills_covered: Optional[str] = Field(default=None, max_length=500)
    duration_hours: Optional[int] = Field(default=None, ge=1)
    difficulty: Optional[str] = Field(default=None, pattern="^(Beginner|Intermediate|Advanced)$")
    status: Optional[str] = Field(default=None, pattern="^(Draft|Active|Archived)$")


class TrainingAssignReq(BaseModel):
    employee_id: int
    program_id: int
    due_date: Optional[date] = None


class TrainingProgressReq(BaseModel):
    progress_percent: int = Field(ge=0, le=100)
    status: Optional[str] = Field(default=None, pattern="^(Not Started|In Progress|Completed)$")


def _notify(session: Session, user_id: int, title: str, message: str, event_type: str, related_id: int | None = None) -> None:
    session.add(
        HRNotification(
            user_id=user_id,
            title=title,
            message=message,
            event_type=event_type,
            related_id=related_id,
            is_read=False,
        )
    )


def _employee_name(session: Session, employee: Employee | None) -> str:
    if not employee:
        return "Employee"
    user = session.get(User, employee.user_id)
    return employee.full_name or (user.username if user else employee.employee_code)


def _program_payload(program: TrainingProgram) -> dict:
    return {
        "id": program.id,
        "title": program.title,
        "description": program.description,
        "category": program.category,
        "skills_covered": program.skills_covered,
        "duration_hours": program.duration_hours,
        "difficulty": program.difficulty,
        "status": program.status,
        "created_by": program.created_by,
        "created_at": program.created_at.isoformat() + "Z" if program.created_at else None,
        "updated_at": program.updated_at.isoformat() + "Z" if program.updated_at else None,
    }


def _assignment_payload(session: Session, assignment: TrainingAssignment) -> dict:
    employee = session.get(Employee, assignment.employee_id)
    program = session.get(TrainingProgram, assignment.program_id)
    effective_status = assignment.status
    if assignment.status != "Completed" and assignment.due_date and assignment.due_date < date.today():
        effective_status = "Overdue"
    return {
        "id": assignment.id,
        "program_id": assignment.program_id,
        "program_title": program.title if program else "",
        "description": program.description if program else "",
        "category": program.category if program else "",
        "skills_covered": program.skills_covered if program else "",
        "duration_hours": program.duration_hours if program else 0,
        "difficulty": program.difficulty if program else "",
        "employee_id": assignment.employee_id,
        "employee_name": _employee_name(session, employee),
        "employee_code": employee.employee_code if employee else "",
        "department": employee.department if employee else "",
        "status": effective_status,
        "progress_percent": assignment.progress_percent,
        "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
        "created_at": assignment.created_at.isoformat() + "Z" if assignment.created_at else None,
        "completed_at": assignment.completed_at.isoformat() + "Z" if assignment.completed_at else None,
    }


def _get_employee_for_user(session: Session, user_id: int) -> Employee:
    employee = session.exec(select(Employee).where(Employee.user_id == user_id)).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found.")
    return employee


def _visible_assignments(session: Session, current_user: User) -> list[TrainingAssignment]:
    assignments = session.exec(select(TrainingAssignment).order_by(TrainingAssignment.created_at.desc())).all()
    if current_user.role in {"hr", "admin"}:
        return assignments
    if current_user.role == "manager":
        employees = session.exec(select(Employee).where(Employee.manager_id == current_user.id)).all()
        employee_ids = {employee.id for employee in employees}
        return [assignment for assignment in assignments if assignment.employee_id in employee_ids]
    employee = _get_employee_for_user(session, current_user.id)
    return [assignment for assignment in assignments if assignment.employee_id == employee.id]


@router.get("/programs")
def list_programs(
    include_archived: bool = False,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    programs = session.exec(select(TrainingProgram).order_by(TrainingProgram.created_at.desc())).all()
    if not include_archived:
        programs = [program for program in programs if program.status != "Archived"]
    return [_program_payload(program) for program in programs]


@router.post("/programs", status_code=201)
def create_program(
    body: TrainingProgramCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr")),
):
    now = datetime.utcnow()
    program = TrainingProgram(
        title=body.title.strip(),
        description=body.description.strip(),
        category=body.category.strip() or "General",
        skills_covered=body.skills_covered.strip(),
        duration_hours=body.duration_hours,
        difficulty=body.difficulty,
        status=body.status,
        created_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    session.add(program)
    session.commit()
    session.refresh(program)
    return _program_payload(program)


@router.put("/programs/{program_id}")
def update_program(
    program_id: int,
    body: TrainingProgramUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr")),
):
    program = session.get(TrainingProgram, program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Training program not found.")
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(program, key, value.strip() if isinstance(value, str) else value)
    program.updated_at = datetime.utcnow()
    session.add(program)
    session.commit()
    session.refresh(program)
    return _program_payload(program)


@router.delete("/programs/{program_id}")
def archive_program(
    program_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr")),
):
    program = session.get(TrainingProgram, program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Training program not found.")
    program.status = "Archived"
    program.updated_at = datetime.utcnow()
    session.add(program)
    session.commit()
    return {"ok": True}


@router.post("/assign", status_code=201)
def assign_training(
    body: TrainingAssignReq,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr")),
):
    employee = session.get(Employee, body.employee_id)
    program = session.get(TrainingProgram, body.program_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found.")
    if not program or program.status == "Archived":
        raise HTTPException(status_code=404, detail="Active training program not found.")
    duplicate = session.exec(
        select(TrainingAssignment)
        .where(TrainingAssignment.employee_id == employee.id)
        .where(TrainingAssignment.program_id == program.id)
        .where(TrainingAssignment.status != "Completed")
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="This training is already assigned to the employee.")

    now = datetime.utcnow()
    assignment = TrainingAssignment(
        program_id=program.id,
        employee_id=employee.id,
        assigned_by=current_user.id,
        due_date=body.due_date,
        created_at=now,
        updated_at=now,
    )
    session.add(assignment)
    session.commit()
    session.refresh(assignment)
    _notify(
        session,
        employee.user_id,
        "Training Assigned",
        f"You have been assigned {program.title}.",
        "training_assigned",
        assignment.id,
    )
    session.commit()
    return _assignment_payload(session, assignment)


@router.get("/assignments/my")
def my_assignments(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("employee")),
):
    employee = _get_employee_for_user(session, current_user.id)
    assignments = session.exec(
        select(TrainingAssignment)
        .where(TrainingAssignment.employee_id == employee.id)
        .order_by(TrainingAssignment.created_at.desc())
    ).all()
    return [_assignment_payload(session, assignment) for assignment in assignments]


@router.get("/assignments")
def list_assignments(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr", "manager")),
):
    return [_assignment_payload(session, assignment) for assignment in _visible_assignments(session, current_user)]


@router.put("/assignments/{assignment_id}/progress")
def update_progress(
    assignment_id: int,
    body: TrainingProgressReq,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    assignment = session.get(TrainingAssignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Training assignment not found.")
    employee = session.get(Employee, assignment.employee_id)
    is_self = employee and employee.user_id == current_user.id
    if not (is_self or current_user.role in {"hr", "admin"}):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    now = datetime.utcnow()
    assignment.progress_percent = body.progress_percent
    if body.status:
        assignment.status = body.status
    elif body.progress_percent >= 100:
        assignment.status = "Completed"
    elif body.progress_percent > 0:
        assignment.status = "In Progress"
    else:
        assignment.status = "Not Started"
    assignment.started_at = assignment.started_at or (now if assignment.progress_percent > 0 else None)
    assignment.completed_at = now if assignment.status == "Completed" else None
    assignment.updated_at = now
    session.add(assignment)

    if assignment.status == "Completed" and employee:
        _notify(
            session,
            employee.user_id,
            "Training Completed",
            "Your training assignment has been marked complete.",
            "training_completed",
            assignment.id,
        )
        for hr_user in session.exec(select(User).where(User.role.in_(["hr", "admin"]))).all():
            _notify(
                session,
                hr_user.id,
                "Training Completed",
                f"{_employee_name(session, employee)} completed a training assignment.",
                "training_completed",
                assignment.id,
            )

    session.commit()
    session.refresh(assignment)
    return _assignment_payload(session, assignment)


@router.get("/summary")
def training_summary(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr", "manager")),
):
    assignments = _visible_assignments(session, current_user)
    total = len(assignments)
    completed = len([assignment for assignment in assignments if assignment.status == "Completed"])
    overdue = len([
        assignment for assignment in assignments
        if assignment.status != "Completed" and assignment.due_date and assignment.due_date < date.today()
    ])
    return {
        "active_programs": len(session.exec(select(TrainingProgram).where(TrainingProgram.status == "Active")).all()),
        "assignments": total,
        "completed": completed,
        "completion_percent": round((completed / total) * 100) if total else 0,
        "overdue": overdue,
    }
