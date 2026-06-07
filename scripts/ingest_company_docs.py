import argparse
import json

from src.services.rag.company_docs_ingestion import CompanyDocsIngestionService


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest TalentForge company documents into Chroma RAG collections.")
    parser.add_argument("--docs-root", default="data/company_docs")
    args = parser.parse_args()

    summary = CompanyDocsIngestionService(args.docs_root).ingest_all()
    print(json.dumps({
        "files_ingested": summary.files_ingested,
        "chunks_ingested": summary.chunks_ingested,
        "results": [
            {"collection": item.collection, "source": item.source, "chunks_stored": item.chunks_stored}
            for item in summary.results
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
