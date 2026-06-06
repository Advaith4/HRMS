import os
import sys
import types
import uuid
import json

os.environ["AUTO_CREATE_DB_SCHEMA"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-talentforge"

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from src.main import app
import src.api.routes.applications as applications_route
import src.api.routes.interview as interview_route
from src.database.connection import create_db_and_tables, engine
from src.models import User, CandidateApplication, InterviewSession, JobPosting, HRNotification

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

def test_should_end_interview_early():
    from src.api.routes.interview import _should_end_interview_early

    # < 5 answers should not end early
    assert not _should_end_interview_early(4, [8, 8, 8])

    # 5 answers but inconsistent score should not end early
    assert not _should_end_interview_early(5, [8, 4, 9, 5, 7])

    # 5 answers with consistently excellent scores should end early
    assert _should_end_interview_early(5, [6, 8, 8, 8, 8])  # last 3 are all >= 7, avg = 8.0, range = 0

    # 5 answers with consistently poor scores should end early
    assert _should_end_interview_early(5, [6, 8, 3, 3, 3])  # last 3 are all <= 5, avg = 3.0, range = 0

    # 15 answers should always end early
    assert _should_end_interview_early(15, [6]*15)

def test_start_interview_for_application_and_violations(monkeypatch):
    monkeypatch.setattr(
        applications_route,
        "extract_text_from_pdf",
        lambda path: (
            "Summary\nTalented Backend developer.\nSkills\nPython, FastAPI, SQL, Docker\n"
            "Projects\nBuilt recruitment workflow APIs."
        ),
    )

    def fake_start(**kwargs):
        return {
            "question": "Tell me about yourself and your experience building APIs with FastAPI.",
            "focus_area": "general role fit",
            "focus_type": "general",
            "interviewer_signal": "Be specific.",
            "pressure_level": "medium",
            "answer_expectation": "Use a concrete example.",
        }

    fake_crew = types.SimpleNamespace(
        run_interview_start=fake_start,
        run_interview_answer=lambda **kwargs: {}
    )
    monkeypatch.setitem(sys.modules, "crew", fake_crew)

    candidate_token = _register(f"cand_{uuid.uuid4().hex[:8]}", "candidate")
    hr_token = _register(f"hr_{uuid.uuid4().hex[:8]}", "hr")
    
    candidate_headers = {"Authorization": f"Bearer {candidate_token}"}
    hr_headers = {"Authorization": f"Bearer {hr_token}"}

    # 1. Create a job posting
    job_res = client.post(
        "/api/jobs",
        headers=hr_headers,
        json={"title": "FastAPI Developer", "description": "Build high-throughput APIs."},
    )
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # 2. Apply to the job
    app_res = client.post(
        "/api/applications/apply",
        headers=candidate_headers,
        data={"job_id": str(job_id)},
        files={"file": ("resume.pdf", b"%PDF-1.4 fake pdf", "application/pdf")},
    )
    assert app_res.status_code == 201
    app_id = app_res.json()["application"]["id"]

    # 3. Start the interview for the application
    start_res = client.post(
        "/api/interview/start-for-application",
        headers=candidate_headers,
        json={"application_id": app_id},
    )
    assert start_res.status_code == 200, start_res.text
    session_data = start_res.json()
    assert session_data["session_id"]
    assert session_data["question"] == "Tell me about yourself and your experience building APIs with FastAPI."
    assert session_data["role"] == "FastAPI Developer"

    session_id = session_data["session_id"]

    # 4. Starting again should resume it
    resume_res = client.post(
        "/api/interview/start-for-application",
        headers=candidate_headers,
        json={"application_id": app_id},
    )
    assert resume_res.status_code == 200
    assert resume_res.json()["session_id"] == session_id
    assert resume_res.json()["status"] == "active"

    # 5. Add a violation
    v1_res = client.post(
        f"/api/interview/{session_id}/violation",
        headers=candidate_headers,
        json={"violation_type": "fullscreen_exit", "detail": "Exited full screen mode."},
    )
    assert v1_res.status_code == 200
    assert v1_res.json()["violations_count"] == 1
    assert v1_res.json()["cancelled"] is False

    # 6. Add a second violation
    v2_res = client.post(
        f"/api/interview/{session_id}/violation",
        headers=candidate_headers,
        json={"violation_type": "tab_switch", "detail": "Switched tabs."},
    )
    assert v2_res.status_code == 200
    assert v2_res.json()["violations_count"] == 2
    assert v2_res.json()["cancelled"] is False

    # 7. Add a third violation -> should cancel session and notify HR
    v3_res = client.post(
        f"/api/interview/{session_id}/violation",
        headers=candidate_headers,
        json={"violation_type": "camera_off", "detail": "Camera disabled."},
    )
    assert v3_res.status_code == 200
    assert v3_res.json()["violations_count"] == 3
    assert v3_res.json()["cancelled"] is True
    assert "cancellation_reason" in v3_res.json()

    # Verify database state for the cancelled session
    with Session(engine) as session:
        db_sess = session.exec(select(InterviewSession).where(InterviewSession.session_token == session_id)).one()
        assert db_sess.status == "cancelled"
        assert db_sess.violations_count == 3
        
        # Verify HR notification was dispatched
        notif = session.exec(select(HRNotification).where(HRNotification.event_type == "interview_cancelled")).first()
        assert notif
        assert "FastAPI Developer" in notif.message
        assert "cancelled" in notif.message

    # 8. Start again when cancelled -> should return status cancelled
    cancelled_start_res = client.post(
        "/api/interview/start-for-application",
        headers=candidate_headers,
        json={"application_id": app_id},
    )
    assert cancelled_start_res.status_code == 200
    assert cancelled_start_res.json()["status"] == "cancelled"
    assert "violations" in cancelled_start_res.json()["message"] or "cancelled" in cancelled_start_res.json()["message"]
