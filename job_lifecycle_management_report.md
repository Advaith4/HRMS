# Job Lifecycle Management Report

Generated: 2026-06-07

Branch: `production-hardening`

## Root Cause

Jobs previously had no lifecycle state. Every job was treated as active:

- candidates could see all jobs returned by the API
- candidates could apply as long as the job row existed
- HR delete attempted hard deletion even when applicant history existed
- delete protection returned a generic conflict message
- RAG job descriptions had no job lifecycle metadata for candidate filtering

This made completed hiring cycles look open and made deletion unsafe for jobs with applications, interviews, AI analysis, and hiring intelligence history.

## Fixes Applied

### Database

- Added `JobPosting.status`.
- Supported statuses:
  - `OPEN`
  - `CLOSED`
  - `ARCHIVED`
- New jobs default to `OPEN`.
- Added idempotent startup migration in `src/database/connection.py` for existing rows.

### Backend API

Updated `src/api/routes/jobs.py`:

- Candidate job listing excludes `ARCHIVED` jobs.
- Candidate job detail returns `404` for archived jobs.
- `POST /api/jobs/{job_id}/close`
  - `OPEN -> CLOSED`
  - preserves applications and all historical records
  - syncs updated job metadata to RAG
- `POST /api/jobs/{job_id}/archive`
  - `OPEN/CLOSED -> ARCHIVED`
  - preserves applications and all historical records
  - syncs updated job metadata to RAG
- `DELETE /api/jobs/{job_id}`
  - allows deletion only when the job has no applications
  - deletes RAG job description only for empty deleted jobs
  - blocks deletion with:

```text
This job contains applicant history and cannot be deleted. Close or archive the job instead.
```

Updated `src/api/routes/applications.py`:

- applying to `CLOSED` jobs returns:

```text
Applications for this position are closed.
```

- applying to `ARCHIVED` jobs returns:

```text
This job is no longer accepting applications.
```

Updated `src/api/routes/dashboard.py`:

- HR dashboards still receive all jobs.
- Candidate dashboards receive `OPEN` and `CLOSED` jobs only.
- Candidate dashboards do not receive `ARCHIVED` jobs.

### RAG Compatibility

Updated:

- `src/services/rag/sync_service.py`
- `src/services/rag/access_control.py`

Changes:

- synced job descriptions now include job status in content and metadata
- candidate RAG access filters `job_descriptions` to `status = OPEN`
- HR/admin/manager RAG access remains unchanged

### UI Changes

Updated HR job cards:

- status badge for `OPEN`, `CLOSED`, and `ARCHIVED`
- edit action
- close applications action for open jobs
- archive action for open/closed jobs
- delete action only for jobs with zero applicants

Updated candidate job experience:

- closed jobs remain visible
- closed jobs show a `Closed` badge
- closed job drawer displays:

```text
Applications for this position are closed.
```

- apply upload and submit controls are disabled for closed jobs
- archived jobs are hidden by backend filtering

## API Changes

Added:

```text
POST /api/jobs/{job_id}/close
POST /api/jobs/{job_id}/archive
```

Preserved:

```text
GET /api/jobs
GET /api/jobs/{job_id}
POST /api/jobs
PUT /api/jobs/{job_id}
DELETE /api/jobs/{job_id}
POST /api/applications/apply
```

Existing response shape is preserved. App exception handling returns validation messages in the existing `error` field.

## Test Results

Focused lifecycle tests:

```text
.venv\Scripts\python.exe -m pytest tests/test_job_lifecycle.py -q
7 passed, 16 warnings
```

Affected backend suites:

```text
.venv\Scripts\python.exe -m pytest tests/test_job_lifecycle.py tests/test_api.py tests/test_rag_access_control.py tests/test_rag_sync_service.py tests/test_rag_automatic_sync.py -q
31 passed, 55 warnings
```

RAG guardrails:

```text
.venv\Scripts\python.exe -m pytest tests/test_rag_query_router.py tests/test_rag_foundation.py tests/test_rag_access_control.py tests/test_rag_sync_service.py -q
21 passed, 1 warning
```

Interview guardrails:

```text
.venv\Scripts\python.exe -m pytest tests/test_interview_stabilization.py tests/test_proctoring.py -q
19 passed, 29 warnings
```

Frontend build:

```text
npm run build
```

Result: passed.

## Remaining Risks

- Existing Chroma job records without `status` metadata will not be returned to candidates until those jobs are resynced. This is conservative and prevents closed/archived leakage.
- The HR UI hides delete for jobs with applicants based on loaded dashboard data; backend delete protection remains authoritative.
- Managers can perform lifecycle actions through the backend, but the current manager UI does not expose dedicated job lifecycle controls.
- Existing production jobs are migrated to `OPEN`; HR should close or archive completed historical jobs after deployment.
