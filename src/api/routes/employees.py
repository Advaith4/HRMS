import json
import logging
from datetime import date, datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from src.api.dependencies import require_roles, get_current_user
from src.database.connection import get_session
from src.models import (
    AttendanceRecord, Employee, LeaveRequest, SkillGapAnalysis, User,
    Department, Designation, EmployeeLifecycleEvent, HRNotification,
    TrainingAssignment, EmployeeTicket, EmployeeProfile
)
from src.services.employee_ai import analyze_skill_gap, answer_hr_question
from src.services.rag.access_control import RAGAccessControl
from src.services.rag.chat_service import RAGChatService


router = APIRouter(prefix="/api/employees", tags=["employees"])
logger = logging.getLogger(__name__)


def get_rag_chat_service() -> RAGChatService:
    return RAGChatService()


def get_rag_access_control() -> RAGAccessControl:
    return RAGAccessControl()


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


def _calculate_career_growth(employee: Employee) -> dict[str, Any]:
    current_skills = [s.strip() for s in employee.skills.split(",") if s.strip()] if employee.skills else []
    designation = (employee.designation or "Employee").strip()
    desig_lower = designation.lower()
    
    if "backend" in desig_lower or "engineer" in desig_lower and "backend" in desig_lower:
        next_role = "Senior Backend Engineer"
        expected_skills = ["Python", "FastAPI", "PostgreSQL", "System Design", "Kubernetes", "Redis", "Microservices"]
        learning_areas = ["System Design & Distributed Systems", "Containerization & Orchestration (Kubernetes)", "Caching strategies with Redis"]
    elif "frontend" in desig_lower or "react" in desig_lower or "ui" in desig_lower:
        next_role = "Senior Frontend Engineer"
        expected_skills = ["React", "JavaScript", "TypeScript", "Next.js", "State Management", "Performance Optimization"]
        learning_areas = ["Server-Side Rendering (Next.js)", "Advanced State Management (Redux/Zustand)", "Web Performance Optimization"]
    elif "qa" in desig_lower or "test" in desig_lower:
        next_role = "QA Lead"
        expected_skills = ["Testing", "Selenium", "Cypress", "CI/CD", "Automation", "Performance Testing"]
        learning_areas = ["Automated Testing Frameworks (Cypress/Playwright)", "CI/CD Pipeline Integration", "Load & Performance Testing"]
    elif "data" in desig_lower:
        next_role = "Senior Data Scientist"
        expected_skills = ["Python", "Machine Learning", "PyTorch", "SQL", "MLOps", "Big Data"]
        learning_areas = ["MLOps & Model Deployment Pipelines", "Deep Learning with PyTorch", "Big Data Processing (Spark)"]
    else:
        next_role = f"Lead {designation}"
        expected_skills = ["Leadership", "Project Management", "Agile", "System Integration", "Communication"]
        learning_areas = ["Technical Leadership & Team Management", "System Integration & Architecture", "Agile & Scrum Methodologies"]
        
    current_lower = {s.lower() for s in current_skills}
    found = [s for s in expected_skills if s.lower() in current_lower]
    for s in current_skills:
        if s.lower() not in {e.lower() for e in expected_skills}:
            found.append(s)
            
    missing = [s for s in expected_skills if s.lower() not in current_lower]
    
    return {
        "current_role": designation,
        "suggested_next_role": next_role,
        "skills_found": found,
        "skills_missing": missing,
        "recommended_learning_areas": learning_areas
    }


def _calculate_promotion_readiness(
    expected_skills: list[str],
    current_skills: list[str],
    training_assignments: list[TrainingAssignment],
    profile_completion: int
) -> dict[str, Any]:
    current_lower = {s.lower() for s in current_skills}
    match_count = len([s for s in expected_skills if s.lower() in current_lower])
    skill_ratio = match_count / len(expected_skills) if expected_skills else 1.0
    
    completed_trainings = [t for t in training_assignments if t.status == "Completed"]
    training_ratio = len(completed_trainings) / len(training_assignments) if training_assignments else 1.0
    
    if skill_ratio >= 0.70 and training_ratio >= 0.75 and profile_completion >= 80:
        status = "Ready"
        explanation = (
            "You have demonstrated strong core competency by matching over 70% of expected skills, "
            "completing the majority of your assigned training programs, and keeping your employee profile fully up-to-date."
        )
    elif skill_ratio >= 0.40 and training_ratio >= 0.50 and profile_completion >= 50:
        status = "Developing"
        missing_core = [s for s in expected_skills if s.lower() not in current_lower]
        missing_str = ", ".join(missing_core[:3])
        explanation = (
            f"You are making steady progress towards the next role. Focus on completing pending training assignments "
            f"and acquiring key missing skills like: {missing_str}."
        )
    else:
        status = "Needs Growth"
        explanation = (
            "Focus on expanding your skill set, completing your assigned training courses, "
            "and ensuring your employee profile is fully completed."
        )
        
    return {
        "status": status,
        "explanation": explanation,
        "skill_match_percent": round(skill_ratio * 100),
        "training_completion_percent": round(training_ratio * 100),
        "profile_completion_percent": profile_completion
    }


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
    training_assignments = session.exec(
        select(TrainingAssignment)
        .where(TrainingAssignment.employee_id == employee.id)
        .order_by(TrainingAssignment.created_at.desc())
    ).all()
    tickets = session.exec(
        select(EmployeeTicket)
        .where(EmployeeTicket.user_id == current_user.id)
        .order_by(EmployeeTicket.created_at.desc())
    ).all()
    latest_skill_gap = session.exec(
        select(SkillGapAnalysis)
        .where(SkillGapAnalysis.employee_id == employee.id)
        .order_by(SkillGapAnalysis.updated_at.desc())
    ).first()
    
    attendance_records = session.exec(
        select(AttendanceRecord)
        .where(AttendanceRecord.employee_id == employee.id)
    ).all()
    
    attendance_summary = {
        "total_checkins": len(attendance_records),
        "today_status": today_record.status if today_record else "Not Checked In"
    }
    
    training_summary = {
        "total_assigned": len(training_assignments),
        "completed": len([item for item in training_assignments if item.status == "Completed"]),
        "pending": len([item for item in training_assignments if item.status != "Completed"]),
    }
    
    # Calculate deterministic career growth & promotion readiness
    career_growth = _calculate_career_growth(employee)
    
    profile = session.exec(
        select(EmployeeProfile)
        .where(EmployeeProfile.user_id == current_user.id)
    ).first()
    profile_completion = profile.completion_percent if profile else 0
    
    current_skills_list = [s.strip() for s in employee.skills.split(",") if s.strip()] if employee.skills else []
    
    designation = (employee.designation or "Employee").strip().lower()
    if "backend" in designation:
        expected_skills = ["Python", "FastAPI", "PostgreSQL", "System Design", "Kubernetes", "Redis", "Microservices"]
    elif "frontend" in designation or "react" in designation or "ui" in designation:
        expected_skills = ["React", "JavaScript", "TypeScript", "Next.js", "State Management", "Performance Optimization"]
    elif "qa" in designation or "test" in designation:
        expected_skills = ["Testing", "Selenium", "Cypress", "CI/CD", "Automation", "Performance Testing"]
    elif "data" in designation:
        expected_skills = ["Python", "Machine Learning", "PyTorch", "SQL", "MLOps", "Big Data"]
    else:
        expected_skills = ["Leadership", "Project Management", "Agile", "System Integration", "Communication"]
        
    readiness = _calculate_promotion_readiness(
        expected_skills,
        current_skills_list,
        training_assignments,
        profile_completion
    )
    career_growth["promotion_readiness"] = readiness
    
    return {
        "employee": _employee_payload(session, employee),
        "attendance_status": _attendance_payload(today_record) if today_record else None,
        "attendance_summary": attendance_summary,
        "leave_summary": {
            "pending": len([item for item in leaves if item.status == "Pending"]),
            "approved": len([item for item in leaves if item.status == "Approved"]),
            "rejected": len([item for item in leaves if item.status == "Rejected"]),
            "recent": [_leave_payload(session, item) for item in leaves[:5]],
        },
        "leave_balance": _leave_balance(leaves),
        "training_summary": training_summary,
        "open_ticket_count": len([ticket for ticket in tickets if ticket.status.lower() != "closed"]),
        "skill_gap": _skill_gap_payload(latest_skill_gap) if latest_skill_gap else None,
        "career_growth": career_growth,
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
    service: RAGChatService = Depends(get_rag_chat_service),
    access_control: RAGAccessControl = Depends(get_rag_access_control),
):
    try:
        plan = access_control.build_plan(current_user, ["company_policies", "employee_knowledge"])
        return service.answer(req.question, plan.collections, filters=plan.filters, user=current_user)
    except Exception as exc:
        logger.exception("Employee RAG assistant failed; falling back to static HR policy answer")
        return answer_hr_question(req.question)


@router.get("/directory")
def get_employee_directory(
    search: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[str] = None,
    sort: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr", "manager"))
):
    query = select(Employee)
    employees = session.exec(query).all()
    
    user_ids = {e.user_id for e in employees if e.user_id}
    manager_ids = {e.manager_id for e in employees if e.manager_id}
    dept_ids = {e.department_id for e in employees if e.department_id}
    desig_ids = {e.designation_id for e in employees if e.designation_id}
    
    users = session.exec(select(User).where(User.id.in_(list(user_ids | manager_ids)))).all() if (user_ids | manager_ids) else []
    depts = session.exec(select(Department).where(Department.id.in_(list(dept_ids)))).all() if dept_ids else []
    desigs = session.exec(select(Designation).where(Designation.id.in_(list(desig_ids)))).all() if desig_ids else []
    
    users_by_id = {u.id: u for u in users}
    depts_by_id = {d.id: d for d in depts}
    desigs_by_id = {dg.id: dg for dg in desigs}
    
    payload = []
    for e in employees:
        u = users_by_id.get(e.user_id)
        username = u.username if u else ""
        mgr = users_by_id.get(e.manager_id)
        manager_name = mgr.username if mgr else ""
        
        dept_name = depts_by_id.get(e.department_id).name if e.department_id and e.department_id in depts_by_id else e.department
        desig_name = desigs_by_id.get(e.designation_id).name if e.designation_id and e.designation_id in desigs_by_id else e.designation
        
        payload.append({
            "id": e.id,
            "user_id": e.user_id,
            "username": username,
            "full_name": e.full_name or username or "",
            "email": e.email or "",
            "phone": e.phone or "",
            "employee_code": e.employee_code,
            "department": dept_name,
            "designation": desig_name,
            "status": e.status or "Active",
            "joining_date": e.joining_date.isoformat() if e.joining_date else None,
            "manager_name": manager_name,
            "work_location": e.work_location or "",
        })
        
    if search:
        search = search.lower()
        payload = [
            x for x in payload
            if search in x["full_name"].lower()
            or search in x["email"].lower()
            or search in x["employee_code"].lower()
            or search in x["username"].lower()
        ]
        
    if department:
        payload = [x for x in payload if x["department"] == department]
        
    if status:
        payload = [x for x in payload if x["status"] == status]
        
    if sort == "joining_date":
        payload.sort(key=lambda x: x["joining_date"] or "")
    elif sort == "department":
        payload.sort(key=lambda x: x["department"] or "")
    elif sort == "designation":
        payload.sort(key=lambda x: x["designation"] or "")
        
    return payload


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
    manager = session.get(User, employee.manager_id) if employee.manager_id else None
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
        "manager_name": manager.username if manager else None,
        "manager_id": employee.manager_id,
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


def _leave_days(leave: LeaveRequest) -> int:
    if leave.start_date and leave.end_date:
        return max(0, (leave.end_date - leave.start_date).days + 1)
    return 0


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


def _leave_balance(leaves: list[LeaveRequest]) -> dict[str, Any]:
    allocations = {"Annual": 15, "Sick": 12, "Casual": 7}
    used = {"Annual": 0, "Sick": 0, "Casual": 0}
    for leave in leaves:
        days = _leave_days(leave)
        key = leave.leave_type.strip().title() if leave.leave_type else "General"
        if key in used and leave.status == "Approved":
            used[key] += days
    remaining = {key: max(0, allocations[key] - used[key]) for key in allocations}
    return {
        "allocations": allocations,
        "used": used,
        "remaining": remaining,
        "notes": "Monthly leave balances are estimated from approved leave requests and standard company policy allocations.",
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


# Phase 1 HR Operations Foundation Endpoints

class EmployeeProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    date_of_birth: Optional[date] = None
    emergency_contact: Optional[str] = None
    status: Optional[str] = None
    work_location: Optional[str] = None
    manager_id: Optional[int] = None
    department_id: Optional[int] = None
    designation_id: Optional[int] = None
    certifications: Optional[str] = None
    years_of_experience: Optional[float] = None
    skills: Optional[str] = None


def _notify_hr_static(session: Session, title: str, message: str, event_type: str, related_id: Optional[int] = None):
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





@router.get("/{employee_id}/profile")
def get_employee_profile(
    employee_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    emp = session.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")
        
    is_self = current_user.id == emp.user_id
    is_mgmt = current_user.role in ["hr", "manager", "admin"]
    if not (is_self or is_mgmt):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
        
    user = session.get(User, emp.user_id)
    username = user.username if user else ""
    
    manager_name = ""
    if emp.manager_id:
        mgr = session.get(User, emp.manager_id)
        manager_name = mgr.username if mgr else ""
        
    dept_name = ""
    if emp.department_id:
        dept = session.get(Department, emp.department_id)
        dept_name = dept.name if dept else ""
    else:
        dept_name = emp.department
        
    desig_name = ""
    if emp.designation_id:
        desig = session.get(Designation, emp.designation_id)
        desig_name = desig.name if desig else ""
    else:
        desig_name = emp.designation
        
    return {
        "id": emp.id,
        "user_id": emp.user_id,
        "username": username,
        "employee_code": emp.employee_code,
        "department": dept_name,
        "department_id": emp.department_id,
        "designation": desig_name,
        "designation_id": emp.designation_id,
        "salary": emp.salary,
        "joining_date": emp.joining_date.isoformat() if emp.joining_date else None,
        "skills": emp.skills,
        "full_name": emp.full_name,
        "email": emp.email,
        "phone": emp.phone,
        "address": emp.address,
        "date_of_birth": emp.date_of_birth.isoformat() if emp.date_of_birth else None,
        "emergency_contact": emp.emergency_contact,
        "status": emp.status,
        "work_location": emp.work_location,
        "manager_id": emp.manager_id,
        "manager_name": manager_name,
        "certifications": emp.certifications,
        "years_of_experience": emp.years_of_experience,
    }


@router.put("/{employee_id}/profile")
def update_employee_profile(
    employee_id: int,
    body: EmployeeProfileUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    emp = session.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")
        
    is_hr = current_user.role in ["hr", "admin"]
    is_self = current_user.id == emp.user_id
    
    if not (is_hr or is_self):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
        
    data = body.model_dump(exclude_none=True)
    if not is_hr:
        # only allow phone, address, emergency_contact, skills
        allowed_fields = {"phone", "address", "emergency_contact", "skills"}
        data = {k: v for k, v in data.items() if k in allowed_fields}
        
    old_status = emp.status
    
    for k, v in data.items():
        if k == "department_id":
            dept = session.get(Department, v)
            if dept:
                emp.department = dept.name
        elif k == "designation_id":
            desig = session.get(Designation, v)
            if desig:
                emp.designation = desig.name
        setattr(emp, k, v)
        
    session.add(emp)
    
    if "status" in data and data["status"] == "Active" and old_status != "Active":
        event = EmployeeLifecycleEvent(
            employee_id=emp.id,
            event_type="Confirmed",
            event_date=date.today(),
            description="Employee status updated to Active / Confirmed.",
            created_by=current_user.id
        )
        session.add(event)
        
        emp_user = session.get(User, emp.user_id)
        emp_name = emp_user.username if emp_user else f"Code {emp.employee_code}"
        _notify_hr_static(
            session,
            title="Employee Confirmed",
            message=f"{emp_name} has been confirmed as an Active employee.",
            event_type="lifecycle_event",
            related_id=emp.id
        )
        
    session.commit()
    return {"ok": True}

