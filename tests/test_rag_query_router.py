import os
import uuid
from datetime import datetime

os.environ["AUTO_CREATE_DB_SCHEMA"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-talentforge"
os.environ["RAG_ANSWER_PROVIDER"] = "extractive"

from fastapi.testclient import TestClient
from sqlmodel import Session

from src.api.dependencies import get_current_user
from src.database.connection import create_db_and_tables, engine
from src.main import app
from src.models import (
    ApplicationAIAnalysis,
    CandidateApplication,
    InterviewIntelligenceReport,
    InterviewSession,
    JobPosting,
    User,
)
from src.services.rag.chroma_service import ChromaService
from src.services.rag.chat_service import RAGChatService
from src.services.rag.embedding_service import EmbeddingService, HashEmbeddingProvider
from src.services.rag.ingestion_service import IngestionService
from src.services.rag.query_router import QueryRouter
from src.services.rag.retrieval_service import RetrievalService

create_db_and_tables()


class BrokenRetrieval:
    def retrieve(self, *args, **kwargs):
        raise RuntimeError("chroma unavailable")


def _chat_stack(path):
    embedding = EmbeddingService(HashEmbeddingProvider(dimension=64))
    chroma = ChromaService(path)
    ingestion = IngestionService(chroma, embedding, chunk_size=120, chunk_overlap=20)
    retrieval = RetrievalService(chroma, embedding, top_k=3)
    chat = RAGChatService(retrieval, QueryRouter())
    return ingestion, chat


def _seed_decision_records():
    suffix = uuid.uuid4().hex[:8]
    with Session(engine) as session:
        hr = User(username=f"phase6_hr_{suffix}", hashed_password="x", role="hr")
        candidate_one = User(username=f"phase6_alina_{suffix}", hashed_password="x", role="candidate")
        candidate_two = User(username=f"phase6_ben_{suffix}", hashed_password="x", role="candidate")
        session.add(hr)
        session.add(candidate_one)
        session.add(candidate_two)
        session.commit()
        session.refresh(hr)
        session.refresh(candidate_one)
        session.refresh(candidate_two)

        job = JobPosting(
            title="Backend Engineer",
            description="Build FastAPI services, PostgreSQL APIs, and debugging workflows.",
            required_skills="Python, FastAPI, PostgreSQL, API debugging",
            department="Engineering",
            created_by=hr.id,
        )
        session.add(job)
        session.commit()
        session.refresh(job)

        app_one = CandidateApplication(
            candidate_user_id=candidate_one.id,
            job_id=job.id,
            resume_text="FastAPI engineer with PostgreSQL performance tuning and API debugging.",
            application_date=datetime.utcnow(),
            status="Shortlisted",
        )
        app_two = CandidateApplication(
            candidate_user_id=candidate_two.id,
            job_id=job.id,
            resume_text="React engineer with limited backend API exposure.",
            application_date=datetime.utcnow(),
            status="Applied",
        )
        session.add(app_one)
        session.add(app_two)
        session.commit()
        session.refresh(app_one)
        session.refresh(app_two)

        session.add(
            ApplicationAIAnalysis(
                application_id=app_one.id,
                fit_score=91,
                recommendation="Strongly Recommended",
                summary="Strong FastAPI, PostgreSQL, and API debugging profile.",
                strengths='["FastAPI", "PostgreSQL tuning", "API debugging"]',
                weaknesses='["Needs leadership examples"]',
                missing_skills="[]",
                status="completed",
            )
        )
        session.add(
            ApplicationAIAnalysis(
                application_id=app_two.id,
                fit_score=58,
                recommendation="Needs Review",
                summary="Frontend-heavy background with weaker backend evidence.",
                strengths='["React"]',
                weaknesses='["Backend depth", "PostgreSQL"]',
                missing_skills='["FastAPI", "API debugging"]',
                status="completed",
            )
        )
        interview = InterviewSession(
            user_id=candidate_one.id,
            session_token=uuid.uuid4().hex,
            role="Backend Engineer",
            avg_score=8.8,
            application_id=app_one.id,
            status="analyzed",
        )
        session.add(interview)
        session.commit()
        session.refresh(interview)
        session.add(
            InterviewIntelligenceReport(
                application_id=app_one.id,
                candidate_id=candidate_one.id,
                session_id=interview.id,
                resume_score=90,
                technical_score=92,
                behavioral_score=78,
                credibility_score=88,
                overall_score=89,
                recommendation="Recommended",
                executive_summary="Strong API design, debugging, and PostgreSQL performance evidence.",
                strengths='["API design", "Debugging"]',
                weaknesses='["Leadership examples"]',
                status="analyzed",
            )
        )
        session.commit()
        return (
            User(id=hr.id, username=hr.username, hashed_password="x", role=hr.role),
            User(id=candidate_one.id, username=candidate_one.username, hashed_password="x", role=candidate_one.role),
            User(id=candidate_two.id, username=candidate_two.username, hashed_password="x", role=candidate_two.role),
        )


def test_hr_database_query_uses_live_hrms_data(tmp_path):
    _ingestion, chat = _chat_stack(tmp_path / "chroma")
    hr, _candidate_one, _candidate_two = _seed_decision_records()

    result = chat.answer("How many applications are in the hiring pipeline?", user=hr)

    assert result["collections_used"] == ["database"]
    assert result["sources"][0]["collection"] == "database"
    assert "Total applications" in result["answer"]
    assert "Application status counts" in result["answer"]


def test_regular_policy_question_stays_rag_only(tmp_path):
    ingestion, chat = _chat_stack(tmp_path / "chroma")
    source = tmp_path / "leave.txt"
    source.write_text("Leave policy grants employees 18 paid leave days each year.", encoding="utf-8")
    ingestion.ingest_file(source, "company_policies")
    hr, _candidate_one, _candidate_two = _seed_decision_records()

    result = chat.answer("What is the leave policy?", ["company_policies"], user=hr)

    assert result["collections_used"] == ["company_policies"]
    assert result["sources"][0]["collection"] == "company_policies"
    assert "18 paid leave days" in result["answer"]


def test_hybrid_candidate_comparison_uses_database_and_rag(tmp_path):
    ingestion, chat = _chat_stack(tmp_path / "chroma")
    source = tmp_path / "backend_jd.txt"
    source.write_text("Backend Engineer role requires FastAPI, PostgreSQL, API debugging, and system design.", encoding="utf-8")
    ingestion.ingest_file(source, "job_descriptions")
    hr, _candidate_one, _candidate_two = _seed_decision_records()

    result = chat.answer("Which candidates are strongest for the Backend Engineer role?", ["job_descriptions"], user=hr)

    assert "database" in result["collections_used"]
    assert "job_descriptions" in result["collections_used"]
    assert any(source["collection"] == "database" for source in result["sources"])
    assert "Strong FastAPI" in result["answer"] or "Decision support score" in result["answer"]


def test_candidate_guidance_is_limited_to_own_records(tmp_path):
    _ingestion, chat = _chat_stack(tmp_path / "chroma")
    _hr, candidate_one, candidate_two = _seed_decision_records()

    result = chat.answer("What skills should I improve?", user=candidate_two)

    assert result["collections_used"][0] == "database"
    assert "Backend depth" in result["answer"] or "FastAPI" in result["answer"]
    assert candidate_one.username not in result["answer"]


def test_hiring_recommendation_summary_contains_decision_context(tmp_path):
    _ingestion, chat = _chat_stack(tmp_path / "chroma")
    hr, _candidate_one, _candidate_two = _seed_decision_records()

    result = chat.answer("Who should move to the next round and what hiring risks exist?", user=hr)

    assert "database" in result["collections_used"]
    assert "Hybrid hiring decision context" in result["answer"]
    assert "hiring decision" in result["sources"][0]["source_collection"].lower()


def test_rag_endpoint_routes_database_question_with_authenticated_user():
    hr, _candidate_one, _candidate_two = _seed_decision_records()
    app.dependency_overrides[get_current_user] = lambda: hr
    try:
        response = TestClient(app).post(
            "/api/rag/chat",
            json={"query": "How many applications are in the hiring pipeline?"},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["collections_used"] == ["database"]
        assert payload["sources"][0]["collection"] == "database"
        assert "Total applications" in payload["answer"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_hybrid_query_falls_back_to_database_when_chroma_is_unavailable():
    hr, _candidate_one, _candidate_two = _seed_decision_records()
    chat = RAGChatService(BrokenRetrieval(), QueryRouter())

    result = chat.answer("Which candidates are strongest for the Backend Engineer role?", ["job_descriptions"], user=hr)

    assert result["collections_used"] == ["database"]
    assert result["sources"][0]["collection"] == "database"
    assert "Hybrid hiring decision context" in result["answer"]


def test_rag_only_query_fails_gracefully_when_chroma_is_unavailable():
    hr, _candidate_one, _candidate_two = _seed_decision_records()
    chat = RAGChatService(BrokenRetrieval(), QueryRouter())

    result = chat.answer("What is the leave policy?", ["company_policies"], user=hr)

    assert result["collections_used"] == []
    assert result["sources"] == []
    assert "temporarily unavailable" in result["answer"]
