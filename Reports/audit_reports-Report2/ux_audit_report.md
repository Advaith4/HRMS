# TalentForge UX Audit Report

## Candidate Experience

| Issue | Severity | Impact |
|---|---|---|
| Interview startup can feel slow because first question waits on resume analysis and LLM generation. | High | Candidate sees long initialization state. |
| Proctoring setup blocks the entire interview and may be impossible on mobile. | High | Mobile candidates cannot proceed. |
| Refresh with `appId` auto-calls start/resume. | Medium | Completed/cancelled users can see confusing errors. |
| Voice answer path requires recording, transcription, review, and submit. | Medium | High friction compared with typing. |
| Ending early says progress will be evaluated, but backend completion may fail and UI exits. | High | Trust issue and possible lost feedback. |

## HR Recruiter Experience

| Issue | Severity | Impact |
|---|---|---|
| Interview reports can disappear or look incomplete after status becomes `analyzed`. | Critical | HR may think interview was not completed. |
| Candidate report aggregates by candidate rather than selected application/job. | High | HR may evaluate the wrong context. |
| Leaderboard/top/compare views use different data filters. | High | Inconsistent rankings. |
| HR actions update leaderboard but not selected report panel. | Medium | Stale detail view after action. |
| Fallback AI reports are not clearly marked as fallback. | Medium | Overconfidence in weak data. |

## Admin/Manager Experience

- Manager access to candidate intelligence should be clarified: view-only frontend exists, but backend allows manager on several intelligence reads.
- Admin bypass exists backend-side, but frontend role routing should consistently handle admin.

## Navigation/Feedback

- Candidate dashboard distinguishes pending/active/completed/cancelled, but analyzed status is not handled.
- Loading states exist but do not expose which phase is slow: resume analysis, LLM question, transcription, or final report.
- Frontend cache can keep stale dashboards after mutations.

## UX Recommendations

1. Add explicit interview status states: pending, active, completed, analyzing, analyzed, failed, cancelled.
2. Show progress messaging for startup: loading application, analyzing resume, preparing first question.
3. Provide a desktop-only proctoring notice before the user enters interview page.
4. Make HR report selection application-specific.
5. Clearly label fallback/estimated AI reports.
