from src.services.rag.chroma_service import ChromaService
from src.services.rag.company_docs_ingestion import CompanyDocsIngestionService
from src.services.rag.embedding_service import EmbeddingService, HashEmbeddingProvider
from src.services.rag.ingestion_service import IngestionService
from src.services.rag.retrieval_service import RetrievalService


def _ingestor(root, chroma_path):
    embedding = EmbeddingService(HashEmbeddingProvider(dimension=64))
    chroma = ChromaService(chroma_path)
    ingestion = IngestionService(chroma, embedding, chunk_size=120, chunk_overlap=20)
    return CompanyDocsIngestionService(root, ingestion), RetrievalService(chroma, embedding, top_k=5), chroma


def test_company_docs_ingestion_is_idempotent_and_updates(tmp_path):
    docs_root = tmp_path / "company_docs"
    policies = docs_root / "policies"
    training = docs_root / "training"
    onboarding = docs_root / "onboarding"
    policies.mkdir(parents=True)
    training.mkdir(parents=True)
    onboarding.mkdir(parents=True)
    leave = policies / "leave_policy.txt"
    leave.write_text("Leave policy grants 18 paid leave days per year.", encoding="utf-8")
    training_doc = training / "communication.txt"
    training_doc.write_text("Communication updates should include blockers and next steps.", encoding="utf-8")

    ingestor, retrieval, chroma = _ingestor(docs_root, tmp_path / "chroma")
    first = ingestor.ingest_all()
    second = ingestor.ingest_all()
    assert first.files_ingested == 2
    assert second.files_ingested == 2
    assert chroma.get_collection("company_policies").count() == 1
    assert chroma.get_collection("employee_knowledge").count() == 1

    leave.write_text("Leave policy grants 20 paid leave days per year after policy revision.", encoding="utf-8")
    ingestor.ingest_all()
    result = retrieval.retrieve("How many paid leave days?", ["company_policies"])
    assert "20 paid leave days" in result["context"]
    assert "18 paid leave days" not in result["context"]


def test_company_docs_route_to_expected_collections(tmp_path):
    docs_root = tmp_path / "company_docs"
    (docs_root / "policies").mkdir(parents=True)
    (docs_root / "onboarding").mkdir(parents=True)
    (docs_root / "training").mkdir(parents=True)
    (docs_root / "policies" / "remote.txt").write_text("Remote work is two days per week.", encoding="utf-8")
    (docs_root / "onboarding" / "first_week.txt").write_text("First week onboarding includes HR orientation.", encoding="utf-8")
    (docs_root / "training" / "reviews.txt").write_text("Performance reviews happen twice per year.", encoding="utf-8")

    _ingestor(docs_root, tmp_path / "chroma")[0].ingest_all()
    chroma = ChromaService(tmp_path / "chroma")
    assert chroma.get_collection("company_policies").count() == 1
    assert chroma.get_collection("employee_knowledge").count() == 2
