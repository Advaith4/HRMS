# TalentForge Architecture Report

Audit scope: FastAPI backend, SQLModel persistence, CrewAI/Groq AI flow, React/Vite frontend, current tests and build tooling. No source code changes were made for this audit.

## System Shape

- Backend entrypoint is `src.main:app`; routers are mounted directly in `src/main.py`.
- Domain code is split by API router under `src/api/routes/`, shared helpers under `src/services/`, and all tables in one large `src/models/__init__.py`.
- Frontend is a React 19 SPA with route-level pages in `frontend/src/pages/`, reusable UI in `frontend/src/components/`, and thin API wrappers in `frontend/src/api/`.
- AI orchestration is split across legacy `crew.py`, task definitions in `tasks/`, agents in `agents/`, and newer services such as `src/services/hiring_intelligence.py`, `src/services/interview_consistency.py`, and `src/services/interview_core.py`.

## Key Findings

| Severity | Finding | Evidence | Impact |
|---|---|---|---|
| Critical | Official interview route is a god module mixing candidate lifecycle, proctoring, HR intelligence, reporting, compare, decision actions, and transcription. | `src/api/routes/interview.py` spans start, answer, sessions, credibility, leaderboard, reports, advance/reject, transcribe, abandon, complete. | High regression risk; hard to test; blurred ownership and access-control boundaries. |
| Critical | Frontend and backend interview start contracts drifted. | Backend `StartForApplicationReq` requires `application_id` at `src/api/routes/interview.py:63`; all three start decorators call the same function at `src/api/routes/interview.py:79-82`; frontend still has manual/resume clients in `frontend/src/api/interview.js:11` and `frontend/src/api/interview.js:30`. | Manual/resume interview entrypoints can fail validation or behave incorrectly. |
| High | Stateful in-memory interview cache is used beside DB state. | `_sessions` is imported from `src.services.interview_core` in both official and mock routers. | Multi-worker deployments lose active sessions; restarts depend on partial DB reconstruction; races possible. |
| High | AI integration is split between legacy and new paths. | `crew.py` still owns `run_interview_start` and `run_interview_answer`; services also own hiring and credibility synthesis. | Hard to reason about cost, prompts, retries, and validation. |
| High | All models live in one monolithic module. | 30+ tables in `src/models/__init__.py`. | Increases coupling, slows navigation, makes migration ownership unclear. |
| High | Database migration model is hand-written startup ALTER/CREATE logic. | `create_db_and_tables()` calls many `_ensure_*` functions in `src/database/connection.py`. | No ordered migration history, no rollback, hard to validate production schema drift. |
| Medium | HR dashboard and intelligence APIs perform payload assembly inside route handlers. | `src/api/routes/dashboard.py`, `src/api/routes/interview.py`. | Business logic cannot be unit-tested cleanly and grows duplicate query patterns. |
| Medium | Frontend pages include very large containers. | `frontend/src/pages/hr/InterviewReports.jsx` is a large all-in-one dashboard page. | Higher render cost and maintenance burden. |
| Medium | Built frontend assets are committed under `static/`. | `static/assets/*`. | Build hash churn causes noisy diffs and can hide source-only audit changes. |

## Dependency Flow

- Frontend pages call wrappers in `frontend/src/api/*`.
- API routes perform validation, authorization, querying, and many domain operations inline.
- Shared services call SQLModel sessions and, for AI, call CrewAI/litellm/Groq directly.
- `src/main.py` imports all routers and startup DB migration functions.

## Circular/Boundary Concerns

- `interview.py` imports many private helpers from `interview_core.py`, suggesting the service boundary is not stable.
- `crew.py` is marked legacy in AGENTS.md but remains the live path for official and mock interview generation.
- Route modules import service internals whose names begin with underscores, increasing coupling.

## Recommended Phase 2 Direction

1. Split official interview into `candidate_interview`, `proctoring`, and `hr_interview_intelligence` routers.
2. Replace private helper imports with public service classes/functions.
3. Make DB state the source of truth for active sessions.
4. Move AI prompt orchestration behind a single LLM gateway with metrics.
5. Introduce Alembic or another real migration workflow before production.
