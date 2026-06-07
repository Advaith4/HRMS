# RAG Population Report

Generated: 2026-06-07

## Knowledge Directories

Created seeded company knowledge under `data/company_docs/`:

- `policies/`
- `onboarding/`
- `training/`

## Documents Ingested

Policies:

- Leave Policy
- Attendance Policy
- Remote Work Policy
- Code of Conduct
- Employee Handbook

Onboarding:

- New Employee Onboarding Guide
- First Week Checklist

Training:

- Engineering Best Practices
- Communication Guidelines
- Performance Review Process

Ingestion command:

```text
python -m scripts.ingest_company_docs --docs-root data/company_docs
```

Latest ingestion result:

```text
files_ingested=10
chunks_ingested=17
```

## Collection Statistics

Local persistent Chroma path: `data/chroma`

```text
company_policies: documents=5 chunks=9
job_descriptions: documents=4 chunks=4
candidate_profiles: documents=4 chunks=4
interview_reports: documents=1 chunks=1
employee_knowledge: documents=5 chunks=8
```

`job_descriptions`, `candidate_profiles`, and `interview_reports` were populated through the RAG sync service with representative HRMS knowledge records for retrieval validation.

## Ingestion Utility

Added:

- `src/services/rag/company_docs_ingestion.py`
- `scripts/ingest_company_docs.py`

The utility:

- ingests all `.txt` and `.md` files under `data/company_docs`
- routes `policies` to `company_policies`
- routes `onboarding` and `training` to `employee_knowledge`
- uses deterministic source IDs
- deletes old chunks for the same source before upserting new chunks
- supports re-ingestion after document edits without duplicates

## Answer Generation

Updated `chat_service` to support:

- token-safe context trimming through `RAG_MAX_CONTEXT_CHARS`
- LiteLLM/Groq answer generation through the existing project LLM router
- configurable answer provider through `RAG_ANSWER_PROVIDER`
- graceful extractive fallback when LLM keys or providers are unavailable
- cleaner fallback answers that prefer complete sentences

The API contract remains unchanged:

```json
{
  "answer": "...",
  "sources": [...],
  "collections_used": [...]
}
```

## Retrieval Examples

Policy questions:

- Leave policy answer: full-time employees receive 18 paid leave days per year; requests should be submitted at least five business days in advance.
- Remote work answer: eligible employees may work remotely up to two days per week with manager approval.

Employee knowledge:

- First week answer: new employees complete HR orientation, security training, access setup, onboarding tasks, and first-month goal alignment.

HR copilot questions:

- Strongest candidates: retrieval returned candidate profile, interview report, and job context for the Senior Backend Engineer role.
- Interview performance: retrieval returned the interview report showing strong FastAPI architecture, API debugging, PostgreSQL performance tuning, and clear incident ownership.
- Common applicant skills: retrieval returned candidate profile evidence including FastAPI, SQL, Docker, REST APIs, dashboards, PostgreSQL, and debugging.

Candidate assistant questions:

- Skill improvement: retrieval returned role requirements plus candidate profile weaknesses such as database tuning, system design evidence, and leadership examples.
- Job requirements: retrieval returned Senior Backend Engineer requirements: Python, FastAPI, PostgreSQL, API debugging, system design, and 5+ years of experience.

## Validation

Passed:

```text
pytest tests/test_rag_foundation.py tests/test_rag_sync_service.py tests/test_rag_access_control.py tests/test_rag_automatic_sync.py tests/test_rag_company_docs.py tests/test_interview_stabilization.py tests/test_proctoring.py -q
37 passed, 12 warnings
```

## Remaining Gaps Before UI

- The UI should pass only the user's query and optional requested scope; backend access control already enforces the actual allowed scope.
- A production reconciliation command can be added later to resync all database-backed entities after Chroma outages.
- LLM answer quality depends on `GROQ_API_KEY`; without it, the backend uses the safe extractive fallback.
