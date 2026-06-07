import json
import os
import uuid
from datetime import datetime

os.environ["AUTO_CREATE_DB_SCHEMA"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-talentforge"

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from src.main import app
from src.database.connection import create_db_and_tables, engine
from src.models import CandidateApplication, InterviewSession, JobPosting, User
from src.services.hiring_intelligence import save_hiring_intelligence_results
from src.services.rag.chroma_service import ChromaService
from src.services.rag.embedding_service import EmbeddingService
from src.services.rag.retrieval_service import RetrievalService
from src.services.recruitment_ai import _upsert_analysis

create_db_and_tables()


def _register(username: str, role: str) -> tuple[int, str]:
    client = TestClient(app)
    response = client.post("/api/auth/register", json={"username": username, "password": "Pass123!"})
    assert response.status_code == 201, response.text
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).one()
        user.role = role
        session.add(user)
        session.commit()
        user_id = user.id
    login = client.post("/api/auth/login", json={"username": username, "password": "Pass123!"})
    assert login.status_code == 200, login.text
    return user_id, login.json()["access_token"]


def _retrieval(path):
    embedding = EmbeddingService()
    return RetrievalService(ChromaService(path), embedding, top_k=3)


def test_job_api_create_update_delete_syncs_to_chroma(monkeypatch, tmp_path):
    chroma_path = tmp_path / "job_chroma"
    monkeypatch.setenv("RAG_CHROMA_PATH", str(chroma_path))
    _hr_id, hr_token = _register(f"rag_sync_hr_{uuid.uuid4().hex[:8]}", "hr")
    client = TestClient(app)

    created = client.post(
        "/api/jobs",
        headers={"Authorization": f"Bearer {hr_token}"},
        json={
            "title": "Platform Engineer",
            "description": "Own Kubernetes platform reliability.",
            "required_skills": "Kubernetes, Terraform",
        },
    )
    assert created.status_code == 201, created.text
    job_id = created.json()["id"]
    retrieval = _retrieval(chroma_path)
    assert "Kubernetes platform reliability" in retrieval.retrieve("Kubernetes platform", ["job_descriptions"])["context"]

    updated = client.put(
        f"/api/jobs/{job_id}",
        headers={"Authorization": f"Bearer {hr_token}"},
        json={"description": "Own incident response automation and platform reliability."},
    )
    assert updated.status_code == 200, updated.text
    assert "incident response automation" in retrieval.retrieve("incident response automation", ["job_descriptions"])["context"]

    deleted = client.delete(f"/api/jobs/{job_id}", headers={"Authorization": f"Bearer {hr_token}"})
    assert deleted.status_code == 200, deleted.text
    assert ChromaService(chroma_path).get_collection("job_descriptions").count() == 0


def test_resume_analysis_completion_syncs_candidate_profile(monkeypatch, tmp_path):
    chroma_path = tmp_path / "candidate_chroma"
    monkeypatch.setenv("RAG_CHROMA_PATH", str(chroma_path))
    candidate = User(username=f"rag_candidate_{uuid.uuid4().hex[:8]}", hashed_password="x", role="candidate")
    hr = User(username=f"rag_hr_owner_{uuid.uuid4().hex[:8]}", hashed_password="x", role="hr")
    with Session(engine) as session:
        session.add(candidate)
        session.add(hr)
        session.commit()
        session.refresh(candidate)
        session.refresh(hr)
        candidate_id = candidate.id
        job = JobPosting(
            title="Analytics Engineer",
            description="Build warehouse models.",
            required_skills="SQL, dbt",
            created_by=hr.id,
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        application = CandidateApplication(
            candidate_user_id=candidate_id,
            job_id=job.id,
            resume_text="Built dbt marts for revenue analytics.",
            application_date=datetime.utcnow(),
        )
        session.add(application)
        session.commit()
        session.refresh(application)

        _upsert_analysis(
            session,
            application,
            {
                "fit_score": 86,
                "recommendation": "Recommended",
                "summary": "Strong dbt revenue analytics profile.",
                "strengths": ["dbt marts"],
                "weaknesses": [],
                "missing_skills": [],
                "observations": ["Revenue analytics"],
                "technical_questions": [],
                "behavioral_questions": [],
                "probing_areas": [],
                "status": "completed",
                "source": "test",
            },
            existing=None,
        )

    retrieved = _retrieval(chroma_path).retrieve("dbt revenue analytics", ["candidate_profiles"])
    assert "dbt revenue analytics" in retrieved["context"]
    assert retrieved["sources"][0]["user_id"] == str(candidate_id)


def test_interview_report_persistence_syncs_report(monkeypatch, tmp_path):
    chroma_path = tmp_path / "interview_chroma"
    monkeypatch.setenv("RAG_CHROMA_PATH", str(chroma_path))
    candidate = User(username=f"rag_int_candidate_{uuid.uuid4().hex[:8]}", hashed_password="x", role="candidate")
    hr = User(username=f"rag_int_hr_{uuid.uuid4().hex[:8]}", hashed_password="x", role="hr")
    with Session(engine) as session:
        session.add(candidate)
        session.add(hr)
        session.commit()
        session.refresh(candidate)
        session.refresh(hr)
        candidate_id = candidate.id
        job = JobPosting(title="API Engineer", description="Build APIs.", required_skills="FastAPI", created_by=hr.id)
        session.add(job)
        session.commit()
        session.refresh(job)
        application = CandidateApplication(
            candidate_user_id=candidate_id,
            job_id=job.id,
            resume_text="Built FastAPI services.",
            application_date=datetime.utcnow(),
        )
        session.add(application)
        session.commit()
        session.refresh(application)
        interview = InterviewSession(
            user_id=candidate_id,
            session_token=uuid.uuid4().hex,
            role="API Engineer",
            messages=json.dumps([{"role": "ai", "content": "Explain an API."}, {"role": "user", "content": "I built FastAPI services."}]),
            avg_score=8.5,
            application_id=application.id,
            status="analyzing",
        )
        session.add(interview)
        session.commit()
        session.refresh(interview)
        save_hiring_intelligence_results(
            session,
            interview,
            {
                "competency_scores": {"technicalDepth": 9, "problemSolving": 8, "systemDesign": 8, "domainKnowledge": 9},
                "job_fit_report": {"jobFit": 88, "strengths": ["FastAPI"], "weaknesses": [], "recommendation": "Recommended"},
                "communication_metrics": {"clarity": 8},
                "behavioral_report": {"categories": {"Behavioral": 7, "Situational": 7, "Leadership": 6}},
                "hiring_risks": [],
                "timeline_replay": [],
                "_source": "test",
            },
            benchmarking_data={},
            filler_counts={},
        )

    retrieved = _retrieval(chroma_path).retrieve("FastAPI technical depth", ["interview_reports"])
    assert "FastAPI" in retrieved["context"]
    assert retrieved["sources"][0]["user_id"] == str(candidate_id)
