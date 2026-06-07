import logging
from typing import Any

from src.services.rag.chroma_service import DEFAULT_COLLECTIONS, ChromaService
from src.services.rag.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(
        self,
        chroma_service: ChromaService | None = None,
        embedding_service: EmbeddingService | None = None,
        top_k: int = 5,
    ):
        self.chroma = chroma_service or ChromaService()
        self.embeddings = embedding_service or EmbeddingService()
        self.top_k = top_k

    def retrieve(
        self,
        query: str,
        collections: list[str] | None = None,
        top_k: int | None = None,
        filters: dict[str, dict] | None = None,
    ) -> dict[str, Any]:
        selected = collections or list(DEFAULT_COLLECTIONS)
        query_embedding = self.embeddings.embed_query(query)
        limit = top_k or self.top_k
        matches = []
        used = []
        for collection in selected:
            try:
                collection_matches = self.chroma.query(
                    collection,
                    query_embedding,
                    limit,
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
        sources = [self._source_from_match(match) for match in selected_matches]
        return {"context": context, "sources": sources, "collections_used": used, "matches": selected_matches}

    def _source_from_match(self, match: dict[str, Any]) -> dict[str, Any]:
        metadata = match.get("metadata") or {}
        return {
            "collection": match.get("collection"),
            "source": metadata.get("source"),
            "filename": metadata.get("filename"),
            "chunk_index": metadata.get("chunk_index"),
            "entity_id": metadata.get("entity_id"),
            "entity_type": metadata.get("entity_type"),
            "user_id": metadata.get("user_id"),
            "source_collection": metadata.get("source_collection"),
            "distance": match.get("distance"),
        }
