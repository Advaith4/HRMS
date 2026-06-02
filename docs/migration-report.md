# JobifyAI Migration Report

Generated: 2026-06-02

## Purpose

This report analyzes the current JobifyAI codebase before any migration or refactor work. It identifies the current architecture, migration risks, safer migration units, and recommended order of work.

## Current Architecture

JobifyAI is a single FastAPI application that serves both the backend API and the static frontend.

- App entry point: `src/main.py`
- Static frontend: `static/`
- API routers: `src/api/routes/`
- SQLModel models: `src/models/__init__.py`
- Database setup and lightweight migrations: `src/database/connection.py`
- Resume analysis and repair logic: `src/resume_lab.py`
- CrewAI orchestration: `crew.py`
- CrewAI agents: `agents/`
- CrewAI tasks: `tasks/`
- Job provider integrations: `utils/job_search.py`

The current deployment model supports Docker and Render. The backend can serve the whole app, while `vercel.json` also allows static frontend deployment.

## Domain Breakdown

### Auth

Auth uses JWT bearer tokens and bcrypt password hashes.

Important files:

- `src/api/routes/auth.py`
- `src/core/security.py`
- `src/api/dependencies.py`

Migration notes:

- Login currently auto-registers unknown users for backward compatibility.
- Existing malformed or empty password hashes are repaired during login.
- This behavior is useful during legacy migration but should not be kept indefinitely in production.

### Resume Lab

Resume Lab handles PDF upload, text extraction, parsing, analysis, safe fixes, rescoring, manual edits, reset, and download.

Important files:

- `src/api/routes/resume.py`
- `src/resume_lab.py`
- `utils/resume_parser.py`

Migration notes:

- This is the safest domain to migrate first.
- `src/resume_lab.py` contains strong deterministic fallback behavior.
- Resume analysis output is validated with Pydantic models.
- Tests already cover parsing, repair, grounded fallback analysis, invented metric prevention, and fix application.

### Jobs

Jobs are fetched from live providers, ranked through CrewAI, and optionally tracked.

Important files:

- `src/api/routes/jobs.py`
- `utils/job_search.py`
- `crew.py`

Migration notes:

- Job provider code is reasonably isolated.
- The LLM is intended to rank real fetched jobs, not invent listings.
- Tracking starts a FastAPI background task for resume tailoring.
- Background tailoring is acceptable for a demo but should become a durable job queue for production.

### Interview

Interview logic supports general sessions, resume-aware sessions, adaptive difficulty, interviewer personas, coaching memory, daily plans, and saved history.

Important files:

- `src/api/routes/interview.py`
- `tasks/interview_task.py`
- `agents/interview_coach.py`
- `crew.py`

Migration notes:

- This is the highest-risk backend migration area.
- The route file is large and mixes routing, state management, scoring, memory, prompt context, persistence, and response shaping.
- Active sessions are held in an in-memory `_sessions` dictionary.
- The Dockerfile starts Uvicorn with multiple workers by default, which can make in-memory session state inconsistent between workers.

## Database State

The project uses SQLModel with SQLite locally and PostgreSQL in production.

Current tables:

- `users`
- `resumes`
- `job_applications`
- `interview_sessions`
- `career_coach_memory`

Migration notes:

- The app does not use Alembic.
- Startup runs lightweight idempotent migration helpers in `src/database/connection.py`.
- Several structured values are stored as JSON strings in text columns:
  - `Resume.parsed_resume`
  - `Resume.last_analysis`
  - `Resume.applied_fixes`
  - `JobApplication.tailored_resume_bullets`
  - `InterviewSession.messages`
  - `InterviewSession.personalization_context`
  - `CareerCoachMemory.recurring_weak_areas`
  - `CareerCoachMemory.score_trend`
  - `CareerCoachMemory.session_history`
  - `CareerCoachMemory.daily_plan`

This is workable for a demo, but a production migration should introduce versioned migrations and consider JSONB or normalized child tables where querying is needed.

## Frontend State

The frontend is a static HTML/CSS/JS application.

Important files:

- `static/index.html`
- `static/style.css`
- `static/script.js`

Migration notes:

- `static/script.js` is very large and owns most UI state, API calls, rendering, auth token handling, resume lab UI, jobs UI, and interview UI.
- API paths are mostly same-origin `/api/...`.
- JWT is stored in `localStorage`.
- If the frontend is split to Vercel or another host, API base URL configuration and CORS must be formalized.

## AI Orchestration State

CrewAI orchestration is centralized in `crew.py`, with agents and tasks split into folders.

Migration notes:

- Several model names are hardcoded in agent files.
- `settings.MODEL_NAME` exists but is not consistently used by agents.
- LLM calls are synchronous and happen during request handling for resume, jobs, and interview flows.
- Some flows include fallback behavior, but observability around LLM latency, retries, and failures is limited.

## Migration Risks

### High Risk

1. In-memory interview sessions with multi-worker deployment.
2. Unversioned database migrations.
3. Large mixed-responsibility interview route.
4. Large frontend controller with tightly coupled UI and API behavior.
5. Auth auto-registration during login.

### Medium Risk

1. JSON stored as text instead of typed JSON fields or normalized tables.
2. Background tailoring not backed by a durable queue.
3. Hardcoded model names and scattered environment loading.
4. Limited integration tests for jobs and interviews.
5. Static frontend assumes same-origin API paths.

### Lower Risk

1. Resume Lab deterministic logic is already well bounded.
2. Job provider fetching has a clear module boundary.
3. Docker and Render deployment are already present.

## Recommended Migration Order

### Phase 1: Stabilize Contracts

- Add API contract tests for resume, jobs, and interview payloads.
- Add tests for DB startup migration behavior.
- Add tests for interview resume-aware start and answer flow using mocked CrewAI calls.
- Freeze current frontend/API response shapes before refactoring.

### Phase 2: Database Migration Foundation

- Introduce Alembic or another versioned migration system.
- Convert existing startup migration logic into explicit migrations.
- Keep startup helpers temporarily as defensive compatibility checks.
- Decide whether JSON text fields should become PostgreSQL JSONB.

### Phase 3: Interview Service Extraction

- Move interview constants and normalization helpers out of the route file.
- Extract session state loading/saving into a service.
- Extract coach memory logic into a service.
- Extract daily plan generation into a service.
- Keep endpoint paths and response shapes unchanged during this phase.

### Phase 4: Replace In-Memory Session State

- Store all active interview state in the database, or use Redis if low-latency live state is needed.
- Remove dependency on process-local `_sessions`.
- Revisit `WEB_CONCURRENCY` after session state is externalized.

### Phase 5: AI Provider Configuration

- Centralize model names, API keys, temperature defaults, and provider settings in `src/config.py`.
- Make agent factories consume settings instead of hardcoded model names.
- Add structured logging around LLM latency and failures.

### Phase 6: Background Work Hardening

- Replace FastAPI background tailoring with a durable queue if production reliability is required.
- Track job status transitions explicitly.
- Store failure reasons for tailoring failures.

### Phase 7: Frontend Migration

- Extract API client logic from `static/script.js`.
- Add configurable API base URL.
- Split frontend state by domain: auth, resume, jobs, interview, coach.
- Consider a framework migration only after API behavior is protected by tests.

## Recommended Target Architecture

Short-term target:

```text
src/
  api/routes/
  services/
    auth_service.py
    resume_service.py
    jobs_service.py
    interview_service.py
    coach_memory_service.py
  repositories/
    resume_repository.py
    interview_repository.py
  ai/
    crew_runner.py
    schemas.py
  database/
    connection.py
    migrations/
```

Longer-term production target:

```text
Frontend
  Static/Vercel or framework app

Backend API
  FastAPI
  PostgreSQL
  Redis or DB-backed interview session state
  Durable worker queue for AI/background jobs

AI Layer
  Provider-configured CrewAI runners
  Structured schemas
  Retry/timeout/observability wrapper
```

## Test Gaps To Close Before Migration

- Auth legacy migration behavior.
- Resume upload with real or fixture PDF.
- Resume analyze with mocked CrewAI success and failure.
- Job feed with mocked provider results and mocked ranking.
- Job tracking background task behavior.
- Interview start, resume-aware start, answer, session reload, and delete.
- Database migration behavior on SQLite and PostgreSQL.
- Frontend smoke tests for login, upload, resume lab, jobs, and interview.

## Immediate Recommendations

1. Do not start with a frontend rewrite.
2. Do not change DB schema until versioned migrations exist.
3. Migrate Resume Lab first if a low-risk proof of migration is needed.
4. Migrate Interview only after tests and service boundaries are introduced.
5. Remove login auto-registration after confirming no legacy users depend on it.
6. Replace in-memory interview state before scaling beyond a single worker.

## Final Assessment

JobifyAI is migration-ready for a staged internal refactor, but not for a big-bang rewrite.

The safest path is:

1. Add contract tests.
2. Add versioned migrations.
3. Extract services behind unchanged endpoints.
4. Replace process-local interview state.
5. Then consider frontend/backend separation.

The highest-value first migration is the Resume Lab domain. The highest-risk migration is Interview, because it currently concentrates the most state, persistence, AI orchestration, and response-shaping behavior in one route module.
