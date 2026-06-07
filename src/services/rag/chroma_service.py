import logging
import os
from pathlib import Path
from typing import Any

import chromadb

logger = logging.getLogger(__name__)

DEFAULT_COLLECTIONS = (
    "company_policies",
    "job_descriptions",
    "candidate_profiles",
    "interview_reports",
    "employee_knowledge",
)


class ChromaService:
    def __init__(self, storage_path: str | Path | None = None):
        self.storage_path = Path(storage_path or os.getenv("RAG_CHROMA_PATH", "data/chroma"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.storage_path))
        self._collections = {
            name: self.client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})
            for name in DEFAULT_COLLECTIONS
        }
        logger.info("Initialized ChromaDB at %s", self.storage_path)

    def get_collection(self, name: str):
        if name not in DEFAULT_COLLECTIONS:
            raise ValueError(f"Unsupported RAG collection: {name}")
        if name not in self._collections:
            self._collections[name] = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[name]

    def add_chunks(
        self,
        collection_name: str,
        ids: list[str],
        chunks: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        if not chunks:
            return
        logger.info("Storing %s chunk(s) in RAG collection %s", len(chunks), collection_name)
        self.get_collection(collection_name).add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def upsert_documents(
        self,
        collection_name: str,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        if not documents:
            return
        logger.info("Upserting %s RAG document(s) in %s", len(documents), collection_name)
        self.get_collection(collection_name).upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def delete_ids(self, collection_name: str, ids: list[str]) -> None:
        if not ids:
            return
        logger.info("Deleting %s RAG document(s) from %s", len(ids), collection_name)
        self.get_collection(collection_name).delete(ids=ids)

    def delete_where(self, collection_name: str, where: dict[str, Any]) -> None:
        logger.info("Deleting RAG documents from %s where=%s", collection_name, where)
        self.get_collection(collection_name).delete(where=where)

    def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        collection = self.get_collection(collection_name)
        result = collection.query(query_embeddings=[query_embedding], n_results=top_k, where=where)
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        ids = result.get("ids", [[]])[0]
        matches = []
        for index, document in enumerate(documents):
            matches.append(
                {
                    "id": ids[index] if index < len(ids) else "",
                    "content": document,
                    "metadata": metadatas[index] if index < len(metadatas) else {},
                    "distance": distances[index] if index < len(distances) else None,
                    "collection": collection_name,
                }
            )
        return matches
