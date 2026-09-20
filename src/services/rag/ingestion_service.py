"""
src/services/rag/ingestion_service.py
Enterprise Ingestion Service with Recursive Character Chunking and Rich Metadata Enrichment.
"""
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docx import Document as DocxDocument
from pypdf import PdfReader

from src.services.rag.chroma_service import ChromaService
from src.services.rag.chunking import RecursiveCharacterChunker
from src.services.rag.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


@dataclass(frozen=True)
class IngestionResult:
    collection: str
    source: str
    chunks_stored: int


class IngestionService:
    def __init__(
        self,
        chroma_service: ChromaService | None = None,
        embedding_service: EmbeddingService | None = None,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
    ):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be non-negative and smaller than chunk_size")
        self.chroma = chroma_service or ChromaService()
        self.embeddings = embedding_service or EmbeddingService()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunker = RecursiveCharacterChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def ingest_file(
        self,
        file_path: str | Path,
        collection: str,
        source_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        replace_existing: bool = True,
    ) -> IngestionResult:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"RAG source file not found: {path}")

        # 1. Multi-Page Extraction & Chunking with Page Tracking
        page_chunks = []
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            try:
                reader = PdfReader(str(path))
                for page_idx, page in enumerate(reader.pages, start=1):
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        chunks = self.chunker.split_text(page_text, page_number=page_idx)
                        page_chunks.extend(chunks)
            except Exception as exc:
                logger.warning("PDF page extraction failed for %s: %s. Falling back to whole-file.", path, exc)
                full_text = self.extract_text(path)
                page_chunks = self.chunker.split_text(full_text, page_number=1)
        else:
            full_text = self.extract_text(path)
            page_chunks = self.chunker.split_text(full_text, page_number=1)

        if not page_chunks:
            logger.warning("No chunks generated for document: %s", path)
            return IngestionResult(collection=collection, source=str(path), chunks_stored=0)

        # 2. Embeddings & Enriched Metadata
        chunk_texts = [c.text for c in page_chunks]
        embeddings = self.embeddings.embed_texts(chunk_texts)
        
        full_content = " ".join(chunk_texts)
        content_hash = hashlib.sha256(full_content.encode("utf-8")).hexdigest()
        sid = str(source_id or path.stem)

        base_metadata = {
            "source": str(path),
            "filename": path.name,
            "source_id": sid,
            "category": (metadata or {}).get("category", "policy"),
            "access_role": (metadata or {}).get("access_role", "employee"),
            "content_hash": content_hash,
        }
        if metadata:
            base_metadata.update(metadata)

        ids = []
        metadatas = []
        for idx, chunk in enumerate(page_chunks):
            cid = f"{collection}:{sid}:chunk:{idx + 1}"
            ids.append(cid)
            metadatas.append({
                **base_metadata,
                "chunk_id": cid,
                "chunk_index": idx + 1,
                "page_number": chunk.page_number,
                "char_start": chunk.char_start,
                "char_end": chunk.char_end,
            })

        # 3. Upsert to Chroma
        if replace_existing:
            self.chroma.delete_where(collection, {"source_id": sid})

        self.chroma.upsert_documents(collection, ids, chunk_texts, embeddings, metadatas)
        logger.info("Ingested %s into %s with %s chunk(s)", path, collection, len(chunk_texts))
        return IngestionResult(collection=collection, source=str(path), chunks_stored=len(chunk_texts))

    def ingest_text(
        self,
        text: str,
        collection: str,
        source_id: str,
        metadata: dict[str, Any] | None = None,
        replace_existing: bool = True,
    ) -> IngestionResult:
        page_chunks = self.chunker.split_text(text, page_number=1)
        if not page_chunks:
            return IngestionResult(collection=collection, source=source_id, chunks_stored=0)

        chunk_texts = [c.text for c in page_chunks]
        embeddings = self.embeddings.embed_texts(chunk_texts)
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        base_metadata = {
            "source": f"db:{source_id}",
            "filename": source_id,
            "source_id": source_id,
            "category": (metadata or {}).get("category", "general"),
            "access_role": (metadata or {}).get("access_role", "employee"),
            "content_hash": content_hash,
        }
        if metadata:
            base_metadata.update(metadata)

        ids = [f"{collection}:{source_id}:chunk:{i + 1}" for i in range(len(chunk_texts))]
        metadatas = [
            {
                **base_metadata,
                "chunk_id": ids[i],
                "chunk_index": i + 1,
                "page_number": page_chunks[i].page_number,
                "char_start": page_chunks[i].char_start,
                "char_end": page_chunks[i].char_end,
            }
            for i in range(len(chunk_texts))
        ]

        if replace_existing:
            self.chroma.delete_where(collection, {"source_id": str(source_id)})

        self.chroma.upsert_documents(collection, ids, chunk_texts, embeddings, metadatas)
        logger.info("Ingested text source_id=%s into %s with %s chunk(s)", source_id, collection, len(chunk_texts))
        return IngestionResult(collection=collection, source=source_id, chunks_stored=len(chunk_texts))

    def extract_text(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported RAG document type: {suffix}")
        if suffix == ".txt":
            return path.read_text(encoding="utf-8", errors="ignore")
        if suffix == ".pdf":
            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        document = DocxDocument(str(path))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)

    def chunk_text(self, text: str) -> list[str]:
        """Backward-compatible helper returning plain text chunk list."""
        chunks = self.chunker.split_text(text)
        return [c.text for c in chunks]
