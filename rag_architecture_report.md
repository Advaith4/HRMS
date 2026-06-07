# RAG Architecture Report

Generated: 2026-06-07

Phase 1 adds an isolated RAG foundation under `src/services/rag/` with ChromaDB persistence at `data/chroma/`.

## Components

- `embedding_service.py`: provider abstraction with deterministic local hash embeddings and optional OpenAI embeddings.
- `chroma_service.py`: `PersistentClient` wrapper and collection management.
- `ingestion_service.py`: PDF, DOCX, and TXT extraction, configurable chunking, embedding, and storage.
- `retrieval_service.py`: query embedding, top-k retrieval, context construction, and source attribution.
- `chat_service.py`: minimal answer generation from retrieved context.
- `src/api/routes/rag.py`: authenticated `POST /api/rag/chat` endpoint.

## Collections

- `company_policies`
- `job_descriptions`
- `candidate_profiles`
- `interview_reports`
- `employee_knowledge`

## Notes

- Default chunk size is `1000` with `200` overlap.
- Source metadata includes source path, filename, source id, chunk index, and collection.
- Local hash embeddings keep tests and development offline-capable. Set `RAG_EMBEDDING_PROVIDER=openai` and `OPENAI_API_KEY` to use OpenAI embeddings.
- No interview, authentication, hiring intelligence, employee, or candidate workflow logic was changed.
