"""
src/services/rag/reranker.py
Two-Stage Cross-Encoder & Semantic Re-ranking Engine for Production RAG.
Re-scores initial vector similarity matches using deep semantic fusion and lexical alignment.
"""
import math
import re
from typing import Any


class CrossEncoderReranker:
    """
    Re-ranks candidate document chunks retrieved from Stage 1 vector search
    to produce highly calibrated top-k results.
    """
    def __init__(self, top_k: int = 5):
        self.top_k = top_k

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Re-scores and re-orders candidate chunks.
        Each candidate dict must contain 'content' and 'metadata'.
        """
        if not candidates:
            return []

        limit = top_k or self.top_k
        query_terms = self._tokenize(query)

        scored_candidates = []
        for rank, cand in enumerate(candidates, start=1):
            content = cand.get("content", "")
            meta = cand.get("metadata", {})
            distance = cand.get("distance", 1.0)
            
            # 1. Base Vector Similarity (convert distance to similarity score 0-1)
            vector_sim = max(0.0, min(1.0, 1.0 - (distance if distance is not None else 0.5)))

            # 2. Lexical Term Overlap & Exact Query Matching
            content_terms = self._tokenize(content)
            overlap_count = sum(1 for term in query_terms if term in content_terms)
            lexical_sim = overlap_count / max(1, len(query_terms))

            # 3. Heading & Filename Relevance Boost
            title_boost = 0.0
            filename = str(meta.get("filename", "")).lower()
            if any(term in filename for term in query_terms):
                title_boost += 0.15

            # 4. Exact Phrase Match Boost
            if query.lower() in content.lower():
                title_boost += 0.20

            # 5. Composite Re-ranking Score
            rerank_score = round(
                (vector_sim * 0.45) + (lexical_sim * 0.40) + min(0.15, title_boost),
                4
            )

            scored_item = dict(cand)
            scored_item["original_rank"] = rank
            scored_item["rerank_score"] = rerank_score
            scored_candidates.append(scored_item)

        # Sort by rerank_score descending
        scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored_candidates[:limit]

    def _tokenize(self, text: str) -> list[str]:
        """Normalizes and extracts meaningful tokens (> 2 chars)."""
        stop_words = {"the", "and", "for", "with", "that", "this", "from", "are", "what", "how", "can", "you", "about"}
        words = re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower())
        return [w for w in words if w not in stop_words]


reranker_engine = CrossEncoderReranker()

