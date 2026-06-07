# Security Fix Report

## Access Control
- Candidate credibility report endpoint now fetches the real `InterviewSession` and enforces ownership before analysis.
- HR/manager/admin roles retain access to HR intelligence routes.
- Candidate users can only access their own interview sessions.

## IDOR Mitigation
- HR advance/reject actions now target the session's attached `application_id` instead of the candidate's latest application.
- Application-scoped sessions enforce candidate ownership at startup.

## Session Safety
- Active sessions are resumed instead of duplicated.
- Cancelled sessions remain cancelled and return cancellation details.
- Candidate exit marks active sessions as `cancelled` with `candidate_exit`.
