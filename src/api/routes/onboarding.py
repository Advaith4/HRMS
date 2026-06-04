from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from src.api.dependencies import get_current_user, require_roles
from src.database.connection import get_session
from src.models import (
    Employee,
    EmployeeOnboarding,
    EmployeeOnboardingTask,
    HRNotification,
    OnboardingTask,
    OnboardingTemplate,
    User,
    OnboardingRequiredDocument,
    EmployeeDocument,
    EmployeeLifecycleEvent,
)


router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


class OnboardingTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    required: bool = True
    display_order: int = 0


class OnboardingTaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    required: Optional[bool] = None
    display_order: Optional[int] = None


class OnboardingTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    tasks: list[OnboardingTaskCreate] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)


class OnboardingTemplateUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    is_active: Optional[bool] = None
    required_documents: Optional[list[str]] = None


class OnboardingAssignReq(BaseModel):
    employee_id: int
    template_id: int
    due_date: Optional[date] = None


class OnboardingTaskStatusReq(BaseModel):
    status: str = Field(pattern="^(Pending|In Progress|Completed)$")
    notes: str = Field(default="", max_length=500)


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


def _task_payload(task: OnboardingTask | EmployeeOnboardingTask) -> dict:
    return {
        "id": task.id,
        "title": getattr(task, "title", getattr(task, "task_title", "")),
        "description": getattr(task, "description", getattr(task, "task_description", "")),
        "required": getattr(task, "is_required", True),
        "display_order": getattr(task, "order_index", 0),
        "status": getattr(task, "status", None),
        "completed_at": task.completed_at.isoformat() + "Z" if getattr(task, "completed_at", None) else None,
        "notes": getattr(task, "notes", ""),
    }


def _template_payload(session: Session, template: OnboardingTemplate) -> dict:
    tasks = session.exec(
        select(OnboardingTask)
        .where(OnboardingTask.template_id == template.id)
        .order_by(OnboardingTask.order_index, OnboardingTask.id)
    ).all()
    req_docs = session.exec(
        select(OnboardingRequiredDocument)
        .where(OnboardingRequiredDocument.template_id == template.id)
    ).all()
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "is_active": template.is_active,
        "created_by": template.created_by,
        "created_at": template.created_at.isoformat() + "Z" if template.created_at else None,
        "updated_at": template.updated_at.isoformat() + "Z" if template.updated_at else None,
        "tasks": [_task_payload(task) for task in tasks],
        "required_documents": [rd.document_type for rd in req_docs],
    }


def _plan_payload(session: Session, plan: EmployeeOnboarding) -> dict:
    employee = session.get(Employee, plan.employee_id)
    template = session.get(OnboardingTemplate, plan.template_id)
    tasks = session.exec(
        select(EmployeeOnboardingTask)
        .where(EmployeeOnboardingTask.employee_onboarding_id == plan.id)
        .order_by(EmployeeOnboardingTask.order_index, EmployeeOnboardingTask.id)
    ).all()
    
    # Required documents from template
    req_docs = session.exec(
        select(OnboardingRequiredDocument)
        .where(OnboardingRequiredDocument.template_id == plan.template_id)
    ).all()
    req_doc_types = [rd.document_type for rd in req_docs]

    # Employee documents
    emp_docs = []
    if employee:
        emp_docs = session.exec(
            select(EmployeeDocument)
            .where(EmployeeDocument.user_id == employee.user_id)
        ).all()

    # Progress computation using 50/50 formula
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.status == "Completed"])
    task_percent = (completed_tasks / total_tasks * 100) if total_tasks else 100.0

    total_req_docs = len(req_doc_types)
    if total_req_docs > 0:
        submitted_valid_types = 0
        for doc_type in req_doc_types:
            has_valid = any(
                d.document_type == doc_type and d.verification_status != "Rejected"
                for d in emp_docs
            )
            if has_valid:
                submitted_valid_types += 1
        doc_percent = (submitted_valid_types / total_req_docs * 100)
    else:
        doc_percent = 100.0

    if total_tasks > 0 and total_req_docs > 0:
        progress = round((task_percent + doc_percent) / 2)
    elif total_tasks > 0:
        progress = round(task_percent)
    elif total_req_docs > 0:
        progress = round(doc_percent)
    else:
        progress = 100

    effective_status = plan.status
    if plan.status != "Completed" and plan.due_date and plan.due_date < date.today():
        effective_status = "Overdue"

    # Detail status for each required document
    required_docs_status = []
    for rd in req_docs:
        # Find latest upload of this type
        latest_doc = None
        for d in emp_docs:
            if d.document_type == rd.document_type:
                if not latest_doc or d.uploaded_at > latest_doc.uploaded_at:
                    latest_doc = d
        required_docs_status.append({
            "document_type": rd.document_type,
            "status": latest_doc.verification_status if latest_doc else "Pending Submission",
            "rejection_comment": latest_doc.rejection_comment if latest_doc else "",
            "document_id": latest_doc.id if latest_doc else None,
            "uploaded_at": latest_doc.uploaded_at.isoformat() + "Z" if latest_doc and latest_doc.uploaded_at else None,
        })

    return {
        "id": plan.id,
        "employee_id": plan.employee_id,
        "employee_name": _employee_name(session, employee),
        "employee_code": employee.employee_code if employee else "",
        "template_id": plan.template_id,
        "template_name": template.name if template else "",
        "status": effective_status,
        "due_date": plan.due_date.isoformat() if plan.due_date else None,
        "progress_percent": progress,
        "pending_count": len([task for task in tasks if task.status != "Completed"]),
        "completed_count": completed_tasks,
        "tasks": [_task_payload(task) for task in tasks],
        "required_documents": required_docs_status,
        "created_at": plan.created_at.isoformat() + "Z" if plan.created_at else None,
        "completed_at": plan.completed_at.isoformat() + "Z" if plan.completed_at else None,
    }


def _get_employee_for_user(session: Session, user_id: int) -> Employee:
    employee = session.exec(select(Employee).where(Employee.user_id == user_id)).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found.")
    return employee


def _assert_plan_access(current_user: User, employee: Employee | None) -> None:
    if current_user.role in {"hr", "admin", "manager"}:
        return
    if employee and employee.user_id == current_user.id:
        return
    raise HTTPException(status_code=403, detail="Insufficient permissions")


@router.get("/templates")
def list_templates(
    include_archived: bool = False,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr", "manager")),
):
    query = select(OnboardingTemplate).order_by(OnboardingTemplate.created_at.desc())
    templates = session.exec(query).all()
    if not include_archived:
        templates = [template for template in templates if template.is_active]
    return [_template_payload(session, template) for template in templates]


@router.post("/templates", status_code=201)
def create_template(
    body: OnboardingTemplateCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr")),
):
    now = datetime.utcnow()
    template = OnboardingTemplate(
        name=body.name.strip(),
        description=body.description.strip(),
        created_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    session.add(template)
    session.commit()
    session.refresh(template)

    for item in body.tasks:
        session.add(
            OnboardingTask(
                template_id=template.id,
                title=item.title.strip(),
                description=item.description.strip(),
                is_required=item.required,
                order_index=item.display_order,
            )
        )
    for doc_type in body.required_documents:
        session.add(
            OnboardingRequiredDocument(
                template_id=template.id,
                document_type=doc_type.strip(),
            )
        )
    session.commit()
    return _template_payload(session, template)


@router.put("/templates/{template_id}")
def update_template(
    template_id: int,
    body: OnboardingTemplateUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr")),
):
    template = session.get(OnboardingTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Onboarding template not found.")
    data = body.model_dump(exclude_none=True)
    required_documents = data.pop("required_documents", None)
    for key, value in data.items():
        setattr(template, key, value.strip() if isinstance(value, str) else value)
    
    if required_documents is not None:
        existing_docs = session.exec(
            select(OnboardingRequiredDocument)
            .where(OnboardingRequiredDocument.template_id == template.id)
        ).all()
        for doc in existing_docs:
            session.delete(doc)
        for doc_type in required_documents:
            session.add(
                OnboardingRequiredDocument(
                    template_id=template.id,
                    document_type=doc_type.strip(),
                )
            )
            
    template.updated_at = datetime.utcnow()
    session.add(template)
    session.commit()
    session.refresh(template)
    return _template_payload(session, template)


@router.delete("/templates/{template_id}")
def archive_template(
    template_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr")),
):
    template = session.get(OnboardingTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Onboarding template not found.")
    template.is_active = False
    template.updated_at = datetime.utcnow()
    session.add(template)
    session.commit()
    return {"ok": True}


@router.post("/templates/{template_id}/tasks", status_code=201)
def add_template_task(
    template_id: int,
    body: OnboardingTaskCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr")),
):
    template = session.get(OnboardingTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Onboarding template not found.")
    task = OnboardingTask(
        template_id=template_id,
        title=body.title.strip(),
        description=body.description.strip(),
        is_required=body.required,
        order_index=body.display_order,
    )
    template.updated_at = datetime.utcnow()
    session.add(task)
    session.add(template)
    session.commit()
    session.refresh(task)
    return _task_payload(task)


@router.put("/tasks/{task_id}")
def update_template_task(
    task_id: int,
    body: OnboardingTaskUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr")),
):
    task = session.get(OnboardingTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Onboarding task not found.")
    data = body.model_dump(exclude_none=True)
    mapping = {"required": "is_required", "display_order": "order_index"}
    for key, value in data.items():
        setattr(task, mapping.get(key, key), value.strip() if isinstance(value, str) else value)
    session.add(task)
    session.commit()
    session.refresh(task)
    return _task_payload(task)


@router.delete("/tasks/{task_id}")
def delete_template_task(
    task_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr")),
):
    task = session.get(OnboardingTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Onboarding task not found.")
    session.delete(task)
    session.commit()
    return {"ok": True}


@router.post("/assign", status_code=201)
def assign_template(
    body: OnboardingAssignReq,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr")),
):
    employee = session.get(Employee, body.employee_id)
    template = session.get(OnboardingTemplate, body.template_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found.")
    if not template or not template.is_active:
        raise HTTPException(status_code=404, detail="Active onboarding template not found.")

    tasks = session.exec(
        select(OnboardingTask)
        .where(OnboardingTask.template_id == template.id)
        .order_by(OnboardingTask.order_index, OnboardingTask.id)
    ).all()
    if not tasks:
        raise HTTPException(status_code=400, detail="Add at least one task before assigning this template.")

    duplicate = session.exec(
        select(EmployeeOnboarding)
        .where(EmployeeOnboarding.employee_id == employee.id)
        .where(EmployeeOnboarding.template_id == template.id)
        .where(EmployeeOnboarding.status != "Completed")
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="This employee already has an active plan for this template.")

    now = datetime.utcnow()
    plan = EmployeeOnboarding(
        employee_id=employee.id,
        template_id=template.id,
        assigned_by=current_user.id,
        status="Active",
        due_date=body.due_date,
        started_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(plan)
    session.commit()
    session.refresh(plan)

    for task in tasks:
        session.add(
            EmployeeOnboardingTask(
                employee_onboarding_id=plan.id,
                task_title=task.title,
                task_description=task.description,
                order_index=task.order_index,
                is_required=task.is_required,
            )
        )
    # Record Onboarding Started event
    session.add(
        EmployeeLifecycleEvent(
            employee_id=employee.id,
            event_type="Onboarding Started",
            event_date=date.today(),
            description=f"Onboarding started with plan: '{template.name}'.",
            created_by=current_user.id
        )
    )
    _notify(
        session,
        employee.user_id,
        "Onboarding Assigned",
        f"You have been assigned the {template.name} onboarding plan.",
        "onboarding_assigned",
        plan.id,
    )
    session.commit()
    return _plan_payload(session, plan)


@router.get("/employee/{employee_id}")
def get_employee_onboarding(
    employee_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    employee = session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found.")
    _assert_plan_access(current_user, employee)
    plans = session.exec(
        select(EmployeeOnboarding)
        .where(EmployeeOnboarding.employee_id == employee_id)
        .order_by(EmployeeOnboarding.created_at.desc())
    ).all()
    return [_plan_payload(session, plan) for plan in plans]


@router.get("/my")
def get_my_onboarding(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("employee")),
):
    employee = _get_employee_for_user(session, current_user.id)
    plans = session.exec(
        select(EmployeeOnboarding)
        .where(EmployeeOnboarding.employee_id == employee.id)
        .order_by(EmployeeOnboarding.created_at.desc())
    ).all()
    return [_plan_payload(session, plan) for plan in plans]


@router.put("/plan/{plan_id}/task/{task_id}")
def update_plan_task(
    plan_id: int,
    task_id: int,
    body: OnboardingTaskStatusReq,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    plan = session.get(EmployeeOnboarding, plan_id)
    task = session.get(EmployeeOnboardingTask, task_id)
    if not plan or not task or task.employee_onboarding_id != plan.id:
        raise HTTPException(status_code=404, detail="Onboarding task not found.")
    employee = session.get(Employee, plan.employee_id)
    _assert_plan_access(current_user, employee)

    now = datetime.utcnow()
    task.status = body.status
    task.notes = body.notes.strip()
    task.completed_at = now if body.status == "Completed" else None
    task.updated_at = now
    session.add(task)

    all_tasks = session.exec(
        select(EmployeeOnboardingTask).where(EmployeeOnboardingTask.employee_onboarding_id == plan.id)
    ).all()
    required_tasks = [item for item in all_tasks if item.is_required]
    if required_tasks and all(item.id == task.id and body.status == "Completed" or item.status == "Completed" for item in required_tasks):
        plan.status = "Completed"
        plan.completed_at = now
        if employee:
            session.add(
                EmployeeLifecycleEvent(
                    employee_id=employee.id,
                    event_type="Onboarding Completed",
                    event_date=date.today(),
                    description="Completed all onboarding checkpoints and documentation.",
                    created_by=current_user.id
                )
            )
            _notify(
                session,
                employee.user_id,
                "Onboarding Completed",
                "Your onboarding plan is complete.",
                "onboarding_completed",
                plan.id,
            )
            for hr_user in session.exec(select(User).where(User.role.in_(["hr", "admin"]))).all():
                _notify(
                    session,
                    hr_user.id,
                    "Onboarding Completed",
                    f"{_employee_name(session, employee)} completed onboarding.",
                    "onboarding_completed",
                    plan.id,
                )
    elif body.status == "In Progress" and plan.status == "Active":
        plan.started_at = plan.started_at or now
    plan.updated_at = now
    session.add(plan)
    session.commit()
    session.refresh(task)
    return _plan_payload(session, plan)


@router.get("/summary")
def onboarding_summary(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr", "manager")),
):
    plans = session.exec(select(EmployeeOnboarding)).all()
    today = date.today()
    new_joiners = session.exec(select(Employee).where(Employee.joining_date >= date(today.year, today.month, 1))).all()
    return {
        "new_joiners": len(new_joiners),
        "active_plans": len([plan for plan in plans if plan.status != "Completed"]),
        "completed_plans": len([plan for plan in plans if plan.status == "Completed"]),
        "overdue_plans": len([plan for plan in plans if plan.status != "Completed" and plan.due_date and plan.due_date < today]),
    }


class RequiredDocumentReq(BaseModel):
    document_type: str = Field(min_length=1, max_length=80)


@router.post("/templates/{template_id}/required-documents", status_code=201)
def add_template_required_document(
    template_id: int,
    body: RequiredDocumentReq,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr")),
):
    template = session.get(OnboardingTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Onboarding template not found.")
    
    existing = session.exec(
        select(OnboardingRequiredDocument)
        .where(OnboardingRequiredDocument.template_id == template.id)
        .where(OnboardingRequiredDocument.document_type == body.document_type.strip())
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Document type already required for this template.")
        
    doc = OnboardingRequiredDocument(
        template_id=template.id,
        document_type=body.document_type.strip(),
    )
    session.add(doc)
    session.commit()
    return _template_payload(session, template)


@router.delete("/templates/{template_id}/required-documents/{document_type}")
def remove_template_required_document(
    template_id: int,
    document_type: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_roles("hr")),
):
    template = session.get(OnboardingTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Onboarding template not found.")
        
    doc = session.exec(
        select(OnboardingRequiredDocument)
        .where(OnboardingRequiredDocument.template_id == template.id)
        .where(OnboardingRequiredDocument.document_type == document_type.strip())
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Required document not found for this template.")
        
    session.delete(doc)
    session.commit()
    return _template_payload(session, template)
