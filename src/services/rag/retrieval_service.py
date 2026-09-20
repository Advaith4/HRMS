"""
src/services/rag/retrieval_service.py
Two-Stage Production Retrieval Service with Cross-Encoder Re-ranking and Rich Citation Attribution.
"""
import logging
from typing import Any

from src.services.rag.chroma_service import DEFAULT_COLLECTIONS, ChromaService
from src.services.rag.embedding_service import EmbeddingService
from src.services.rag.reranker import CrossEncoderReranker, reranker_engine

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(
        self,
        chroma_service: ChromaService | None = None,
        embedding_service: EmbeddingService | None = None,
        reranker: CrossEncoderReranker | None = None,
        top_k: int = 5,
    ):
        self.chroma = chroma_service or ChromaService()
        self.embeddings = embedding_service or EmbeddingService()
        self.reranker = reranker or reranker_engine
        self.top_k = top_k

    def retrieve(
        self,
        query: str,
        collections: list[str] | None = None,
        top_k: int | None = None,
        filters: dict[str, dict] | None = None,
        apply_reranking: bool = True,
    ) -> dict[str, Any]:
        selected = collections or list(DEFAULT_COLLECTIONS)
        query_embedding = self.embeddings.embed_query(query)
        limit = top_k or self.top_k
        
        # Stage 1: Vector Search across candidate collections (Fetch 3x pool, min 15)
        stage1_fetch_limit = max(limit * 3, 15)
        matches = []
        used = []

        for collection in selected:
            try:
                collection_matches = self.chroma.query(
                    collection,
                    query_embedding,
                    top_k=stage1_fetch_limit,
                    where=(filters or {}).get(collection),
                )
            except ValueError:
                logger.warning("Skipping unsupported RAG collection %s", collection)
                continue
            if collection_matches:
                used.append(collection)
                matches.extend(collection_matches)

        matches.sort(key=lambda match: match["distance"] if match["distance"] is not None else 999)
        selected_matches = matches[:limit]
        context = "\n\n".join(match["content"] for match in selected_matches)

        # Stage 2: Cross-Encoder & Semantic Re-ranking
        if apply_reranking and matches:
            selected_matches = self.reranker.rerank(query=query, candidates=matches, top_k=limit)
        else:
            selected_matches = matches[:limit]

        formatted_chunks = []
        for match in selected_matches:
            meta = match.get("metadata") or {}
            source_name = meta.get("filename") or meta.get("source") or match.get("collection", "knowledge_base")
            page = meta.get("page_number", 1)
            chunk_id = meta.get("chunk_id", "0")
            formatted_chunks.append(f"--- Document: {source_name} | Page: {page} | Chunk: {chunk_id} ---\n{match['content']}")

        context = "\n\n".join(formatted_chunks)
        sources = [self._source_from_match(match) for match in selected_matches]
        return {"context": context, "sources": sources, "collections_used": used, "matches": selected_matches}
        return {
            "context": context,
            "sources": sources,
            "collections_used": used,
            "matches": selected_matches,
            "reranked": apply_reranking,
        }

    def _source_from_match(self, match: dict[str, Any]) -> dict[str, Any]:
        metadata = match.get("metadata") or {}
        content = match.get("content") or ""
        snippet = (content[:200] + "...") if len(content) > 200 else content

        return {
            "collection": match.get("collection"),
            "source": metadata.get("source"),
            "filename": metadata.get("filename"),
            "chunk_id": metadata.get("chunk_id"),
            "chunk_index": metadata.get("chunk_index"),
            "page_number": metadata.get("page_number", 1),
            "category": metadata.get("category", "policy"),
            "access_role": metadata.get("access_role", "employee"),
            "entity_id": metadata.get("entity_id"),
            "entity_type": metadata.get("entity_type"),
            "user_id": metadata.get("user_id"),
            "source_collection": metadata.get("source_collection"),
            "distance": match.get("distance"),
            "rerank_score": match.get("rerank_score"),
            "original_rank": match.get("original_rank"),
            "snippet": snippet,
        }
