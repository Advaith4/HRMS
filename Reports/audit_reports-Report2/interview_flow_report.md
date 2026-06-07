# TalentForge Interview Flow Report

## Sequence Diagram Description

Candidate -> Frontend -> API -> Database -> LLM -> Evaluation -> Hiring Intelligence -> HR Dashboard

1. Candidate opens `frontend/src/pages/interview/InterviewPage.jsx`.
2. Page loads candidate applications via dashboard data.
3. Candidate clicks Start/Resume.
4. Frontend calls `startInterviewForApplication()` in `frontend/src/api/interview.js`.
5. Backend `start_interview()` loads `CandidateApplication`, verifies ownership, checks existing session, loads `JobPosting`, resume text, resume analysis, coach memory, and creates `InterviewSession`.
6. Backend calls `crew.run_interview_start()` to generate first question.
7. Candidate answers in `InterviewWorkspaceShell`.
8. Frontend may record audio, transcribe via `/api/interview/transcribe`, then submits text to `/api/interview/answer`.
9. Backend calls `crew.run_interview_answer()` to evaluate answer and generate next question.
10. Backend appends user/feedback/AI messages to DB and updates coach memory.
11. When phase reaches Final Evaluation or user completes manually, session becomes completed and `compile_hiring_intelligence()` is queued.
12. Hiring intelligence triggers credibility analysis, synthesizes report, saves JSON fields, and changes session status to `analyzed`.
13. HR opens `InterviewReports.jsx`; frontend calls leaderboard/report/top/compare endpoints.

## Data Writes

- `InterviewSession` created with first AI message.
- `Resume.last_analysis` and `Resume.parsed_resume` may be updated during interview start.
- `CareerCoachMemory` updates during start and each answer.
- `InterviewSession.messages`, `personalization_context`, `difficulty`, `avg_score`, `status`, and intelligence JSON fields update over time.
- `CandidateCredibilityReport` is upserted during credibility/hiring intelligence.
- `HRNotification` is created for proctoring cancellation.

## Data Reads

- Candidate application, job posting, resume, previous analysis, coach memory.
- Existing interview sessions by application and status.
- HR intelligence reads sessions, applications, analyses, credibility reports, users, and jobs.

## API Calls

- `GET /api/dashboard/candidate`
- `POST /api/interview/start`
- `POST /api/interview/answer`
- `POST /api/interview/transcribe`
- `POST /api/interview/{session_id}/violation`
- `POST /api/interview/{session_id}/complete`
- `GET /api/interview/intelligence/*`

## LLM Calls

- Resume analysis may run at interview start if missing.
- First question generation calls `run_interview_start`.
- Every answer calls `run_interview_answer`; this can include evaluation plus follow-up generation.
- Completion calls credibility analysis and hiring intelligence synthesis.
- Voice path calls Groq Whisper transcription per recorded answer.

## Highest Priority Flow Issues

| Severity | Finding | Evidence |
|---|---|---|
| Critical | Three backend start routes all point to application-only model. | `src/api/routes/interview.py:79-82`, `StartForApplicationReq` at line 63. |
| Critical | `startInterviewForApplication()` posts to `/api/interview/start`, while comments say `/start-for-application`. | `frontend/src/api/interview.js:230-236`. It works only because backend aliases the route. |
| High | Manual and resume-aware frontend clients are stale. | `frontend/src/api/interview.js:11`, `frontend/src/api/interview.js:30`. |
| High | Session status changes from completed to analyzed after report generation. | `src/services/hiring_intelligence.py:457`. |
| High | HR reports aggregate by candidate instead of selected application/job. | `intelligence_candidate_report(candidate_id)` in `src/api/routes/interview.py`. |
| Medium | Proctoring events are client-driven and can be bypassed. | Frontend controls event detection; backend only counts posted violations. |
