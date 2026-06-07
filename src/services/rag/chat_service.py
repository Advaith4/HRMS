import logging
import os
import re

from src.models import User
from src.services.rag.query_router import QueryRouter
from src.services.rag.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


class RAGChatService:
    def __init__(
        self,
        retrieval_service: RetrievalService | None = None,
        query_router: QueryRouter | None = None,
        max_context_chars: int | None = None,
    ):
        self.retrieval = retrieval_service or RetrievalService()
        self.query_router = query_router or QueryRouter()
        self.max_context_chars = max_context_chars or int(os.getenv("RAG_MAX_CONTEXT_CHARS", "6000"))

    def answer(
        self,
        query: str,
        collections: list[str] | None = None,
        filters: dict[str, dict] | None = None,
        user: User | None = None,
    ) -> dict:
        clean_query = (query or "").strip()
        if not clean_query:
            raise ValueError("query is required")

        route = self.query_router.route(clean_query, user) if user else None
        if route and route.mode == "database":
            answer = self._generate_answer(clean_query, self._trim_context(route.database_context))
            return {
                "answer": answer,
                "sources": route.database_sources,
                "collections_used": ["database"],
            }

        retrieval = self.retrieval.retrieve(clean_query, collections=collections, filters=filters)
        context_parts = []
        sources = []
        collections_used = []
        if route and route.mode == "hybrid" and route.database_context:
            context_parts.append(route.database_context)
            sources.extend(route.database_sources)
            collections_used.append("database")
        context_parts.append(retrieval["context"])
        sources.extend(retrieval["sources"])
        collections_used.extend(retrieval["collections_used"])
        context = self._trim_context("\n\n".join(part for part in context_parts if part.strip()))
        answer = self._generate_answer(clean_query, context)
        return {
            "answer": answer,
            "sources": sources,
            "collections_used": list(dict.fromkeys(collections_used)),
        }

    def _generate_answer(self, query: str, context: str) -> str:
        if not context.strip():
            return "I could not find relevant knowledge base content for that question."
        llm_answer = self._generate_llm_answer(query, context)
        if llm_answer:
            return llm_answer
        return self._extractive_answer(query, context)

    def _generate_llm_answer(self, query: str, context: str) -> str | None:
        provider = os.getenv("RAG_ANSWER_PROVIDER", "llm").strip().lower()
        if provider in {"extractive", "none", "off"}:
            return None
        if not os.getenv("GROQ_API_KEY"):
            return None
        try:
            import src.services.llm_router  # noqa: F401 - installs project LiteLLM routing
            import litellm

            model = os.getenv("RAG_ANSWER_MODEL", os.getenv("MODEL_NAME", "llama-3.1-8b-instant"))
            if not model.startswith("groq/"):
                model = f"groq/{model}"
            response = litellm.completion(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are TalentForge HRMS Copilot. Answer only from the provided context. "
                            "Be concise, practical, and mention when context is insufficient."
                        ),
                    },
                    {"role": "user", "content": f"QUESTION:\n{query}\n\nCONTEXT:\n{context}"},
                ],
                temperature=0.2,
                timeout=float(os.getenv("RAG_ANSWER_TIMEOUT", "10")),
            )
            answer = response.choices[0].message.content.strip()
            return answer or None
        except Exception as exc:  # noqa: BLE001
            logger.warning("RAG LLM answer generation failed; using extractive fallback. error=%s", exc)
            return None

    def _extractive_answer(self, query: str, context: str) -> str:
        query_terms = {term.lower() for term in re.findall(r"[A-Za-z0-9_]+", query) if len(term) > 2}
        sentences = re.split(r"(?<=[.!?])\s+|\n{2,}", context)
        candidates = [sentence.strip() for sentence in sentences if sentence.strip()]
        complete = [sentence for sentence in candidates if sentence.endswith((".", "!", "?"))]
        ranked = sorted(
            complete or candidates,
            key=lambda sentence: sum(1 for term in query_terms if term in sentence.lower()),
            reverse=True,
        )
        selected = ranked[:3]
        return " ".join(selected) if selected else context[:800]

    def _trim_context(self, context: str) -> str:
        if len(context) <= self.max_context_chars:
            return context
        return context[: self.max_context_chars].rsplit("\n\n", 1)[0] or context[: self.max_context_chars]
