# TalentForge AI Project Scope

Current scope date: June 2, 2026

## 1. Project Summary

TalentForge AI is a FastAPI-based recruitment intelligence and HRMS foundation. The current implemented product focuses on hiring workflows: candidates can register, browse jobs, and apply with PDF resumes; HR and managers can manage or review recruitment data; AI analysis helps recruiters evaluate candidate-job fit and generate interview preparation material.

The app is served as a single FastAPI service:

- Backend API: `src/main.py`
- Static frontend: `static/`
- Database layer: SQLModel with Supabase PostgreSQL in normal operation
- AI orchestration: CrewAI with Groq model access
- Compatibility entry point: `app.py`

## 2. Objectives Completed So Far

- Rebranded and organized the app as TalentForge AI.
- Added role-based access control for candidate, HR, manager, admin, and employee roles.
- Added Supabase PostgreSQL configuration and deployment guidance.
- Kept SQLite support for isolated tests and legacy migration tooling.
- Added candidate application workflow with PDF resume parsing.
- Added HR job management.
- Added management dashboards for candidates, applications, rankings, and job postings.
- Added AI recruitment analysis with a deterministic fallback when LLM/CrewAI is unavailable.
- Added scripts for schema initialization, privileged user bootstrap, and SQLite-to-Postgres migration.
- Updated README and deployment documentation.
- Added regression tests for auth, RBAC, jobs, candidate applications, AI analysis, rankings, and resume lab logic.

## 3. Users And Roles

Public registration creates candidate users only. Privileged users are created or promoted server-side.

| Role | Current Scope |
| --- | --- |
| candidate | Register/login, browse jobs, view job details, apply with PDF resume, view own applications, upload/view own resume |
| hr | Create/update/delete jobs, view candidates, view all applications, re-run AI analysis, rank candidates for jobs |
| manager | View candidates, view all applications, re-run AI analysis, rank candidates for jobs |
| admin | Bypasses backend role checks and can access protected backend routes |
| employee | Stored as a supported role and reserved for future HRMS modules |

## 4. Authentication And RBAC Scope

Implemented:

- Password hashing with bcrypt.
- JWT creation and verification.
- Bearer-token authentication through FastAPI dependencies.
- Public registration with role escalation blocked.
- Login response includes `role` and `has_resume`.
- Backend authorization through `require_roles(...)`.
- Admin bypass behavior in `require_roles(...)`.

Important behavior:

- `/api/auth/register` accepts only `username` and `password`.
- Users cannot register themselves as `hr`, `manager`, or `admin`.
- To create privileged users, run:

```bash
python -m scripts.bootstrap_user --username admin --password "CHANGE_ME" --role admin
python -m scripts.bootstrap_user --username hr_user --password "CHANGE_ME" --role hr
```

## 5. Candidate Scope

Implemented frontend views:

- Candidate dashboard
- Job listing
- Job details
- Apply to job
- My applications

Implemented candidate capabilities:

- Create candidate account.
- Log in and persist session in local storage.
- View available jobs.
- Open job details.
- Submit a PDF resume for a selected job.
- See application status and attached AI analysis.
- Upload a personal resume through the backend resume API.
- Fetch own resume metadata and parsed sections.

Candidate restrictions:

- Cannot create, update, or delete jobs.
- Cannot view all candidates.
- Cannot view all applications.
- Cannot access management rankings.

## 6. HR And Management Scope

Implemented frontend views:

- Management dashboard
- Jobs management
- Candidates list
- Applications list
- Candidate profile modal/details
- AI analysis modal
- Candidate ranking panel

Implemented HR capabilities:

- Create job postings.
- Edit job postings.
- Delete job postings when no candidate application exists for that job.
- View candidates.
- View candidate profiles with application history.
- View all applications.
- View AI analysis for each application.
- Re-run AI analysis for an application.
- Rank applicants for a selected job.

Implemented manager capabilities:

- View candidates.
- View applications.
- Re-run AI analysis.
- Rank applicants.

Manager restrictions:

- Managers cannot create, update, or delete jobs in the current route design.

Admin behavior:

- Admin is allowed by backend role checks.
- Frontend shows an employee metric card only for admin users.
- Employee APIs are read-only shells at this stage.

## 7. Job Posting Scope

Implemented model: `JobPosting`

Fields:

- `title`
- `description`
- `required_skills`
- `department`
- `salary_range`
- `experience_required`
- `created_at`
- `created_by`

Implemented operations:

| Endpoint | Role Scope | Description |
| --- | --- | --- |
| `GET /api/jobs` | candidate, hr, manager, admin | List jobs |
| `GET /api/jobs/{job_id}` | candidate, hr, manager, admin | View one job |
| `POST /api/jobs` | hr, admin | Create job |
| `PUT /api/jobs/{job_id}` | hr, admin | Update job |
| `DELETE /api/jobs/{job_id}` | hr, admin | Delete job if it has no applications |

## 8. Candidate Application Scope

Implemented model: `CandidateApplication`

Fields:

- `candidate_user_id`
- `job_id`
- `resume_text`
- `application_date`
- `status`

Implemented behavior:

- Candidate uploads PDF during application.
- App extracts text from the PDF.
- App rejects non-PDF uploads.
- App rejects files above 5 MB.
- App rejects PDFs where usable text cannot be extracted.
- Uploaded PDF is stored temporarily, parsed, then removed.
- Application is persisted with extracted resume text.
- AI analysis is triggered after application creation.

Implemented operations:

| Endpoint | Role Scope | Description |
| --- | --- | --- |
| `POST /api/applications/apply` | candidate, admin | Apply to a job with PDF resume |
| `GET /api/applications/me` | candidate, admin | Candidate's own applications |
| `GET /api/applications` | hr, manager, admin | All applications |
| `POST /api/applications/{application_id}/analyze` | hr, manager, admin | Re-run AI analysis |
| `GET /api/applications/rankings/{job_id}` | hr, manager, admin | Rank applicants for a job |

## 9. AI Recruitment Analysis Scope

Implemented model: `ApplicationAIAnalysis`

Fields:

- `application_id`
- `fit_score`
- `recommendation`
- `summary`
- `strengths`
- `weaknesses`
- `missing_skills`
- `observations`
- `technical_questions`
- `behavioral_questions`
- `probing_areas`
- `status`
- `error_message`
- `source`
- `created_at`
- `updated_at`

Implemented AI flow:

1. Candidate applies with a resume.
2. Resume text is extracted.
3. `src/services/recruitment_ai.py` loads the job and application.
4. CrewAI runs the recruitment analyst agent and task.
5. AI output is expected as structured JSON.
6. Output is normalized and persisted.
7. If AI fails, deterministic fallback analysis is generated.

AI output scope:

- Fit score from 0 to 100.
- Recommendation:
  - `Strongly Recommended`
  - `Recommended`
  - `Consider`
  - `Reject`
- Summary for recruiter review.
- Strengths and weaknesses.
- Missing required skills.
- Observations.
- Technical interview questions.
- Behavioral interview questions.
- Probing areas.

Fallback scoring scope:

- Parses resume sections.
- Compares resume terms with job required skills.
- Scores skill match, experience/project evidence, education evidence, and title relevance.
- Produces recruiter-facing recommendations even when Groq/CrewAI is unavailable.

## 10. Resume Scope

Implemented model: `Resume`

Fields:

- `user_id`
- `raw_text`
- `original_text`
- `current_text`
- `parsed_resume`
- `last_analysis`
- `applied_fixes`
- `created_at`
- `updated_at`

Implemented resume APIs:

| Endpoint | Role Scope | Description |
| --- | --- | --- |
| `POST /api/resume/upload` | candidate, admin | Upload and parse candidate resume PDF |
| `GET /api/resume/me` | candidate, admin | Fetch current user's resume metadata |

Implemented parsing logic:

- PDF text extraction through `utils/resume_parser.py`.
- Resume parsing and deterministic validation through `src/resume_lab.py`.
- Stored parsed sections for future resume lab workflows.

Frontend note:

- The active TalentForge frontend focuses on job applications and management dashboards. Resume upload APIs exist, but the current static frontend does not expose a full standalone resume lab workflow.

## 11. Candidate Review Scope

Implemented endpoints:

| Endpoint | Role Scope | Description |
| --- | --- | --- |
| `GET /api/candidates` | hr, manager, admin | List candidate users |
| `GET /api/candidates/{candidate_id}` | hr, manager, admin | View candidate profile and applications |

Candidate payload includes:

- Candidate identity
- Role
- Target role
- Location
- Experience
- Created date
- Application count
- Optional application details

## 12. Employee Scope

Implemented model: `Employee`

Fields:

- `user_id`
- `employee_code`
- `department`
- `designation`
- `salary`
- `joining_date`
- `skills`

Implemented endpoints:

| Endpoint | Role Scope | Description |
| --- | --- | --- |
| `GET /api/employees` | hr, manager, admin | List employee records |
| `GET /api/employees/{employee_id}` | hr, manager, admin | View one employee record |

Current status:

- Employee functionality is a shell for future HRMS expansion.
- No frontend CRUD workflow exists yet.
- No employee onboarding, attendance, payroll, leave, or performance modules are implemented yet.

## 13. Frontend Scope

Implemented frontend files:

- `static/index.html`
- `static/script.js`
- `static/style.css`

Implemented frontend behaviors:

- Login/register toggle.
- Session persistence with `localStorage`.
- Role-aware navigation.
- Candidate dashboard metrics.
- Candidate job listing and application flow.
- Management dashboard metrics.
- HR job create/edit/delete form.
- Candidate table.
- Applications table.
- AI analysis modal.
- Re-analysis action.
- Job-specific ranking panel.
- Refresh and logout controls.

Frontend role routing:

- Candidate users land on candidate dashboard.
- HR, manager, and admin users land on management dashboard.
- Employee users receive a placeholder message because employee workflows are future scope.

## 14. Database Scope

Primary database:

- Supabase PostgreSQL through SQLModel.

Supported test/migration database:

- SQLite only when explicitly configured for tests and legacy migration.

Implemented tables:

- `users`
- `resumes`
- `job_applications`
- `interview_sessions`
- `career_coach_memory`
- `job_postings`
- `candidate_applications`
- `application_ai_analyses`
- `employees`

Migration approach:

- No Alembic.
- `src/database/connection.py` runs idempotent lightweight startup migrations.
- `AUTO_CREATE_DB_SCHEMA=true` creates SQLModel tables at startup where allowed.
- Helpers ensure newer columns/tables exist for:
  - user role
  - application AI analysis
  - resume lab fields
  - interview context fields
  - career coach memory

## 15. Scripts Scope

Implemented scripts:

| Script | Purpose |
| --- | --- |
| `scripts/init_database.py` | Create tables and run lightweight migrations |
| `scripts/bootstrap_user.py` | Create or promote privileged users |
| `scripts/migrate_sqlite_to_postgres.py` | Copy legacy SQLite data into PostgreSQL |

Migration script scope:

- Creates destination tables.
- Copies source tables in foreign-key-safe order.
- Resets PostgreSQL identity sequences.
- Requires an empty destination database for clean migration.

## 16. Deployment Scope

Implemented deployment files:

- `Dockerfile`
- `render.yaml`
- `vercel.json`
- `.env.example`
- `docs/deployment.md`

Supported deployment:

- Docker backend service.
- Render web service or blueprint using Docker.
- Static frontend can be hosted separately through Vercel, but the primary current app serves frontend and backend from FastAPI.

Required production environment:

- `DATABASE_URL`
- `SECRET_KEY`
- `GROQ_API_KEY`
- `PGSSLMODE`
- `DATABASE_CONNECT_TIMEOUT`
- `AUTO_CREATE_DB_SCHEMA`
- `MODEL_NAME`
- `DEBUG`

Optional Supabase metadata:

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`

## 17. Testing Scope

Implemented tests:

- `tests/test_api.py`
- `tests/test_resume_lab.py`

Covered by tests:

- Candidate registration and login.
- Login response role.
- Public registration role escalation rejection.
- HR job management.
- Candidate read-only job access.
- Candidate application flow.
- RBAC enforcement for candidates and HR.
- AI application analysis persistence.
- Candidate ranking.
- Resume parser section extraction.
- Resume text repair.
- Resume analysis validation.
- Resume fix application.

Current passing result:

```text
15 passed, 1 warning
```

## 18. Legacy And Available Modules

The repository still contains legacy Jobify/CrewAI modules and route code that are useful for future expansion:

- `crew.py`
- `agents/job_finder.py`
- `agents/skill_matcher.py`
- `agents/resume_optimizer.py`
- `agents/interview_coach.py`
- `tasks/job_task.py`
- `tasks/match_task.py`
- `tasks/resume_task.py`
- `tasks/interview_task.py`
- `src/api/routes/interview.py`
- `JobApplication`, `InterviewSession`, and `CareerCoachMemory` models

Current exposure note:

- `src/main.py` includes auth, resume, jobs, applications, candidates, and employees routers.
- The interview router exists in the codebase but is not mounted in the current FastAPI app.
- The current frontend is recruitment-focused and does not expose the older Jobify navigation.

## 19. Security Scope

Implemented:

- `.env` is ignored by Git.
- `.env.example` contains placeholders only.
- Passwords are bcrypt-hashed.
- JWT tokens include user id, username, role, and expiry.
- Protected API routes require bearer auth.
- Role escalation through public registration is blocked.
- Temporary uploaded PDFs are deleted after parsing.
- Broken local proxy environment variables are cleared at startup when they point to known-dead local proxy ports.

Current security limitations:

- No refresh-token rotation.
- No password reset flow.
- No account lockout or brute-force throttling.
- No audit log for privileged actions.
- No admin UI for role changes.
- Admin bypass is broad by design and should be monitored before production expansion.

## 20. Known Limitations

- Employee module is read-only and skeletal.
- Manager role can review applications but cannot manage jobs.
- Admin-specific frontend controls are minimal.
- No dedicated admin user-management UI yet.
- No Alembic migrations; schema changes rely on lightweight startup helpers.
- Resume lab APIs exist, but the active frontend does not expose the full resume lab workflow.
- Interview route and career coach logic exist in code but are not mounted in the current app.
- AI output depends on Groq/CrewAI availability, although fallback scoring keeps the workflow usable.
- Candidate application upload supports text-extractable PDFs only, not scanned-image resumes.
- No file storage service is used; resumes are parsed and temporary files are removed.
- No email notifications.
- No candidate status update endpoint for HR yet.
- No analytics export or reporting module yet.

## 21. Suggested Next Scope

High priority:

- Add admin-only user role management endpoint and UI.
- Add HR application status update workflow.
- Add employee CRUD and onboarding workflow.
- Add better frontend resume upload/profile management.
- Add production-grade audit logging for privileged actions.

Medium priority:

- Mount or retire the interview route intentionally.
- Add candidate profile editing.
- Add search/filter/sort for jobs, candidates, and applications.
- Add pagination for management tables.
- Add rate limiting for auth endpoints.
- Add richer deployment health checks.

Future HRMS modules:

- Employee onboarding
- Attendance
- Leave management
- Payroll
- Performance reviews
- Department/team management
- HR analytics dashboards

## 22. Acceptance Criteria For Current Scope

The current scope is considered complete when:

- App starts with `uvicorn src.main:app --host 127.0.0.1 --port 8000`.
- `/` serves the TalentForge frontend.
- `/api/docs` serves FastAPI docs.
- `/api/health` returns `{"status": "ok"}`.
- Candidate registration produces a candidate account only.
- HR/admin users can be bootstrapped from the server.
- Candidate can browse jobs and apply with a PDF.
- HR can create jobs and view submitted applications.
- AI analysis is persisted for applications.
- Ranking endpoint returns ordered applicants for a job.
- Test suite passes with `pytest tests/ -v`.

