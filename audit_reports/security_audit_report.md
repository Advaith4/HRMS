# TalentForge Security Audit Report

## Authentication/RBAC

- JWT uses HS256 and validates DB role matches token role.
- `require_roles()` supports admin bypass.
- Public registration creates candidates only.

## Findings

| Severity | Finding | Evidence | Impact |
|---|---|---|---|
| Critical | `POST /api/interview/{session_id}/credibility` does not verify requester owns the session or has HR role before analysis. | Route calls `analyze_credibility(db, session_id, force=force)` at `src/api/routes/interview.py:821-824`. | Any authenticated user may trigger/report credibility for another session if they know numeric ID. |
| Critical | HR intelligence report is candidate-id scoped and exposes resume excerpt and all sessions to HR/manager. | `GET /api/interview/intelligence/report/{candidate_id}`. | Overexposure across jobs/applications; manager may see more candidate data than intended. |
| High | Advance/reject actions operate on latest application by candidate, not a specific application. | `intelligence_advance_candidate` and reject find latest application by `session.user_id`. | Wrong job application can be advanced/rejected. |
| High | Proctoring is client-enforced. | Browser detects fullscreen/tab/camera/screen-share and posts violations. | Bypassable by modified client or direct API calls. |
| High | No rate limiting on login, register, transcribe, interview answer, or credibility endpoints. | No rate-limit middleware observed. | Brute-force and LLM-cost abuse risk. |
| High | Uploaded document paths are stored and reviewed by APIs; file access controls require careful verification. | Document models store `stored_path`. | Risk of path disclosure/IDOR if route checks are incomplete. |
| Medium | CORS allows configured origins with credentials and all methods/headers. | `src/main.py` CORS middleware. | Misconfigured prod origins can broaden attack surface. |
| Medium | GET response cache is in frontend memory and role-independent within same JS runtime. | `frontend/src/api/axios.js`. | After logout/login, stale cached data risk unless page reload clears memory. |
| Medium | JWT revocation is not supported. | Stateless JWT only. | Compromised token valid until expiry. |

## IDOR Hotspots

- Interview credibility by numeric session id.
- HR intelligence candidate report by candidate id.
- Application hire/analyze/credibility by application id.
- Document decision routes by document id.
- Employee and lifecycle routes by employee id.

## Sensitive Data Exposure

- Candidate report returns resume text excerpt.
- Interview messages may include personal information and are returned in full session history to owners.
- HR dashboards expose candidate usernames, target roles, application states, and AI analysis.

## Recommendations

1. Add ownership/role checks inside credibility analysis route.
2. Make HR actions application-scoped and job-scoped.
3. Add rate limiting and request size limits.
4. Add audit logging for HR reads/actions.
5. Use server-side proctoring attestation or treat proctoring as advisory only.
