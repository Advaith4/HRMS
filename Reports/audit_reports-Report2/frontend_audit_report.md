# TalentForge Frontend Audit Report

## Verification

- `npm run build` passed.
- `npm run lint` failed with 210 errors and 16 warnings.

## Critical Findings

| Severity | Finding | Evidence | Impact |
|---|---|---|---|
| Critical | `InterviewReports.jsx` references `MessageSquare` without importing it. | Lint reported `MessageSquare is not defined`; source reference `frontend/src/pages/hr/InterviewReports.jsx:632`. | HR intelligence page can crash at runtime. |
| Critical | Interview API clients are stale. | `startInterview()` and `startInterviewFromResume()` in `frontend/src/api/interview.js` send role/resume payloads to backend start endpoints that require `application_id`. | Manual/resume interview flows broken. |
| High | Candidate interview page auto-starts when `appId` is in URL. | `frontend/src/pages/interview/InterviewPage.jsx:51-55`. | Refresh triggers resume/start API call; can show error for completed/cancelled sessions. |
| High | Proctoring is entirely browser event driven. | `InterviewWorkspaceShell` posts violations from client effects. | A malicious client can skip or spoof violations. |
| High | JSON parsing in render can crash UI. | `InterviewWorkspaceShell` parses `session.personalization_context` inline. | Invalid JSON can blank interview workspace. |
| High | Frontend GET cache ignores params in key. | Cache key is `baseURL + config.url` only in `frontend/src/api/axios.js`. | Distinct GETs with different params can collide. |
| Medium | 30s GET cache can stale dashboards and report polling. | `CACHE_TTL_MS = 30_000`. | HR may not see just-generated reports/actions immediately. |
| Medium | Many setState-in-effect lint errors. | Lint output. | Render cascades and hard-to-debug component behavior. |
| Medium | Large HR report component combines fetching, charts, tabs, actions, and detail panels. | `frontend/src/pages/hr/InterviewReports.jsx`. | Difficult to maintain and optimize. |
| Medium | Unused imports and variables throughout app. | Lint output: 226 total problems. | Build passes but quality gates fail. |

## UX/State Issues

- Interview cancellation from setup simply calls `onEnd`; it does not necessarily abandon server session.
- If completion API fails, UI calls `onEnd()` and can hide progress despite failure.
- Voice recording plus transcription adds a second network call per answer and fallback to text is not always clearly tied to preserved state.
- HR actions reload leaderboard but do not refresh the selected candidate report.

## Recommended Fixes

1. Fix lint gate blockers first, especially `MessageSquare`.
2. Remove or repair stale `startInterview`/`startInterviewFromResume` clients.
3. Make cache key include params and add mutation-driven invalidation.
4. Wrap JSON parsing in safe helpers.
5. Split `InterviewReports.jsx` into data hooks, tables, charts, and detail panels.
