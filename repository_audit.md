# TalentForge Repository Census & Submission Readiness Audit

Audit date: 2026-06-07  
Scope: `D:\GitHub\HRMS` working tree, excluding `.git/` internals as repository metadata.  
Method: filesystem census with ignored files included, `git status`, `graphify query`, import/reference searches, startup/config inspection, frontend route/build inspection, and runtime entrypoint tracing. No application code was modified.

## 1. Executive Summary

TalentForge is a full-stack FastAPI + React/Vite HRMS and recruitment intelligence application. The runtime core is coherent: `src.main:app` creates the FastAPI app, initializes the database/migrations, registers API routers, and serves the built SPA from `static/`. The frontend source in `frontend/src/` builds into `static/` via `frontend/vite.config.js`, and the backend imports AI orchestration, RAG, interview, auth, employee, and application services through explicit module references.

The submission risk is not the application core. The risk is repository presentation. The working tree contains many files that are clearly local-only, generated, historical, or tool-specific: `.venv/`, `.opencode/node_modules/`, `.env`, `.env.postgres`, many SQLite databases and logs under `data/`, generated frontend assets under `static/`, graphify outputs, Python bytecode caches, scratch probes, temporary root scripts, local agent/tool folders, and a large set of historical reports. Several of these are already covered by `.gitignore`, which is strong evidence that they should not be part of a professional submission repository.

Important nuance: `crew.py` looks historical and the AGENTS notes say "Legacy - do not reference", but it is actively imported by `src/resume_lab.py`, `src/api/routes/interview.py`, and `src/api/routes/mock_interview.py`. It must be retained unless the runtime is refactored.

## 2. Repository Structure Overview

| Path | Purpose | Runtime Required | Submission Posture |
|---|---|---:|---|
| `src/` | FastAPI app, routers, models, services, config, auth, DB | Yes | Keep |
| `frontend/src/` | React SPA source, pages, API clients, components | Yes for source builds | Keep |
| `frontend/public/`, `frontend/index.html`, frontend config | Vite app shell and public assets | Yes for source builds | Keep |
| `static/` | Built SPA served by FastAPI | Yes for backend-only deployment unless rebuilt during deploy | Keep only if deployment uses prebuilt assets |
| `agents/`, `tasks/`, `utils/`, `crew.py` | CrewAI agents/tasks and utility functions used by runtime services | Yes | Keep |
| `scripts/` | Bootstrap/migration/ingestion/simulation commands | No for request runtime, yes for operations | Keep as support/dev tooling |
| `tests/`, `pytest.ini`, `frontend/tests/`, `frontend/playwright.config.js` | Backend and browser validation | No | Keep for technical review |
| `Dockerfile`, `docker-compose.yml`, `render.yaml`, `vercel.json`, `.dockerignore` | Deployment/container config | Deployment-specific | Keep or document selected path |
| `README.md`, `AGENTS.md`, `Reports/` | Docs, agent instructions, historical/audit reports | No | Keep curated docs; archive bulk reports |
| `data/` | SQLite DBs, uploads, logs, demo PDFs, local CrewAI/chroma storage | No for clean submission; runtime-created locally | GitIgnore |
| `.venv/`, `.pytest_cache/`, `__pycache__/`, `*.pyc` | Local generated dependency/test/cache files | No | GitIgnore / remove from repo |
| `.agents/`, `.opencode/`, `.codex/`, `graphify-out/` | Local AI agent/tooling and generated graph outputs | No | GitIgnore or archive externally |
| `scratch/`, `scratch_append.py`, `temp_backend_check.py`, `tests_login.py`, `check_ids.js` | Ad hoc probes and experiments | No | Archive or remove |

## 3. Complete File & Folder Census

This census classifies every repository item by either individual file or verified path pattern. Vendored/generated/runtime directories with thousands of files are covered by path-level rules because each file in those directories has the same responsibility and submission posture.

### Root Files

| File | Purpose / Responsibility | Active Reference Evidence | Category | Runtime Required |
|---|---|---|---|---:|
| `README.md` | Main project documentation, quickstart, API/deployment overview | Read by reviewers, not imported | Documentation | No |
| `AGENTS.md` | Local agent/project instructions and architecture notes | Supplied as repo instructions; not runtime | Development Tooling | No |
| `requirements.txt` | Python dependency manifest | Dockerfile copies it; quickstart uses it | Configuration | Yes |
| `Dockerfile` | Production backend container image | `render.yaml` points to it | Deployment | Deployment yes |
| `docker-compose.yml` | Local PostgreSQL service | No app import; local infra | Deployment | No |
| `render.yaml` | Render deployment manifest | References `Dockerfile`, health path `/api/health` | Deployment | Deployment yes |
| `vercel.json` | Static SPA deployment to Vercel from `static/` | Routes `static/index.html` and assets | Deployment | Deployment-specific |
| `.dockerignore` | Docker build exclusion policy | Used by Docker build context | Configuration | Deployment yes |
| `.gitignore` | Repository ignore policy | Lists `.env`, `.venv/`, `data/`, `*.db`, `.agents/`, `.opencode/`, `.codex/`, logs | Configuration | No |
| `.env.example` | Safe env variable template | Matches `src/config.py` settings | Configuration | No runtime, yes onboarding |
| `.env` | Local secret/runtime env file | `src/config.py` loads `.env`; `.gitignore` excludes it | Configuration | Local only |
| `.env.postgres` | Alternate/local DB env file | Not auto-loaded by `src/config.py`; local deployment aid | Configuration | No |
| `pytest.ini` | Pytest config | Sets `pythonpath = .`, `testpaths = tests` | Testing | No |
| `app.py` | Compatibility entrypoint delegating to `src.main:app` | Contains `from src.main import app` | Runtime Support | Optional |
| `crew.py` | CrewAI orchestration for resume, jobs, interviews | Imported by `src/resume_lab.py`, `src/api/routes/interview.py`, `src/api/routes/mock_interview.py` | Runtime Critical | Yes |
| `check_ids.js` | Static HTML/script ID checker for old static app shape | References `static/script.js`, which is not present in current build | Temporary | No |
| `temp_backend_check.py` | Manual local HTTP probe for backend root | `requests.get('http://127.0.0.1:8000')`; not imported | Temporary | No |
| `tests_login.py` | Manual register/login probe | Direct local HTTP requests; not under `tests/` | Temporary | No |
| `scratch_append.py` | Appends text to a user IDE/agent walkthrough path outside repo | Writes to `C:/Users/Acer/.gemini/...`; not runtime | Temporary | No |

### Backend Source: `src/`

| Path | Purpose / Responsibility | Evidence | Category | Runtime Required |
|---|---|---|---|---:|
| `src/__init__.py` | Package marker | Enables `src.*` imports | Runtime Support | Yes |
| `src/main.py` | FastAPI app entrypoint, middleware, lifespan DB init, router registration, SPA static mount | Imports settings, DB, handlers, routers; mounted by Docker CMD and `app.py` | Runtime Critical | Yes |
| `src/config.py` | Pydantic settings from `.env` | `settings = Settings()` used by DB, security, main, agents | Runtime Critical | Yes |
| `src/resume_lab.py` | Resume text cleanup, parsing, analysis validation, fixes, fallback scoring | Imported by resume/application routes and utils; imports `crew.run_resume_analyzer` | Runtime Critical | Yes |
| `src/database/__init__.py` | DB package marker | Enables database package import | Runtime Support | Yes |
| `src/database/connection.py` | Engine/session creation, schema creation, idempotent migrations | `src.main` calls `create_db_and_tables()` during lifespan | Runtime Critical | Yes |
| `src/models/__init__.py` | SQLModel table definitions and `USER_ROLES` | Imported by DB creation, dependencies, routes, services; defines 30+ tables | Runtime Critical | Yes |
| `src/api/__init__.py` | API package marker | Enables router imports | Runtime Support | Yes |
| `src/api/dependencies.py` | Auth/RBAC dependencies | Imported by routers; decodes JWT and role guards | Runtime Critical | Yes |
| `src/core/__init__.py` | Core package marker | Enables core imports | Runtime Support | Yes |
| `src/core/security.py` | bcrypt password hashing, JWT encode/decode | Imported by auth/dependencies/database bootstrap | Runtime Critical | Yes |
| `src/core/exceptions.py` | Standard FastAPI exception handlers | Registered in `src.main.py` | Runtime Critical | Yes |
| `src/api/routes/*.py` | API routers for auth, resume, jobs, applications, candidates, employees, dashboard, interview, mock interview, departments, designations, lifecycle, tickets, salary, promotions, notifications, onboarding, training, profile, rag, admin | All imported in `src.main.py` and included via `app.include_router(...)` | Runtime Critical | Yes |
| `src/services/*.py` | AI, interview, transcription, employee, hiring intelligence, LLM routing services | Imported by routes and `crew.py`; direct runtime call paths | Runtime Critical | Yes |
| `src/services/rag/*.py` | RAG access, chat, ingestion, embeddings, retrieval, Chroma sync, company docs | Imported by RAG/admin/employees/jobs/recruitment/hiring services and tests | Runtime Critical / Support | Yes |

### Backend AI/Utility Packages

| Path | Purpose / Responsibility | Evidence | Category | Runtime Required |
|---|---|---|---|---:|
| `agents/interview_coach.py` | CrewAI interview agents | Imported by `crew.py` | Runtime Critical | Yes |
| `agents/job_finder.py` | CrewAI job finder agent | Imported by `crew.py` | Runtime Critical | Yes |
| `agents/recruitment_analyst.py` | CrewAI application-analysis agent | Imported by `src/services/recruitment_ai.py` | Runtime Critical | Yes |
| `agents/resume_optimizer.py` | CrewAI resume optimizer/rewriter agents | Imported by `crew.py` | Runtime Critical | Yes |
| `agents/skill_matcher.py` | Skill matching agent/module | No direct import found in first-party runtime scan | Manual Review Required | No evidence |
| `tasks/interview_task.py` | CrewAI interview/evaluator/follow-up tasks | Imported by `crew.py` | Runtime Critical | Yes |
| `tasks/job_task.py` | CrewAI role inference/job ranking tasks | Imported by `crew.py` | Runtime Critical | Yes |
| `tasks/recruitment_task.py` | CrewAI application-analysis task | Imported by `src/services/recruitment_ai.py` | Runtime Critical | Yes |
| `tasks/resume_task.py` | CrewAI resume task definitions | Imported by `crew.py` | Runtime Critical | Yes |
| `tasks/match_task.py` | Matching task module | No direct import found in first-party runtime scan | Manual Review Required | No evidence |
| `utils/resume_parser.py` | PDF extraction/cleaning helpers | Imported by `src/api/routes/resume.py` and `applications.py` | Runtime Critical | Yes |
| `utils/job_search.py` | Jooble/RapidAPI job fetching | Imported by `crew.py` | Runtime Support | Yes when live jobs enabled |
| `utils/skill_scorer.py` | Match score, priority, action plan helpers | Imported by `crew.py` | Runtime Critical | Yes |

### Frontend Source: `frontend/`

| Path | Purpose / Responsibility | Evidence | Category | Runtime Required |
|---|---|---|---|---:|
| `frontend/package.json` | Frontend dependencies and scripts | Defines `dev`, `build`, `lint`, `e2e` | Configuration | Yes for source build |
| `frontend/package-lock.json` | Locked npm dependency graph | Used by reproducible install/build | Configuration | Yes for source build |
| `frontend/vite.config.js` | Vite config, React/Tailwind plugins, build output to `../static`, `/api` proxy | `npm run build` uses it | Configuration | Yes for source build |
| `frontend/index.html` | Vite HTML shell | Vite entry document | Runtime Critical | Yes for source build |
| `frontend/eslint.config.js` | ESLint config | `npm run lint` uses it | Development Tooling | No |
| `frontend/playwright.config.js` | Browser E2E config | `npm run e2e` uses it; starts Vite dev server | Testing | No |
| `frontend/README.md` | Vite/React frontend docs | Documentation only | Documentation | No |
| `frontend/.gitignore` | Frontend local ignore policy | Tooling config | Configuration | No |
| `frontend/public/icons.svg`, `frontend/public/favicon.svg` | Public static assets copied by Vite | Referenced by Vite public asset handling | Runtime Support | Yes for source build |
| `frontend/src/main.jsx` | React root entry | Imports `App.jsx` and `index.css` | Runtime Critical | Yes |
| `frontend/src/App.jsx` | Routes, role guards, lazy page imports, layout wiring | Lazy imports dashboards/interviews/assistant/admin pages | Runtime Critical | Yes |
| `frontend/src/index.css`, `frontend/src/App.css` | Global styling | Imported by frontend entry/app | Runtime Support | Yes |
| `frontend/src/api/*.js` | Axios client and endpoint-specific API wrappers | Imported throughout pages/components; maps to backend `/api/*` routes | Runtime Critical | Yes |
| `frontend/src/store/*.js` | Zustand auth/layout state | Imported by route guards/layout/API client | Runtime Critical | Yes |
| `frontend/src/context/ThemeContext.jsx` | Theme provider | Used in `App.jsx` | Runtime Support | Yes |
| `frontend/src/hooks/*.js` | Recorder/media hooks | Imported by interview workspace | Runtime Critical | Yes |
| `frontend/src/pages/**/*.jsx` | Role dashboards, interview pages, HR subpages, assistant, admin | Lazy-loaded or imported by dashboards/routes | Runtime Critical | Yes |
| `frontend/src/components/**/*.jsx` | Layout, UI, modals, drawers, interview, charts, profile widgets | Imported by pages/layout | Runtime Critical | Yes |
| `frontend/src/assets/hero.png` | Login hero image | Imported by `LoginPage.jsx` | Runtime Support | Yes |
| `frontend/src/assets/react.svg`, `frontend/src/assets/vite.svg` | Vite starter assets | No evidence from current imports except file presence; likely leftover | Manual Review Required | No evidence |
| `frontend/tests/e2e/interview-browser-validation.spec.js` | Browser E2E validation | Playwright config points to `tests/e2e` | Testing | No |

### Built Frontend: `static/`

| Path | Purpose / Responsibility | Evidence | Category | Runtime Required |
|---|---|---|---|---:|
| `static/index.html` | Built SPA shell served by FastAPI and Vercel config | `src.main` mounts `static`; `vercel.json` routes to it | Generated Artifact / Runtime Support | Yes if deploy does not rebuild frontend |
| `static/favicon.svg`, `static/icons.svg` | Built/copied static assets | Served by FastAPI static mount | Generated Artifact / Runtime Support | Yes with prebuilt static |
| `static/assets/*.js`, `static/assets/*.css`, `static/assets/*.png` | Hashed Vite build chunks and assets | `frontend/vite.config.js` outputs to `../static`; `static/index.html` references hashed assets | Generated Artifact / Runtime Support | Yes with prebuilt static |

### Tests and Validation

| Path | Purpose / Responsibility | Evidence | Category | Runtime Required |
|---|---|---|---|---:|
| `tests/conftest.py` | Test fixtures/environment | Imported by pytest | Testing | No |
| `tests/test_api.py` | Core API tests | Imports `src.main`, routes, services, models | Testing | No |
| `tests/test_resume_lab.py` | Resume lab pure-function tests | Imports `src.resume_lab` | Testing | No |
| `tests/test_proctoring.py` | Proctoring/interview behavior tests | Imports interview route/core | Testing | No |
| `tests/test_hiring_intelligence.py` | Hiring intelligence tests | Imports hiring service/models | Testing | No |
| `tests/test_interview_stabilization.py` | Interview state/status tests | Imports interview status/core/routes | Testing | No |
| `tests/test_job_lifecycle.py` | Job lifecycle tests | Imports application route, DB, models | Testing | No |
| `tests/test_phase2a.py` | Onboarding/training phase tests | Imports Phase 2 models/routes via app | Testing | No |
| `tests/test_rag_*.py` | RAG foundation, query, sync, company docs, access control tests | Import RAG services and routes | Testing | No |
| `tests_login.py` | Manual HTTP login script outside pytest suite | Not included by `pytest.ini testpaths = tests` | Temporary | No |

### Scripts

| Path | Purpose / Responsibility | Evidence | Category | Runtime Required |
|---|---|---|---|---:|
| `scripts/__init__.py` | Scripts package marker | Enables `python -m scripts.*` | Runtime Support | No |
| `scripts/bootstrap_user.py` | Bootstrap privileged users | AGENTS quickstart references `python -m scripts.bootstrap_user` | Development Tooling | Operational support |
| `scripts/init_database.py` | Local DB initialization | Script-only; no runtime import found | Development Tooling | No |
| `scripts/migrate_sqlite_to_postgres.py` | Data migration helper | Script-only; deployment/data migration support | Development Tooling | No |
| `scripts/ingest_company_docs.py` | RAG company docs ingestion | Imports `CompanyDocsIngestionService` | Development Tooling | No |
| `scripts/simulate_interview.py` | Local simulated interview flow | Script-only; imports models/routes | Experimental | No |

### Documentation and Historical Reports

| Path | Purpose / Responsibility | Evidence | Category | Runtime Required |
|---|---|---|---|---:|
| `Reports/*.md` | Historical cleanup, RAG, production, employee, HR, roadmap, sync reports | Markdown docs; no runtime imports | Documentation / Archive | No |
| `Reports/audit_reports-Report2/*.md` | Prior audit reports | Markdown docs | Archive / Historical | No |
| `Reports/artifacts-Report1/*.md` | LLM/interview pipeline artifacts | Markdown docs | Archive / Historical | No |
| `Reports/docs-Report3/*.md` | Day 3 documentation | Markdown docs | Documentation / Archive | No |
| `Reports/docs-Report3/screenshots/*.png` | Documentation screenshots | Image docs | Documentation / Archive | No |
| `Reports/phase2_reports-Report4/*.md` | Phase 2 implementation/security/performance reports | Markdown docs | Archive / Historical | No |

Note: `git status --short` shows many deleted files in old root folders (`audit_reports/`, `docs/`, `phase2_reports/`, etc.) and an untracked `Reports/` folder. Evidence suggests reports were reorganized but not yet staged/committed. This is a repository hygiene item, not a runtime issue.

### Runtime Data, Local Artifacts, and Generated Files

| Path Pattern | Purpose / Responsibility | Evidence | Category | Runtime Required |
|---|---|---|---|---:|
| `data/*.db`, `data/test_*.db`, `data/demo.db`, `data/hrms.db`, `data/interview_smoke_*.db` | Local SQLite databases from dev/test/demo runs | `.gitignore` excludes `data/` and `*.db`; tests create isolated DBs | Generated Artifact / Temporary | No |
| `data/*.log`, `data/vite-dev.*.log`, `data/server.log` | Local server/Vite logs | `.gitignore` excludes `data/` and `*.log` | Generated Artifact | No |
| `data/profile_documents/**` | Uploaded candidate/employee documents | Runtime user uploads; `.gitignore` excludes `data/` | Generated Artifact / Sensitive Runtime Data | No for submission |
| `data/.crewai_storage/**` | Local CrewAI storage | `src.main._prepare_crewai_storage()` creates under `data/.crewai_storage` | Generated Artifact | No |
| `data/chroma/**` if present | RAG vector storage | `.gitignore` explicitly excludes `data/chroma/`; `ChromaService` default path is `data/chroma` | Generated Artifact | No |
| `data/*.py` (`gen_resumes.py`, `e2e_demo.py`, `e2e_validation.py`, `calibration_test.py`, `timing_test.py`) | Local demo/calibration scripts stored with runtime data | Not imported by runtime; under ignored `data/` | Experimental / Temporary | No |
| `data/resume_*.pdf`, `data/test.pdf` | Demo/test PDFs | Not imported; under ignored `data/` | Testing / Temporary | No |
| `__pycache__/**`, `src/**/__pycache__/**`, `agents/**/__pycache__/**`, `tasks/**/__pycache__/**`, `tests/**/__pycache__/**`, `utils/**/__pycache__/**`, `scratch/**/__pycache__/**` | Python bytecode caches | `.gitignore` excludes `__pycache__/`, `**pycache**/`, `*.pyc` | Generated Artifact | No |
| `.pytest_cache/**` | Pytest cache | `.gitignore` excludes `.pytest_cache/` | Generated Artifact | No |
| `.venv/**` | Local Python virtualenv and installed packages | `.gitignore` excludes `.venv/`; dependencies are represented by `requirements.txt` | Generated Artifact / Development Tooling | No |
| `.opencode/**`, `.opencode/node_modules/**` | Local OpenCode plugin/config and Node dependencies | `.gitignore` excludes `.opencode/` and `node_modules/` | Development Tooling / Generated Artifact | No |
| `.agents/**` | Local Codex/agent skills and docs | `.gitignore` excludes `.agents/`; not app runtime | Development Tooling | No |
| `.codex/**` | Local Codex hooks/config | `.gitignore` excludes `.codex/` | Development Tooling | No |
| `graphify-out/**` | Generated graphify graph, HTML, manifest, chunks, lock, costs | AGENTS says graph exists; generated by graphify; `.gitignore` only excludes some cache files, not all output | Generated Artifact / Development Tooling | No |
| `scratch/**` | Ad hoc probes, logs, route lists, benchmarks, DB/API audits | Not imported; named scratch; logs/probes | Experimental / Temporary | No |

## 4. Runtime Dependency Analysis

### Backend Startup Flow

Evidence:

- `Dockerfile` CMD runs `uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}`.
- `app.py` imports `app` from `src.main` for compatibility.
- `src/main.py` imports `settings`, `create_db_and_tables`, exception handlers, and all route modules.
- Lifespan calls `create_db_and_tables()` on startup.
- `src/main.py` registers middleware, `/api/health`, 21 routers, and mounts `static/` last with SPA fallback.

Required backend runtime files:

- `src/main.py`, `src/config.py`, `src/database/connection.py`, `src/models/__init__.py`
- `src/api/dependencies.py`, `src/core/security.py`, `src/core/exceptions.py`
- all files under `src/api/routes/`
- all imported service modules under `src/services/` and `src/services/rag/`
- `agents/`, `tasks/`, `utils/`, and `crew.py`
- `requirements.txt`
- `.env` or equivalent environment variables at runtime, but not committed

### Router and Service Mapping

Evidence from `src/main.py`:

`auth`, `resume`, `jobs`, `applications`, `candidates`, `employees`, `dashboard`, `interview`, `mock_interview`, `departments`, `designations`, `lifecycle`, `tickets`, `salary`, `promotions`, `notifications`, `onboarding`, `training`, `profile`, `rag`, and `admin` are imported and included.

Selected service dependencies:

- `applications.py` imports `parse_resume`, `recruitment_ai`, `interview_status`, `utils.resume_parser`.
- `resume.py` imports `utils.resume_parser`.
- `interview.py` imports interview core/status, hiring intelligence, transcription service, `crew.run_interview_answer`.
- `mock_interview.py` imports `crew.run_interview_start`, `crew.run_interview_answer`, and mock summary service.
- `jobs.py`, `recruitment_ai.py`, and `hiring_intelligence.py` sync data into RAG through `RAGSyncService`.
- `employees.py` uses `employee_ai`, `RAGAccessControl`, and `RAGChatService`.
- `admin.py` uses RAG ingestion/embedding/chroma services for policy/knowledge management.

### Frontend Runtime Flow

Evidence:

- `frontend/src/main.jsx` imports `App.jsx` and `index.css`.
- `frontend/src/App.jsx` defines role guards and routes, lazy-loads all dashboard/interview/admin/assistant pages.
- `frontend/src/api/axios.js` configures base URL, bearer token injection, 30s GET cache, and 401 logout.
- `frontend/vite.config.js` builds to `../static` and proxies `/api` to `127.0.0.1:8000` during dev.
- `src/main.py` serves `static/` as the production SPA mount.

Required frontend runtime files:

- For source repository/build: `frontend/package*.json`, `frontend/vite.config.js`, `frontend/index.html`, `frontend/public/`, `frontend/src/`.
- For backend-only deployment without frontend build step: `static/index.html`, `static/assets/*`, `static/icons.svg`, `static/favicon.svg`.

### Database Runtime

Evidence:

- `src/config.py` defines `DATABASE_URL`, `PGSSLMODE`, pooling, and schema flags.
- `src/database/connection.py` requires nonempty `DATABASE_URL`, normalizes Postgres URLs, creates SQLModel engine, and creates/migrates tables at startup.
- Tests override `DATABASE_URL` to isolated SQLite DBs before importing `src.main`.

Required:

- Runtime requires a configured database URL.
- Local SQLite DB files under `data/` are not required in submission because schema is created from models/migrations.
- PostgreSQL/Supabase settings belong in environment variables, not committed `.env`.

### AI/ML Runtime

Evidence:

- `requirements.txt` includes `crewai`, `groq`, `litellm`, `openai`, `chromadb`.
- `src/services/llm_router.py` routes LLM calls and reads `GROQ_API_KEY`.
- `agents/*.py` create CrewAI agents via `get_llm`.
- `crew.py`, `recruitment_ai.py`, `employee_ai.py`, `interview_consistency.py`, `hiring_intelligence.py`, and RAG services provide deterministic fallback paths where applicable.

Required:

- Source code in `agents/`, `tasks/`, `utils/`, `crew.py`, `src/services/`.
- API keys via environment for full AI behavior.
- No generated CrewAI storage or Chroma DB files are required in repository submission.

### Auth Runtime

Evidence:

- `src/core/security.py` hashes/verifies passwords and creates/decodes JWTs using `settings.SECRET_KEY`.
- `src/api/dependencies.py` uses `HTTPBearer`, `decode_token`, `User`, and role guards.
- `src/models/__init__.py` defines `USER_ROLES`.
- `src/config.py` validates production secret strength for non-SQLite/non-debug deployments.

Required:

- `src/core/security.py`, `src/api/dependencies.py`, `src/models/__init__.py`, `src/config.py`.
- Secret key via environment, not committed.

## 5. Classification Table

| Category | Files / Folders |
|---|---|
| Runtime Critical | `src/main.py`, `src/config.py`, `src/database/connection.py`, `src/models/__init__.py`, `src/api/dependencies.py`, `src/core/security.py`, `src/core/exceptions.py`, `src/api/routes/*.py`, `src/services/**/*.py`, `src/resume_lab.py`, `crew.py`, runtime-used files in `agents/`, `tasks/`, `utils/`, `frontend/src/**`, `frontend/index.html`, `frontend/public/**` |
| Runtime Support | `app.py`, package `__init__.py` files, `static/**` when using prebuilt frontend deployment, `scripts/bootstrap_user.py` for operational bootstrap |
| Documentation | `README.md`, selected `Reports/docs-Report3/*.md`, selected screenshots, selected production/RAG reports if curated |
| Deployment | `Dockerfile`, `docker-compose.yml`, `render.yaml`, `vercel.json`, `.dockerignore` |
| Configuration | `requirements.txt`, `.env.example`, `.gitignore`, `pytest.ini`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/vite.config.js`, `frontend/eslint.config.js`, `frontend/.gitignore`, `frontend/playwright.config.js` |
| Development Tooling | `scripts/*.py`, `.agents/**`, `.opencode/**`, `.codex/**`, `graphify-out/**` |
| Testing | `tests/**`, `frontend/tests/**`, demo/test PDFs only if intentionally retained for tests |
| Experimental | `scratch/**`, `scripts/simulate_interview.py`, `data/*.py`, possibly `agents/skill_matcher.py`, `tasks/match_task.py` |
| Temporary | `temp_backend_check.py`, `tests_login.py`, `scratch_append.py`, `check_ids.js`, logs |
| Generated Artifact | `.venv/**`, `node_modules/**`, `__pycache__/**`, `*.pyc`, `.pytest_cache/**`, `static/**`, `data/*.db`, `data/.crewai_storage/**`, `data/chroma/**`, `graphify-out/**` |
| Archive / Historical | Bulk `Reports/**` implementation/audit/history files, old moved report folders shown as deleted by git status |
| Unknown | No fully unknown first-party runtime files after inspection; only `agents/skill_matcher.py` and `tasks/match_task.py` require manual review because no runtime import was found |

## 6. Professional Submission Review

Flagged items that may make the repository look temporary, experimental, duplicated, unfinished, generated, debug-only, or development-only:

| Item | Concern | Evidence |
|---|---|---|
| `.env`, `.env.postgres` | Secrets/local credentials risk | `.gitignore` excludes `.env`; `src/config.py` loads `.env`; `.env.example` exists |
| `.venv/` | Vendored local environment bloats repository | `.gitignore` excludes `.venv/`; dependencies are in `requirements.txt` |
| `.opencode/node_modules/` | Vendored local tool dependencies | `.gitignore` excludes `.opencode/` and `node_modules/` |
| `data/*.db`, `data/profile_documents/**`, `data/.crewai_storage/**` | Runtime/generated/sensitive user data | `.gitignore` excludes `data/`; app creates storage and uploads under `data/` |
| `__pycache__/**`, `*.pyc`, `.pytest_cache/**` | Generated caches | `.gitignore` excludes them |
| `scratch/**`, `scratch_append.py`, `temp_backend_check.py`, `tests_login.py`, `check_ids.js` | Ad hoc debugging/manual probes | Not imported; root scripts read localhost or missing `static/script.js` |
| `graphify-out/**` | Generated tool output | AGENTS says graph generated at `graphify-out/`; not app runtime |
| `Reports/**` bulk | Reviewer noise and historical clutter | Many report sets from prior phases; no runtime imports |
| `static/**` | Generated frontend output may duplicate source | Vite builds `frontend` to `static`; FastAPI serves it |
| `frontend/src/assets/react.svg`, `frontend/src/assets/vite.svg` | Starter-template residue | No import evidence found in current route/component scan |
| `agents/skill_matcher.py`, `tasks/match_task.py` | Possible unused/older matching path | No direct runtime import found |
| `crew.py` naming/comment | Looks legacy, but is runtime-critical | Imported by resume/interview/mock routes; should be renamed only via future refactor |
| Git status report move | Working tree appears mid-reorganization | `git status --short` shows old report paths deleted and new `Reports/` untracked |

## 7. Cleanup Recommendations

### Keep

| Item | Reason | Evidence | Confidence |
|---|---|---|---:|
| `src/**` excluding caches | Application backend core | Imported by `src.main`, routes/services/models | 100% |
| `frontend/src/**`, `frontend/public/**`, `frontend/index.html`, `frontend/package*.json`, `frontend/vite.config.js` | Frontend source build | `main.jsx` -> `App.jsx`; Vite config builds to `static` | 100% |
| `agents/interview_coach.py`, `agents/job_finder.py`, `agents/recruitment_analyst.py`, `agents/resume_optimizer.py` | Runtime CrewAI agents | Imported by `crew.py` and `recruitment_ai.py` | 100% |
| `tasks/interview_task.py`, `tasks/job_task.py`, `tasks/recruitment_task.py`, `tasks/resume_task.py` | Runtime CrewAI task definitions | Imported by `crew.py` and `recruitment_ai.py` | 100% |
| `utils/resume_parser.py`, `utils/job_search.py`, `utils/skill_scorer.py` | Runtime helper modules | Imported by routes and `crew.py` | 100% |
| `crew.py` | Active interview/resume orchestration | Imported by `src/resume_lab.py`, `interview.py`, `mock_interview.py` | 100% |
| `requirements.txt` | Backend dependency manifest | Dockerfile copies it; app imports dependencies | 100% |
| `Dockerfile`, `render.yaml`, `.dockerignore` | Render/container deployment | Render manifest points to Dockerfile | 95% |
| `.env.example` | Reviewer/onboarding configuration template | Mirrors `src/config.py` settings | 95% |
| `README.md` | Main reviewer-facing documentation | Explains app and setup | 95% |

### Keep For Documentation

| Item | Reason | Evidence | Confidence |
|---|---|---|---:|
| `Reports/docs-Report3/deployment.md`, `migration-report.md`, `interview.md`, selected screenshots | Useful proof of implementation/deployment journey | Markdown/screenshots; reviewer-facing if curated | 80% |
| `Reports/production_hardening_report.md`, `Reports/rag_architecture_report.md`, `Reports/rag_production_readiness_report.md` | Supports technical panel discussion if summarized | No runtime role; relevant topics | 75% |
| `AGENTS.md` | Useful for coding agents; may be too internal for public repo | Contains precise architecture notes; not runtime | 70% |

### Archive

| Item | Reason | Evidence | Confidence |
|---|---|---|---:|
| Bulk `Reports/audit_reports-Report2/**`, `Reports/artifacts-Report1/**`, `Reports/phase2_reports-Report4/**` | Valuable history but too noisy for judges/recruiters | Many historical markdown reports, no runtime imports | 90% |
| `graphify-out/**` | Useful local code graph but generated and tool-specific | Generated graph files, chunks, manifest, HTML | 95% |
| `scratch/**` | May contain useful probes but not submission-ready | Ad hoc filenames/logs; no runtime imports | 90% |
| `scripts/simulate_interview.py` | Demo/experimental support | Script-only simulation | 75% |

### GitIgnore

| Item | Reason | Evidence | Confidence |
|---|---|---|---:|
| `.env`, `.env.postgres` | Secrets/local config | `.gitignore` excludes `.env`; values loaded from env | 100% |
| `.venv/**` | Local dependency install | `.gitignore` excludes `.venv/` | 100% |
| `.opencode/**`, `.agents/**`, `.codex/**` | Local agent/tool config | `.gitignore` excludes these folders | 100% |
| `data/**` | DBs, uploads, logs, CrewAI storage, Chroma | `.gitignore` excludes `data/`; app creates runtime data there | 100% |
| `__pycache__/**`, `*.pyc`, `.pytest_cache/**` | Generated caches | `.gitignore` excludes them | 100% |
| `static/**` if deployment rebuilds frontend | Generated build output | Vite config outputs to `../static` | 80% |
| `graphify-out/**` | Generated graph output | Tool-generated; only partial ignore exists | 95% |

### Safe To Remove

| Item | Reason | Evidence | Confidence |
|---|---|---|---:|
| `__pycache__/**`, `*.pyc` | Regenerated automatically | Python bytecode cache; ignored | 100% |
| `.pytest_cache/**` | Regenerated by pytest | Pytest cache; ignored | 100% |
| `.venv/**` | Recreated from `requirements.txt` | Ignored local env | 100% |
| `.opencode/node_modules/**` | Recreated from `.opencode/package-lock.json` if needed | Node dependency cache; ignored | 100% |
| `data/*.log`, `scratch/*.log` | Runtime/dev logs | Ignored log patterns; not imported | 100% |
| `data/test_*.db`, `data/interview_smoke_*.db` | Test DB artifacts | Tests create DBs dynamically; ignored `*.db` | 95% |
| `temp_backend_check.py`, `tests_login.py` | Manual probes outside pytest | Direct localhost requests; no imports | 95% |
| `check_ids.js` | Obsolete static checker | Reads missing `static/script.js`; current Vite build uses hashed assets | 95% |
| `scratch_append.py` | Writes outside repo to local IDE/agent path | Not app-related; risky local-only script | 100% |

### Manual Review Required

| Item | Reason | Evidence | Confidence |
|---|---|---|---:|
| `agents/skill_matcher.py` | No direct runtime import found; may be future/legacy AI feature | Import/reference search did not find it | 75% |
| `tasks/match_task.py` | No direct runtime import found; may pair with `skill_matcher.py` | Import/reference search did not find it | 75% |
| `frontend/src/assets/react.svg`, `frontend/src/assets/vite.svg` | Likely starter remnants but confirm no hidden CSS/public references | Import scan did not find current usage | 80% |
| `static/**` | Keep if backend deployment serves prebuilt frontend; remove from source repo if CI builds it | `src.main` serves static; Vite generates it | 85% |
| `Reports/**` curated subset | Some reports may help portfolio narrative; most are noisy | Docs are historical, not runtime | 80% |
| `.env.postgres` | Could be sanitized template or local secret file; current `.env.example` already covers safe template role | Not auto-loaded by settings | 85% |

## 8. Safe Removal Candidates

These are candidates that can be removed without affecting application functionality, assuming no one relies on them as local convenience files:

- All `__pycache__/` folders and `*.pyc` files.
- `.pytest_cache/`.
- `.venv/`.
- `.opencode/node_modules/`.
- `data/*.db`, `data/test_*.db`, `data/interview_smoke_*.db`, `data/*.log`, `data/.crewai_storage/**`, `data/profile_documents/**`, `data/chroma/**`.
- `scratch/*.log`, generated route/output files in `scratch/`.
- `temp_backend_check.py`, `tests_login.py`, `check_ids.js`, `scratch_append.py`.
- `graphify-out/chunk_*.txt`, `.graphify_chunk_*`, `.graphify_python`, `.graphify_root`, `.rebuild.lock`, `graph.html`, `graph.json`, `cost.json`, `manifest.json` if not intentionally publishing the graph as a local analysis artifact.

High-confidence but still worth one human glance:

- `frontend/src/assets/react.svg`, `frontend/src/assets/vite.svg`.
- `agents/skill_matcher.py`, `tasks/match_task.py` only after confirming no planned demo path uses them.

## 9. Manual Review Candidates

| Candidate | Why Manual | Suggested Decision |
|---|---|---|
| `static/**` | It is generated, but the backend serves it directly and Vercel config deploys it | Keep for hackathon if no CI frontend build; otherwise ignore generated build and document build step |
| `Reports/**` | Some reports help show technical maturity; too many look noisy | Move curated docs into `docs/`; archive the rest outside submission |
| `AGENTS.md` | Excellent internal architecture notes, but agent-specific | Keep if repo is used with AI coding agents; otherwise convert key parts into `docs/architecture.md` |
| `app.py` | Compatibility entrypoint only | Keep if demos/scripts expect `uvicorn app:app`; otherwise document `src.main:app` as canonical |
| `docker-compose.yml` | Only starts Postgres, not the full app | Keep if local Postgres setup is documented; otherwise move to dev docs |
| `vercel.json` | Static-only frontend deployment, while app is full-stack FastAPI | Keep only if a separate static frontend deployment is part of submission |
| `.env.postgres` | May duplicate `.env.example` and could include sensitive values | Replace with safe documented template or remove |

## 10. Final Submission Repository Blueprint

Recommended professional repository shape:

```text
.
├── README.md
├── AGENTS.md                         # optional; or convert key content into docs/
├── requirements.txt
├── .env.example
├── .gitignore
├── .dockerignore
├── Dockerfile
├── render.yaml
├── docker-compose.yml                # optional local DB support
├── vercel.json                       # optional only if static frontend deploy is real
├── pytest.ini
├── app.py                            # optional compatibility entrypoint
├── crew.py                           # keep: actively imported
├── src/
├── agents/
├── tasks/
├── utils/
├── scripts/
├── frontend/
├── tests/
├── static/                           # keep only if deploying prebuilt assets
└── docs/                             # curated docs/screenshots, not bulk historical reports
```

Do not include in the final submission repository:

```text
.env
.env.postgres unless sanitized and renamed
.venv/
.pytest_cache/
__pycache__/
*.pyc
data/
scratch/
graphify-out/
.agents/
.opencode/
.codex/
bulk Reports/ history unless curated into docs/
temp_backend_check.py
tests_login.py
scratch_append.py
check_ids.js
```

Submission narrative recommendation:

- Make `README.md` the judge-facing entrypoint with demo credentials, architecture diagram, setup, screenshots, and deployment notes.
- Keep tests visible: `tests/`, `pytest.ini`, `frontend/tests/e2e/`, and lint/e2e scripts demonstrate engineering seriousness.
- Keep operational scripts, but document them in `README.md` or `docs/operations.md`.
- If `static/` remains committed, state clearly that it is the current Vite production build served by FastAPI. If CI/build pipeline rebuilds frontend, remove `static/` from source control and produce it during deployment.
- Preserve historical reports externally or in a compressed archive outside the main submission; curated docs should tell a clean story, not expose every intermediate debugging artifact.
