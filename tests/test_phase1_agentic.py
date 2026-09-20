"""
tests/test_phase1_agentic.py
Phase 1: Agentic AI Foundations Comprehensive Test Suite.
Tests Planner Agent DAG, Validator Reflection Loop, Resilience (Retry & Timeouts),
Dual-Tier Memory, HITL Governance, and Request Tracing.
"""
import asyncio
import os
import time
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

os.environ["AUTO_CREATE_DB_SCHEMA"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-talentforge"

from src.core.logging_middleware import RequestTracingMiddleware, log_agent_execution
from src.core.memory import ShortTermWorkingMemory, working_memory
from src.core.resilience import (
    ErrorTaxonomy,
    ResilienceException,
    exponential_backoff_retry,
    with_async_timeout,
)
from src.database.connection import create_db_and_tables, engine
from src.main import app
from src.models import (
    ApplicationAIAnalysis,
    AuditLog,
    CandidateApplication,
    JobPosting,
    User,
)
from src.services.planner_agent import plan_recruitment_workflow
from src.services.recruitment_ai import analyze_application
from src.services.validator_agent import validate_evaluation_payload

create_db_and_tables()
client = TestClient(app)


def _register(username: str, role: str) -> str:
    client.post("/api/auth/register", json={"username": username, "password": "Pass123!"})
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if user:
            user.role = role
            session.add(user)
            session.commit()
    login = client.post("/api/auth/login", json={"username": username, "password": "Pass123!"})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_planner_agent_generates_valid_dag_before_execution():
    """Task 1.1: Verify Planner Agent emits ordered execution steps before worker agents."""
    job_title = "Senior Python AI Engineer"
    job_desc = "Lead development of autonomous multi-agent HRMS microservices using FastAPI, CrewAI, and LangChain."
    required_skills = "Python, FastAPI, CrewAI, ChromaDB, PostgreSQL, Docker"
    resume_text = (
        "Alice Smith - Senior AI Engineer with 6 years of experience building Python and FastAPI microservices. "
        "Proficient in CrewAI, vector databases (ChromaDB), Docker, and PostgreSQL."
    )

    plan = plan_recruitment_workflow(
        job_title=job_title,
        job_description=job_desc,
        required_skills=required_skills,
        resume_text=resume_text,
        request_id="req-test-planner-1",
    )

    assert plan.job_title == job_title
    assert plan.estimated_complexity in {"medium", "high"}
    assert len(plan.steps) == 4
    # Ensure step 1 is Planner and final step is Validator
    assert plan.steps[0].agent_name == "PlannerAgent"
    assert plan.steps[-1].agent_name == "ValidatorAgent"
    assert [s.step_number for s in plan.steps] == [1, 2, 3, 4]


def test_validator_agent_confidence_scoring_and_reflection():
    """Task 1.2: Verify Validator Agent confidence scoring and retry triggering."""
    resume_text = "Experienced Python developer with 4 years in backend API design and SQLite."
    
    # 1. High-confidence, well-grounded evaluation
    valid_eval = {
        "fit_score": 85,
        "recommendation": "Recommended",
        "strengths": ["Shows evidence for Python developer", "4 years backend API design"],
        "weaknesses": ["No explicit cloud deployment mentioned"],
        "missing_skills": ["Docker", "Kubernetes"],
    }
    result_valid = validate_evaluation_payload(
        resume_text=resume_text,
        job_title="Python Developer",
        required_skills="Python, SQLite",
        evaluation=valid_eval,
        iteration=1,
    )
    assert result_valid.is_valid is True
    assert result_valid.confidence_score >= 0.75
    assert result_valid.retry_recommended is False
    assert result_valid.hallucination_detected is False

    # 2. Low-confidence, hallucinated evaluation (claims skills not in resume)
    hallucinated_eval = {
        "fit_score": 95,
        "recommendation": "Strongly Recommended",
        "strengths": [
            "Expertise in Quantum Computing and Rust kernel programming",
            "Extensive experience leading aerospace avionics teams",
            "Advanced biotechnology genetic sequencing expertise",
        ],
        "weaknesses": [],
        "missing_skills": [],
    }
    result_hallucinated = validate_evaluation_payload(
        resume_text=resume_text,
        job_title="Python Developer",
        required_skills="Python, SQLite",
        evaluation=hallucinated_eval,
        iteration=1,
    )
    assert result_hallucinated.confidence_score < 0.75
    assert result_hallucinated.retry_recommended is True
    assert result_hallucinated.hallucination_detected is True


def test_exponential_backoff_retry_mechanism():
    """Task 1.3: Verify exponential backoff retries transient failures and succeeds."""
    attempts = 0

    @exponential_backoff_retry(max_retries=3, initial_delay=0.05, backoff_factor=1.5)
    def flaky_llm_call():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("Simulated Groq 429 Rate Limit / Network Hiccup")
        return {"status": "success", "content": "LLM output generated after backoff"}

    start_time = time.perf_counter()
    result = flaky_llm_call()
    duration = time.perf_counter() - start_time

    assert attempts == 3
    assert result["status"] == "success"
    assert duration >= 0.05


def test_async_timeout_handling():
    """Task 1.4: Verify timeout deadline returns fallback or raises resilience exception."""
    async def slow_llm_call():
        await asyncio.sleep(0.5)
        return {"result": "too slow"}

    async def run_timeout_test():
        fallback = {"status": "fallback_applied", "fit_score": 50}
        return await with_async_timeout(
            slow_llm_call(),
            timeout_seconds=0.05,
            fallback_value=fallback,
        )

    result = asyncio.run(run_timeout_test())
    assert result == {"status": "fallback_applied", "fit_score": 50}


def test_short_term_working_memory():
    """Task 1.6: Verify working memory buffers intermediate agent execution traces."""
    mem = ShortTermWorkingMemory(capacity=10)
    session_id = "sess-test-123"

    mem.set_context(session_id, "current_job", "ML Engineer")
    mem.append_step(session_id, "PlannerAgent", "PlanCreated", {"steps": 4})
    mem.append_step(session_id, "ResumeAnalystAgent", "ResumeScored", {"fit_score": 88})

    assert mem.get_context(session_id, "current_job") == "ML Engineer"
    history = mem.get_history(session_id)
    assert len(history) == 2
    assert history[0]["agent"] == "PlannerAgent"
    assert history[1]["agent"] == "ResumeAnalystAgent"


def test_hitl_approval_and_audit_trail_flow():
    """Task 1.5: Verify Human-in-the-Loop approval state machine and audit log trail."""
    suffix = uuid.uuid4().hex[:6]
    hr_token = _register(f"hr_{suffix}", "hr")
    cand_token = _register(f"cand_{suffix}", "candidate")

    # 1. Setup candidate, job, and application in DB
    with Session(engine) as session:
        hr_user = session.exec(select(User).where(User.username == f"hr_{suffix}")).one()
        candidate = session.exec(select(User).where(User.username == f"cand_{suffix}")).one()
        job = JobPosting(
            title=f"Fullstack Dev {suffix}",
            description="Develop robust web applications with React and FastAPI.",
            department="Engineering",
            required_skills="React, FastAPI, SQL",
            created_by=hr_user.id,
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        app_obj = CandidateApplication(
            candidate_user_id=candidate.id,
            job_id=job.id,
            resume_text="Fullstack Developer with 3 years experience in React frontend and FastAPI backend.",
            status="pending",
        )
        session.add(app_obj)
        session.commit()
        session.refresh(app_obj)
        app_id = app_obj.id

    # 2. Trigger AI Analysis (executes Planner -> Worker -> Validator)
    with Session(engine) as session:
        analysis = analyze_application(session, app_id, force=True)
        assert analysis.confidence_score is not None
        assert analysis.execution_plan is not None
        assert analysis.hitl_status in {"pending_hr_review", "completed"}

    # 3. HR approves via HITL endpoint
    response = client.post(
        f"/api/applications/{app_id}/hitl-decision",
        json={"decision": "approve", "new_score": 88, "notes": "Strong candidate with solid portfolio."},
        headers=_headers(hr_token),
    )
    assert response.status_code == 200, response.text
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["application_status"] == "shortlisted"
    assert res_data["analysis"]["hitl_status"] == "approved"

    # 4. Verify immutable Audit Log trail
    audit_resp = client.get(
        f"/api/applications/{app_id}/audit-trail",
        headers=_headers(hr_token),
    )
    assert audit_resp.status_code == 200, audit_resp.text
    logs = audit_resp.json()
    assert len(logs) >= 1
    assert logs[0]["action"] == "HITL_APPROVE"
    assert "Strong candidate" in logs[0]["details"]


def test_request_tracing_middleware():
    """Task 1.9: Verify RequestTracingMiddleware attaches X-Request-ID and tracks latency."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"].startswith("req-")
    assert "X-Process-Time-Ms" in response.headers

