import os
import uuid

os.environ["AUTO_CREATE_DB_SCHEMA"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-talentforge"

from fastapi.testclient import TestClient
from sqlmodel import Session, select

import src.api.routes.applications as applications_route
from src.database.connection import create_db_and_tables, engine
from src.main import app
from src.models import CandidateApplication, JobPosting, User

create_db_and_tables()
client = TestClient(app)


def _register(username: str, role: str) -> str:
    response = client.post("/api/auth/register", json={"username": username, "password": "Pass123!"})
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


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_job(hr_token: str, title: str = "Lifecycle Engineer") -> dict:
    response = client.post(
        "/api/jobs",
        headers=_headers(hr_token),
        json={
            "title": title,
            "description": "Build production lifecycle systems.",
            "required_skills": "Python, FastAPI",
            "department": "Engineering",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _apply(candidate_token: str, job_id: int):
    return client.post(
        "/api/applications/apply",
        headers=_headers(candidate_token),
        data={"job_id": str(job_id)},
        files={"file": ("resume.pdf", b"%PDF-1.4 fake pdf", "application/pdf")},
    )


def test_new_jobs_default_open_and_can_be_closed():
    hr_token = _register(f"job_life_hr_{uuid.uuid4().hex[:8]}", "hr")
    job = _create_job(hr_token)
    assert job["status"] == "OPEN"

    closed = client.post(f"/api/jobs/{job['id']}/close", headers=_headers(hr_token))
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "CLOSED"


def test_archive_job_hides_it_from_candidate_list_and_detail():
    hr_token = _register(f"job_archive_hr_{uuid.uuid4().hex[:8]}", "hr")
    candidate_token = _register(f"job_archive_candidate_{uuid.uuid4().hex[:8]}", "candidate")
    job = _create_job(hr_token, "Archive Only Role")

    archived = client.post(f"/api/jobs/{job['id']}/archive", headers=_headers(hr_token))
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "ARCHIVED"

    candidate_jobs = client.get("/api/jobs", headers=_headers(candidate_token))
    assert candidate_jobs.status_code == 200
    assert all(item["id"] != job["id"] for item in candidate_jobs.json())

    candidate_detail = client.get(f"/api/jobs/{job['id']}", headers=_headers(candidate_token))
    assert candidate_detail.status_code == 404

    hr_detail = client.get(f"/api/jobs/{job['id']}", headers=_headers(hr_token))
    assert hr_detail.status_code == 200
    assert hr_detail.json()["status"] == "ARCHIVED"


def test_candidate_cannot_apply_to_closed_job(monkeypatch):
    monkeypatch.setattr(applications_route, "extract_text_from_pdf", lambda path: "x" * 80)
    hr_token = _register(f"job_closed_hr_{uuid.uuid4().hex[:8]}", "hr")
    candidate_token = _register(f"job_closed_candidate_{uuid.uuid4().hex[:8]}", "candidate")
    job = _create_job(hr_token)
    client.post(f"/api/jobs/{job['id']}/close", headers=_headers(hr_token))

    applied = _apply(candidate_token, job["id"])
    assert applied.status_code == 409
    assert applied.json()["error"] == "Applications for this position are closed."


def test_candidate_cannot_apply_to_archived_job(monkeypatch):
    monkeypatch.setattr(applications_route, "extract_text_from_pdf", lambda path: "x" * 80)
    hr_token = _register(f"job_arch_apply_hr_{uuid.uuid4().hex[:8]}", "hr")
    candidate_token = _register(f"job_arch_apply_candidate_{uuid.uuid4().hex[:8]}", "candidate")
    job = _create_job(hr_token)
    client.post(f"/api/jobs/{job['id']}/archive", headers=_headers(hr_token))

    applied = _apply(candidate_token, job["id"])
    assert applied.status_code == 409
    assert applied.json()["error"] == "This job is no longer accepting applications."


def test_delete_empty_job_removes_job():
    hr_token = _register(f"job_delete_hr_{uuid.uuid4().hex[:8]}", "hr")
    job = _create_job(hr_token)

    deleted = client.delete(f"/api/jobs/{job['id']}", headers=_headers(hr_token))
    assert deleted.status_code == 200, deleted.text

    missing = client.get(f"/api/jobs/{job['id']}", headers=_headers(hr_token))
    assert missing.status_code == 404


def test_delete_job_with_applications_is_blocked_and_history_preserved(monkeypatch):
    monkeypatch.setattr(applications_route, "extract_text_from_pdf", lambda path: "x" * 80)
    hr_token = _register(f"job_block_hr_{uuid.uuid4().hex[:8]}", "hr")
    candidate_token = _register(f"job_block_candidate_{uuid.uuid4().hex[:8]}", "candidate")
    job = _create_job(hr_token)
    applied = _apply(candidate_token, job["id"])
    assert applied.status_code == 201, applied.text
    application_id = applied.json()["application"]["id"]

    deleted = client.delete(f"/api/jobs/{job['id']}", headers=_headers(hr_token))
    assert deleted.status_code == 409
    assert deleted.json()["error"] == (
        "This job contains applicant history and cannot be deleted. Close or archive the job instead."
    )

    with Session(engine) as session:
        assert session.get(JobPosting, job["id"]) is not None
        assert session.get(CandidateApplication, application_id) is not None


def test_lifecycle_actions_require_management_role():
    hr_token = _register(f"job_auth_hr_{uuid.uuid4().hex[:8]}", "hr")
    candidate_token = _register(f"job_auth_candidate_{uuid.uuid4().hex[:8]}", "candidate")
    manager_token = _register(f"job_auth_manager_{uuid.uuid4().hex[:8]}", "manager")
    job = _create_job(hr_token)

    candidate_close = client.post(f"/api/jobs/{job['id']}/close", headers=_headers(candidate_token))
    assert candidate_close.status_code == 403

    manager_close = client.post(f"/api/jobs/{job['id']}/close", headers=_headers(manager_token))
    assert manager_close.status_code == 200

    candidate_delete = client.delete(f"/api/jobs/{job['id']}", headers=_headers(candidate_token))
    assert candidate_delete.status_code == 403
