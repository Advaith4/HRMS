# TalentForge Backend Audit Report

## Verification

- `pytest tests -q` failed during collection because `SECRET_KEY` was not accepted by current settings validation.
- The failure appears environment/config related: tests set a test key, but current config treated it as non-test deployment.

## Findings

| Severity | Finding | Evidence | Impact |
|---|---|---|---|
| Critical | Interview router has too many responsibilities. | `src/api/routes/interview.py` contains candidate, HR, proctoring, intelligence, and transcription endpoints. | Security and regression risk. |
| Critical | Endpoint aliases share incompatible semantics. | `/start`, `/start-for-application`, and `/start-from-resume` all use `StartForApplicationReq`. | Contract drift and client breakage. |
| High | Session status state machine is inconsistent. | `completed`, `cancelled`, `active`, `analyzed` used across code without central enum. | Reports and dashboards disagree. |
| High | Many service helpers are private but imported across modules. | `interview.py` imports many underscore-prefixed helpers from `interview_core.py`. | No stable service API. |
| High | Background tasks lack durable queue/retry. | FastAPI `BackgroundTasks` calls analysis/intelligence. | Lost work on process crash; no observability. |
| High | HR intelligence endpoints manually check roles instead of using dependencies. | `current_user.role not in (...)` repeated. | Inconsistent admin bypass semantics and harder testing. |
| Medium | Route handlers perform business transactions directly. | Applications hire flow creates employees, profiles, docs, onboarding, notifications inline. | Large transaction blast radius and weak rollback design. |
| Medium | Exception handling often falls back silently for AI. | Hiring intelligence catches broad exceptions and emits fallback. | HR may trust low-confidence synthetic report. |
| Medium | No rate limiting on LLM-heavy endpoints. | Interview answer, transcribe, credibility, report generation. | Abuse/cost exposure. |
| Medium | Tests do not currently run in this environment. | Pytest collection error from `SECRET_KEY`. | CI confidence is low. |

## Transaction Issues

- Hiring a candidate mutates `User`, `Employee`, documents, onboarding, notifications, and application status in one route.
- Interview completion commits status before background intelligence is guaranteed.
- Duplicate start/apply/hire operations are guarded mostly by application logic rather than DB uniqueness.

## Logging/Observability Gaps

- LLM latency, token usage, fallback source, and background task state are not consistently stored.
- HR reports do not expose whether data is AI-generated, fallback-generated, pending, or failed in a durable way.

## Recommended Backend Refactor

1. Create services: `InterviewLifecycleService`, `InterviewEvaluationService`, `HiringIntelligenceService`, `ApplicationHiringService`.
2. Introduce explicit enums/constants for statuses.
3. Replace background tasks with a durable job table or queue.
4. Add DB uniqueness for application/session invariants.
5. Add route-level tests for every role and ownership boundary.
