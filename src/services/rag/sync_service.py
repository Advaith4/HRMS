import json
import logging
from datetime import datetime
from typing import Any

from src.models import ApplicationAIAnalysis, CandidateApplication, InterviewIntelligenceReport, InterviewSession, JobPosting
from src.services.rag.chroma_service import ChromaService
from src.services.rag.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return datetime.utcnow().isoformat()
    return str(value)


def _json_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return value
        return json.dumps(parsed, ensure_ascii=True)
    return json.dumps(value, ensure_ascii=True)


class RAGSyncService:
    """Synchronizes HRMS database entities into RAG Chroma collections."""

    def __init__(
        self,
        chroma_service: ChromaService | None = None,
        embedding_service: EmbeddingService | None = None,
    ):
        self.chroma = chroma_service or ChromaService()
        self.embeddings = embedding_service or EmbeddingService()

    def document_id(self, source_collection: str, entity_type: str, entity_id: int | str) -> str:
        return f"{source_collection}:{entity_type}:{entity_id}"

    def upsert_entity(
        self,
        source_collection: str,
        entity_type: str,
        entity_id: int | str,
        content: str,
        *,
        user_id: int | None = None,
        created_at: Any = None,
        updated_at: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        doc_id = self.document_id(source_collection, entity_type, entity_id)
        clean_content = " ".join((content or "").split())
        if not clean_content:
            logger.info("Skipping empty RAG sync entity_type=%s entity_id=%s", entity_type, entity_id)
            return doc_id
        rag_metadata = {
            "entity_id": str(entity_id),
            "entity_type": entity_type,
            "created_at": _iso(created_at),
            "updated_at": _iso(updated_at),
            "source_collection": source_collection,
        }
        if user_id is not None:
            rag_metadata["user_id"] = str(user_id)
        for key, value in (metadata or {}).items():
            if value is not None:
                rag_metadata[key] = str(value)
        embedding = self.embeddings.embed_texts([clean_content])
        self.chroma.upsert_documents(source_collection, [doc_id], [clean_content], embedding, [rag_metadata])
        logger.info("RAG sync upserted entity_type=%s entity_id=%s collection=%s", entity_type, entity_id, source_collection)
        return doc_id

    def delete_entity(self, source_collection: str, entity_type: str, entity_id: int | str) -> str:
        doc_id = self.document_id(source_collection, entity_type, entity_id)
        self.chroma.delete_ids(source_collection, [doc_id])
        logger.info("RAG sync deleted entity_type=%s entity_id=%s collection=%s", entity_type, entity_id, source_collection)
        return doc_id

    def sync_job(self, job: JobPosting) -> str:
        content = "\n".join(
            [
                f"Job Title: {job.title}",
                f"Status: {getattr(job, 'status', 'OPEN') or 'OPEN'}",
                f"Department: {job.department}",
                f"Description: {job.description}",
                f"Required Skills: {job.required_skills}",
                f"Experience Required: {job.experience_required}",
                f"Salary Range: {job.salary_range}",
            ]
        )
        return self.upsert_entity(
            "job_descriptions",
            "job",
            job.id,
            content,
            user_id=job.created_by,
            created_at=job.created_at,
            updated_at=getattr(job, "updated_at", None) or datetime.utcnow(),
            metadata={"title": job.title, "department": job.department, "status": getattr(job, "status", "OPEN") or "OPEN"},
        )

    def delete_job(self, job_id: int | str) -> str:
        return self.delete_entity("job_descriptions", "job", job_id)

    def sync_candidate_profile(
        self,
        application: CandidateApplication,
        analysis: ApplicationAIAnalysis | None = None,
        job: JobPosting | None = None,
    ) -> str:
        content = "\n".join(
            [
                f"Candidate Application ID: {application.id}",
                f"Candidate User ID: {application.candidate_user_id}",
                f"Job: {job.title if job else application.job_id}",
                f"Resume Text: {application.resume_text}",
                f"Analysis Summary: {analysis.summary if analysis else ''}",
                f"Recommendation: {analysis.recommendation if analysis else ''}",
                f"Fit Score: {analysis.fit_score if analysis else ''}",
                f"Strengths: {_json_text(analysis.strengths if analysis else None)}",
                f"Weaknesses: {_json_text(analysis.weaknesses if analysis else None)}",
                f"Missing Skills: {_json_text(analysis.missing_skills if analysis else None)}",
                f"Observations: {_json_text(analysis.observations if analysis else None)}",
            ]
        )
        return self.upsert_entity(
            "candidate_profiles",
            "candidate_application",
            application.id,
            content,
            user_id=application.candidate_user_id,
            created_at=application.application_date,
            updated_at=analysis.updated_at if analysis else datetime.utcnow(),
            metadata={"job_id": application.job_id, "analysis_id": analysis.id if analysis else None},
        )

    def delete_candidate_profile(self, application_id: int | str) -> str:
        return self.delete_entity("candidate_profiles", "candidate_application", application_id)

    def sync_interview_report(
        self,
        report: InterviewIntelligenceReport,
        interview_session: InterviewSession | None = None,
        application: CandidateApplication | None = None,
    ) -> str:
        content = "\n".join(
            [
                f"Interview Report ID: {report.id}",
                f"Candidate ID: {report.candidate_id}",
                f"Application ID: {report.application_id}",
                f"Session ID: {report.session_id}",
                f"Recommendation: {report.recommendation}",
                f"Executive Summary: {report.executive_summary}",
                f"Overall Score: {report.overall_score}",
                f"Technical Score: {report.technical_score}",
                f"Behavioral Score: {report.behavioral_score}",
                f"Credibility Score: {report.credibility_score}",
                f"Strengths: {_json_text(report.strengths)}",
                f"Weaknesses: {_json_text(report.weaknesses)}",
                f"Technical Assessment: {_json_text(report.technical_assessment)}",
                f"Behavioral Assessment: {_json_text(report.behavioral_assessment)}",
                f"Resume Validation: {_json_text(report.resume_validation)}",
            ]
        )
        return self.upsert_entity(
            "interview_reports",
            "interview_report",
            report.session_id,
            content,
            user_id=report.candidate_id,
            created_at=report.created_at,
            updated_at=report.updated_at,
            metadata={
                "report_id": report.id,
                "application_id": report.application_id,
                "session_id": report.session_id,
                "candidate_id": report.candidate_id,
                "job_id": application.job_id if application else None,
                "session_status": interview_session.status if interview_session else None,
            },
        )

    def delete_interview_report(self, session_id: int | str) -> str:
        return self.delete_entity("interview_reports", "interview_report", session_id)
