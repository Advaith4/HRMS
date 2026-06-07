import logging
from dataclasses import dataclass
from pathlib import Path

from src.services.rag.chroma_service import ChromaService
from src.services.rag.embedding_service import EmbeddingService
from src.services.rag.ingestion_service import IngestionService, IngestionResult

logger = logging.getLogger(__name__)

COMPANY_DOC_COLLECTIONS = {
    "policies": "company_policies",
    "onboarding": "employee_knowledge",
    "training": "employee_knowledge",
}


@dataclass(frozen=True)
class CompanyDocsIngestionSummary:
    files_ingested: int
    chunks_ingested: int
    results: list[IngestionResult]


class CompanyDocsIngestionService:
    def __init__(
        self,
        docs_root: str | Path = "data/company_docs",
        ingestion_service: IngestionService | None = None,
    ):
        self.docs_root = Path(docs_root)
        self.ingestion = ingestion_service or IngestionService(
            ChromaService(),
            EmbeddingService(),
        )

    def ingest_all(self) -> CompanyDocsIngestionSummary:
        results: list[IngestionResult] = []
        for section, collection in COMPANY_DOC_COLLECTIONS.items():
            folder = self.docs_root / section
            if not folder.exists():
                logger.info("Company docs folder missing; skipping %s", folder)
                continue
            for path in sorted(folder.iterdir()):
                if not path.is_file() or path.suffix.lower() not in {".txt", ".md"}:
                    continue
                source_id = self._source_id(section, path)
                result = self.ingestion.ingest_file(
                    path,
                    collection,
                    source_id=source_id,
                    metadata={
                        "doc_section": section,
                        "doc_type": "company_document",
                        "source_collection": collection,
                    },
                    replace_existing=True,
                )
                results.append(result)
        chunks = sum(result.chunks_stored for result in results)
        logger.info("Company docs ingestion complete files=%s chunks=%s", len(results), chunks)
        return CompanyDocsIngestionSummary(files_ingested=len(results), chunks_ingested=chunks, results=results)

    def _source_id(self, section: str, path: Path) -> str:
        return f"company_docs:{section}:{path.stem}"
