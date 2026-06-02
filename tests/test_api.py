import os
import uuid
from pathlib import Path

Path("data").mkdir(exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{(Path('data') / f'test_day1_{uuid.uuid4().hex}.db').as_posix()}"
os.environ["AUTO_CREATE_DB_SCHEMA"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-talentforge"

from fastapi.testclient import TestClient

from src.main import app
import src.api.routes.applications as applications_route

client = TestClient(app)


def _register(username: str, role: str) -> str:
    response = client.post(
        "/api/auth/register",
        json={"username": username, "password": "Pass123!", "role": role},
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def test_register_and_login_returns_role():
    username = f"candidate_{uuid.uuid4().hex[:8]}"
    token = _register(username, "candidate")
    assert token

    response = client.post("/api/auth/login", json={"username": username, "password": "Pass123!"})
    assert response.status_code == 200
    assert response.json()["role"] == "candidate"


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
