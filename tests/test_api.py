import os
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
import src.services.recruitment_ai as recruitment_ai
from src.database.connection import create_db_and_tables, engine
from src.models import User

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
    assert "FastAPI" in mine.json()[0]["resume_text"]

    all_applications = client.get("/api/applications", headers=hr_headers)
    assert all_applications.status_code == 200
    assert len(all_applications.json()) >= 1

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
    assert application["ai_analysis"]["fit_score"] == 82
    assert application["ai_analysis"]["recommendation"] == "Recommended"
    assert application["ai_analysis"]["interview_prep"]["technical_questions"]

    refreshed = client.post(f"/api/applications/{application['id']}/analyze", headers=hr_headers)
    assert refreshed.status_code == 200
    assert refreshed.json()["application"]["ai_analysis"]["status"] == "completed"

    rankings = client.get(f"/api/applications/rankings/{job_id}", headers=hr_headers)
    assert rankings.status_code == 200
    assert rankings.json()["rankings"][0]["rank"] == 1
    assert rankings.json()["rankings"][0]["analysis"]["fit_score"] == 82
