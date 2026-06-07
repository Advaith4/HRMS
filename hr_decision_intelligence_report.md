# HR Decision Intelligence Report

Generated: 2026-06-07

## Routing Strategy

Phase 6 adds `src/services/rag/query_router.py`.

The router classifies each assistant query into:

- `database`: live HRMS metrics and status questions.
- `rag`: policy, document, job-description, and general knowledge retrieval.
- `hybrid`: decision-support questions that need both live HRMS records and Chroma knowledge.

`/api/rag/chat` keeps the same API contract. The frontend still sends only:

```json
{
  "query": "..."
}
```

The backend now passes the authenticated user into `RAGChatService`, which uses `QueryRouter` to assemble the correct context server-side.

## Supported Query Categories

Database-only:

- application status
- candidate counts
- hiring pipeline metrics
- job statistics
- interview status
- employee statistics

RAG-only:

- company policies
- onboarding/training knowledge
- job-description content
- general authorized knowledge-base lookup

Hybrid decision intelligence:

- strongest candidates for a role
- shortlisted candidate comparison
- next-round recommendations
- hiring risk summaries
- JD-to-candidate matching
- active candidate summaries
- candidate skill-gap guidance
- interview feedback and preparation guidance

## Context Sources

Responses now attribute information from:

- `Database`
- `Resume Analysis`
- `Interview Reports`
- `Job Descriptions`
- `Policies`

Database source attribution is exposed as a simple `database` source in the existing `sources` response array. Internal table names and implementation details are not exposed to the UI.

## Hybrid Examples Covered

The test suite validates:

- HR database query: hiring pipeline application counts.
- RAG query: leave policy answer remains Chroma-backed.
- Hybrid candidate comparison: database candidate evidence plus retrieved job-description context.
- Candidate skill-gap guidance: candidate-owned application and analysis records only.
- Hiring recommendation summary: decision context from application status, resume analysis, interview report, and job requirements.
- API endpoint routing: `/api/rag/chat` uses authenticated user context when deciding the query route.

## HR Insights Generated

HR Copilot can now produce decision-support context containing:

- ranked candidate summaries using stored fit score and interview score
- candidate strengths, weaknesses, missing skills, and recommendations
- job requirements relevant to the decision
- application status and interview report summaries
- hiring risk cues from weaknesses, missing skills, and interview feedback
- pipeline and employee statistics from live HRMS records

The ranking score is decision-support only. It does not mutate HRMS scoring, interview intelligence scoring, or hiring workflows.

## Candidate Intelligence

Career Assistant can now answer candidate-owned questions using:

- live application status
- owned interview progress
- owned interview feedback
- resume analysis weaknesses and missing skills
- job requirements for applied roles

Candidate access restrictions remain server-side through the existing RAG access-control model and candidate-owned SQL queries.

## Validation Results

Passed:

```text
.venv\Scripts\python.exe -m pytest tests/test_rag_query_router.py -q
6 passed, 1 warning
```

Passed:

```text
.venv\Scripts\python.exe -m pytest tests/test_rag_query_router.py tests/test_rag_foundation.py tests/test_rag_sync_service.py tests/test_rag_access_control.py tests/test_rag_automatic_sync.py tests/test_rag_company_docs.py -q
24 passed, 1 warning
```

Interview guardrail passed:

```text
.venv\Scripts\python.exe -m pytest tests/test_interview_stabilization.py tests/test_proctoring.py -q
19 passed, 29 warnings
```

## Files Modified

- `src/api/routes/rag.py`
- `src/services/rag/chat_service.py`
- `src/services/rag/query_router.py`
- `tests/test_rag_query_router.py`

## Remaining Limitations

- Query routing is deterministic keyword-based. It is reliable and testable, but a future classifier can improve ambiguous wording.
- Hybrid ranking uses available stored scores and summaries; it does not replace recruiter judgment.
- Database intelligence currently summarizes core hiring/application/job/interview/employee data. More domains can be added later without changing the chat API.
- Missed Chroma syncs still require the future reconciliation command noted in earlier RAG reports.
