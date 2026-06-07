import hashlib
import logging
import math
import os
import re
from abc import ABC, abstractmethod
from typing import Iterable

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def dimension(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class HashEmbeddingProvider(EmbeddingProvider):
    """Deterministic local embeddings for offline development and tests."""

    def __init__(self, dimension: int = 384):
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self._dimension
        tokens = re.findall(r"[A-Za-z0-9_]+", text.lower())
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self._dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model: str = "text-embedding-3-small"):
        from openai import OpenAI

        self.model = model
        self.client = OpenAI()
        self._dimension = 1536

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]


class EmbeddingService:
    def __init__(self, provider: EmbeddingProvider | None = None):
        self.provider = provider or build_embedding_provider()

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        clean_texts = [text or "" for text in texts]
        if not clean_texts:
            return []
        logger.info("Embedding %s text chunk(s)", len(clean_texts))
        return self.provider.embed_texts(clean_texts)


def build_embedding_provider() -> EmbeddingProvider:
    provider = os.getenv("RAG_EMBEDDING_PROVIDER", "hash").strip().lower()
    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("RAG_EMBEDDING_PROVIDER=openai but OPENAI_API_KEY is missing; using hash embeddings")
            return HashEmbeddingProvider()
        return OpenAIEmbeddingProvider(os.getenv("RAG_OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"))
    return HashEmbeddingProvider()
