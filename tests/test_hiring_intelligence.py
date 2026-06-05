import os
import sys
import uuid
import json
from pathlib import Path

# Set up environment and DB for tests
Path("data").mkdir(exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{(Path('data') / f'test_hiring_{uuid.uuid4().hex}.db').as_posix()}"
os.environ["AUTO_CREATE_DB_SCHEMA"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-talentforge"

from fastapi.testclient import TestClient
from sqlmodel import Session, select
import litellm
import pytest

from src.main import app
from src.database.connection import create_db_and_tables, engine
from src.models import User, InterviewSession, CandidateApplication, JobPosting, Resume
from src.services.hiring_intelligence import compile_hiring_intelligence, calculate_benchmarking
import src.api.routes.interview as interview_route

create_db_and_tables()
client = TestClient(app)

class MockMessage:
    def __init__(self, content):
        self.content = content

class MockChoice:
    def __init__(self, content):
        self.message = MockMessage(content)

class MockCompletionResponse:
    def __init__(self, content):
        self.choices = [MockChoice(content)]

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

def test_hiring_intelligence_compilation_and_storage(monkeypatch):
    # Mock LLM API call
    mock_json = {
        "competency_scores": {
            "technicalDepth": 8.5,
            "problemSolving": 8.0,
            "communication": 9.0,
            "leadership": 7.0,
            "systemDesign": 8.5,
            "confidence": 9.0,
            "domainKnowledge": 8.5,
            "explanations": {
                "technicalDepth": "Strong depth.",
                "problemSolving": "Strong problem solving.",
                "communication": "Strong communication.",
                "leadership": "Good leadership potential.",
                "systemDesign": "Solid system design tradeoffs.",
                "confidence": "Highly confident candidate.",
                "domainKnowledge": "Strong alignment with role."
            },
            "overall_confidence": 8.5
        },
        "job_fit_report": {
            "jobFit": 88,
            "strengths": ["FastAPI", "Python", "SQLModel"],
            "weaknesses": ["None"],
            "recommendedRole": "Senior Software Engineer",
            "riskLevel": "Low"
        },
        "communication_metrics": {
            "clarity": 9.0,
            "vocabulary": 8.5,
            "confidence": 9.0,
            "conciseness": 8.0,
            "communicationEffectiveness": 8.5
        },
        "behavioral_report": {
            "categories": {
                "Technical": 8.5,
                "Behavioral": 8.0,
                "Situational": 8.5,
                "Leadership": 7.0
            }
        },
        "hiring_risks": [
            {
                "risk": "Short length of tenure",
                "evidence": "6 months at company X."
            }
        ],
        "timeline_replay": [
            {
                "turn": 1,
                "phase": "Introduction",
                "question": "Tell me about yourself.",
                "answer": "I am a backend developer.",
                "score": 8.0,
                "competencyImpact": {
                    "technicalDepth": 0.5,
                    "communication": 0.3
                },
                "credibilityImpact": {
                    "claim": "FastAPI",
                    "status": "supported"
                }
            }
        ]
    }
    
    monkeypatch.setattr(
        litellm,
        "completion",
        lambda **kwargs: MockCompletionResponse(json.dumps(mock_json))
    )

    token = _register(f"candidate_{uuid.uuid4().hex[:8]}", "candidate")
    headers = {"Authorization": f"Bearer {token}"}

    # Start session and add completed messages
    with Session(engine) as session_db:
        user = session_db.exec(select(User)).first()
        job = JobPosting(title="Senior Dev", description="Write code", required_skills="FastAPI", created_by=user.id)
        session_db.add(job)
        session_db.commit()
        session_db.refresh(job)

        app_rec = CandidateApplication(candidate_user_id=user.id, job_id=job.id, resume_text="FastAPI Backend Engineer", status="Applied")
        session_db.add(app_rec)
        session_db.commit()
        session_db.refresh(app_rec)

        resume = Resume(user_id=user.id, raw_text="FastAPI Backend Engineer")
        session_db.add(resume)
        session_db.commit()

        # Create session record
        messages = [
            {"role": "ai", "content": "Tell me about yourself.", "phase": "Introduction"},
            {"role": "user", "content": "I work with Python and FastAPI.", "score": 8, "phase": "Introduction"},
            {"role": "feedback", "content": "Score: 8/10", "score": 8, "phase": "Introduction"}
        ]
        sess = InterviewSession(
            user_id=user.id,
            session_token=uuid.uuid4().hex,
            role="Senior Dev",
            difficulty=5,
            training_mode="adaptive",
            interviewer_persona="balanced",
            application_id=app_rec.id,
            status="completed",
            messages=json.dumps(messages),
            avg_score=8.0
        )
        session_db.add(sess)
        session_db.commit()
        session_db.refresh(sess)
        sess_id = sess.id

    # Compile hiring intelligence
    compile_hiring_intelligence(sess_id)

    # Fetch and assert
    with Session(engine) as session_db:
        updated_sess = session_db.get(InterviewSession, sess_id)
        assert updated_sess.status == "analyzed"
        assert updated_sess.competency_scores is not None
        assert updated_sess.job_fit_report is not None
        assert updated_sess.communication_metrics is not None
        assert updated_sess.behavioral_report is not None
        assert updated_sess.hiring_risks is not None
        assert updated_sess.timeline_replay is not None
        assert updated_sess.benchmarking is not None

        # Verify parsed structure
        comp = json.loads(updated_sess.competency_scores)
        assert comp["technicalDepth"] == 8.5
        assert comp["explanations"]["technicalDepth"] == "Strong depth."

        fit = json.loads(updated_sess.job_fit_report)
        assert fit["jobFit"] == 88
        assert fit["riskLevel"] == "Low"

        comm = json.loads(updated_sess.communication_metrics)
        assert comm["clarity"] == 9.0
        assert comm["fillerWords"] is not None

        bench = json.loads(updated_sess.benchmarking)
        # 1 completed candidate should flag insufficient data
        assert bench["insufficient_data"] is True


def test_benchmarking_percentile_calculations():
    with Session(engine) as session_db:
        # Create unique job
        job = JobPosting(title="Data Eng", description="SQL work", required_skills="SQL", created_by=1)
        session_db.add(job)
        session_db.commit()
        session_db.refresh(job)

        # Create 3 users and applications
        users = []
        apps = []
        for i in range(4):
            u = User(username=f"bench_cand_{uuid.uuid4().hex[:6]}", hashed_password="hashedpassword", role="candidate")
            session_db.add(u)
            session_db.commit()
            session_db.refresh(u)
            users.append(u)

            a = CandidateApplication(candidate_user_id=u.id, job_id=job.id, resume_text="Data Analyst with SQL", status="Applied")
            session_db.add(a)
            session_db.commit()
            session_db.refresh(a)
            apps.append(a)

        # Create session records for 3 candidates (1 remains uncompleted)
        sessions_list = []
        scores = [90.0, 80.0, 70.0]
        for idx in range(3):
            s = InterviewSession(
                user_id=users[idx].id,
                session_token=uuid.uuid4().hex,
                role="Data Eng",
                application_id=apps[idx].id,
                status="completed",
                avg_score=scores[idx] / 10.0
            )
            session_db.add(s)
            session_db.commit()
            session_db.refresh(s)
            sessions_list.append(s)

        # Verify 3 completed sessions for this job. Total candidates is 3.
        # Candidate 1: score = 90.0. Rank = 1. Percentile = 100%.
        bench_1 = calculate_benchmarking(session_db, sessions_list[0], apps[0], 90.0)
        assert bench_1["insufficient_data"] is False
        assert bench_1["ranking"] == 1
        assert bench_1["percentile"] == 100.0

        # Candidate 3: score = 70.0. Rank = 3. Percentile = 33.3%.
        bench_3 = calculate_benchmarking(session_db, sessions_list[2], apps[2], 70.0)
        assert bench_3["insufficient_data"] is False
        assert bench_3["ranking"] == 3
        assert bench_3["percentile"] == 33.3


def test_claim_verification_depth_and_phase_freeze(monkeypatch):
    import types
    # Mock start and answer
    monkeypatch.setitem(
        sys.modules,
        "crew",
        types.SimpleNamespace(
            run_interview_start=lambda **kwargs: {"question": "Intro question", "focus_area": "general", "focus_type": "general"},
            run_interview_answer=lambda **kwargs: {"next_question": "Next question", "evaluation": {"score": 7}, "focus_area": "FastAPI", "focus_type": "domain"}
        )
    )

    username = f"candidate_{uuid.uuid4().hex[:8]}"
    token = _register(username, "candidate")
    headers = {"Authorization": f"Bearer {token}"}

    with Session(engine) as session_db:
        # Create resume that mentions "FastAPI" and "React"
        user = session_db.exec(select(User).where(User.username == username)).one()
        resume = Resume(user_id=user.id, raw_text="Experienced in React, Python, and FastAPI backend developments.")
        session_db.add(resume)
        session_db.commit()

    # Start session
    start_resp = client.post(
        "/api/interview/start-from-resume",
        headers=headers,
        json={"role": "Backend Engineer", "difficulty": 5}
    )
    assert start_resp.status_code == 200
    sess_id = start_resp.json()["session_id"]
    
    # 1. First turn: submit answer that mentions the "React" claim
    # This should trigger claim verification: React
    ans_1 = client.post(
        "/api/interview/answer",
        headers=headers,
        json={"session_id": sess_id, "answer": "I built several applications using React frontend."}
    )
    assert ans_1.status_code == 200
    p_context_1 = ans_1.json().get("personalization_context", {})
    # Active claim verification is triggered
    assert p_context_1.get("verification_active") is True
    assert p_context_1.get("current_verification_claim") == "React"
    assert p_context_1.get("verification_depth") == 0
    # Phase is frozen (e.g. still at introduction / same round)
    assert ans_1.json().get("phase") == "Introduction"

    # 2. Second turn: answer follow-up 1
    # This advances verification depth to 1
    ans_2 = client.post(
        "/api/interview/answer",
        headers=headers,
        json={"session_id": sess_id, "answer": "I used state management and hooks in React."}
    )
    p_context_2 = ans_2.json().get("personalization_context", {})
    assert p_context_2.get("verification_active") is True
    assert p_context_2.get("current_verification_claim") == "React"
    assert p_context_2.get("verification_depth") == 1
    # Phase still frozen
    assert ans_2.json().get("phase") == "Introduction"

    # 3. Third turn: answer follow-up 2
    # Since depth is 1, answering this completes turn 2 (from perspective of follow-ups)
    # Verification should deactivate, and phase progression should resume
    ans_3 = client.post(
        "/api/interview/answer",
        headers=headers,
        json={"session_id": sess_id, "answer": "I optimized renders using useMemo and useCallback."}
    )
    p_context_3 = ans_3.json().get("personalization_context", {})
    # Verification active is False
    assert p_context_3.get("verification_active") is False
    assert p_context_3.get("current_verification_claim") is None
    # Claim React is verified
    assert "React" in p_context_3.get("verified_claims", [])
    # Phase progression resumes to next phase (Resume Deep Dive)
    assert ans_3.json().get("phase") == "Resume Deep Dive"
