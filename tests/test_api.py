import os
import sys
import types
import uuid
from pathlib import Path

Path("data").mkdir(exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{(Path('data') / f'test_day1_{uuid.uuid4().hex}.db').as_posix()}"
os.environ["AUTO_CREATE_DB_SCHEMA"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-talentforge"

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from src.main import app
import src.api.routes.applications as applications_route
import src.api.routes.interview as interview_route
import src.services.recruitment_ai as recruitment_ai
from src.database.connection import create_db_and_tables, engine
from src.models import Employee, User

create_db_and_tables()
client = TestClient(app)


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


def test_register_and_login_returns_role():
    username = f"candidate_{uuid.uuid4().hex[:8]}"
    token = _register(username, "candidate")
    assert token

    response = client.post("/api/auth/login", json={"username": username, "password": "Pass123!"})
    assert response.status_code == 200
    assert response.json()["role"] == "candidate"


def test_public_registration_rejects_role_escalation():
    response = client.post(
        "/api/auth/register",
        json={"username": f"admin_{uuid.uuid4().hex[:8]}", "password": "Pass123!", "role": "admin"},
    )
    assert response.status_code == 422


def test_hr_can_manage_jobs_candidate_can_only_read():
    candidate_token = _register(f"candidate_{uuid.uuid4().hex[:8]}", "candidate")
    hr_token = _register(f"hr_{uuid.uuid4().hex[:8]}", "hr")

    candidate_headers = {"Authorization": f"Bearer {candidate_token}"}
    hr_headers = {"Authorization": f"Bearer {hr_token}"}

    denied = client.post("/api/jobs", headers=candidate_headers, json={"title": "Nope", "description": "Nope"})
    assert denied.status_code == 403

    created = client.post(
        "/api/jobs",
        headers=hr_headers,
        json={
            "title": "Backend Developer",
            "description": "Build TalentForge APIs.",
            "required_skills": "Python, FastAPI",
            "department": "Engineering",
        },
    )
    assert created.status_code == 201, created.text
    job_id = created.json()["id"]

    listed = client.get("/api/jobs", headers=candidate_headers)
    assert listed.status_code == 200
    assert any(job["id"] == job_id for job in listed.json())

    updated = client.put(f"/api/jobs/{job_id}", headers=hr_headers, json={"salary_range": "10-14 LPA"})
    assert updated.status_code == 200
    assert updated.json()["salary_range"] == "10-14 LPA"

    deleted = client.delete(f"/api/jobs/{job_id}", headers=hr_headers)
    assert deleted.status_code == 200


def test_stale_jwt_role_claim_is_rejected():
    username = f"stale_role_{uuid.uuid4().hex[:8]}"
    stale_token = _register(username, "candidate")

    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).one()
        user.role = "hr"
        session.add(user)
        session.commit()

    stale_response = client.get("/api/candidates", headers={"Authorization": f"Bearer {stale_token}"})
    assert stale_response.status_code == 401

    fresh_login = client.post("/api/auth/login", json={"username": username, "password": "Pass123!"})
    assert fresh_login.status_code == 200
    fresh_response = client.get(
        "/api/candidates",
        headers={"Authorization": f"Bearer {fresh_login.json()['access_token']}"},
    )
    assert fresh_response.status_code == 200


def test_employee_profiles_are_hr_or_admin_only():
    hr_token = _register(f"hr_{uuid.uuid4().hex[:8]}", "hr")
    manager_token = _register(f"manager_{uuid.uuid4().hex[:8]}", "manager")
    employee_username = f"employee_{uuid.uuid4().hex[:8]}"

    with Session(engine) as session:
        employee_user = User(
            username=employee_username,
            hashed_password="not-used",
            role="employee",
        )
        session.add(employee_user)
        session.commit()
        session.refresh(employee_user)
        session.add(
            Employee(
                user_id=employee_user.id,
                employee_code=f"EMP-{uuid.uuid4().hex[:6]}",
                department="People",
                designation="Coordinator",
                salary=50000,
            )
        )
        session.commit()

    manager_response = client.get("/api/employees", headers={"Authorization": f"Bearer {manager_token}"})
    assert manager_response.status_code == 403

    hr_response = client.get("/api/employees", headers={"Authorization": f"Bearer {hr_token}"})
    assert hr_response.status_code == 200
    assert any(employee["username"] == employee_username for employee in hr_response.json())


def test_candidate_application_flow_and_rbac(monkeypatch):
    monkeypatch.setattr(
        applications_route,
        "extract_text_from_pdf",
        lambda path: (
            "Summary\nBackend developer.\nSkills\nPython, FastAPI, SQL\n"
            "Experience\nBuilt hiring workflow tools."
        ),
    )

    candidate_token = _register(f"candidate_{uuid.uuid4().hex[:8]}", "candidate")
    hr_token = _register(f"hr_{uuid.uuid4().hex[:8]}", "hr")
    candidate_headers = {"Authorization": f"Bearer {candidate_token}"}
    hr_headers = {"Authorization": f"Bearer {hr_token}"}

    created = client.post(
        "/api/jobs",
        headers=hr_headers,
        json={"title": "API Engineer", "description": "Own Day 1 APIs."},
    )
    job_id = created.json()["id"]

    applied = client.post(
        "/api/applications/apply",
        headers=candidate_headers,
        data={"job_id": str(job_id)},
        files={"file": ("resume.pdf", b"%PDF-1.4 fake pdf", "application/pdf")},
    )
    assert applied.status_code == 201, applied.text
    assert applied.json()["application"]["status"] == "Applied"

    mine = client.get("/api/applications/me", headers=candidate_headers)
    assert mine.status_code == 200
    assert len(mine.json()) == 1
    assert "resume_text" not in mine.json()[0]

    all_applications = client.get("/api/applications", headers=hr_headers)
    assert all_applications.status_code == 200
    assert len(all_applications.json()) >= 1
    assert "FastAPI" in all_applications.json()[0]["resume_text"]


    candidate_denied = client.get("/api/candidates", headers=candidate_headers)
    assert candidate_denied.status_code == 403

    hr_denied = client.get("/api/applications/me", headers=hr_headers)
    assert hr_denied.status_code == 403


def test_application_ai_analysis_and_ranking(monkeypatch):
    monkeypatch.setattr(
        applications_route,
        "extract_text_from_pdf",
        lambda path: (
            "Summary\nBackend developer.\nSkills\nPython, FastAPI, SQL, Docker\n"
            "Projects\nBuilt recruitment workflow APIs."
        ),
    )
    monkeypatch.setattr(
        recruitment_ai,
        "_run_crewai_analysis",
        lambda resume_text, job: {
            "fit_score": 82,
            "recommendation": "Recommended",
            "summary": "Strong backend fit for this opening.",
            "strengths": ["Matches FastAPI and SQL requirements."],
            "weaknesses": ["Docker depth should be validated."],
            "missing_skills": [],
            "observations": ["Resume is aligned with backend API work."],
            "interview_prep": {
                "technical_questions": ["Explain a FastAPI service you built."],
                "behavioral_questions": ["Describe a time you handled ambiguity."],
                "probing_areas": ["API ownership", "SQL schema design"],
            },
        },
    )

    candidate_token = _register(f"candidate_{uuid.uuid4().hex[:8]}", "candidate")
    hr_token = _register(f"hr_{uuid.uuid4().hex[:8]}", "hr")
    candidate_headers = {"Authorization": f"Bearer {candidate_token}"}
    hr_headers = {"Authorization": f"Bearer {hr_token}"}

    created = client.post(
        "/api/jobs",
        headers=hr_headers,
        json={
            "title": "Backend Developer",
            "description": "Build recruitment intelligence APIs.",
            "required_skills": "Python, FastAPI, SQL, Docker",
        },
    )
    job_id = created.json()["id"]

    applied = client.post(
        "/api/applications/apply",
        headers=candidate_headers,
        data={"job_id": str(job_id)},
        files={"file": ("resume.pdf", b"%PDF-1.4 fake pdf", "application/pdf")},
    )
    assert applied.status_code == 201, applied.text
    application = applied.json()["application"]
    
    # Query applications list for HR to get the populated AI analysis (since it runs in background)
    apps = client.get("/api/applications", headers=hr_headers)
    assert apps.status_code == 200
    app_payload = [a for a in apps.json() if a["id"] == application["id"]][0]
    assert app_payload["ai_analysis"]["fit_score"] == 82
    assert app_payload["ai_analysis"]["recommendation"] == "Recommended"
    assert app_payload["ai_analysis"]["interview_prep"]["technical_questions"]


    refreshed = client.post(f"/api/applications/{application['id']}/analyze", headers=hr_headers)
    assert refreshed.status_code == 200
    assert refreshed.json()["application"]["ai_analysis"]["status"] == "completed"

    rankings = client.get(f"/api/applications/rankings/{job_id}", headers=hr_headers)
    assert rankings.status_code == 200
    assert rankings.json()["rankings"][0]["rank"] == 1
    assert rankings.json()["rankings"][0]["analysis"]["fit_score"] == 82


def test_day3_candidate_hire_to_employee_portal_flow(monkeypatch):
    monkeypatch.setattr(
        applications_route,
        "extract_text_from_pdf",
        lambda path: (
            "Summary\nBackend developer.\nSkills\nPython, FastAPI, SQL, Docker\n"
            "Projects\nBuilt employee lifecycle workflow APIs."
        ),
    )
    monkeypatch.setattr(
        recruitment_ai,
        "_run_crewai_analysis",
        lambda resume_text, job: {
            "fit_score": 90,
            "recommendation": "Strongly Recommended",
            "summary": "Excellent fit.",
            "strengths": ["Strong Python and FastAPI experience."],
            "weaknesses": [],
            "missing_skills": [],
            "observations": ["Ready for hiring workflow."],
            "interview_prep": {
                "technical_questions": ["Explain your FastAPI architecture."],
                "behavioral_questions": ["Describe ownership."],
                "probing_areas": ["API depth"],
            },
        },
    )

    candidate_username = f"candidate_{uuid.uuid4().hex[:8]}"
    candidate_token = _register(candidate_username, "candidate")
    hr_token = _register(f"hr_{uuid.uuid4().hex[:8]}", "hr")
    candidate_headers = {"Authorization": f"Bearer {candidate_token}"}
    hr_headers = {"Authorization": f"Bearer {hr_token}"}

    created = client.post(
        "/api/jobs",
        headers=hr_headers,
        json={
            "title": "Backend Developer",
            "description": "Build TalentForge HRMS APIs.",
            "required_skills": "Python, FastAPI, SQL",
            "department": "Engineering",
        },
    )
    assert created.status_code == 201, created.text
    job_id = created.json()["id"]

    applied = client.post(
        "/api/applications/apply",
        headers=candidate_headers,
        data={"job_id": str(job_id)},
        files={"file": ("resume.pdf", b"%PDF-1.4 fake pdf", "application/pdf")},
    )
    assert applied.status_code == 201, applied.text
    application_id = applied.json()["application"]["id"]

    hired = client.post(
        f"/api/applications/{application_id}/hire",
        headers=hr_headers,
        json={"department": "Engineering", "designation": "Backend Developer", "salary": 75000},
    )
    assert hired.status_code == 201, hired.text
    assert hired.json()["application"]["status"] == "Hired"
    assert hired.json()["employee"]["designation"] == "Backend Developer"
    assert "Python" in hired.json()["employee"]["skills"]

    stale_candidate = client.get("/api/applications/me", headers=candidate_headers)
    assert stale_candidate.status_code == 401

    login = client.post("/api/auth/login", json={"username": candidate_username, "password": "Pass123!"})
    assert login.status_code == 200
    assert login.json()["role"] == "employee"
    employee_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    denied_management = client.get("/api/applications", headers=employee_headers)
    assert denied_management.status_code == 403

    dashboard = client.get("/api/employees/dashboard", headers=employee_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["employee"]["employee_code"]

    check_in = client.post("/api/employees/attendance/check-in", headers=employee_headers)
    assert check_in.status_code == 201
    assert check_in.json()["attendance"]["status"] == "Checked In"

    check_out = client.post("/api/employees/attendance/check-out", headers=employee_headers)
    assert check_out.status_code == 200
    assert check_out.json()["attendance"]["status"] == "Completed"

    leave = client.post(
        "/api/employees/leave",
        headers=employee_headers,
        json={
            "leave_type": "Annual",
            "start_date": "2026-06-10",
            "end_date": "2026-06-11",
            "reason": "Family event",
        },
    )
    assert leave.status_code == 201, leave.text
    leave_id = leave.json()["leave"]["id"]

    leave_list = client.get("/api/employees/leave", headers=hr_headers)
    assert leave_list.status_code == 200
    assert any(item["id"] == leave_id for item in leave_list.json())

    decision = client.post(
        f"/api/employees/leave/{leave_id}/decision",
        headers=hr_headers,
        json={"status": "Approved", "manager_note": "Enjoy your leave."},
    )
    assert decision.status_code == 200
    assert decision.json()["leave"]["status"] == "Approved"

    skill_gap = client.post(
        "/api/employees/skill-gap/me/analyze",
        headers=employee_headers,
        json={"role_expectations": "Python FastAPI SQL Kubernetes"},
    )
    assert skill_gap.status_code == 200
    assert "Kubernetes".lower() in [item.lower() for item in skill_gap.json()["analysis"]["missing_skills"]]

    assistant = client.post(
        "/api/employees/assistant",
        headers=employee_headers,
        json={"question": "How do I apply for leave?"},
    )
    assert assistant.status_code == 200
    assert "leave" in assistant.json()["answer"].lower()


def test_candidates_and_managers_cannot_use_employee_self_service():
    candidate_token = _register(f"candidate_{uuid.uuid4().hex[:8]}", "candidate")
    manager_token = _register(f"manager_{uuid.uuid4().hex[:8]}", "manager")

    candidate_response = client.get(
        "/api/employees/dashboard",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert candidate_response.status_code == 403

    manager_response = client.post(
        "/api/employees/attendance/check-in",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert manager_response.status_code == 403


def test_employee_directory_routing():
    hr_token = _register(f"hr_{uuid.uuid4().hex[:8]}", "hr")
    response = client.get(
        "/api/employees/directory",
        headers={"Authorization": f"Bearer {hr_token}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_candidate_can_start_and_answer_mock_interview(monkeypatch):
    def fake_start(**kwargs):
        return {
            "question": "Tell me about yourself and why you're a good fit for this Software Engineer role.",
            "focus_area": "general role fit",
            "focus_type": "general",
            "interviewer_signal": "Be specific.",
            "pressure_level": "medium",
            "answer_expectation": "Use a concrete example.",
        }

    def fake_answer(**kwargs):
        return {
            "next_question": "Describe one technical tradeoff you made.",
            "evaluation": {
                "score": 7,
                "what_went_well": ["Specific example"],
                "what_was_missing": ["More metrics"],
                "how_to_improve": ["Quantify the outcome"],
                "next_focus": "technical tradeoffs",
            },
            "focus_area": "technical tradeoffs",
            "focus_type": "domain",
            "new_difficulty": 6,
            "answer_expectation": "Explain the decision and result.",
        }

    monkeypatch.setitem(
        sys.modules,
        "crew",
        types.SimpleNamespace(run_interview_start=fake_start, run_interview_answer=fake_answer),
    )

    token = _register(f"candidate_{uuid.uuid4().hex[:8]}", "candidate")
    headers = {"Authorization": f"Bearer {token}"}

    started = client.post(
        "/api/interview/start",
        headers=headers,
        json={"role": "Software Engineer", "difficulty": 5},
    )
    assert started.status_code == 200, started.text
    payload = started.json()
    assert payload["session_id"]
    assert payload["question"].startswith("Tell me about yourself")
    assert payload["db_id"]

    answered = client.post(
        "/api/interview/answer",
        headers=headers,
        json={"session_id": payload["session_id"], "answer": "I built a FastAPI service and chose SQLModel for typed persistence."},
    )
    assert answered.status_code == 200, answered.text
    answer_payload = answered.json()
    assert answer_payload["next_question"] == "Describe one technical tradeoff you made."
    assert answer_payload["evaluation"]["score"] == 7
    assert answer_payload["avg_score"] == 7


def test_resume_aware_interview_uses_latest_application_resume(monkeypatch):
    resume_text = (
        "Summary\nBackend engineer focused on FastAPI services and hiring workflow automation.\n"
        "Skills\nPython, FastAPI, SQLModel, PostgreSQL, React\n"
        "Experience\nBuilt candidate screening APIs, resume analysis tools, and interview scoring dashboards."
    )
    monkeypatch.setattr(applications_route, "extract_text_from_pdf", lambda path: resume_text)
    monkeypatch.setattr(
        interview_route,
        "analyze_resume",
        lambda text, role: {
            "score": 82,
            "breakdown": {"impact": 80, "clarity": 84, "structure": 82, "ats": 86},
            "sections": [
                {
                    "section": "Experience",
                    "issues": [
                        {
                            "problem": "Needs stronger metrics",
                            "original": "Built candidate screening APIs",
                        }
                    ],
                }
            ],
        },
    )

    def fake_start(**kwargs):
        assert kwargs["resume_context"]["skills"]
        assert kwargs["weak_areas"]
        return {
            "question": "Tell me about yourself and why you're a good fit for this Backend Engineer role.",
            "focus_area": kwargs["weak_areas"][0],
            "focus_type": "weak_area",
            "answer_expectation": "Use resume evidence.",
        }

    monkeypatch.setitem(
        sys.modules,
        "crew",
        types.SimpleNamespace(run_interview_start=fake_start, run_interview_answer=lambda **kwargs: {}),
    )

    candidate_token = _register(f"candidate_{uuid.uuid4().hex[:8]}", "candidate")
    hr_token = _register(f"hr_{uuid.uuid4().hex[:8]}", "hr")
    candidate_headers = {"Authorization": f"Bearer {candidate_token}"}
    hr_headers = {"Authorization": f"Bearer {hr_token}"}

    created = client.post(
        "/api/jobs",
        headers=hr_headers,
        json={"title": "Backend Engineer", "description": "Build HRMS APIs."},
    )
    assert created.status_code == 201, created.text

    applied = client.post(
        "/api/applications/apply",
        headers=candidate_headers,
        data={"job_id": str(created.json()["id"])},
        files={"file": ("resume.pdf", b"%PDF-1.4 fake pdf", "application/pdf")},
    )
    assert applied.status_code == 201, applied.text

    started = client.post(
        "/api/interview/start-from-resume",
        headers=candidate_headers,
        json={"role": "Backend Engineer", "difficulty": 6},
    )
    assert started.status_code == 200, started.text
    payload = started.json()
    assert payload["personalized"] is True
    assert payload["resume_source"] == "application"
    assert payload["resume_score"] == 82
    assert payload["weak_areas"]


def test_interview_intelligence_compare_accepts_frontend_payload():
    candidate_username = f"candidate_{uuid.uuid4().hex[:8]}"
    _register(candidate_username, "candidate")
    hr_token = _register(f"hr_{uuid.uuid4().hex[:8]}", "hr")

    with Session(engine) as session:
        candidate_id = session.exec(select(User).where(User.username == candidate_username)).one().id

    response = client.post(
        "/api/interview/intelligence/compare",
        headers={"Authorization": f"Bearer {hr_token}"},
        json={"candidate_ids": [candidate_id]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["comparison"][0]["candidate_id"] == candidate_id
