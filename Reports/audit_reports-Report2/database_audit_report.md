# TalentForge Database Audit Report

## ER Diagram Description

Core hiring graph:

`User(candidate)` -> `Resume`
`User(candidate)` -> `CandidateApplication` -> `JobPosting`
`CandidateApplication` -> `ApplicationAIAnalysis`
`CandidateApplication` -> `InterviewSession`
`InterviewSession` -> `CandidateCredibilityReport`
`InterviewSession` stores hiring intelligence JSON fields directly.

Employee graph:

`User(employee)` -> `Employee` -> attendance, leave, salary, promotion, lifecycle, onboarding, training, tickets, documents.

Profile/document graph:

`User` -> `CandidateProfile` or `EmployeeProfile`
`User` -> candidate/employee documents, with HR review metadata.

## Relationship Mapping

- `users.id` is referenced by resumes, applications, interviews, notifications, profiles, documents, and employee records.
- `candidate_applications.id` is referenced by `application_ai_analyses.application_id` and `interview_sessions.application_id`.
- `interview_sessions.id` is referenced by `candidate_credibility_reports.session_id`.
- `job_postings.id` is referenced by `candidate_applications.job_id`.
- `employees.id` is referenced by attendance, leave, salary, promotions, onboarding, training, tickets, documents.

## Findings

| Severity | Finding | Evidence | Potential Failure |
|---|---|---|---|
| Critical | SQLite migrations add `interview_sessions.application_id` without a foreign key. | SQLite `_ensure_interview_context_columns` adds `"application_id": "INTEGER"` in `src/database/connection.py:198`; model declares FK at `src/models/__init__.py:68`. | Dev/test SQLite can permit orphan interview sessions that production PostgreSQL rejects. |
| Critical | Startup migrations are not schema-versioned. | Repeated `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` and `CREATE TABLE IF NOT EXISTS` in `src/database/connection.py`. | Production drift, silent partial migrations, hard rollback. |
| High | Interview status state machine is inconsistent. | `hiring_intelligence.py` sets `interview_session.status = "analyzed"` at line 457; many consumers check only `"completed"`. | Successfully analyzed interviews can disappear from completed filters. |
| High | No unique constraint prevents multiple interview sessions per application. | `InterviewSession.application_id` is indexed but not unique in `src/models/__init__.py:68`; start code checks then inserts separately. | Concurrent starts can create duplicate active sessions. |
| High | No composite unique constraint prevents duplicate applications. | `CandidateApplication` has individual indexes on candidate and job only. | Concurrent applies can create duplicates despite route-level check. |
| High | JSON stored as text for key analytical fields. | `messages`, `personalization_context`, `competency_scores`, `job_fit_report`, etc. in `InterviewSession`. | Cannot index/query intelligence reliably; invalid JSON possible; PostgreSQL JSONB benefits lost. |
| Medium | Cascade behavior is not explicit. | Models use FK fields but no SQLModel relationships/cascade settings. | Deletes can fail or leave orphan rows depending on DB settings. |
| Medium | Some indexes are missing for common filters. | HR dashboard orders by `created_at`/`application_date`; intelligence filters by status and application/job. | Slow dashboards as data grows. |
| Medium | `_next_employee_code()` counts all employees then loops. | `src/api/routes/applications.py:401`. | Race condition can produce duplicate employee codes under concurrent hires. |

## Query Pattern Risks

- HR dashboard has batch fetching for applications, analyses, users, jobs, and sessions, which is good.
- Intelligence leaderboard/report routes perform per-candidate lookups in loops, causing N+1 behavior.
- Candidate report chooses latest application by candidate, not by selected job/application, risking cross-application mixing.

## Potential Failures

1. A candidate starts the same interview in two tabs; both requests pass the existence check and insert duplicate sessions.
2. Hiring intelligence completes, marks status `analyzed`, and candidate dashboard no longer marks the interview completed.
3. SQLite accepts data that PostgreSQL rejects because migration-created columns lack constraints.
4. Deleting users/applications can leave related records or fail due to unspecified cascade policy.
