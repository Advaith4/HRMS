# API Optimization Report

## Endpoint Contract Fixes
- `startInterviewForApplication` now calls `/api/interview/start-for-application`.
- `/api/interview/start`, `/api/interview/start-for-application`, and `/api/interview/start-from-resume` share a compatible start model.
- Answer responses now include lifecycle `status`, so the frontend can move into analysis polling without guessing.

## Dashboard Payloads
- HR dashboard batch-loads `InterviewIntelligenceReport` records by application id.
- Candidate dashboard includes:
  - `can_start_interview`
  - `can_resume_interview`
  - `interview_completed`
  - `interview_analyzing`
  - `interview_score`

## Data Integrity
- Added startup migration helpers for the intelligence report table.
- Added unique indexes for one application per candidate/job and one interview session per application.
