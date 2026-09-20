"""
tests/test_phase4_rag.py
Unit and Integration Tests for Phase 4 Production RAG Pipeline.
Verifies:
  1. Hierarchical Recursive Character Chunker
  2. Cross-Encoder & Semantic Re-ranking Engine
  3. Two-Stage Retrieval with Rich Source Attribution
  4. RAG Chat Citation Synthesis
  5. Evidence Artifact Generation
"""
import json
import os
from pathlib import Path
import pytest

from src.services.rag.chunking import RecursiveCharacterChunker, DocumentChunk
from src.services.rag.reranker import CrossEncoderReranker
from src.services.rag.retrieval_service import RetrievalService
from src.services.rag.chroma_service import ChromaService
from src.services.rag.embedding_service import EmbeddingService
from src.services.rag.chat_service import RAGChatService


def test_recursive_character_chunker_bounds_and_overlap():
    chunker = RecursiveCharacterChunker(chunk_size=100, chunk_overlap=20)
    text = (
        "Paragraph 1 contains general background on company benefits.\n\n"
        "Paragraph 2 details the sick leave entitlement of 12 days per calendar year. "
        "A medical certificate is required for leaves extending beyond 2 consecutive days.\n\n"
        "Paragraph 3 covers maternity and paternity leave provisions."
    )
    chunks = chunker.split_text(text, page_number=2)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert isinstance(chunk, DocumentChunk)
        assert len(chunk.text) <= 120  # bounded
        assert chunk.page_number == 2
        assert chunk.chunk_index >= 1


def test_cross_encoder_reranker_scoring_and_ordering():
    reranker = CrossEncoderReranker()
    query = "maternity leave policy duration"
    candidates = [
        {
            "id": "c1",
            "content": "Parking passes are issued at the reception desk on the first floor.",
            "distance": 0.20,
            "metadata": {"filename": "Facilities_Guide.pdf", "category": "facilities"},
        },
        {
            "id": "c2",
            "content": "Eligible female employees receive 26 weeks of paid maternity leave under the Maternity Benefit Act.",
            "distance": 0.45,
            "metadata": {"filename": "Leave_and_Attendance_Policy_2026.pdf", "category": "leave_policy"},
        },
        {
            "id": "c3",
            "content": "Lunch breaks are 45 minutes between 12:30 PM and 2:00 PM.",
            "distance": 0.30,
            "metadata": {"filename": "Workplace_Rules.pdf", "category": "general"},
        },
    ]

    reranked = reranker.rerank(query=query, candidates=candidates, top_k=2)
    assert len(reranked) == 2
    # The maternity document should be ranked #1
    assert reranked[0]["id"] == "c2"
    assert "rerank_score" in reranked[0]
    assert reranked[0]["rerank_score"] > reranked[1]["rerank_score"]


def test_two_stage_retrieval_service_execution():
    chroma = ChromaService()
    embedding_svc = EmbeddingService()
    reranker = CrossEncoderReranker()
    retrieval_svc = RetrievalService(chroma_service=chroma, embedding_service=embedding_svc, reranker=reranker)

    # Ingest a test document
    text = "Probation period for all software engineers is 6 months from joining."
    emb = embedding_svc.embed_texts([text])
    chroma.upsert_documents(
        collection_name="company_policies",
        documents=[text],
        embeddings=emb,
        metadatas=[{
            "filename": "Employee_Handbook_2026.pdf",
            "source": "Employee_Handbook_2026.pdf",
            "page_number": 4,
            "chunk_id": "probation_chunk_1",
            "access_role": "employee",
            "category": "probation",
        }],
        ids=["probation_chunk_1"],
    )

    result = retrieval_svc.retrieve("What is the probation period?", collections=["company_policies"], top_k=3)
    assert "context" in result
    assert "sources" in result
    assert len(result["sources"]) >= 1
    src = result["sources"][0]
    assert "filename" in src
    assert "page_number" in src
    assert "chunk_id" in src
    assert "snippet" in src
    assert "--- Document:" in result["context"]


def test_rag_chat_service_answer_and_sources():
    chroma = ChromaService()
    embedding_svc = EmbeddingService()
    retrieval_svc = RetrievalService(chroma_service=chroma, embedding_service=embedding_svc)
    chat_svc = RAGChatService(retrieval_service=retrieval_svc)

    response = chat_svc.answer("What is the sick leave policy?", collections=["company_policies"])
    assert "answer" in response
    assert isinstance(response["answer"], str)
    assert len(response["answer"]) > 0
    assert "sources" in response
    assert "collections_used" in response


def test_rag_evidence_artifacts_exist_and_valid():
    evidence_dir = Path("evidence/rag")
    assert evidence_dir.exists()

    triad_file = evidence_dir / "rag_triad_metrics.json"
    assert triad_file.exists()
    with open(triad_file, "r", encoding="utf-8") as f:
        triad_data = json.load(f)
        assert "aggregate_scores" in triad_data
        assert triad_data["aggregate_scores"]["mean_groundedness_faithfulness"] > 0.70

    reranker_file = evidence_dir / "reranker_benchmark_results.json"
    assert reranker_file.exists()
    with open(reranker_file, "r", encoding="utf-8") as f:
        reranker_data = json.load(f)
        assert "pipeline_comparison" in reranker_data
        assert "performance_delta" in reranker_data["pipeline_comparison"]

    chunking_md = evidence_dir / "chunking_strategy_comparison.md"
    assert chunking_md.exists()
    assert chunking_md.stat().st_size > 100

