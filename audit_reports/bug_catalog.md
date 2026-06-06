# TalentForge Bug Catalog

## Critical

1. Backend aliases `/start`, `/start-for-application`, and `/start-from-resume` to an application-only request model. Evidence: `src/api/routes/interview.py:63`, `src/api/routes/interview.py:79-82`.
2. Frontend `startInterview()` and `startInterviewFromResume()` send payloads that no longer match backend. Evidence: `frontend/src/api/interview.js:11`, `frontend/src/api/interview.js:30`.
3. Hiring intelligence changes session status to `analyzed`, but many consumers only handle `completed`. Evidence: `src/services/hiring_intelligence.py:457`, `src/api/routes/dashboard.py:213`.
4. Credibility endpoint lacks session ownership/role enforcement. Evidence: `src/api/routes/interview.py:821-824`.
5. HR InterviewReports references undefined `MessageSquare`, causing runtime crash. Evidence: lint and `frontend/src/pages/hr/InterviewReports.jsx:632`.

## High

6. Duplicate active interview sessions can be created under concurrent starts because no unique DB constraint exists on `application_id`.
7. Duplicate applications can be created under concurrent applies because no composite unique constraint exists on candidate/job.
8. HR advance/reject can mutate the wrong application because it selects latest application by candidate.
9. Application credibility endpoint ignores analyzed sessions by filtering only completed.
10. Leaderboard/top candidates exclude analyzed sessions.
11. Candidate dashboard excludes analyzed sessions from completed state.
12. Manual interview and resume interview comments/API wrappers are stale.
13. Proctoring can be bypassed by direct API usage.
14. BackgroundTasks are not durable and can be lost on process crash.
15. Pytest currently fails collection due to `SECRET_KEY` config.
16. Frontend lint fails with 226 problems.
17. Frontend GET cache key ignores query params.
18. Invalid JSON in session context can crash render paths.
19. `_next_employee_code()` is race-prone.
20. SQLite migrations lack equivalent FK constraints for added columns.

## Medium

21. HR intelligence report mixes candidate-level applications/sessions.
22. Full message JSON is rewritten every answer.
23. Resume analysis can rerun in multiple flows.
24. Fallback AI reports are not prominently labeled.
25. No rate limit on LLM-cost endpoints.
26. Large route/page modules reduce maintainability.
27. Broad exception fallbacks hide real AI failures.
28. Candidate interview cancel from setup may not abandon server session.
29. HR action reloads leaderboard but not selected report details.
30. Vite build output is committed, causing static hash churn.

## Low

31. Many unused imports/variables in frontend.
32. Some route comments no longer match actual endpoints.
33. Use of JSON text fields reduces queryability.
34. No line-item token/cost tracking for AI calls.
35. Some UI labels call the official application interview a mock interview.
