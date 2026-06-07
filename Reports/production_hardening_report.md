# Production Hardening Report

Generated: 2026-06-07

Branch: `production-hardening`

## Issues Found

### 1. RAG Retrieval Outage Could Break Assistant Responses

Severity: Medium

Root cause:

- `RAGChatService.answer()` called Chroma retrieval directly for RAG and hybrid queries.
- If Chroma or embedding retrieval raised an unexpected exception, the request could fail even when hybrid database context was already available.
- This affected reliability for HR Copilot and Career Assistant during Chroma outages or transient retrieval failures.

Fix applied:

- Added a narrow fallback in `src/services/rag/chat_service.py`.
- Hybrid queries now return available live database context if Chroma retrieval fails.
- Pure RAG queries now return a graceful temporary-unavailable answer instead of raising an internal error.
- Errors are logged with stack traces for operations visibility.

Validation result:

- Added negative-path tests in `tests/test_rag_query_router.py`:
  - hybrid query falls back to database when Chroma is unavailable
  - RAG-only query fails gracefully when Chroma is unavailable

## Areas Audited

### HRMS Core

Reviewed through existing API coverage:

- jobs
- applications
- candidate flow
- resume-aware application/interview flow
- role-based API behavior

Validation:

```text
.venv\Scripts\python.exe -m pytest tests/test_api.py -q
13 passed, 42 warnings
```

No HRMS core code changes were required.

### Interview System

Reviewed as a frozen, feature-complete module.

Validation:

```text
.venv\Scripts\python.exe -m pytest tests/test_interview_stabilization.py tests/test_proctoring.py -q
19 passed, 29 warnings
```

No interview logic changes were made.

### RAG Platform

Reviewed:

- Chroma retrieval
- ingestion
- sync service
- access control
- source attribution
- query routing
- hybrid SQL + RAG intelligence
- candidate ownership filtering

Validation:

```text
.venv\Scripts\python.exe -m pytest tests/test_rag_query_router.py tests/test_rag_foundation.py tests/test_rag_sync_service.py tests/test_rag_access_control.py tests/test_rag_automatic_sync.py tests/test_rag_company_docs.py -q
26 passed, 1 warning
```

Fix applied only for verified Chroma/retrieval failure handling.

### Frontend

Reviewed:

- HR Copilot page
- Career Assistant page
- sidebar routes
- production bundle generation

Validation:

```text
npm run build
```

Result: passed.

No frontend code changes were required in this hardening pass.

### Security

Verified through tests and code review:

- candidate-owned RAG metadata filters
- HR/admin/manager access to HR Copilot data
- candidate denial for employee knowledge
- server-side query routing using authenticated user context
- endpoint-level routing through `/api/rag/chat`

No authorization defects were found during this pass.

### Performance

Reviewed:

- RAG query flow
- database query routing
- Chroma retrieval path
- frontend bundle output

No measurable performance regression was found. No speculative optimization was applied.

### Reliability

Verified failure modes:

- LLM unavailable already falls back to extractive answer generation.
- Empty context already returns a safe no-content answer.
- Chroma/retrieval unavailable now fails gracefully.
- Hybrid decision queries now preserve database-backed decision context during retrieval failure.

## Test Runner Note

A parallel validation attempt caused a PostgreSQL test schema race because multiple pytest processes reset the same `talentforge_test` schema concurrently.

Observed error:

```text
schema "public" does not exist
duplicate key value violates unique constraint "pg_type_typname_nsp_index"
```

Resolution:

- Reran the affected suites sequentially.
- Sequential runs passed.

This was a test execution concurrency issue, not an application regression.

## Files Modified

- `src/services/rag/chat_service.py`
- `tests/test_rag_query_router.py`
- `production_hardening_report.md`

## Remaining Risks

- Full frontend lint still has pre-existing unrelated warnings/errors from older files; production build passes.
- Query routing remains deterministic keyword-based by design.
- Chroma sync remains best-effort after HRMS commits; a future reconciliation command can repair missed syncs after extended outages.
- PostgreSQL-backed test suites should be run sequentially unless test database isolation is improved.
