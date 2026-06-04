import os
import uuid
from pathlib import Path
from datetime import date, datetime

Path("data").mkdir(exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{(Path('data') / f'test_phase2a_{uuid.uuid4().hex}.db').as_posix()}"
os.environ["AUTO_CREATE_DB_SCHEMA"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-talentforge-phase2a"

from fastapi.testclient import TestClient
from sqlmodel import Session, select, text
import pytest

from src.main import app
from src.database.connection import create_db_and_tables, engine
from src.models import Employee, User, OnboardingTemplate, OnboardingTask, EmployeeOnboarding, EmployeeOnboardingTask, TrainingProgram, TrainingAssignment

create_db_and_tables()
client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    with Session(engine) as session:
        session.exec(text("DELETE FROM employee_onboarding_tasks"))
        session.exec(text("DELETE FROM employee_onboarding"))
        session.exec(text("DELETE FROM onboarding_tasks"))
        session.exec(text("DELETE FROM onboarding_templates"))
        session.exec(text("DELETE FROM training_assignments"))
        session.exec(text("DELETE FROM training_programs"))
        session.commit()


def _register(username: str, role: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={"username": username, "password": "Pass123!"},
    )
    assert response.status_code == 201, response.text
    if role == "candidate":
        return response.json()["access_token"]

    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).one()
        user.role = role
        session.add(user)
        session.commit()

    login = client.post("/api/auth/login", json={"username": username, "password": "Pass123!"})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def test_onboarding_templates_and_tasks():
    hr_token = _register(f"hr_{uuid.uuid4().hex[:8]}", "hr")
    hr_headers = {"Authorization": f"Bearer {hr_token}"}

    # 1. Create Template
    response = client.post(
        "/api/onboarding/templates",
        headers=hr_headers,
        json={
            "name": "Standard Onboarding",
            "description": "Welcome to TalentForge",
            "tasks": [
                {"title": "Submit Documents", "description": "Upload ID, Photo, and Resume", "required": True, "display_order": 1},
                {"title": "Meet Manager", "description": "1-on-1 intro", "required": False, "display_order": 2}
            ]
        }
    )
    assert response.status_code == 201, response.text
    template = response.json()
    assert template["name"] == "Standard Onboarding"
    assert len(template["tasks"]) == 2
    template_id = template["id"]

    # 2. Get Templates
    response = client.get("/api/onboarding/templates", headers=hr_headers)
    assert response.status_code == 200
    templates = response.json()
    assert len(templates) >= 1
    assert any(t["id"] == template_id for t in templates)

    # 3. Update Template
    response = client.put(
        f"/api/onboarding/templates/{template_id}",
        headers=hr_headers,
        json={"name": "Updated Standard Onboarding", "description": "Updated Description"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Standard Onboarding"

    # 4. Add template task
    response = client.post(
        f"/api/onboarding/templates/{template_id}/tasks",
        headers=hr_headers,
        json={"title": "Fill Feedback Form", "description": "Share your experience", "required": True, "display_order": 3}
    )
    assert response.status_code == 201
    task_id = response.json()["id"]

    # 5. Update template task
    response = client.put(
        f"/api/onboarding/tasks/{task_id}",
        headers=hr_headers,
        json={"title": "Fill Detailed Feedback Form", "required": False}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Fill Detailed Feedback Form"
    assert response.json()["required"] is False

    # 6. Delete template task
    response = client.delete(f"/api/onboarding/tasks/{task_id}", headers=hr_headers)
    assert response.status_code == 200

    # 7. Archive template (soft delete)
    response = client.delete(f"/api/onboarding/templates/{template_id}", headers=hr_headers)
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_onboarding_assignment_and_progression():
    hr_token = _register(f"hr_{uuid.uuid4().hex[:8]}", "hr")
    hr_headers = {"Authorization": f"Bearer {hr_token}"}

    # Setup template
    resp = client.post(
        "/api/onboarding/templates",
        headers=hr_headers,
        json={
            "name": "Developer Onboarding",
            "tasks": [
                {"title": "Set up Dev Env", "required": True, "display_order": 1},
                {"title": "First PR", "required": True, "display_order": 2}
            ]
        }
    )
    assert resp.status_code == 201
    template_id = resp.json()["id"]

    # Create employee user
    employee_username = f"emp_{uuid.uuid4().hex[:8]}"
    employee_token = _register(employee_username, "employee")
    employee_headers = {"Authorization": f"Bearer {employee_token}"}

    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == employee_username)).one()
        employee = Employee(
            user_id=user.id,
            employee_code=f"EMP-{uuid.uuid4().hex[:6]}",
            full_name="Jane Doe",
            joining_date=date.today(),
            status="Active"
        )
        session.add(employee)
        session.commit()
        session.refresh(employee)
        employee_id = employee.id

    # Assign template to employee
    response = client.post(
        "/api/onboarding/assign",
        headers=hr_headers,
        json={
            "employee_id": employee_id,
            "template_id": template_id,
            "due_date": date.today().isoformat()
        }
    )
    assert response.status_code == 201, response.text
    plan = response.json()
    assert plan["status"] == "Active"
    assert len(plan["tasks"]) == 2
    plan_id = plan["id"]

    # Get employee onboarding profile (via HR)
    response = client.get(f"/api/onboarding/employee/{employee_id}", headers=hr_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

    # Get employee onboarding (via employee self)
    response = client.get("/api/onboarding/my", headers=employee_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == plan_id

    # Complete a task
    task1 = plan["tasks"][0]
    response = client.put(
        f"/api/onboarding/plan/{plan_id}/task/{task1['id']}",
        headers=employee_headers,
        json={"status": "Completed", "notes": "Configured IDE"}
    )
    assert response.status_code == 200
    updated_plan = response.json()
    assert updated_plan["progress_percent"] == 50
    assert updated_plan["status"] == "Active"

    # Complete the second (and final required) task
    task2 = plan["tasks"][1]
    response = client.put(
        f"/api/onboarding/plan/{plan_id}/task/{task2['id']}",
        headers=employee_headers,
        json={"status": "Completed", "notes": "PR merged"}
    )
    assert response.status_code == 200
    completed_plan = response.json()
    assert completed_plan["progress_percent"] == 100
    assert completed_plan["status"] == "Completed"
    assert completed_plan["completed_at"] is not None

    # Verify summary
    response = client.get("/api/onboarding/summary", headers=hr_headers)
    assert response.status_code == 200
    summary = response.json()
    assert summary["completed_plans"] == 1
    assert summary["active_plans"] == 0


def test_training_programs_and_assignments():
    hr_token = _register(f"hr_{uuid.uuid4().hex[:8]}", "hr")
    hr_headers = {"Authorization": f"Bearer {hr_token}"}

    # 1. Create program
    response = client.post(
        "/api/training/programs",
        headers=hr_headers,
        json={
            "title": "FastAPI Security 101",
            "description": "Learn OAuth2 and JWT in FastAPI",
            "category": "Engineering",
            "skills_covered": "FastAPI, JWT, Security",
            "duration_hours": 4,
            "difficulty": "Intermediate",
            "status": "Active"
        }
    )
    assert response.status_code == 201, response.text
    program = response.json()
    assert program["title"] == "FastAPI Security 101"
    program_id = program["id"]

    # 2. Update program
    response = client.put(
        f"/api/training/programs/{program_id}",
        headers=hr_headers,
        json={"difficulty": "Advanced"}
    )
    assert response.status_code == 200
    assert response.json()["difficulty"] == "Advanced"

    # Create employee user
    employee_username = f"emp_{uuid.uuid4().hex[:8]}"
    employee_token = _register(employee_username, "employee")
    employee_headers = {"Authorization": f"Bearer {employee_token}"}

    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == employee_username)).one()
        employee = Employee(
            user_id=user.id,
            employee_code=f"EMP-{uuid.uuid4().hex[:6]}",
            full_name="John Smith",
            joining_date=date.today(),
            status="Active"
        )
        session.add(employee)
        session.commit()
        session.refresh(employee)
        employee_id = employee.id

    # 3. Assign program to employee
    response = client.post(
        "/api/training/assign",
        headers=hr_headers,
        json={
            "employee_id": employee_id,
            "program_id": program_id,
            "due_date": date.today().isoformat()
        }
    )
    assert response.status_code == 201, response.text
    assignment_id = response.json()["id"]

    # 4. Get assignments (via HR)
    response = client.get("/api/training/assignments", headers=hr_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1

    # 5. Get my assignments (via employee)
    response = client.get("/api/training/assignments/my", headers=employee_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == assignment_id

    # 6. Update progress
    response = client.put(
        f"/api/training/assignments/{assignment_id}/progress",
        headers=employee_headers,
        json={"progress_percent": 60, "status": "In Progress"}
    )
    assert response.status_code == 200
    assert response.json()["progress_percent"] == 60
    assert response.json()["status"] == "In Progress"

    # Complete it
    response = client.put(
        f"/api/training/assignments/{assignment_id}/progress",
        headers=employee_headers,
        json={"progress_percent": 100}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Completed"

    # 7. Summary
    response = client.get("/api/training/summary", headers=hr_headers)
    assert response.status_code == 200
    summary = response.json()
    assert summary["completed"] == 1
    assert summary["completion_percent"] == 100

    # 8. Archive program
    response = client.delete(f"/api/training/programs/{program_id}", headers=hr_headers)
    assert response.status_code == 200
