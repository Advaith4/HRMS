# TalentForge AI - Project Scope, Architecture, and Interview Knowledge Base

This document is a presentation and interview preparation knowledge base for the TalentForge AI repository. It is written so that a reader can understand the project, explain its architecture, prepare a demo, and answer technical questions without opening the source code.

Assumption note: some intent is inferred from repository structure, README content, tests, route names, and implementation patterns. Inferred points are marked as assumptions where appropriate.

---

## 1. Executive Summary

### Project Name

TalentForge AI

### One-Line Description

TalentForge AI is a full-stack AI-powered HR and talent lifecycle platform that connects recruitment, resume analysis, interviews, hiring intelligence, employee operations, training, onboarding, and company knowledge retrieval.

### Elevator Pitch - 30 Seconds

TalentForge AI is an HR operating system that helps organizations manage the full talent journey from candidate application to employee growth. Candidates can upload resumes, apply to jobs, complete mock or official interviews, and use a career assistant. HR teams can post jobs, review AI-ranked applicants, inspect interview intelligence, manage onboarding, training, documents, salary, promotions, tickets, and use a role-aware RAG copilot for HR knowledge.

### Elevator Pitch - 60 Seconds

TalentForge AI solves the problem of disconnected HR workflows. Instead of separate tools for job posting, resume screening, interviews, employee records, onboarding, training, and policy questions, it provides one connected platform. The backend is built with FastAPI and SQLModel, the frontend is a React and Vite single-page application, and AI features use CrewAI, Groq, deterministic fallback logic, and Chroma-backed retrieval. The system supports different roles such as candidate, employee, HR, manager, and admin, each with their own dashboard and permissions. A candidate can apply to a job, receive AI resume and fit analysis, complete an adaptive proctored interview, and then be converted into an employee record.

### Elevator Pitch - 2 Minutes

TalentForge AI is a complete AI-assisted talent lifecycle platform. It starts with candidates: they register, browse jobs, upload resumes, apply to roles, receive AI-assisted screening, and practice with mock interviews. For official job applications, they can complete a structured interview with proctoring, adaptive phases, score tracking, credibility analysis, and hiring intelligence reports.

For HR and managers, the system provides job management, application review, candidate ranking, interview intelligence, candidate comparison, document verification, onboarding, training, salary, promotions, tickets, leave workflows, and dashboards. For employees, it provides attendance, leave, onboarding tasks, training assignments, skill gap analysis, profile management, documents, tickets, and career timeline data. For admins, it provides user management and knowledge base management.

Technically, TalentForge AI uses FastAPI as the API server, React 19 with Vite as the frontend, SQLModel with SQLite or PostgreSQL for relational persistence, JWT and role-based access control for security, CrewAI and Groq for AI orchestration, and ChromaDB for retrieval-augmented generation. A major design strength is graceful degradation: if external LLM services are unavailable, several workflows still return deterministic fallback results instead of failing completely.

---

## 2. Problem Statement

### Real-World Problem

Hiring and HR operations often happen across disconnected systems:

- Job posting tools
- Resume screening spreadsheets
- Interview notes
- Employee records
- Onboarding checklists
- Training trackers
- Salary and promotion records
- HR ticket systems
- Policy documents
- Informal chat or email threads

This fragmentation makes decision-making slow and inconsistent. HR teams may struggle to compare candidates fairly, candidates may receive little structured feedback, and employee lifecycle information may not connect back to recruitment or training decisions.

### Why the Problem Matters

People decisions affect hiring quality, candidate experience, employee growth, compliance, productivity, and retention. When information is scattered:

- HR spends more time collecting context than making decisions.
- Candidates may be judged inconsistently.
- Interview evidence may not be connected to resume claims.
- Employees may not receive timely onboarding or training.
- Managers may lack visibility into team readiness.
- Company knowledge may be hard to search.

### Existing Challenges

- Manual resume screening is time-consuming.
- Interview feedback can be subjective and unstructured.
- HR dashboards often show data but do not assist decisions.
- AI tools are often bolted onto one workflow rather than integrated.
- Policy and employee knowledge is usually stored in static documents.
- Small teams and hackathon-style projects cannot build enterprise HR suites from scratch.

### Impact on Users

- Candidates get a guided application and interview experience.
- HR teams get centralized applicant, interview, and employee data.
- Managers get operational visibility.
- Employees get structured self-service workflows.
- Admins can manage users and knowledge content.

### Why This Solution Is Useful

TalentForge AI is useful because it connects multiple HR workflows into one coherent system. The project demonstrates not only CRUD operations, but also AI-assisted analysis, structured interviews, role-aware dashboards, database persistence, RAG-based knowledge retrieval, authentication, deployment configuration, and test coverage.

---

## 3. Project Goals

### Main Objective

Build a working AI-powered HRMS and recruitment platform that supports the candidate-to-employee lifecycle in one application.

### Secondary Objectives

- Provide role-specific portals for candidates, employees, HR, managers, and admins.
- Analyze resumes and job applications using AI plus fallback scoring.
- Run mock interviews and official proctored interviews.
- Generate hiring intelligence reports.
- Manage employee lifecycle workflows such as onboarding, training, leave, salary, promotions, tickets, and documents.
- Provide a RAG-based HR and career assistant.
- Support local and production deployment.
- Keep the system testable without requiring external AI services.

### Expected Outcomes

- A candidate can apply for jobs and complete interview workflows.
- HR can review, rank, advance, reject, and hire candidates.
- Employees can interact with operational HR workflows.
- Admins can manage users and knowledge content.
- AI-backed systems produce explainable analysis and fallbacks.

### Success Criteria

- The backend starts as `src.main:app`.
- The frontend builds into `static/` and is served by FastAPI.
- Authentication and role guards protect sensitive routes.
- Core workflows are covered by automated tests.
- The project can run locally with SQLite and deploy with PostgreSQL.

---

## 4. High-Level Architecture

### Overall Architecture

TalentForge AI uses a modern full-stack architecture:

- React SPA for user interfaces.
- FastAPI for REST APIs.
- SQLModel for relational data modeling.
- SQLite for local development and PostgreSQL for production.
- CrewAI and Groq for AI-assisted workflows.
- ChromaDB for RAG vector retrieval.
- Docker and Render configuration for deployment.

### Architecture Diagram

```text
User
  |
  v
React 19 + Vite SPA
  |
  v
Axios API Layer
  |
  v
FastAPI Backend (src.main:app)
  |
  +--> JWT Authentication + RBAC Dependencies
  |
  +--> REST Routers
  |      +--> Auth
  |      +--> Jobs and Applications
  |      +--> Resume Lab
  |      +--> Interview and Mock Interview
  |      +--> Hiring Intelligence
  |      +--> Employee Lifecycle
  |      +--> RAG Chat
  |      +--> Admin Knowledge
  |
  +--> Domain Services
  |      +--> Recruitment AI
  |      +--> Interview Core
  |      +--> Hiring Intelligence
  |      +--> Resume Analysis
  |      +--> Employee AI
  |      +--> RAG Services
  |
  +--> SQLModel Database
  |
  +--> Chroma Vector Store
  |
  +--> File Storage under data/
```

### Component Relationships

- `frontend/src/App.jsx` defines the role-aware SPA route map.
- `frontend/src/api/*.js` files call matching backend endpoints.
- `src/main.py` creates the FastAPI app, configures startup behavior, registers routers, and serves static frontend assets.
- `src/api/routes/*.py` files expose domain-specific API endpoints.
- `src/services/*.py` files contain business logic and AI orchestration.
- `src/models/__init__.py` defines SQLModel tables.
- `src/database/connection.py` creates the database engine, sessions, tables, and idempotent migrations.

---

## 5. Complete System Workflow

### End-to-End Candidate-to-Hire Workflow

1. User launches the application in the browser.
2. FastAPI serves the built React SPA from `static/`, or the developer runs Vite from `frontend/`.
3. User registers or logs in.
4. Backend hashes passwords with bcrypt and issues a JWT.
5. Frontend stores auth state through Zustand and sends the JWT with future requests.
6. React Router redirects the user to the correct dashboard based on role.
7. Candidate browses job postings.
8. Candidate uploads or submits resume/application data.
9. Backend stores the resume and candidate application.
10. Recruitment AI analyzes the application against the job.
11. If AI is unavailable, deterministic fallback analysis still produces a usable result.
12. HR sees ranked candidates and analysis inside HR dashboards.
13. Candidate may practice in the mock interview module.
14. Candidate starts an official application-linked interview.
15. Interview engine builds context from resume, job, application, training mode, persona, and session memory.
16. Candidate answers questions through the interview workspace.
17. Backend evaluates answers, updates session state, tracks phase progression, and stores messages.
18. Proctoring events can be recorded against official interviews.
19. When the interview completes, backend compiles hiring intelligence.
20. Hiring intelligence generates competency, communication, risk, benchmarking, and recommendation data.
21. Credibility analysis compares resume claims against interview evidence.
22. HR reviews interview reports, leaderboards, comparison views, and application details.
23. HR advances, rejects, or hires the candidate.
24. On hire, the system creates an employee record and links lifecycle data.
25. Employee can use onboarding, training, attendance, leave, profile, documents, and ticket workflows.
26. Admin and HR knowledge can be indexed into RAG collections.
27. HR, candidates, and employees can ask role-scoped assistant questions.

### Employee Lifecycle Workflow

```text
Candidate hired
  |
  v
Employee record created
  |
  v
Onboarding template assigned
  |
  v
Required documents uploaded and reviewed
  |
  v
Training programs assigned
  |
  v
Skill gap analysis generated
  |
  v
Attendance, leave, tickets, salary, promotion, and lifecycle events tracked
```

---

## 6. Technology Stack

| Technology | What It Is | Role in Project | Why It Was Chosen |
| --- | --- | --- | --- |
| Python | General-purpose backend language | Backend, services, AI orchestration, scripts, tests | Strong ecosystem for FastAPI, AI, PDF parsing, and data workflows |
| FastAPI | Python web API framework | Main backend application in `src.main:app` | Fast development, automatic OpenAPI docs, dependency injection |
| Uvicorn | ASGI server | Runs FastAPI locally and in Docker | Standard server for FastAPI applications |
| SQLModel | ORM combining SQLAlchemy and Pydantic patterns | Database models and sessions | Reduces boilerplate for typed database models |
| SQLite | File-based relational database | Local development and isolated tests | Simple setup, no external database required |
| PostgreSQL | Production-grade relational database | Production deployment target | Better concurrency, reliability, and managed hosting support |
| psycopg2-binary | PostgreSQL driver | Connects SQLModel/SQLAlchemy to PostgreSQL | Common Python PostgreSQL adapter |
| Pydantic / Pydantic Settings | Data validation and settings management | Request models, response models, env config | Typed validation and `.env` loading |
| JWT / python-jose | Token-based authentication | Login sessions and route protection | Stateless authentication for APIs |
| bcrypt | Password hashing | Secure password storage | Industry-standard adaptive password hashing |
| CrewAI | Multi-agent AI orchestration library | Recruitment analysis and interview-style AI agents | Allows task/agent separation for AI workflows |
| Groq | LLM provider | Main configured LLM provider | Fast hosted inference for `llama-3.1-8b-instant` |
| LiteLLM | LLM routing library | LLM abstraction/routing support | Allows provider abstraction and routed completions |
| OpenAI package | LLM/embedding integration dependency | Optional embeddings and AI integrations | Supports optional OpenAI-backed RAG embeddings |
| pypdf | PDF text extraction library | Resume parsing | Extracts text from uploaded resumes |
| python-docx | Word document parsing library | Document/resume utility support | Enables DOCX handling in supporting utilities |
| ChromaDB | Vector database | RAG storage and retrieval | Local-friendly vector search for company and HR knowledge |
| React 19 | Frontend UI library | SPA user interface | Component-based UI for dashboards and workflows |
| Vite | Frontend build tool | Dev server and production build | Fast builds, simple SPA workflow |
| React Router | Frontend routing | Role-based pages and navigation | Client-side navigation with guards |
| Zustand | State management | Auth and layout state | Lightweight state store |
| Axios | HTTP client | API calls from frontend | Interceptors, timeout handling, request helpers |
| TailwindCSS | Utility-first CSS framework | Frontend styling | Fast UI development and consistent styling |
| Framer Motion | Animation library | Frontend motion | Smooth transitions and UI polish |
| Recharts | Charting library | Dashboards and reports | React-friendly charts for HR metrics |
| Lucide React | Icon library | UI icons | Consistent icon set |
| React Dropzone | File upload UI helper | Resume/document upload flows | Improved drag-and-drop upload UX |
| pytest | Python test framework | Backend test suite | Simple and powerful test runner |
| Playwright | Browser automation framework | Frontend e2e config and interview browser validation | Useful for real browser workflow testing |
| Docker | Containerization | Production runtime image | Reproducible deployment |
| Render | Cloud deployment target | `render.yaml` web service | Simple Docker web service deployment |
| Vercel config | Static SPA hosting config | `vercel.json` for static frontend | Supports frontend-only static deployment when backend is separate |

---

## 7. Repository Structure Analysis

### Tree Summary

```text
HRMS/
  AGENTS.md
  README.md
  SCOPE.md
  app.py
  crew.py
  requirements.txt
  Dockerfile
  docker-compose.yml
  render.yaml
  vercel.json
  pytest.ini
  src/
    main.py
    config.py
    resume_lab.py
    core/
      security.py
      exceptions.py
    database/
      connection.py
    models/
      __init__.py
    api/
      dependencies.py
      routes/
        admin.py
        applications.py
        auth.py
        candidates.py
        dashboard.py
        departments.py
        designations.py
        employees.py
        interview.py
        jobs.py
        lifecycle.py
        mock_interview.py
        notifications.py
        onboarding.py
        profile.py
        promotions.py
        rag.py
        resume.py
        salary.py
        tickets.py
        training.py
    services/
      recruitment_ai.py
      interview_core.py
      interview_status.py
      hiring_intelligence.py
      interview_consistency.py
      mock_interview_summary.py
      employee_ai.py
      transcription_service.py
      llm_router.py
      rag/
        access_control.py
        chat_service.py
        chroma_service.py
        company_docs_ingestion.py
        embedding_service.py
        ingestion_service.py
        query_router.py
        retrieval_service.py
        sync_service.py
  agents/
  tasks/
  utils/
  scripts/
  frontend/
    src/
      App.jsx
      api/
      pages/
      components/
      hooks/
      store/
      context/
    package.json
    vite.config.js
  static/
    index.html
    assets/
    Images/
  tests/
  graphify-out/
```

### Important Files and Folders

| Path | Purpose |
| --- | --- |
| `README.md` | Product overview, screenshots, architecture, run instructions |
| `AGENTS.md` | Developer/agent instructions and project gotchas |
| `src/main.py` | FastAPI app, startup/lifespan behavior, router registration, SPA static serving |
| `src/config.py` | Environment-backed settings with production secret validation |
| `src/database/connection.py` | SQLModel engine, sessions, table creation, idempotent schema migrations |
| `src/models/__init__.py` | SQLModel table definitions for users, recruitment, interviews, employees, documents, onboarding, training, and intelligence |
| `src/api/dependencies.py` | JWT authentication and role-based dependencies |
| `src/core/security.py` | bcrypt password hashing and JWT encode/decode helpers |
| `src/resume_lab.py` | Resume text repair, parsing, analysis validation, fallback scoring, and safe fixes |
| `src/api/routes/` | REST endpoints grouped by domain |
| `src/services/` | Business logic and AI/RAG service implementations |
| `src/services/rag/` | RAG access control, embeddings, Chroma storage, retrieval, query routing, chat, sync |
| `agents/` | CrewAI agent definitions |
| `tasks/` | CrewAI task definitions |
| `utils/` | Supporting utilities for resume parsing, job search, and skill scoring |
| `scripts/` | Operational scripts such as admin bootstrap, database migration, seeding, ingestion, and interview simulation |
| `frontend/` | React 19 + Vite frontend source |
| `frontend/src/api/` | Axios API wrappers matching backend domains |
| `frontend/src/pages/` | Role dashboards and feature pages |
| `frontend/src/components/` | Reusable UI, layout, modals, drawers, charts, interview workspaces |
| `static/` | Built frontend assets and screenshot images served by FastAPI |
| `tests/` | pytest test suite covering API, RAG, interviews, proctoring, hiring intelligence, tickets, lifecycle, and resume lab |
| `Dockerfile` | Multi-stage production container |
| `docker-compose.yml` | Local PostgreSQL service |
| `render.yaml` | Render Docker web service configuration |
| `vercel.json` | Static SPA deployment configuration |

---

## 8. Module-by-Module Breakdown

### Backend Entrypoint - `src/main.py`

Purpose:

- Create the FastAPI app.
- Configure startup tasks.
- Register routers.
- Serve the frontend SPA from `static/`.
- Expose health check endpoint `/api/health`.

Inputs:

- Environment settings from `src/config.py`.
- Database connection from `src/database/connection.py`.
- Route modules from `src/api/routes/`.

Outputs:

- A running ASGI application named `app`.
- Registered API endpoints.
- Static frontend serving behavior.

Important behavior:

- Registers routers for auth, resume, jobs, applications, candidates, employees, dashboard, interview, mock interview, departments, designations, lifecycle, tickets, salary, promotions, notifications, onboarding, training, profile, RAG, and admin.
- Creates database tables on startup when configured.
- Contains Windows-specific proxy cleanup for broken proxy environment variables.
- Isolates CrewAI storage into the project data directory.

### Configuration - `src/config.py`

Purpose:

- Centralize application settings.
- Load `.env` values.
- Validate production safety requirements.

Key settings:

- `APP_NAME`
- `DEBUG`
- `GROQ_API_KEY`
- `MODEL_NAME`
- `DATABASE_URL`
- `SECRET_KEY`
- `ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `ALLOWED_ORIGINS`
- PostgreSQL/Supabase deployment settings

Security detail:

- In non-debug, non-SQLite deployments, weak or short `SECRET_KEY` values are rejected.

### Database Layer - `src/database/connection.py`

Purpose:

- Build the SQLModel engine.
- Provide DB session dependencies.
- Create tables.
- Apply lightweight idempotent migrations.

Inputs:

- `DATABASE_URL`
- PostgreSQL-related environment settings

Outputs:

- SQLModel database engine.
- Session generator for FastAPI dependencies.
- Tables and schema adjustments.

Important design:

- SQLite is used by default for local/test-style development.
- PostgreSQL is supported for production.
- Schema evolution is handled by `_ensure_*` functions rather than a full Alembic migration system.
- This is practical for a project/hackathon scope and avoids migration tooling complexity.

### Models - `src/models/__init__.py`

Purpose:

- Define all relational database tables.

Major table groups:

- Identity: `User`
- Resume and applications: `Resume`, `JobApplication`, `JobPosting`, `CandidateApplication`, `ApplicationAIAnalysis`
- Interviews: `InterviewSession`, `MockInterviewSession`, `CareerCoachMemory`, `CandidateCredibilityReport`, `InterviewIntelligenceReport`
- Employees: `Employee`, `AttendanceRecord`, `LeaveRequest`, `SkillGapAnalysis`
- Organization: `Department`, `Designation`
- Lifecycle: `EmployeeLifecycleEvent`, `EmployeeTicket`, `SalaryHistory`, `PromotionHistory`, `IncrementHistory`, `HRNotification`
- Profiles and documents: `CandidateProfile`, `EmployeeProfile`, `CandidateDocument`, `EmployeeDocument`
- Onboarding and training: `OnboardingTemplate`, `OnboardingTask`, `EmployeeOnboarding`, `EmployeeOnboardingTask`, `OnboardingRequiredDocument`, `TrainingProgram`, `TrainingAssignment`

### Authentication and Authorization

Files:

- `src/core/security.py`
- `src/api/dependencies.py`
- `src/api/routes/auth.py`

Purpose:

- Register users.
- Authenticate users.
- Hash passwords.
- Issue and validate JWT tokens.
- Enforce role-based access.

Roles:

- `candidate`
- `employee`
- `hr`
- `manager`
- `admin`

Important logic:

- Public registration creates candidate accounts.
- JWT payload includes user id, username, role, and expiry.
- Backend validates that token role still matches the stored user role.
- `admin` bypasses role checks in `require_roles`.

### Resume Lab - `src/resume_lab.py` and `src/api/routes/resume.py`

Purpose:

- Upload and store resumes.
- Parse resume text.
- Clean and repair PDF extraction artifacts.
- Analyze resume quality.
- Generate issues, strengths, weaknesses, priorities, and scores.
- Apply safe fixes only when supported by existing resume evidence.

Inputs:

- Uploaded PDF resume.
- Extracted text.
- Optional target role.

Outputs:

- Stored resume record.
- Parsed sections.
- Resume analysis payload.
- Safe rewrite suggestions.

Internal logic:

- Cleans text.
- Repairs broken spacing.
- Detects section headings.
- Extracts skills and bullet content.
- Attempts AI analysis.
- Normalizes and validates AI payload.
- Falls back to deterministic analysis when AI fails.
- Uses truth guards to avoid inventing unsupported achievements.

### Recruitment AI - `src/services/recruitment_ai.py`

Purpose:

- Analyze candidate applications against job postings.
- Generate fit score, strengths, weaknesses, missing skills, recommendation, observations, and interview preparation questions.
- Rank applications for a job.
- Sync candidate analysis into RAG context where applicable.

Inputs:

- Candidate application.
- Resume text.
- Job posting requirements.

Outputs:

- `ApplicationAIAnalysis` records.
- Ranking payloads.
- Candidate profile payloads.

Internal logic:

- Attempts CrewAI analysis.
- Extracts and validates structured JSON from AI output.
- Calculates fallback skill matching if AI fails.
- Normalizes recommendation labels.
- Sorts rankings by recommendation and score.

### Interview Engine - `src/api/routes/interview.py` and `src/services/interview_core.py`

Purpose:

- Run official interviews linked to resumes or applications.
- Track interview state.
- Evaluate answers.
- Enforce proctoring.
- Generate interview completion data.
- Support HR-facing intelligence endpoints.

Key backend routes:

- `POST /api/interview/start`
- `POST /api/interview/start-from-resume`
- `POST /api/interview/start-for-application`
- `POST /api/interview/answer`
- `POST /api/interview/{session_id}/violation`
- `POST /api/interview/{session_id}/complete`
- `POST /api/interview/{session_id}/abandon`
- `GET /api/interview/sessions`
- `GET /api/interview/sessions/{session_id}`
- `POST /api/interview/{session_id}/credibility`
- `GET /api/interview/intelligence/leaderboard`
- `GET /api/interview/intelligence/report/{candidate_id}`
- `POST /api/interview/intelligence/compare`
- `POST /api/interview/intelligence/{session_id}/advance`
- `POST /api/interview/intelligence/{session_id}/reject`
- `GET /api/interview/intelligence/top-candidates`
- `GET /api/interview/intelligence/followup-questions/{session_id}`
- `POST /api/interview/transcribe`

Internal logic:

- Builds personalization context from resume and application.
- Normalizes training mode and interviewer persona.
- Tracks interview phases and required turns.
- Saves messages to `InterviewSession`.
- Computes average score.
- Records proctoring violations.
- Cancels or completes sessions according to status rules.
- Notifies HR when relevant.
- Invokes hiring intelligence after completion.

Frontend files:

- `frontend/src/pages/interview/InterviewPage.jsx`
- `frontend/src/components/interview/InterviewWorkspace.jsx`
- `frontend/src/components/interview/InterviewWorkspaceShell.jsx`
- `frontend/src/api/interview.js`

### Mock Interview - `src/api/routes/mock_interview.py`

Purpose:

- Provide a candidate practice interview separate from official application interviews.

Key backend routes:

- `POST /api/mock-interview/start`
- `POST /api/mock-interview/answer`
- `POST /api/mock-interview/{session_id}/complete`
- `GET /api/mock-interview/sessions`

Internal logic:

- Creates a `MockInterviewSession`.
- Accepts role, difficulty, persona, interview type, and duration settings.
- Evaluates answers.
- Produces a practice-oriented summary.
- Keeps practice data separate from official hiring interview data.

Frontend files:

- `frontend/src/pages/interview/MockInterviewPage.jsx`
- `frontend/src/components/interview/MockInterviewWorkspace.jsx`
- `frontend/src/components/interview/MockInterviewSummary.jsx`
- `frontend/src/api/mock_interview.js`

### Hiring Intelligence - `src/services/hiring_intelligence.py`

Purpose:

- Produce HR-facing interview intelligence after official interviews.

Inputs:

- Completed interview session.
- Resume/application/job context.
- Interview messages and evaluation scores.

Outputs:

- `InterviewIntelligenceReport`.
- Competency scores.
- Job fit report.
- Communication metrics.
- Behavioral report.
- Hiring risks.
- Timeline replay.
- Benchmarking.
- Recommendation.

Important algorithm:

```text
Hiring score = 35% resume score + 40% interview score + 25% credibility score
```

### Interview Consistency - `src/services/interview_consistency.py`

Purpose:

- Compare resume claims against interview evidence.
- Produce credibility reports.

Inputs:

- Resume text.
- Interview messages.
- Job context.

Outputs:

- `CandidateCredibilityReport`.
- Supported claims.
- Weak claims.
- Missing evidence.
- Follow-up topics.
- Recommendation.

Design note:

- The service does not claim to detect lies. It checks whether resume claims were supported by interview evidence.

### Employee AI - `src/services/employee_ai.py`

Purpose:

- Generate employee skill gap analysis.
- Answer HR-style questions.

Inputs:

- Employee record.
- Role expectations.
- User question.

Outputs:

- Skill gaps.
- Strengths.
- Recommended training.
- HR answer payloads.

### RAG System - `src/services/rag/`

Purpose:

- Provide retrieval-augmented answers over company and HR knowledge.

Major components:

- `access_control.py`: determines which collections and filters a user may access.
- `embedding_service.py`: hash embeddings by default, optional OpenAI embeddings.
- `chroma_service.py`: ChromaDB collection access.
- `ingestion_service.py`: document ingestion into vector collections.
- `company_docs_ingestion.py`: company document ingestion workflow.
- `retrieval_service.py`: query-time vector retrieval.
- `query_router.py`: routes questions to suitable sources.
- `chat_service.py`: generates final answer using retrieved context.
- `sync_service.py`: syncs jobs, candidates, interviews, and employee knowledge into RAG.

Exposed route:

- `POST /api/rag/chat`

Collections mentioned in the README:

- `company_policies`
- `job_descriptions`
- `candidate_profiles`
- `interview_reports`
- `employee_knowledge`

### Employee Operations Routes

Files:

- `employees.py`
- `lifecycle.py`
- `tickets.py`
- `salary.py`
- `promotions.py`
- `onboarding.py`
- `training.py`
- `profile.py`
- `departments.py`
- `designations.py`
- `notifications.py`

Purpose:

- Manage employee records, attendance, leave, profiles, documents, skill gaps, onboarding, training, tickets, salary, promotions, departments, designations, notifications, and lifecycle history.

### Admin Module - `src/api/routes/admin.py`

Purpose:

- Manage users.
- Manage company policies.
- Manage knowledge documents.
- Trigger reindexing of policy and knowledge content.

Key routes:

- `GET /api/admin/users`
- `PUT /api/admin/users/{user_id}`
- Policy CRUD routes.
- Knowledge CRUD routes.
- Reindex endpoints.

### Frontend Application

Purpose:

- Provide role-specific dashboards and workflows.

Key files:

- `frontend/src/App.jsx`: routing and role guards.
- `frontend/src/api/axios.js`: shared Axios setup with timeout, cache behavior, and auth handling.
- `frontend/src/store/authStore.js`: auth state.
- `frontend/src/store/layoutStore.js`: layout state.
- `frontend/src/components/layout/`: sidebar, top bar, and layout shell.
- `frontend/src/pages/`: dashboard and workflow pages.
- `frontend/src/components/interview/`: interview and mock interview UI.
- `frontend/src/components/drawers/`: detail drawers for jobs, analysis, employees, notifications.
- `frontend/src/components/modals/`: create/update modal workflows.
- `frontend/src/components/charts/`: chart components.

Routes include:

- `/login`
- `/dashboard/hr`
- `/dashboard/admin`
- `/dashboard/manager`
- `/dashboard/candidate`
- `/dashboard/employee`
- `/hr/jobs`
- `/hr/pipeline`
- `/hr/candidates`
- `/hr/intelligence`
- `/hr/copilot`
- `/hr/onboarding`
- `/hr/training`
- `/hr/documents`
- `/career-assistant`
- `/jobs`
- `/applications`
- `/interview`
- `/mock-interview`

---

## 9. Data Flow Analysis

### Authentication Data Flow

```text
Login form
  |
  v
POST /api/auth/login
  |
  v
Password verified with bcrypt
  |
  v
JWT created with user id, username, role, expiry
  |
  v
Frontend stores auth state
  |
  v
Protected API calls include bearer token
  |
  v
Backend dependencies validate token and role
```

### Resume/Application Data Flow

```text
Candidate uploads resume/applies to job
  |
  v
Resume text extracted and stored
  |
  v
CandidateApplication created
  |
  v
Recruitment AI analyzes resume against job
  |
  v
ApplicationAIAnalysis stored
  |
  v
HR dashboard displays score, recommendation, strengths, weaknesses
```

### Interview Data Flow

```text
Candidate starts interview
  |
  v
Backend loads resume/application context
  |
  v
InterviewSession created or resumed
  |
  v
Question sent to frontend
  |
  v
Candidate answers through workspace
  |
  v
Answer submitted to /api/interview/answer
  |
  v
Evaluation generated and stored
  |
  v
Next phase/question selected
  |
  v
Session completes
  |
  v
Hiring intelligence and credibility reports generated
  |
  v
HR reviews candidate intelligence
```

### RAG Data Flow

```text
Jobs / candidates / interviews / policies / employee docs
  |
  v
RAG sync or ingestion service
  |
  v
Embedding provider
  |
  v
ChromaDB collection
  |
  v
User asks assistant question
  |
  v
Access control determines allowed collections
  |
  v
Query router selects retrieval targets
  |
  v
Retrieved context sent to answer service
  |
  v
Role-aware answer returned with sources
```

### Storage

- Relational business data is stored in SQLite or PostgreSQL.
- Vector knowledge data is stored in ChromaDB.
- Uploaded files and CrewAI storage are placed under project data paths.
- Built frontend assets are stored in `static/`.

---

## 10. Core Algorithms

### Resume Text Repair and Parsing

Purpose:

- Convert messy PDF-extracted resume text into analyzable sections.

Inputs:

- Raw resume text extracted from PDF.

Outputs:

- Cleaned text.
- Parsed sections.
- Skills, summary, experience, projects, education, and related content.

Logic:

- Normalize whitespace.
- Repair character-spaced text.
- Detect headings.
- Identify bullets.
- Split skill lists.
- Deduplicate extracted items.

Advantages:

- Improves reliability of resume analysis.
- Works even when AI is unavailable.

Limitations:

- PDF extraction quality can vary.
- Non-standard resume layouts may still be difficult.

### Resume Analysis Validation and Truth Guard

Purpose:

- Prevent AI-generated fixes from inventing unsupported information.

Inputs:

- Original resume text.
- AI or fallback analysis.
- Suggested improvements.

Outputs:

- Normalized and validated analysis.
- Safe manual guidance when a rewrite would require unsupported facts.

Logic:

- Coerce and normalize JSON payloads.
- Clamp numeric scores.
- Normalize issue structure.
- Check whether suggested improvements add meaningful unsupported claims.
- Provide manual guidance if evidence is missing.

Advantages:

- Keeps resume suggestions defensible.
- Useful for interview preparation because candidates should not claim invented achievements.

Limitations:

- It cannot fully prove factual truth.
- It can only compare suggestions with the provided resume text.

### Recruitment Fit Scoring

Purpose:

- Score candidate fit against job requirements.

Inputs:

- Resume text.
- Job title, description, and required skills.

Outputs:

- Fit score.
- Recommendation.
- Matched skills.
- Missing skills.
- Strengths and weaknesses.
- Interview prep questions.

Logic:

- Attempts CrewAI/Groq analysis.
- Extracts structured JSON.
- Falls back to deterministic skill matching based on required skill terms.
- Maps score to recommendation.

Advantages:

- Provides useful output even without AI.
- Transparent enough to discuss in interviews.

Limitations:

- Deterministic fallback depends on keyword overlap.
- AI analysis quality depends on prompt and model behavior.

### Adaptive Interview Phase Control

Purpose:

- Keep interviews structured instead of free-form.

Inputs:

- Current phase.
- Answer count.
- Phase turn count.
- Scores.
- Resume/application context.

Outputs:

- Next question.
- Next phase.
- Completion flag.
- Feedback and score.

Logic:

- Defines interview phases and turn requirements.
- Tracks completed turns by phase.
- Chooses focus areas based on weak areas and training mode.
- Ends when required phase turns are complete or early-ending criteria are met.

Advantages:

- Makes interviews explainable and repeatable.
- Supports adaptive personalization.

Limitations:

- Phase logic is simpler than a full enterprise assessment engine.
- Likely scoped for a project/demo timeline.

### Proctoring Violation Tracking

Purpose:

- Enforce integrity during official interviews.

Inputs:

- Frontend proctoring events such as tab switching, camera/screen sharing failures, or fullscreen exits.

Outputs:

- Violation records.
- Updated session status.
- Possible cancellation.

Logic:

- Frontend detects events in interview workspace shell.
- Backend stores violation count and details.
- Official sessions can be cancelled after threshold breaches.

Advantages:

- Demonstrates security-minded assessment design.

Limitations:

- Browser proctoring is not foolproof.
- Strong proctoring would require more advanced enterprise tooling.

### Credibility Analysis

Purpose:

- Compare resume claims with interview evidence.

Inputs:

- Resume text.
- Interview Q&A messages.
- Job context.

Outputs:

- Credibility score.
- Supported claims.
- Weak claims.
- Missing evidence.
- Follow-up topics.

Logic:

- Extracts resume claims.
- Extracts interview Q&A.
- Attempts AI credibility evaluation.
- Falls back to deterministic scoring and summarization.
- Stores report.

Advantages:

- Adds an evidence-based layer to hiring decisions.

Limitations:

- It is not lie detection.
- It only checks whether evidence appears in the interview.

### Hiring Intelligence Compilation

Purpose:

- Transform interview results into HR decision context.

Inputs:

- Interview session.
- Resume/application context.
- Scores and messages.

Outputs:

- Structured intelligence report.
- Recommendation.
- Benchmarking.
- Communication metrics.
- Risk flags.

Logic:

- Generates or falls back to structured reports.
- Counts filler words.
- Calculates benchmark metrics.
- Persists report and syncs to RAG when possible.

Advantages:

- Makes interview data actionable for HR.

Limitations:

- Benchmark quality depends on available historical sessions.

### RAG Query Routing and Retrieval

Purpose:

- Answer role-aware HR/career questions using stored knowledge.

Inputs:

- User question.
- User role and identity.
- Indexed documents.

Outputs:

- Answer.
- Sources.
- Route metadata.

Logic:

- Access control chooses allowed collections.
- Query router determines likely knowledge domains.
- Retrieval service fetches relevant chunks from Chroma.
- Chat service produces final answer with context.

Advantages:

- Reduces hallucination compared with answering without project/company context.
- Supports different users seeing different knowledge.

Limitations:

- Hash embeddings are local-friendly but less semantically powerful than production embedding models.
- RAG answer quality depends on indexed document quality.

---

## 11. Database Analysis

### Database Type

The project uses SQLModel over a relational database.

- Local/development: SQLite.
- Production: PostgreSQL.

### Schema Overview

The schema covers five large domains:

1. Identity and access.
2. Recruitment and applications.
3. Interviews and hiring intelligence.
4. Employee lifecycle operations.
5. Profiles, documents, onboarding, training, and notifications.

### Major Tables

| Table | Model | Purpose |
| --- | --- | --- |
| `users` | `User` | Accounts, roles, active status |
| `resumes` | `Resume` | Uploaded resume text and metadata |
| `job_applications` | `JobApplication` | Legacy/simple application record |
| `job_postings` | `JobPosting` | Jobs created by HR/admin |
| `candidate_applications` | `CandidateApplication` | Candidate applications to job postings |
| `application_ai_analyses` | `ApplicationAIAnalysis` | AI/fallback recruitment analysis |
| `interview_sessions` | `InterviewSession` | Official interview records |
| `mock_interview_sessions` | `MockInterviewSession` | Practice interview records |
| `career_coach_memory` | `CareerCoachMemory` | Long-term candidate coaching context |
| `candidate_credibility_reports` | `CandidateCredibilityReport` | Resume-vs-interview credibility analysis |
| `interview_intelligence_reports` | `InterviewIntelligenceReport` | HR-facing interview intelligence |
| `employees` | `Employee` | Employee records after hiring |
| `attendance_records` | `AttendanceRecord` | Check-in/check-out records |
| `leave_requests` | `LeaveRequest` | Leave workflow |
| `skill_gap_analyses` | `SkillGapAnalysis` | Employee skill gap results |
| `departments` | `Department` | Organization departments |
| `designations` | `Designation` | Job titles/levels |
| `employee_lifecycle_events` | `EmployeeLifecycleEvent` | Career timeline events |
| `employee_tickets` | `EmployeeTicket` | HR/support tickets |
| `salary_history` | `SalaryHistory` | Salary revisions |
| `promotion_history` | `PromotionHistory` | Promotion records |
| `increment_history` | `IncrementHistory` | Increment records |
| `hr_notifications` | `HRNotification` | HR notifications |
| `candidate_profiles` | `CandidateProfile` | Candidate profile details |
| `employee_profiles` | `EmployeeProfile` | Employee profile details |
| `candidate_documents` | `CandidateDocument` | Candidate uploaded documents |
| `employee_documents` | `EmployeeDocument` | Employee uploaded documents |
| `onboarding_templates` | `OnboardingTemplate` | Reusable onboarding templates |
| `onboarding_tasks` | `OnboardingTask` | Template tasks |
| `employee_onboarding` | `EmployeeOnboarding` | Assigned onboarding plans |
| `employee_onboarding_tasks` | `EmployeeOnboardingTask` | Employee-specific onboarding task status |
| `onboarding_required_documents` | `OnboardingRequiredDocument` | Documents required by onboarding templates |
| `training_programs` | `TrainingProgram` | Training catalog |
| `training_assignments` | `TrainingAssignment` | Employee training assignments |

### Relationships

- `User` connects to resumes, applications, interviews, candidate profile, and employee records.
- `JobPosting` connects to candidate applications.
- `CandidateApplication` connects candidate, job, analysis, and official interview.
- `InterviewSession` connects to candidate, application, credibility report, and intelligence report.
- `Employee` connects to attendance, leave, salary, promotions, onboarding, training, tickets, documents, and lifecycle events.

### Data Lifecycle

```text
User registers
  |
  v
Candidate data created
  |
  v
Resume and application stored
  |
  v
Analysis and interview records generated
  |
  v
HR decision made
  |
  v
Employee record created if hired
  |
  v
Lifecycle, training, onboarding, salary, promotion, and support records accumulate
```

### Migration Strategy

The repository uses startup table creation plus idempotent `_ensure_*` schema update functions in `src/database/connection.py`. This is a practical project-scope alternative to Alembic migrations. For production at larger scale, a formal migration system would be a future improvement.

---

## 12. API Analysis

### Authentication

Most sensitive endpoints use JWT bearer authentication. Role-specific dependencies protect HR, manager, admin, employee, and candidate workflows.

### API Summary Table

| Router | Prefix | Main Purpose | Key Endpoints |
| --- | --- | --- | --- |
| Auth | `/api/auth` | Register and login | `POST /register`, `POST /login` |
| Resume | `/api/resume` | Resume upload and retrieval | `POST /upload`, `GET /me` |
| Jobs | `/api/jobs` | Job posting management | `GET /`, `GET /{job_id}`, `POST /`, `PUT /{job_id}`, `DELETE /{job_id}`, `POST /{job_id}/close`, `POST /{job_id}/archive` |
| Applications | `/api/applications` | Candidate applications and hiring | `POST /apply`, `GET /me`, `GET /`, `POST /{id}/analyze`, `POST /{id}/hire`, `GET /rankings/{job_id}`, `GET /{id}/credibility` |
| Candidates | `/api/candidates` | Candidate listing/details | `GET /`, `GET /{candidate_id}` |
| Dashboard | `/api/dashboard` | Dashboard aggregates | `GET /hr`, `GET /candidate`, `GET /hr/reviews` |
| Employees | `/api/employees` | Employee operations | Employee list, dashboard, attendance, leave, skill gap, assistant, directory, profile |
| Interview | `/api/interview` | Official interviews and intelligence | Start, answer, violation, complete, abandon, sessions, credibility, leaderboard, reports, compare, transcribe |
| Mock Interview | `/api/mock-interview` | Candidate practice interviews | `POST /start`, `POST /answer`, `POST /{session_id}/complete`, `GET /sessions` |
| Departments | `/api/departments` | Department CRUD | `GET /`, `POST /`, `PUT /{id}`, `DELETE /{id}` |
| Designations | `/api/designations` | Designation CRUD | `GET /`, `POST /`, `PUT /{id}`, `DELETE /{id}` |
| Lifecycle | `/api/lifecycle` | Employee timeline | `GET /employee/{id}`, `POST /employee/{id}` |
| Tickets | `/api/tickets` | Employee/HR tickets | Create, list, resolvers, detail, assign, status |
| Salary | `/api/salary` | Salary history | `GET /employee/{id}`, `POST /employee/{id}` |
| Promotions | `/api/promotions` | Promotions | `GET /recent`, `GET /employee/{id}`, `POST /employee/{id}` |
| Notifications | `/api/notifications` | HR notifications | `GET /`, `PUT /read-all`, `PUT /{id}/read` |
| Onboarding | `/api/onboarding` | Templates and employee onboarding | Template CRUD, task CRUD, assign, employee views, summaries, required docs |
| Training | `/api/training` | Training programs and assignments | Program CRUD, assign, assignment list, progress, summary |
| Profile | `/api/profile` | Candidate/employee profiles and documents | Profile get/update, document upload/download/review/decision |
| RAG | `/api/rag` | AI assistant over indexed knowledge | `POST /chat` |
| Admin | `/api/admin` | Admin user and knowledge management | User list/update, policy CRUD/reindex, knowledge CRUD/reindex |

### Request Flow

```text
Frontend component
  |
  v
frontend/src/api/*.js
  |
  v
Axios instance with auth token
  |
  v
FastAPI route
  |
  v
Dependency injection: DB session + current user
  |
  v
Domain service / SQLModel queries
  |
  v
JSON response
```

---

## 13. Security Analysis

### Implemented Security Features

- Password hashing with bcrypt.
- JWT access tokens using HS256.
- Token expiry configured for 7 days.
- HTTP bearer authentication.
- Backend role checks with `require_roles`.
- Admin role bypass for role checks.
- Token role is checked against the current database user role.
- Inactive users are rejected.
- Production secret validation rejects weak `SECRET_KEY` values for non-debug non-SQLite deployments.
- Public registration creates only candidate accounts.
- Privileged users require bootstrap/admin action.
- File/document review workflows exist for HR.
- Official interviews track proctoring violations.
- RAG has role-aware access control.

### Authorization Model

Roles:

- Candidate: application, resume, interviews, career assistant, candidate dashboard.
- Employee: employee dashboard, attendance, leave, onboarding, training, profile, tickets.
- HR: job, candidate, employee, onboarding, training, documents, salary, promotions, interview intelligence.
- Manager: manager dashboard and selected HR pipeline/intelligence/training views.
- Admin: user management, policy/knowledge management, and role bypass.

### Input Validation

- Pydantic models validate request payloads.
- SQLModel provides typed data models.
- Resume analysis normalizes AI responses before storing/using them.
- RAG chat request/response models define expected structure.

### Data Protection

- Passwords are not stored in plaintext.
- JWTs avoid server-side session storage.
- Role-based dependencies protect sensitive endpoints.
- Candidate and employee document workflows include review/decision status.

### Potential Weaknesses

- The project uses app-level startup migrations rather than formal migration tooling.
- Browser proctoring can be bypassed by determined users and should not be treated as enterprise-grade invigilation.
- JWT storage security depends on frontend implementation details and browser environment.
- File upload validation should be reviewed carefully before production.
- CORS defaults are limited to localhost URLs and may need production configuration.
- Rate limiting is not apparent in the repository.
- Audit logging appears partial rather than enterprise-complete.
- Hash embeddings are useful locally but are not ideal for high-quality production semantic search.

Most of these are reasonable omissions for a project built under limited time or hackathon-style constraints.

---

## 14. Deployment Architecture

### Local Deployment

Backend:

```powershell
cd D:\GitHub\HRMS
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd D:\GitHub\HRMS\frontend
npm install
npm run dev
```

Frontend dev server:

```text
http://localhost:5173
```

Backend:

```text
http://127.0.0.1:8000
```

### Production Build

```powershell
cd frontend
npm run build
```

The Vite build outputs to:

```text
static/
```

FastAPI then serves the SPA from `/`.

### Docker Deployment

The Dockerfile uses:

- `python:3.10-slim`
- A builder stage for dependencies
- A runtime stage with a non-root user
- App files copied into `/app`
- `uvicorn src.main:app`
- Configurable `PORT`
- Configurable `WEB_CONCURRENCY`

Run:

```bash
docker build -t talentforge-ai .
docker run --env-file .env -p 8000:8000 talentforge-ai
```

### Docker Compose

`docker-compose.yml` provides a local PostgreSQL 16 service:

- Database: `talentforge`
- User: `talentforge`
- Port: `5432`
- Persistent volume: `postgres_data`

### Render Deployment

`render.yaml` defines:

- Docker web service named `talentforge-ai`.
- Health check path `/api/health`.
- Generated `SECRET_KEY`.
- PostgreSQL/SSL-oriented environment variables.
- `GROQ_API_KEY` and `DATABASE_URL` as manually supplied secrets.

### Vercel Static Deployment

`vercel.json` supports serving the built `static/` frontend as a static SPA. This is only for frontend/static hosting; the backend API must still run elsewhere.

### Required Environment Variables

Important variables:

- `DATABASE_URL`
- `SECRET_KEY`
- `GROQ_API_KEY`
- `MODEL_NAME`
- `DEBUG`
- `AUTO_CREATE_DB_SCHEMA`
- `PGSSLMODE`
- `DATABASE_CONNECT_TIMEOUT`

Optional RAG/production variables:

- `RAG_CHROMA_PATH`
- `RAG_EMBEDDING_PROVIDER`
- `RAG_ANSWER_PROVIDER`
- `RAG_ANSWER_MODEL`
- `RAG_MAX_CONTEXT_CHARS`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `JOOBLE_API_KEY`
- `RAPIDAPI_KEY`

---

## 15. Design Decisions

### Why FastAPI?

FastAPI provides fast API development, typed request/response validation, dependency injection, async support, and automatic docs. It fits a project that needs many domain-specific endpoints quickly.

### Why React + Vite?

React supports component-based dashboards and complex stateful interfaces. Vite provides fast local development and simple production builds. The frontend builds into `static/`, which allows FastAPI to serve the full app.

### Why SQLModel?

SQLModel combines SQLAlchemy-style persistence with Pydantic-style models. This reduces boilerplate for a project with many database tables.

### Why SQLite and PostgreSQL?

SQLite keeps local development and tests easy. PostgreSQL is more appropriate for production. Supporting both gives the project a low-friction development path and a realistic deployment path.

### Why CrewAI and Groq?

CrewAI helps structure AI workflows as agents and tasks. Groq provides fast inference for the configured `llama-3.1-8b-instant` model. The system also includes fallback logic, which reduces dependency risk.

### Why ChromaDB?

ChromaDB is local-friendly and suitable for a project RAG system. It avoids requiring a managed vector database during development.

### Why Role-Specific Dashboards?

HRMS users have very different needs. A candidate, employee, HR user, manager, and admin should not see the same interface. Role-based dashboards make the system easier to explain and demonstrate.

### Why Startup Migrations Instead of Alembic?

Likely due to project scope or time limitations. The repository uses idempotent `_ensure_*` functions, which are simpler for a fast-moving project. A production-grade system would likely adopt Alembic or another migration tool.

### Why Deterministic Fallbacks?

External LLM APIs can fail, be unavailable, or produce invalid JSON. Deterministic fallback logic ensures the core demo and tests still work without API keys.

---

## 16. Challenges and Solutions

### Challenge: Many HR Domains in One System

Solution:

- The backend is divided into domain routers.
- The frontend uses role dashboards and feature-specific components.
- Models are grouped by lifecycle domain.

### Challenge: AI Output Can Be Unreliable

Solution:

- AI payloads are parsed and normalized.
- Fallback scoring and deterministic outputs are used.
- Resume Lab includes truth guards and validation.

### Challenge: Interviews Need Structure

Solution:

- Interview phases and turn requirements are implemented.
- Session state is persisted.
- Official and mock interviews use separate database models.

### Challenge: Hiring Decisions Need Explainability

Solution:

- Application analysis stores strengths, weaknesses, missing skills, recommendations, and prep questions.
- Hiring intelligence produces multiple decision dimensions.
- Credibility analysis compares claims with evidence.

### Challenge: Different Users Need Different Access

Solution:

- JWT includes role.
- Backend dependencies enforce role access.
- Frontend route guards redirect users to appropriate dashboards.
- RAG access control limits knowledge retrieval.

### Challenge: Local Development Should Be Easy

Solution:

- SQLite can be used locally.
- Tests override database settings.
- Frontend dev server proxies `/api` to FastAPI.
- Docker and Render config are included for production.

---

## 17. Known Limitations

- No formal Alembic migration system is present.
- Browser proctoring is not equivalent to enterprise proctoring.
- RAG hash embeddings are lower quality than dedicated semantic embedding models.
- AI outputs depend on external services when not using fallbacks.
- File upload security and virus scanning are not shown as enterprise-grade features.
- Rate limiting is not apparent.
- CORS defaults target local origins.
- The system is broad; some modules may be demo-depth rather than enterprise-depth.
- Observability, monitoring, and audit logs appear limited.
- Some deployment variables imply external services such as Supabase, but local operation is still supported.

These limitations are understandable for a portfolio or hackathon-style project and represent future production hardening areas.

---

## 18. Future Enhancements

### Short-Term Improvements

- Add a generated API reference from OpenAPI.
- Add more frontend e2e tests.
- Add stricter file type and size validation.
- Improve error messages in AI workflows.
- Add admin UI for environment/system health.
- Add better resume preview and parsed section display.

### Medium-Term Improvements

- Add Alembic migrations.
- Add rate limiting.
- Add structured audit logs.
- Add notification delivery via email or messaging.
- Add richer candidate communication workflows.
- Add more robust interview rubric configuration.
- Add organization/team-level settings.
- Add background job queue for long-running AI tasks.

### Production-Grade Improvements

- Add SSO/SAML/OAuth enterprise login.
- Add object storage for documents.
- Add antivirus scanning for uploads.
- Add observability with metrics, traces, and logs.
- Add tenant isolation for multi-company SaaS use.
- Add managed vector database option.
- Add stronger proctoring integrations.
- Add data retention policies.
- Add GDPR/PII controls and export/delete workflows.
- Add SOC2-style audit and access logs.

---

## 19. Demo Walkthrough

### Demo Setup

1. Start backend with `uvicorn src.main:app --reload --host 127.0.0.1 --port 8000`.
2. Start frontend with `npm run dev` from `frontend/`, or serve built static assets through FastAPI.
3. Create an admin user with `scripts.bootstrap_user`.
4. Prepare candidate, HR/admin, and employee accounts.
5. Ensure sample job postings and resumes are available.

### Demo Script

1. Open the login page.
   - Say: "TalentForge AI is role-based. The same platform supports candidates, HR, managers, employees, and admins."

2. Log in as a candidate.
   - Show candidate dashboard.
   - Show jobs and applications.
   - Say: "Candidates can browse jobs, apply, upload resumes, and track their application status."

3. Upload or show a resume.
   - Show resume analysis if available.
   - Say: "Resume Lab repairs extracted text, detects sections, scores the resume, and avoids suggesting unsupported claims."

4. Open mock interview.
   - Configure role, difficulty, persona, and interview type.
   - Start a mock session.
   - Say: "Mock interviews are practice sessions stored separately from official hiring interviews."

5. Open official interview.
   - Start from an application.
   - Show proctoring notice and interview workspace.
   - Submit an answer.
   - Say: "Official interviews are application-linked, phase-aware, and can record proctoring violations."

6. Log in as HR or admin.
   - Show HR dashboard.
   - Show jobs, applications, and candidate pipeline.
   - Say: "HR can review AI-generated application analysis and ranked candidates."

7. Open interview intelligence.
   - Show leaderboard or candidate report.
   - Say: "The system combines resume score, interview score, and credibility score into a transparent hiring score."

8. Show document verification and onboarding.
   - Say: "Once hired, the candidate can move into employee lifecycle workflows."

9. Log in as employee.
   - Show employee dashboard.
   - Show attendance, leave, onboarding, training, and tickets.
   - Say: "The platform continues after hiring, so recruitment data connects to employee growth."

10. Show HR Copilot or Career Assistant.
    - Ask a policy or career question.
    - Say: "The assistant uses RAG over role-scoped company and HR knowledge."

### Closing Demo Line

"The key idea is that TalentForge is not only a resume parser or dashboard. It connects the full talent lifecycle from candidate screening to interview intelligence to employee growth."

---

## 20. Interview Preparation Section

### Beginner Questions

**Q1. What is TalentForge AI?**

TalentForge AI is a full-stack HR and recruitment platform that supports candidates, HR, managers, employees, and admins. It includes job applications, resume analysis, interviews, hiring intelligence, employee workflows, onboarding, training, documents, tickets, and RAG-based assistants.

**Q2. What are the main technologies used?**

The backend uses Python, FastAPI, SQLModel, SQLite/PostgreSQL, JWT, bcrypt, CrewAI, Groq, and ChromaDB. The frontend uses React 19, Vite, React Router, Zustand, Axios, TailwindCSS, Framer Motion, Recharts, and Lucide React.

**Q3. What roles does the system support?**

It supports candidate, employee, HR, manager, and admin roles.

**Q4. Where is the backend entrypoint?**

The backend entrypoint is `src.main:app`.

**Q5. Where is the frontend located?**

The frontend source is in `frontend/`, and its production build outputs to `static/`.

### Intermediate Questions

**Q1. How does authentication work?**

Users log in through `/api/auth/login`. Passwords are verified with bcrypt. The backend creates a JWT containing user id, username, role, and expiry. Protected routes use bearer authentication and validate that the token role matches the stored user role.

**Q2. How does application analysis work?**

When a candidate applies, the system stores the application and can run recruitment analysis. The service tries AI analysis through CrewAI/Groq and normalizes the result. If AI fails, it falls back to deterministic skill matching and recommendation logic.

**Q3. What is the difference between interview and mock interview?**

Official interviews use `InterviewSession`, are tied to hiring/application context, can include proctoring, and generate HR intelligence. Mock interviews use `MockInterviewSession`, are practice-oriented, and are stored separately.

**Q4. How does the Resume Lab avoid hallucinated improvements?**

It validates AI analysis, compares suggested improvements with original resume evidence, and returns manual guidance when a suggestion would require facts not present in the resume.

**Q5. How is the frontend protected?**

`frontend/src/App.jsx` uses `RoleGuard` to restrict routes based on auth state and role. Backend route dependencies still enforce the real security boundary.

### Advanced Questions

**Q1. How does the system handle AI failure?**

Several services use fallback logic. Recruitment analysis, resume analysis, interview credibility, mock interview summaries, and hiring intelligence include deterministic or rule-based paths so the system can continue working when an LLM is unavailable or returns invalid data.

**Q2. How is hiring intelligence calculated?**

The system combines multiple signals. The documented composite hiring score is 35% resume score, 40% interview score, and 25% credibility score. It also stores reports such as competency scores, job fit, communication metrics, behavioral insights, risks, timeline replay, and benchmarking.

**Q3. How does RAG access control work conceptually?**

The RAG access control layer determines which knowledge collections and filters are allowed for a user based on role and identity. Then query routing and retrieval fetch relevant context before the chat service generates an answer.

**Q4. Why are there both relational and vector databases?**

The relational database stores structured business data such as users, applications, interviews, and employee records. The vector database stores searchable knowledge chunks for semantic retrieval in the assistant.

**Q5. What is the most important architectural tradeoff?**

The project prioritizes breadth and working workflows over enterprise depth. For example, startup migrations and local Chroma are practical for a portfolio/hackathon project, while production systems would add formal migrations, stronger observability, and managed infrastructure.

### Architecture Questions

**Q1. Describe the system architecture.**

The user interacts with a React SPA. The SPA calls FastAPI endpoints through Axios. FastAPI validates JWTs and roles, routes requests to domain routers, and uses service modules for business logic. SQLModel stores relational data in SQLite/PostgreSQL, while ChromaDB stores vectorized RAG knowledge.

**Q2. Why split API routes by domain?**

The system covers many domains, so separate routers keep code organized: auth, jobs, applications, interviews, employees, onboarding, training, RAG, admin, and so on.

**Q3. How does the frontend connect to the backend?**

Each frontend domain has an API wrapper in `frontend/src/api/`. These use a shared Axios instance to call backend `/api` routes.

**Q4. How is the production frontend served?**

Vite builds the frontend into `static/`. FastAPI serves those static files and falls back to the SPA entrypoint for client-side routes.

### Design Decision Questions

**Q1. Why use FastAPI instead of Django?**

FastAPI is lightweight, fast to develop with, has excellent type validation, and works well for API-first SPAs. Django would provide more built-in admin and ORM features but may be heavier for this architecture.

**Q2. Why use SQLModel instead of raw SQL?**

SQLModel provides typed models and reduces boilerplate while still using relational database concepts.

**Q3. Why include deterministic fallbacks?**

Fallbacks make the application demoable and testable without depending entirely on external AI availability.

**Q4. Why separate mock interview from official interview?**

Practice data should not pollute hiring decisions. Separate models and routes make the distinction clear.

**Q5. Why include RAG?**

RAG lets users ask questions over company and HR knowledge while grounding answers in indexed documents and role-accessible context.

### Security Questions

**Q1. How are passwords protected?**

Passwords are hashed using bcrypt before storage.

**Q2. How are routes protected?**

Protected routes require a bearer JWT. Backend dependencies validate the token and enforce roles.

**Q3. Can a candidate register as HR?**

Public registration creates candidate users. Privileged users are bootstrapped or managed by admins.

**Q4. What security weaknesses remain?**

Potential improvements include rate limiting, stronger file scanning, full audit logs, formal migration control, stronger proctoring, and production CORS configuration.

**Q5. How does the app prevent stale role tokens?**

The backend checks that the token role matches the current role stored in the user table.

### Scalability Questions

**Q1. What scales well already?**

The API is modular, PostgreSQL is supported, the frontend is chunked/lazy-loaded, and Docker deployment is available.

**Q2. What would need improvement for large scale?**

Add a background job queue, managed object storage, formal migrations, monitoring, rate limiting, caching, multi-tenant controls, and managed vector database support.

**Q3. How would you scale AI tasks?**

Move long-running AI work to a queue, store job status, retry failures, and use provider abstraction with rate-limit handling.

**Q4. How would you scale file uploads?**

Use object storage such as S3 or Supabase Storage, scan files, store metadata in the relational DB, and serve files with signed URLs.

### "Why Did You Choose X?" Questions

**Q1. Why React?**

React is well-suited for complex dashboards, reusable components, and role-specific SPAs.

**Q2. Why Vite?**

Vite gives fast local development and simple production builds.

**Q3. Why PostgreSQL support?**

PostgreSQL is production-grade and handles concurrent relational workloads better than SQLite.

**Q4. Why ChromaDB?**

Chroma is easy to run locally and appropriate for a project-level RAG system.

**Q5. Why Groq?**

Groq offers fast hosted LLM inference for the configured model, which is useful for interactive AI workflows.

---

## 21. Resume Description

### 1-Line Version

Built TalentForge AI, a full-stack AI-powered HRMS platform for recruitment, adaptive interviews, hiring intelligence, employee lifecycle management, and RAG-based HR assistance.

### 2-Line Version

Built TalentForge AI using FastAPI, React, SQLModel, CrewAI/Groq, and ChromaDB to connect candidate applications, resume analysis, interviews, hiring intelligence, onboarding, training, and employee operations. Implemented JWT/RBAC, AI fallbacks, role-specific dashboards, official and mock interviews, and RAG assistants.

### 50-Word Version

Developed TalentForge AI, a full-stack HR and recruitment platform using FastAPI, React, SQLModel, CrewAI/Groq, and ChromaDB. The system supports candidate applications, resume analysis, adaptive interviews, hiring intelligence, employee lifecycle workflows, onboarding, training, documents, tickets, JWT/RBAC security, role dashboards, and RAG-based HR/career assistants.

### 100-Word Version

Developed TalentForge AI, a full-stack AI-powered HRMS and recruitment platform that manages the complete talent lifecycle from candidate application to employee growth. Built a FastAPI backend with SQLModel, SQLite/PostgreSQL, JWT authentication, role-based access control, CrewAI/Groq AI workflows, deterministic fallback scoring, and ChromaDB-powered RAG. Built a React 19 + Vite frontend with role-specific dashboards for candidates, employees, HR, managers, and admins. Implemented resume analysis, job applications, application ranking, mock interviews, official proctored interviews, credibility analysis, hiring intelligence reports, onboarding, training, document verification, salary, promotions, tickets, and HR/career assistants.

---

## 22. Presentation Script

### 2-Minute Presentation

Good morning/afternoon. My project is TalentForge AI, an AI-powered HR and talent lifecycle platform. The goal is to solve a common problem in hiring and HR: data is scattered across resumes, job posts, interview notes, employee records, training plans, and policy documents.

TalentForge connects these workflows into one system. Candidates can register, browse jobs, upload resumes, apply, use resume analysis, practice mock interviews, and complete official application-linked interviews. HR can post jobs, review AI-ranked applicants, inspect interview intelligence, compare candidates, verify documents, and manage onboarding and training. Employees can manage attendance, leave, onboarding tasks, training, documents, tickets, and profile information.

Technically, the backend is built with FastAPI and SQLModel, using SQLite for development and PostgreSQL for production. The frontend is a React and Vite single-page application. AI features use CrewAI and Groq, with deterministic fallback logic so the system still works when the LLM is unavailable. The RAG assistant uses ChromaDB and role-aware access control.

The main highlight is that TalentForge is not just a CRUD HRMS. It connects resume evidence, job requirements, interview performance, credibility analysis, and employee lifecycle data into decision-ready workflows.

### 5-Minute Presentation

TalentForge AI is a full-stack AI-powered HRMS and recruitment platform. The main problem it solves is fragmentation in HR workflows. In many organizations, recruitment, interviews, onboarding, employee records, training, and HR knowledge are handled in different systems. This creates delays, inconsistent decisions, and poor visibility.

The platform supports five roles: candidate, employee, HR, manager, and admin. Each role has a dedicated dashboard and protected access. Candidates can register, apply to jobs, upload resumes, view applications, use a career assistant, practice mock interviews, and complete official interviews. HR can create jobs, review candidates, run AI analysis, compare applicants, inspect interview intelligence, verify documents, and manage employee operations. Employees can handle attendance, leave, onboarding, training, tickets, and profile workflows. Admins can manage users and knowledge content.

The architecture has a React 19 + Vite frontend and a FastAPI backend. The frontend calls domain-specific API wrappers using Axios. The backend has separate routers for auth, jobs, applications, interviews, mock interviews, employees, onboarding, training, RAG, admin, and more. SQLModel defines the database tables, and the system supports SQLite locally and PostgreSQL in production.

The AI layer has multiple parts. Resume Lab parses and repairs resume text, analyzes resume quality, and uses truth guards to avoid unsupported claims. Recruitment AI analyzes candidate fit against job requirements and ranks applications. The interview engine supports official application-linked interviews with phases, scoring, proctoring events, and completion logic. Mock interviews are separate practice sessions. Hiring intelligence combines resume score, interview score, and credibility score into a transparent decision report. The RAG assistant indexes policies, jobs, candidates, interviews, and employee knowledge into ChromaDB and answers role-scoped questions.

A key design decision is fallback behavior. AI systems can fail, so the project includes deterministic fallback logic for resume analysis, recruitment scoring, credibility analysis, and summaries. That makes the system more reliable for demos and tests.

For deployment, the project includes a Dockerfile, Render configuration, Vercel static configuration, and Docker Compose for PostgreSQL. The frontend builds into the backend `static/` directory, so FastAPI can serve the full app.

In summary, TalentForge AI demonstrates a complete talent lifecycle platform with real architecture: authentication, role-based authorization, database persistence, AI workflows, RAG, frontend dashboards, tests, and deployment support.

### 10-Minute Presentation

TalentForge AI is an AI-powered talent lifecycle platform. The idea behind the project is that HR work is not one isolated process. Hiring connects to interviewing, interviewing connects to onboarding, onboarding connects to training, and training connects to employee growth. Most HR systems treat these as separate modules, but TalentForge connects them into one workflow.

The problem starts with recruitment. A candidate applies with a resume, HR needs to compare that resume with job requirements, and interviewers need structured evidence. Without a connected system, this becomes manual and subjective. TalentForge addresses this by allowing candidates to upload resumes, apply to jobs, receive AI-assisted analysis, practice mock interviews, and complete official interviews.

The system supports five roles. Candidates use the candidate dashboard, jobs, applications, career assistant, mock interview, and official interview routes. HR users manage jobs, pipelines, candidates, interview intelligence, onboarding, training, documents, salary, promotions, and employee records. Managers get selected operational and pipeline views. Employees get attendance, leave, onboarding, training, tickets, documents, and profile workflows. Admins manage users, policies, and knowledge documents.

Architecturally, the frontend is React 19 with Vite. It uses React Router for route protection, Zustand for auth and layout state, Axios for API calls, TailwindCSS for styling, Recharts for charts, Framer Motion for transitions, and Lucide React for icons. The frontend is lazy-loaded by route and builds into the `static/` folder.

The backend is FastAPI. The entrypoint is `src.main:app`, which registers routers for auth, resume, jobs, applications, candidates, employees, dashboards, interviews, mock interviews, departments, designations, lifecycle, tickets, salary, promotions, notifications, onboarding, training, profile, RAG, and admin. The backend uses SQLModel with SQLite for local development and PostgreSQL for production. The database schema includes users, resumes, applications, jobs, interviews, mock interviews, credibility reports, intelligence reports, employees, attendance, leave, departments, designations, lifecycle events, tickets, salary, promotions, notifications, profiles, documents, onboarding, and training.

Authentication uses bcrypt for password hashing and JWT for stateless sessions. The JWT stores the user id, username, role, and expiry. Backend dependencies validate the token, check that the user is active, and verify that the token role still matches the database role. Role dependencies protect sensitive endpoints, while admin can bypass role checks.

The AI systems are the most distinctive part. Resume Lab cleans and repairs extracted resume text, detects sections, analyzes quality, and validates AI output. It includes a truth guard so suggested resume improvements do not invent unsupported claims. Recruitment AI analyzes a candidate application against a job posting, produces scores and recommendations, and falls back to deterministic skill matching if AI is unavailable.

The interview system has two separate paths. Official interviews use `InterviewSession` and are application-linked. They support phases, adaptive focus areas, personas, training modes, proctoring violation tracking, answer evaluation, completion, abandonment, credibility analysis, and HR-facing intelligence reports. Mock interviews use `MockInterviewSession` and are practice-oriented, so they do not pollute hiring data.

Hiring intelligence turns completed interviews into decision context. It includes competency scores, job fit, communication metrics, behavioral reports, risks, timeline replay, benchmarking, and recommendations. A transparent composite hiring score combines resume score, interview score, and credibility score.

The RAG system adds a knowledge layer. It uses ChromaDB to store company policies, job descriptions, candidate profiles, interview reports, and employee knowledge. Access control determines which collections a user can query. The query router and retrieval service fetch context, and the chat service returns role-aware answers.

Deployment is also covered. The project includes a Dockerfile that builds dependencies in one stage and runs the app as a non-root user in another stage. Render configuration defines a Docker web service with environment variables and a health check. Docker Compose provides PostgreSQL locally. Vercel configuration supports serving the built frontend statically when the backend is deployed separately.

The key tradeoff is that this is broad and practical rather than enterprise-heavy. It uses startup migration helpers instead of Alembic, local Chroma instead of a managed vector database, and browser-based proctoring instead of enterprise proctoring. These are reasonable project-scope decisions and provide clear future improvement paths.

Overall, TalentForge AI demonstrates full-stack engineering, AI integration, fallback design, database modeling, role-based security, RAG, interview workflows, and deployment readiness in one coherent project.

---

## 23. Judge / Interviewer Cheat Sheet

### Project Objective

Build a full-stack AI-powered HRMS that connects recruitment, resume screening, interviews, hiring intelligence, employee operations, onboarding, training, documents, and HR knowledge assistance.

### Key Technologies

- Backend: FastAPI, Python, SQLModel, SQLite, PostgreSQL
- Frontend: React 19, Vite, React Router, Zustand, Axios, TailwindCSS
- AI: CrewAI, Groq, LiteLLM, deterministic fallback logic
- RAG: ChromaDB, hash/OpenAI embeddings, role-aware retrieval
- Security: JWT, bcrypt, role-based access control
- Deployment: Docker, Render, Vercel static config, Docker Compose PostgreSQL
- Testing: pytest, Playwright configuration

### Key Achievements

- Role-specific portals for candidate, employee, HR, manager, and admin.
- Resume Lab with text repair, analysis validation, and truth guards.
- Application analysis and candidate ranking.
- Separate mock and official interview systems.
- Proctored official interviews with phase tracking.
- Hiring intelligence and credibility reports.
- Employee lifecycle modules: attendance, leave, onboarding, training, documents, tickets, salary, promotions.
- RAG-based HR/career assistant with access control.
- Production deployment files and test coverage.

### Architecture Summary

```text
React SPA
  -> Axios API calls
  -> FastAPI routers
  -> JWT/RBAC dependencies
  -> Domain services
  -> SQLModel database + Chroma vector store
  -> AI providers with deterministic fallback
```

### Major Challenges

- Integrating many HR workflows coherently.
- Making AI outputs reliable and structured.
- Keeping official and mock interview data separate.
- Supporting multiple roles safely.
- Making the system demoable without external AI services.

### Future Scope

- Alembic migrations.
- Background job queue.
- Rate limiting and audit logs.
- Object storage and file scanning.
- Enterprise SSO.
- Managed vector database.
- Stronger proctoring.
- Multi-tenant SaaS support.

### Best One-Sentence Defense

TalentForge AI is valuable because it turns disconnected HR workflows into one evidence-driven talent lifecycle system, connecting resume analysis, interviews, hiring decisions, employee growth, and company knowledge in a single full-stack application.

