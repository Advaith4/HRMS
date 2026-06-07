import os
import uuid
from datetime import datetime

os.environ["AUTO_CREATE_DB_SCHEMA"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-talentforge"

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from src.api.routes.rag import get_rag_chat_service
from src.main import app
from src.database.connection import create_db_and_tables, engine
from src.models import CandidateApplication, JobPosting, User
from src.services.rag.access_control import RAGAccessControl
from src.services.rag.chroma_service import ChromaService
from src.services.rag.chat_service import RAGChatService
from src.services.rag.embedding_service import EmbeddingService, HashEmbeddingProvider
from src.services.rag.retrieval_service import RetrievalService
from src.services.rag.sync_service import RAGSyncService

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


def _rag_stack(path):
    embedding = EmbeddingService(HashEmbeddingProvider(dimension=64))
    chroma = ChromaService(path)
    sync = RAGSyncService(chroma, embedding)
    retrieval = RetrievalService(chroma, embedding, top_k=5)
    chat = RAGChatService(retrieval)
    return sync, chat, chroma


def test_access_control_generates_candidate_metadata_filters():
    candidate = User(id=42, username="candidate", hashed_password="x", role="candidate")
    plan = RAGAccessControl().build_plan(candidate, ["candidate_profiles", "interview_reports"])
    assert plan.collections == ["candidate_profiles", "interview_reports"]
    assert plan.filters["candidate_profiles"] == {"user_id": "42"}
    assert plan.filters["interview_reports"] == {"user_id": "42"}


def test_candidate_cannot_request_employee_knowledge():
    candidate = User(id=42, username="candidate", hashed_password="x", role="candidate")
    try:
        RAGAccessControl().build_plan(candidate, ["employee_knowledge"])
    except PermissionError as exc:
        assert "employee_knowledge" in str(exc)
    else:
        raise AssertionError("candidate employee_knowledge access should be denied")


def test_candidate_rag_endpoint_only_returns_own_profile(tmp_path):
    candidate_one_id, candidate_one_token = _register(f"rag_cand_one_{uuid.uuid4().hex[:8]}", "candidate")
    candidate_two_id, _candidate_two_token = _register(f"rag_cand_two_{uuid.uuid4().hex[:8]}", "candidate")
    sync, chat, _chroma = _rag_stack(tmp_path / "chroma")

    sync.sync_candidate_profile(
        CandidateApplication(
            id=501,
            candidate_user_id=candidate_one_id,
            job_id=10,
            resume_text="Candidate one owns payroll API integration experience.",
            application_date=datetime.utcnow(),
            status="Applied",
        )
    )
    sync.sync_candidate_profile(
        CandidateApplication(
            id=502,
            candidate_user_id=candidate_two_id,
            job_id=10,
            resume_text="Candidate two owns confidential security architecture experience.",
            application_date=datetime.utcnow(),
            status="Applied",
        )
    )

    app.dependency_overrides[get_rag_chat_service] = lambda: chat
    try:
        response = TestClient(app).post(
            "/api/rag/chat",
            headers={"Authorization": f"Bearer {candidate_one_token}"},
            json={"query": "security architecture payroll API", "collections": ["candidate_profiles"]},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["sources"]
        assert all(source["user_id"] == str(candidate_one_id) for source in payload["sources"])
        assert "Candidate two" not in payload["answer"]
        assert "payroll API" in payload["answer"]
    finally:
        app.dependency_overrides.pop(get_rag_chat_service, None)


def test_hr_rag_endpoint_can_retrieve_candidate_profiles(tmp_path):
    candidate_id, _candidate_token = _register(f"rag_hr_view_cand_{uuid.uuid4().hex[:8]}", "candidate")
    _hr_id, hr_token = _register(f"rag_hr_{uuid.uuid4().hex[:8]}", "hr")
    sync, chat, _chroma = _rag_stack(tmp_path / "chroma")
    sync.sync_candidate_profile(
        CandidateApplication(
            id=601,
            candidate_user_id=candidate_id,
            job_id=10,
            resume_text="Candidate has workforce analytics and retention dashboard experience.",
            application_date=datetime.utcnow(),
            status="Applied",
        )
    )

    app.dependency_overrides[get_rag_chat_service] = lambda: chat
    try:
        response = TestClient(app).post(
            "/api/rag/chat",
            headers={"Authorization": f"Bearer {hr_token}"},
            json={"query": "retention dashboard", "collections": ["candidate_profiles"]},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["sources"][0]["user_id"] == str(candidate_id)
        assert "retention dashboard" in payload["answer"]
    finally:
        app.dependency_overrides.pop(get_rag_chat_service, None)


def test_chroma_restart_persistence_for_synced_job(tmp_path):
    chroma_path = tmp_path / "persistent_chroma"
    embedding = EmbeddingService(HashEmbeddingProvider(dimension=64))
    sync = RAGSyncService(ChromaService(chroma_path), embedding)
    sync.sync_job(
        JobPosting(
            id=701,
            title="Data Engineer",
            description="Own durable lakehouse pipelines and governance.",
            required_skills="Python, SQL",
            department="Data",
            created_by=1,
            created_at=datetime.utcnow(),
        )
    )

    restarted_chroma = ChromaService(chroma_path)
    retrieval = RetrievalService(restarted_chroma, embedding, top_k=1)
    result = retrieval.retrieve("lakehouse pipelines", ["job_descriptions"])
    assert restarted_chroma.get_collection("job_descriptions").count() == 1
    assert "lakehouse pipelines" in result["context"]
