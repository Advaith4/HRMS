import json
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from src.api.dependencies import require_roles
from src.database.connection import get_session
from src.models import AttendanceRecord, Employee, LeaveRequest, SkillGapAnalysis, User
from src.services.employee_ai import analyze_skill_gap, answer_hr_question

router = APIRouter(prefix="/api/employees", tags=["employees"])


class LeaveCreateReq(BaseModel):
    leave_type: str = Field(default="General", max_length=60)
    start_date: date
    end_date: date
    reason: str = Field(default="", max_length=2000)


class LeaveDecisionReq(BaseModel):
    status: str = Field(pattern="^(Approved|Rejected)$")
    manager_note: str = Field(default="", max_length=2000)


class SkillGapReq(BaseModel):
    role_expectations: str = Field(default="", max_length=2000)


class HRAssistantReq(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


@router.get("")
def list_employees(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr")),
):
    employees = session.exec(select(Employee).order_by(Employee.id.desc())).all()
    # Batch-fetch all users in one query to avoid N+1
    user_ids = list({e.user_id for e in employees if e.user_id})
    users_by_id: dict[int, User] = {}
    if user_ids:
        for u in session.exec(select(User).where(User.id.in_(user_ids))).all():
            users_by_id[u.id] = u
    return [
        {
            "id": e.id,
            "user_id": e.user_id,
            "username": users_by_id[e.user_id].username if e.user_id in users_by_id else "",
            "employee_code": e.employee_code,
            "department": e.department,
            "designation": e.designation,
            "salary": e.salary,
            "joining_date": e.joining_date.isoformat() if e.joining_date else None,
            "skills": e.skills,
        }
        for e in employees
    ]


@router.get("/me")
def my_employee_profile(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("employee")),
):
    employee = _get_employee_for_user(session, current_user.id)
    return _employee_payload(session, employee)


@router.get("/dashboard")
def employee_dashboard(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("employee")),
):
    employee = _get_employee_for_user(session, current_user.id)
    today_record = _today_attendance(session, employee)
    leaves = session.exec(
        select(LeaveRequest)
        .where(LeaveRequest.employee_id == employee.id)
        .order_by(LeaveRequest.created_at.desc())
    ).all()
    latest_skill_gap = session.exec(
        select(SkillGapAnalysis)
        .where(SkillGapAnalysis.employee_id == employee.id)
        .order_by(SkillGapAnalysis.updated_at.desc())
    ).first()
    return {
        "employee": _employee_payload(session, employee),
        "attendance_status": _attendance_payload(today_record) if today_record else None,
        "leave_summary": {
            "pending": len([item for item in leaves if item.status == "Pending"]),
            "approved": len([item for item in leaves if item.status == "Approved"]),
            "rejected": len([item for item in leaves if item.status == "Rejected"]),
            "recent": [_leave_payload(session, item) for item in leaves[:5]],
        },
        "skill_gap": _skill_gap_payload(latest_skill_gap) if latest_skill_gap else None,
    }


@router.post("/attendance/check-in", status_code=201)
def check_in(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("employee")),
):
    employee = _get_employee_for_user(session, current_user.id)
    existing = _today_attendance(session, employee)
    if existing and existing.check_out is None:
        return {"success": True, "attendance": _attendance_payload(existing)}
    if existing and existing.check_out is not None:
        raise HTTPException(status_code=409, detail="Attendance is already completed for today.")

    now = datetime.utcnow()
    record = AttendanceRecord(
        employee_id=employee.id,
        user_id=current_user.id,
        work_date=date.today(),
        check_in=now,
        status="Checked In",
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return {"success": True, "attendance": _attendance_payload(record)}


@router.post("/attendance/check-out")
def check_out(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("employee")),
):
    employee = _get_employee_for_user(session, current_user.id)
    record = _today_attendance(session, employee)
    if not record:
        raise HTTPException(status_code=400, detail="Check in before checking out.")
    if record.check_out is not None:
        return {"success": True, "attendance": _attendance_payload(record)}

    record.check_out = datetime.utcnow()
    record.status = "Completed"
    record.updated_at = datetime.utcnow()
    session.add(record)
    session.commit()
    session.refresh(record)
    return {"success": True, "attendance": _attendance_payload(record)}


@router.get("/attendance")
def attendance_history(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("employee")),
):
    employee = _get_employee_for_user(session, current_user.id)
    records = session.exec(
        select(AttendanceRecord)
        .where(AttendanceRecord.employee_id == employee.id)
        .order_by(AttendanceRecord.work_date.desc(), AttendanceRecord.created_at.desc())
    ).all()
    return [_attendance_payload(record) for record in records]


@router.post("/leave", status_code=201)
def submit_leave(
    req: LeaveCreateReq,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("employee")),
):
    if req.end_date < req.start_date:
        raise HTTPException(status_code=400, detail="End date cannot be before start date.")

    employee = _get_employee_for_user(session, current_user.id)

    # Check for identical duplicate leave request (same start and end date)
    duplicate = session.exec(
        select(LeaveRequest)
        .where(LeaveRequest.employee_id == employee.id)
        .where(LeaveRequest.start_date == req.start_date)
        .where(LeaveRequest.end_date == req.end_date)
        .where(LeaveRequest.status != "Rejected")
    ).first()
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="A leave request for these dates is already pending or approved."
        )

    now = datetime.utcnow()
    leave = LeaveRequest(
        employee_id=employee.id,
        user_id=current_user.id,
        leave_type=req.leave_type.strip() or "General",
        start_date=req.start_date,
        end_date=req.end_date,
        reason=req.reason.strip(),
        status="Pending",
        created_at=now,
        updated_at=now,
    )
    session.add(leave)
    session.commit()
    session.refresh(leave)
    return {"success": True, "leave": _leave_payload(session, leave)}


@router.get("/leave/me")
def my_leave_requests(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("employee")),
):
    employee = _get_employee_for_user(session, current_user.id)
    requests = session.exec(
        select(LeaveRequest)
        .where(LeaveRequest.employee_id == employee.id)
        .order_by(LeaveRequest.created_at.desc())
    ).all()
    return [_leave_payload(session, item) for item in requests]


@router.get("/leave")
def list_leave_requests(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr", "manager")),
):
    requests = session.exec(select(LeaveRequest).order_by(LeaveRequest.created_at.desc())).all()
    # Batch-fetch related employees and users to avoid N+1 queries
    emp_ids = list({r.employee_id for r in requests if r.employee_id})
    user_ids = list({r.user_id for r in requests if r.user_id})
    emps_by_id: dict[int, Employee] = {}
    users_by_id: dict[int, User] = {}
    if emp_ids:
        for e in session.exec(select(Employee).where(Employee.id.in_(emp_ids))).all():
            emps_by_id[e.id] = e
    if user_ids:
        for u in session.exec(select(User).where(User.id.in_(user_ids))).all():
            users_by_id[u.id] = u
    return [
        {
            "id": r.id,
            "employee_id": r.employee_id,
            "employee_code": emps_by_id[r.employee_id].employee_code if r.employee_id in emps_by_id else "",
            "username": users_by_id[r.user_id].username if r.user_id in users_by_id else "",
            "leave_type": r.leave_type,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
            "reason": r.reason,
            "status": r.status,
            "manager_note": r.manager_note,
            "decided_by": r.decided_by,
            "created_at": r.created_at.isoformat() + "Z" if r.created_at else None,
            "updated_at": r.updated_at.isoformat() + "Z" if r.updated_at else None,
        }
        for r in requests
    ]


@router.post("/leave/{leave_id}/decision")
def decide_leave_request(
    leave_id: int,
    req: LeaveDecisionReq,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr", "manager")),
):
    leave = session.get(LeaveRequest, leave_id)
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    leave.status = req.status
    leave.manager_note = req.manager_note.strip() or None
    leave.decided_by = current_user.id
    leave.updated_at = datetime.utcnow()
    session.add(leave)
    session.commit()
    session.refresh(leave)
    return {"success": True, "leave": _leave_payload(session, leave)}


@router.get("/skill-gap/me")
def my_skill_gap(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("employee")),
):
    employee = _get_employee_for_user(session, current_user.id)
    analysis = session.exec(
        select(SkillGapAnalysis)
        .where(SkillGapAnalysis.employee_id == employee.id)
        .order_by(SkillGapAnalysis.updated_at.desc())
    ).first()
    if not analysis:
        return {"success": True, "has_analysis": False}
    return {"success": True, "has_analysis": True, "analysis": _skill_gap_payload(analysis)}


@router.post("/skill-gap/me/analyze")
def analyze_my_skill_gap(
    req: SkillGapReq,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("employee")),
):
    employee = _get_employee_for_user(session, current_user.id)
    payload = analyze_skill_gap(employee, req.role_expectations)
    now = datetime.utcnow()
    record = SkillGapAnalysis(
        employee_id=employee.id,
        user_id=current_user.id,
        role_expectations=payload["role_expectations"],
        missing_skills=json.dumps(payload["missing_skills"], ensure_ascii=True),
        growth_areas=json.dumps(payload["growth_areas"], ensure_ascii=True),
        learning_suggestions=json.dumps(payload["learning_suggestions"], ensure_ascii=True),
        summary=payload["summary"],
        source=payload["source"],
        error_message=payload.get("error_message"),
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return {"success": True, "analysis": _skill_gap_payload(record)}


@router.post("/assistant")
def hr_assistant(
    req: HRAssistantReq,
    current_user: User = Depends(require_roles("employee")),
):
    return answer_hr_question(req.question)


@router.get("/{employee_id}")
def get_employee(
    employee_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr")),
):
    employee = session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return _employee_payload(session, employee)


def _get_employee_for_user(session: Session, user_id: int) -> Employee:
    employee = session.exec(select(Employee).where(Employee.user_id == user_id)).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")
    return employee


def _today_attendance(session: Session, employee: Employee) -> AttendanceRecord | None:
    return session.exec(
        select(AttendanceRecord)
        .where(AttendanceRecord.employee_id == employee.id)
        .where(AttendanceRecord.work_date == date.today())
        .order_by(AttendanceRecord.created_at.desc())
    ).first()


def _employee_payload(session: Session, employee: Employee) -> dict[str, Any]:
    user = session.get(User, employee.user_id)
    return {
        "id": employee.id,
        "user_id": employee.user_id,
        "username": user.username if user else "",
        "employee_code": employee.employee_code,
        "department": employee.department,
        "designation": employee.designation,
        "salary": employee.salary,
        "joining_date": employee.joining_date.isoformat() if employee.joining_date else None,
        "skills": employee.skills,
    }


def _attendance_payload(record: AttendanceRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "employee_id": record.employee_id,
        "user_id": record.user_id,
        "work_date": record.work_date.isoformat() if record.work_date else None,
        "check_in": record.check_in.isoformat() + "Z" if record.check_in else None,
        "check_out": record.check_out.isoformat() + "Z" if record.check_out else None,
        "status": record.status,
    }


def _leave_payload(session: Session, leave: LeaveRequest) -> dict[str, Any]:
    employee = session.get(Employee, leave.employee_id)
    user = session.get(User, leave.user_id)
    return {
        "id": leave.id,
        "employee_id": leave.employee_id,
        "employee_code": employee.employee_code if employee else "",
        "username": user.username if user else "",
        "leave_type": leave.leave_type,
        "start_date": leave.start_date.isoformat() if leave.start_date else None,
        "end_date": leave.end_date.isoformat() if leave.end_date else None,
        "reason": leave.reason,
        "status": leave.status,
        "manager_note": leave.manager_note,
        "decided_by": leave.decided_by,
        "created_at": leave.created_at.isoformat() + "Z" if leave.created_at else None,
        "updated_at": leave.updated_at.isoformat() + "Z" if leave.updated_at else None,
    }


def _skill_gap_payload(analysis: SkillGapAnalysis) -> dict[str, Any]:
    return {
        "id": analysis.id,
        "employee_id": analysis.employee_id,
        "role_expectations": analysis.role_expectations,
        "missing_skills": _load_json(analysis.missing_skills),
        "growth_areas": _load_json(analysis.growth_areas),
        "learning_suggestions": _load_json(analysis.learning_suggestions),
        "summary": analysis.summary,
        "source": analysis.source,
        "error_message": analysis.error_message,
        "updated_at": analysis.updated_at.isoformat() + "Z" if analysis.updated_at else None,
    }


def _load_json(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []
