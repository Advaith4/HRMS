# HR Intelligence Fix Report

## What Changed
- Added `InterviewIntelligenceReport` as a first-class database table for HR-facing interview reports.
- Upserted report rows by `session_id` or `application_id` after hiring intelligence compilation.
- HR dashboard now batch-loads report rows and exposes:
  - `ai_summary`
  - `overall_score`
  - `recommendation`
  - `report_id`
- Candidate intelligence report endpoints now include the persisted intelligence report when available.

## Lifecycle
- Final interview completion sets status to `analyzing`.
- Successful report persistence sets status to `analyzed`.
- Failed persistence marks the session `failed` instead of leaving it stuck in `analyzing`.

## Visibility
- Application credibility and candidate intelligence queries now include successful lifecycle statuses instead of only `completed`.
- Candidate dashboard distinguishes `interview_analyzing` from `interview_completed`.
