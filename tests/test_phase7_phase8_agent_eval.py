"""
tests/test_phase7_phase8_agent_eval.py
Unit and Integration Tests for Phase 7 & 8:
Multi-Agent Workflow Benchmarking, Task Success Rates, Latency SLAs, and Human-in-the-Loop (HITL) Evaluation.
"""
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from src.main import app
from src.database.connection import create_db_and_tables, engine
from src.core.security import hash_password, create_access_token
from src.models import (
    CandidateApplication,
    HumanEvaluation,
    JobPosting,
    User,
)

create_db_and_tables()


def _seed_user(username: str, role: str) -> tuple[User, str]:
    with Session(engine) as session:
        user = User(
            username=f"{username}_{uuid.uuid4().hex[:6]}",
            hashed_password=hash_password("password123"),
            role=role,
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        token = create_access_token(user_id=user.id, username=user.username, role=user.role)
        return user, token


def _seed_application(candidate_id: int) -> CandidateApplication:
    with Session(engine) as session:
        job = JobPosting(
            title="Senior Backend Engineer",
            description="FastAPI, PostgreSQL microservices",
            required_skills="Python, FastAPI, PostgreSQL",
            department="Engineering",
            created_by=candidate_id,
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        app_record = CandidateApplication(
            candidate_user_id=candidate_id,
            job_id=job.id,
            resume_text="Experienced Python FastAPI developer",
            status="Applied",
            application_date=datetime.utcnow(),
        )
        session.add(app_record)
        session.commit()
        session.refresh(app_record)
        return app_record


def test_agent_benchmark_metrics_and_slas():
    summary_path = Path("evidence/evaluation/agent_benchmark_summary.json")
    report_path = Path("evidence/evaluation/agent_benchmark_report.md")

    assert summary_path.exists(), "agent_benchmark_summary.json missing"
    assert report_path.exists(), "agent_benchmark_report.md missing"

    with open(summary_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["total_scenarios_evaluated"] >= 20
    assert data["performance_metrics"]["task_success_rate_pct"] >= 95.0
    assert data["performance_metrics"]["tool_selection_accuracy_pct"] >= 90.0
    assert 2.0 <= data["performance_metrics"]["average_steps_per_task"] <= 3.5
    assert data["latency_percentiles_ms"]["p95"] <= 4500.0


def test_human_evaluation_model_and_composite():
    candidate, _ = _seed_user("cand_eval_1", "candidate")
    reviewer, _ = _seed_user("hr_eval_1", "hr")
    app_rec = _seed_application(candidate.id)

    composite = round((5 + 4 + 5 + 4) / 4.0, 2)
    eval_record = HumanEvaluation(
        application_id=app_rec.id,
        reviewer_id=reviewer.id,
        correctness=5,
        helpfulness=4,
        completeness=5,
        safety_groundedness=4,
        composite_rating=composite,
        feedback_notes="Strong verified candidate profile.",
        decision_override="agreed",
    )

    with Session(engine) as session:
        session.add(eval_record)
        session.commit()
        session.refresh(eval_record)
        assert eval_record.id is not None
        assert eval_record.composite_rating == 4.5
        assert eval_record.decision_override == "agreed"


def test_human_evaluation_endpoints_crud_and_summary():
    candidate, _ = _seed_user("cand_eval_2", "candidate")
    hr, hr_token = _seed_user("hr_eval_2", "hr")
    app_rec = _seed_application(candidate.id)

    client = TestClient(app)

    # 1. Submit Human Evaluation
    res = client.post(
        f"/api/applications/{app_rec.id}/human-evaluation",
        headers={"Authorization": f"Bearer {hr_token}"},
        json={
            "correctness": 5,
            "helpfulness": 5,
            "completeness": 4,
            "safety_groundedness": 5,
            "feedback_notes": "Spot-on ATS scoring and FastAPI technical questions.",
            "decision_override": "agreed",
        },
    )
    assert res.status_code == 200, res.text
    payload = res.json()
    assert payload["success"] is True
    assert payload["evaluation"]["composite_rating"] == 4.75

    # 2. Get Evaluation for Application
    get_res = client.get(
        f"/api/applications/{app_rec.id}/human-evaluation",
        headers={"Authorization": f"Bearer {hr_token}"},
    )
    assert get_res.status_code == 200
    evals = get_res.json()
    assert len(evals) >= 1
    assert evals[0]["correctness"] == 5

    # 3. Get System-wide Summary
    summary_res = client.get(
        "/api/applications/human-evaluation/summary",
        headers={"Authorization": f"Bearer {hr_token}"},
    )
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total_evaluations"] >= 1
    assert summary["average_composite_rating"] >= 4.0


def test_human_evaluation_rbac_security():
    candidate, cand_token = _seed_user("cand_eval_3", "candidate")
    app_rec = _seed_application(candidate.id)
    client = TestClient(app)

    # Candidate should not be allowed to submit human evaluation ratings
    res = client.post(
        f"/api/applications/{app_rec.id}/human-evaluation",
        headers={"Authorization": f"Bearer {cand_token}"},
        json={
            "correctness": 5,
            "helpfulness": 5,
            "completeness": 5,
            "safety_groundedness": 5,
        },
    )
    assert res.status_code in (401, 403)


def test_evaluation_evidence_files_exist():
    summary = Path("evidence/evaluation/agent_benchmark_summary.json")
    ratings = Path("evidence/evaluation/human_evaluation_ratings.json")
    report = Path("evidence/evaluation/agent_benchmark_report.md")

    assert summary.exists()
    assert ratings.exists()
    assert report.exists()

    with open(ratings, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert len(data) >= 5
