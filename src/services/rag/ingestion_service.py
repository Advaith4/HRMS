import logging
import hashlib
from dataclasses import dataclass
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader

from src.services.rag.chroma_service import ChromaService
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
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be non-negative and smaller than chunk_size")
        self.chroma = chroma_service or ChromaService()
        self.embeddings = embedding_service or EmbeddingService()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def ingest_file(
        self,
        file_path: str | Path,
        collection: str,
        source_id: str | None = None,
        metadata: dict | None = None,
        replace_existing: bool = True,
    ) -> IngestionResult:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"RAG source file not found: {path}")
        text = self.extract_text(path)
        chunks = self.chunk_text(text)
        embeddings = self.embeddings.embed_texts(chunks)
        base_metadata = {
            "source": str(path),
            "filename": path.name,
            "source_id": source_id or path.stem,
        }
        if metadata:
            base_metadata.update(metadata)
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        base_metadata["content_hash"] = content_hash
        ids = [f"{collection}:{base_metadata['source_id']}:chunk:{index}" for index in range(len(chunks))]
        metadatas = [{**base_metadata, "chunk_index": index} for index in range(len(chunks))]
        if replace_existing:
            self.chroma.delete_where(collection, {"source_id": str(base_metadata["source_id"])})
        self.chroma.upsert_documents(collection, ids, chunks, embeddings, metadatas)
        logger.info("Ingested %s into %s with %s chunk(s)", path, collection, len(chunks))
        return IngestionResult(collection=collection, source=str(path), chunks_stored=len(chunks))

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
        normalized = " ".join((text or "").split())
        if not normalized:
            return []
        words = normalized.split()
        chunks: list[str] = []
        current: list[str] = []
        current_len = 0
        for word in words:
            next_len = current_len + len(word) + (1 if current else 0)
            if current and next_len > self.chunk_size:
                chunks.append(" ".join(current))
                overlap_words: list[str] = []
                overlap_len = 0
                for old_word in reversed(current):
                    candidate_len = overlap_len + len(old_word) + (1 if overlap_words else 0)
                    if candidate_len > self.chunk_overlap:
                        break
                    overlap_words.insert(0, old_word)
                    overlap_len = candidate_len
                current = overlap_words
                current_len = len(" ".join(current))
            current.append(word)
            current_len += len(word) + (1 if current_len else 0)
        if current:
            chunks.append(" ".join(current))
        return chunks
