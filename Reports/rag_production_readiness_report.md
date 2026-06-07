# RAG Production Readiness Report

Generated: 2026-06-07

## Architecture Findings

- Data flow is complete for Phase 3: HRMS entities sync into Chroma, retrieval builds context from Chroma matches, and `/api/rag/chat` returns answers with source attribution.
- Chroma persistence is production-oriented through `PersistentClient`; the storage path now supports `RAG_CHROMA_PATH` and defaults to `data/chroma`.
- Metadata is sufficient for future role-based access: `entity_id`, `entity_type`, `user_id`, `created_at`, `updated_at`, `source_collection`, plus entity-specific IDs.
- Sync operations are idempotent because deterministic document IDs are upserted rather than appended.
- Sync failures are logged and swallowed after primary HRMS commits, so Chroma availability does not break core workflows.

## Fixes Applied

- Added `src/services/rag/access_control.py`.
- Added authorization-aware retrieval filters for candidate-owned `candidate_profiles` and `interview_reports`.
- Hardened `/api/rag/chat` so collection access is generated from the authenticated user, not trusted client input.
- Added Chroma metadata filtering support in retrieval.
- Added source metadata fields to RAG responses while preserving the existing response shape.
- Added configurable Chroma storage path via `RAG_CHROMA_PATH`.
- Added automatic-sync and access-control tests.

## Retrieval Flow

```text
Authenticated user
-> server builds RAG access plan
-> query embedded
-> Chroma queried per authorized collection
-> private collections filtered by metadata when needed
-> top matches ranked by distance
-> context assembled
-> answer generated
-> sources returned
```

## Authorization Model

HR roles (`hr`, `admin`, `manager`) can retrieve:

- `company_policies`
- `job_descriptions`
- `candidate_profiles`
- `interview_reports`
- `employee_knowledge`

Candidates can retrieve:

- `company_policies`
- `job_descriptions`
- their own `candidate_profiles`
- their own `interview_reports`

Employees can retrieve:

- `company_policies`
- `job_descriptions`
- `employee_knowledge`

Client-provided collection lists are treated only as a requested scope. The server intersects them with role access rules and applies metadata filters where required.

## Validation Results

Passed:

```text
pytest tests/test_rag_foundation.py tests/test_rag_sync_service.py tests/test_rag_access_control.py tests/test_rag_automatic_sync.py tests/test_interview_stabilization.py tests/test_proctoring.py -q
34 passed, 12 warnings
```

Covered:

- TXT ingestion into Chroma.
- Sync create/update/delete idempotency.
- Job API create/update/delete sync.
- Resume/application analysis sync.
- Interview report persistence sync.
- Candidate cannot access another candidate's RAG data.
- HR can access authorized candidate RAG data.
- Chroma restart persistence.
- `/api/rag/chat` validation, authorization, and source attribution.

## Remaining Risks

- The default answer generator is extractive and deterministic. It is safe for backend readiness, but a future LLM answer provider should be added behind the existing chat service boundary.
- PDF/DOCX parsing quality depends on document structure and upstream libraries.
- Chroma sync is best-effort after HRMS commits; a future background reconciliation job can repair missed syncs if Chroma is unavailable during a write.
