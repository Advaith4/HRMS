from datetime import datetime

from src.models import ApplicationAIAnalysis, CandidateApplication, InterviewIntelligenceReport, InterviewSession, JobPosting
from src.services.rag.chroma_service import ChromaService
from src.services.rag.embedding_service import EmbeddingService, HashEmbeddingProvider
from src.services.rag.retrieval_service import RetrievalService
from src.services.rag.sync_service import RAGSyncService


def _sync_stack(path):
    embedding = EmbeddingService(HashEmbeddingProvider(dimension=64))
    chroma = ChromaService(path)
    sync = RAGSyncService(chroma, embedding)
    retrieval = RetrievalService(chroma, embedding, top_k=3)
    return sync, retrieval, chroma


def test_job_create_update_delete_sync_is_idempotent(tmp_path):
    sync, retrieval, chroma = _sync_stack(tmp_path / "chroma")
    job = JobPosting(
        id=101,
        title="Backend Engineer",
        description="Build FastAPI services and PostgreSQL integrations.",
        required_skills="Python, FastAPI, PostgreSQL",
        department="Engineering",
        salary_range="10-15 LPA",
        experience_required="3 years",
        created_by=7,
        created_at=datetime(2026, 1, 1),
    )

    doc_id = sync.sync_job(job)
    sync.sync_job(job)
    assert chroma.get_collection("job_descriptions").count() == 1
    assert doc_id == "job_descriptions:job:101"
    metadata = chroma.get_collection("job_descriptions").get(ids=[doc_id])["metadatas"][0]
    assert metadata["entity_id"] == "101"
    assert metadata["entity_type"] == "job"
    assert metadata["user_id"] == "7"
    assert metadata["source_collection"] == "job_descriptions"

    job.description = "Build FastAPI services, Chroma retrieval, and PostgreSQL integrations."
    sync.sync_job(job)
    retrieved = retrieval.retrieve("Who builds Chroma retrieval?", ["job_descriptions"])
    assert "Chroma retrieval" in retrieved["context"]
    assert retrieved["sources"][0]["collection"] == "job_descriptions"

    sync.delete_job(job.id)
    assert chroma.get_collection("job_descriptions").count() == 0


def test_candidate_profile_sync_updates_retrieval_content(tmp_path):
    sync, retrieval, chroma = _sync_stack(tmp_path / "chroma")
    application = CandidateApplication(
        id=202,
        candidate_user_id=42,
        job_id=101,
        resume_text="Built payroll dashboards with SQL and React.",
        application_date=datetime(2026, 1, 2),
        status="Applied",
    )
    analysis = ApplicationAIAnalysis(
        id=303,
        application_id=202,
        fit_score=72,
        recommendation="Recommended",
        summary="Strong SQL dashboard experience.",
        strengths='["SQL analytics"]',
        weaknesses='["Needs API depth"]',
        missing_skills='["FastAPI"]',
        observations='["Dashboard project evidence"]',
        status="completed",
        updated_at=datetime(2026, 1, 3),
    )

    sync.sync_candidate_profile(application, analysis)
    sync.sync_candidate_profile(application, analysis)
    assert chroma.get_collection("candidate_profiles").count() == 1
    metadata = chroma.get_collection("candidate_profiles").get(
        ids=["candidate_profiles:candidate_application:202"]
    )["metadatas"][0]
    assert metadata["entity_id"] == "202"
    assert metadata["entity_type"] == "candidate_application"
    assert metadata["user_id"] == "42"
    assert metadata["source_collection"] == "candidate_profiles"

    analysis.summary = "Strong SQL dashboard and API integration experience."
    application.resume_text = "Built payroll dashboards with SQL, React, and API integrations."
    sync.sync_candidate_profile(application, analysis)
    retrieved = retrieval.retrieve("API integration experience", ["candidate_profiles"])
    assert "API integration" in retrieved["context"]
    assert retrieved["sources"][0]["source"] is None
    assert retrieved["sources"][0]["collection"] == "candidate_profiles"


def test_interview_report_sync_is_idempotent_and_retrievable(tmp_path):
    sync, retrieval, chroma = _sync_stack(tmp_path / "chroma")
    session = InterviewSession(
        id=404,
        user_id=42,
        session_token="abc",
        role="Backend Engineer",
        avg_score=8,
        application_id=202,
        status="analyzed",
    )
    report = InterviewIntelligenceReport(
        id=505,
        application_id=202,
        candidate_id=42,
        session_id=404,
        resume_score=80,
        technical_score=88,
        behavioral_score=76,
        credibility_score=82,
        overall_score=84,
        recommendation="Recommended",
        executive_summary="Candidate showed strong debugging and API design evidence.",
        strengths='["Debugging", "API design"]',
        weaknesses='["Needs scale examples"]',
        technical_assessment='{"apiDesign": 9}',
        behavioral_assessment='{"teamwork": 7}',
        resume_validation='{"credibility_score": 82}',
        status="analyzed",
        created_at=datetime(2026, 1, 4),
        updated_at=datetime(2026, 1, 5),
    )

    sync.sync_interview_report(report, session)
    sync.sync_interview_report(report, session)
    assert chroma.get_collection("interview_reports").count() == 1
    metadata = chroma.get_collection("interview_reports").get(
        ids=["interview_reports:interview_report:404"]
    )["metadatas"][0]
    assert metadata["entity_id"] == "404"
    assert metadata["entity_type"] == "interview_report"
    assert metadata["user_id"] == "42"
    assert metadata["source_collection"] == "interview_reports"

    report.executive_summary = "Candidate showed strong distributed debugging and API design evidence."
    sync.sync_interview_report(report, session)
    retrieved = retrieval.retrieve("distributed debugging", ["interview_reports"])
    assert "distributed debugging" in retrieved["context"]
    assert retrieved["sources"][0]["collection"] == "interview_reports"
