import os
import uuid

os.environ["AUTO_CREATE_DB_SCHEMA"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-talentforge"

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from src.api.routes.rag import get_rag_chat_service
from src.main import app
from src.database.connection import create_db_and_tables, engine
from src.models import User
from src.services.rag.chroma_service import ChromaService
from src.services.rag.chat_service import RAGChatService
from src.services.rag.embedding_service import EmbeddingService, HashEmbeddingProvider
from src.services.rag.ingestion_service import IngestionService
from src.services.rag.retrieval_service import RetrievalService

create_db_and_tables()


def _register(username: str, role: str = "hr") -> str:
    client = TestClient(app)
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


def _rag_stack(path):
    embedding = EmbeddingService(HashEmbeddingProvider(dimension=64))
    chroma = ChromaService(path)
    ingestion = IngestionService(chroma, embedding, chunk_size=80, chunk_overlap=20)
    retrieval = RetrievalService(chroma, embedding, top_k=3)
    chat = RAGChatService(retrieval)
    return ingestion, retrieval, chat


def test_ingestion_retrieval_and_chat_pipeline(tmp_path):
    source = tmp_path / "policy.txt"
    source.write_text(
        "Remote work policy allows employees to work from home two days per week. "
        "Managers approve exceptions for client deadlines.",
        encoding="utf-8",
    )
    ingestion, retrieval, chat = _rag_stack(tmp_path / "chroma")

    result = ingestion.ingest_file(source, "company_policies")
    assert result.chunks_stored >= 1

    retrieved = retrieval.retrieve("How many remote work days are allowed?", ["company_policies"])
    assert retrieved["sources"]
    assert retrieved["collections_used"] == ["company_policies"]

    answer = chat.answer("How many remote work days are allowed?", ["company_policies"])
    assert "two days" in answer["answer"].lower() or "2 days" in answer["answer"].lower()
    assert answer["sources"][0]["filename"] == "policy.txt"


def test_rag_chat_endpoint_returns_sources(tmp_path):
    source = tmp_path / "job.txt"
    source.write_text("Backend engineers must know FastAPI, SQL, and API debugging.", encoding="utf-8")
    ingestion, _retrieval, chat = _rag_stack(tmp_path / "chroma")
    ingestion.ingest_file(source, "job_descriptions")

    app.dependency_overrides[get_rag_chat_service] = lambda: chat
    try:
        token = _register(f"rag_hr_{uuid.uuid4().hex[:8]}")
        client = TestClient(app)
        response = client.post(
            "/api/rag/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"query": "What should backend engineers know?", "collections": ["job_descriptions"]},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert "FastAPI" in payload["answer"]
        assert payload["collections_used"] == ["job_descriptions"]
        assert payload["sources"][0]["filename"] == "job.txt"
    finally:
        app.dependency_overrides.pop(get_rag_chat_service, None)


def test_rag_chat_rejects_unknown_collection():
    token = _register(f"rag_bad_{uuid.uuid4().hex[:8]}")
    client = TestClient(app)
    response = client.post(
        "/api/rag/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "Hello", "collections": ["unknown"]},
    )
    assert response.status_code == 400


def test_candidate_rag_chat_rejects_unauthorized_collection():
    token = _register(f"rag_unauth_{uuid.uuid4().hex[:8]}", "candidate")
    client = TestClient(app)
    response = client.post(
        "/api/rag/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "Hello", "collections": ["employee_knowledge"]},
    )
    assert response.status_code == 403


def test_chat_service_llm_fallback_preserves_answer(monkeypatch, tmp_path):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    source = tmp_path / "policy.txt"
    source.write_text("Remote work is allowed two days per week with manager approval.", encoding="utf-8")
    ingestion, _retrieval, chat = _rag_stack(tmp_path / "chroma")
    ingestion.ingest_file(source, "company_policies")

    def broken_completion(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    import litellm

    monkeypatch.setattr(litellm, "completion", broken_completion)
    answer = chat.answer("What is the remote work policy?", ["company_policies"])
    assert "two days per week" in answer["answer"]
