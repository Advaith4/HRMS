# TalentForge AI Project Scope

Current scope date: June 2, 2026

## 1. Project Summary

TalentForge AI is a FastAPI-based recruitment intelligence and HRMS foundation. The current implemented product now covers the core hiring-to-employee lifecycle: candidates can register, browse jobs, and apply with PDF resumes; HR can hire candidates into employee records; employees can access a portal for profile, attendance, leave, skill development, and HR support; HR and managers can review recruitment and workforce data.

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
- Completed the pre-Day-3 technical audit and stabilization report.
- Hardened JWT role validation against the current database role.
- Added production secret validation for non-test deployments.
- Restricted employee profile API access to HR/admin because employee records may contain sensitive compensation data.
- Added regression tests for stale JWT role claims and employee endpoint access.
- Implemented Day 3 Candidate to Employee conversion and Employee Portal.
- Added attendance check-in/check-out and attendance history.
- Added employee leave request submission and HR/manager approval workflow.
- Added lightweight skill gap analysis and HR Assistant with deterministic fallback behavior.
- Added frontend employee dashboard, attendance, leave, skill development, and HR assistant views.

## 3. Users And Roles

Public registration creates candidate users only. Privileged users are created or promoted server-side.

| Role | Current Scope |
| --- | --- |
| candidate | Register/login, browse jobs, view job details, apply with PDF resume, view own applications, upload/view own resume |
| hr | Create/update/delete jobs, view candidates, view all applications, re-run AI analysis, rank candidates for jobs |
| manager | View candidates, view all applications, re-run AI analysis, rank candidates for jobs |
| admin | Bypasses backend role checks and can access protected backend routes |
| employee | Employee dashboard, profile, attendance, leave requests, skill gap analysis, HR Assistant |

## 4. Authentication And RBAC Scope

Implemented:

- Password hashing with bcrypt.
- JWT creation and verification.
- Bearer-token authentication through FastAPI dependencies.
- Public registration with role escalation blocked.
- Login response includes `role` and `has_resume`.
- Backend authorization through `require_roles(...)`.
- Admin bypass behavior in `require_roles(...)`.
- JWT role claims are checked against valid roles and must match the user's current database role.
- Stale tokens are rejected after a user's role changes; users must log in again to receive a fresh role claim.
- Non-SQLite, non-debug deployments reject weak or placeholder `SECRET_KEY` values.

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
- Admin reaches employee APIs through the backend admin bypass.
- HR can convert hired candidates into employee profiles.
- Managers can review and decide leave requests, but cannot access sensitive employee profile records.

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
| `POST /api/applications/{application_id}/hire` | hr, admin | Convert candidate application into employee profile |

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
| `GET /api/employees` | hr, admin | List employee records |
| `GET /api/employees/{employee_id}` | hr, admin | View one employee record |
| `GET /api/employees/me` | employee, admin | View own employee profile |
| `GET /api/employees/dashboard` | employee, admin | Employee dashboard summary |
| `POST /api/employees/attendance/check-in` | employee, admin | Check in for today's attendance |
| `POST /api/employees/attendance/check-out` | employee, admin | Check out for today's attendance |
| `GET /api/employees/attendance` | employee, admin | View own attendance history |
| `POST /api/employees/leave` | employee, admin | Submit a leave request |
| `GET /api/employees/leave/me` | employee, admin | View own leave requests |
| `GET /api/employees/leave` | hr, manager, admin | View leave requests |
| `POST /api/employees/leave/{leave_id}/decision` | hr, manager, admin | Approve or reject leave |
| `GET /api/employees/skill-gap/me` | employee, admin | View latest skill gap analysis |
| `POST /api/employees/skill-gap/me/analyze` | employee, admin | Generate skill gap analysis |
| `POST /api/employees/assistant` | employee, admin | Ask lightweight HR Assistant |

Current status:

- Employee functionality is now a working Day 3 MVP.
- Employee records are created from hired candidate applications.
- No standalone employee CRUD workflow exists yet.
- Payroll and performance modules are not implemented yet.
- Managers cannot access employee profile records in the current backend design.

Implemented employee lifecycle models:

- `AttendanceRecord`
- `LeaveRequest`
- `SkillGapAnalysis`

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
- Hire candidate action.
- Employee directory for HR/admin.
- Leave request review for HR/manager.
- Employee dashboard.
- Employee attendance check-in/check-out.
- Employee leave submission.
- Employee skill gap analysis.
- Employee HR Assistant.
- Refresh and logout controls.

Frontend role routing:

- Candidate users land on candidate dashboard.
- HR, manager, and admin users land on management dashboard.
- Employee users land on the employee dashboard and cannot access management views.

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
- `attendance_records`
- `leave_requests`
- `skill_gap_analyses`

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
- Rejection of stale JWT role claims after database role changes.
- HR job management.
- Candidate read-only job access.
- HR-only employee profile access, with manager denial.
- Candidate application flow.
- RBAC enforcement for candidates and HR.
- AI application analysis persistence.
- Candidate ranking.
- Candidate to employee conversion.
- Employee login after hire.
- Employee dashboard access.
- Employee attendance check-in/check-out.
- Employee leave request and HR approval.
- Skill gap fallback analysis.
- HR Assistant fallback answer.
- Employee RBAC denial for candidates/managers.
- Resume parser section extraction.
- Resume text repair.
- Resume analysis validation.
- Resume fix application.

Current passing result:

```text
19 passed, 16 warnings
```

Last verified command:

```bash
.\.venv\Scripts\python.exe -m pytest tests/ -v
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
- JWT role claims must match a valid current database role.
- Weak/default JWT secrets are rejected for non-SQLite, non-debug deployments.
- Employee profile endpoints are limited to HR/admin.
- Temporary uploaded PDFs are deleted after parsing.
- Broken local proxy environment variables are cleared at startup when they point to known-dead local proxy ports.

Current security limitations:

- No refresh-token rotation.
- No password reset flow.
- No account lockout or brute-force throttling.
- No audit log for privileged actions.
- No admin UI for role changes.
- Admin bypass is broad by design and should be monitored before production expansion.
- Users must log in again after role changes because stale JWTs are rejected.

## 20. Known Limitations

- Employee module is MVP-grade and focused on the critical Day 3 workflow.
- Manager role can review applications but cannot manage jobs.
- Manager role cannot access employee profile records.
- Admin-specific frontend controls are minimal.
- No dedicated admin user-management UI yet.
- No Alembic migrations; schema changes rely on lightweight startup helpers.
- Resume lab APIs exist, but the active frontend does not expose the full resume lab workflow.
- Interview route and career coach logic exist in code but are not mounted in the current app.
- AI output depends on Groq/CrewAI availability, although fallback scoring keeps the workflow usable.
- Candidate application upload supports text-extractable PDFs only, not scanned-image resumes.
- No file storage service is used; resumes are parsed and temporary files are removed.
- No email notifications.
- No generic candidate status update endpoint beyond hiring workflow yet.
- No analytics export or reporting module yet.
- Attendance has no geolocation, biometric verification, or advanced reporting.
- Leave workflow has approve/reject but no policy accrual engine.
- Skill gap and HR Assistant are lightweight and fallback-first.

## 21. Pre-Day-3 Audit Status

Completed audit document:

- `docs/pre-day-3-technical-audit.md`

Audit scores:

| Area | Score |
| --- | --- |
| Architecture health | 84 / 100 |
| Security health | 88 / 100 |
| Maintainability | 80 / 100 |

Audit result:

- TalentForge is ready to begin Day 3.
- No Must Fix Before Day 3 blockers remain after the stabilization pass.
- Legacy Jobify-era interview, job-feed, and resume optimization code remains unmounted or dormant and should not be exposed unless intentionally productized.
- Lightweight startup migrations are acceptable for the current scope, but Day 3 schema growth should be handled carefully.

Files changed by the audit/stabilization pass:

- `src/config.py`
- `src/api/dependencies.py`
- `src/api/routes/employees.py`
- `tests/test_api.py`
- `docs/pre-day-3-technical-audit.md`

Recommended future cleanup candidates:

- Empty stubs: `agents/skill_matcher.py`, `tasks/match_task.py`
- Dormant interview route and agents/tasks
- Legacy job-feed/search modules
- Old Jobify migration docs and screenshots

## 22. Day 3 Implementation Status

Priority decision:

- Candidate to Employee conversion and Employee Portal were implemented first.
- Attendance and Leave were prioritized over advanced AI depth.
- Skill Gap Analysis and HR Assistant were implemented as lightweight, fallback-safe MVP features.

Completed Day 3 workflow:

1. Candidate applies to a job.
2. AI analysis and ranking remain available.
3. HR hires the candidate from the applications workflow.
4. Employee profile is created.
5. Candidate user's role changes to `employee`.
6. Employee logs in again with the same credentials.
7. Employee dashboard is available.
8. Employee can check in and check out.
9. Employee can submit leave requests.
10. HR/manager can approve or reject leave requests.
11. Employee can run skill gap analysis.
12. Employee can ask HR Assistant questions.

Completion report:

- `docs/day3-completion-report.md`

## 23. Suggested Next Scope

High priority:

- Add admin-only user role management endpoint and UI.
- Add HR application status update workflow.
- Add employee CRUD and onboarding workflow refinements.
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

- Employee onboarding refinement
- Attendance analytics
- Leave policy/accrual management
- Payroll
- Performance reviews
- Department/team management
- HR analytics dashboards

## 24. Acceptance Criteria For Current Scope

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
- Employee profile APIs reject managers and allow HR/admin.
- Stale JWT role claims are rejected after role changes.
- HR can hire a candidate and create an employee record.
- Hired employee can log in and access employee dashboard.
- Employee can check in, check out, and view attendance history.
- Employee can submit leave and HR/manager can approve or reject it.
- Employee can run skill gap analysis and use HR Assistant.
- Test suite passes with `pytest tests/ -v`.
