# TalentForge HR Intelligence Audit

## Pipeline Trace

Application submitted -> background resume analysis -> candidate interview -> answer evaluation -> session completion -> credibility report -> hiring intelligence JSON -> HR dashboard/report.

## Visibility Checks

| Step | Current Behavior | Risk |
|---|---|---|
| Application Submitted | `CandidateApplication` is created and analysis background task starts. | Background failures are logged but not surfaced strongly. |
| Resume Analysis | `ApplicationAIAnalysis` is unique per application. | Pending/failed state can leave HR with empty analysis. |
| Interview | `InterviewSession` links to `application_id`. | Duplicate sessions possible under race. |
| Evaluation | Feedback is embedded in `InterviewSession.messages`. | Not queryable as structured rows. |
| Credibility | `CandidateCredibilityReport` is unique by session. | Manual endpoint lacks ownership/role guard for candidates vs HR. |
| Intelligence Report | Stored as JSON text fields on interview session. | Session status becomes `analyzed`. |
| HR Dashboard | HR app payload includes latest session by application. | Some UI/API paths only treat `completed` as complete, hiding analyzed sessions. |

## Findings

| Severity | Finding | Evidence |
|---|---|---|
| Critical | Successful intelligence compilation can make completion checks fail. | Status set to `analyzed` in `src/services/hiring_intelligence.py:457`; candidate dashboard uses `sess.status == "completed"` at `src/api/routes/dashboard.py:213`. |
| High | Application credibility endpoint only finds `InterviewSession.status == "completed"`. | `src/api/routes/applications.py:440-443`. |
| High | Leaderboard includes completed and cancelled but not analyzed. | `src/api/routes/interview.py:860`. |
| High | Top candidates only query completed. | `src/api/routes/interview.py:1189`. |
| High | Candidate report averages only sessions with status completed. | `src/api/routes/interview.py:981`. |
| High | Intelligence report is candidate-scoped, not application/job scoped. | `GET /api/interview/intelligence/report/{candidate_id}`. |
| Medium | HR report detail may use the latest session, not necessarily selected job/application. | Candidate report queries latest app and all sessions for candidate. |
| Medium | Frontend GET cache can show stale HR reports for 30 seconds. | `frontend/src/api/axios.js:16` and line 58. |

## Failure Points

- Background task can fail silently into fallback generation.
- Credibility report can fail and intelligence fallback still emits generic estimates.
- Report writes are not transactional with status reads by dashboard.
- HR actions advance/reject latest candidate application rather than a specific application.

## Recommendations

1. Define allowed terminal statuses: use `completed` plus `analysis_status`, or update all reads to include `analyzed`.
2. Make HR report endpoints application-scoped.
3. Add persisted `InterviewEvaluation` or turn table.
4. Surface background task state: pending, processing, analyzed, failed.
5. Invalidate frontend cache after advance/reject and report polling.
