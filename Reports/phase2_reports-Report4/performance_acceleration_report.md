# HRMS Phase 2 Performance Acceleration Report

## Dependency Map

Interview answer submission -> `src/api/routes/interview.py`
Question/evaluation engine -> `crew.py`
Credibility analysis -> `src/services/interview_consistency.py`
Hiring intelligence synthesis -> `src/services/hiring_intelligence.py`
Report polling -> `frontend/src/components/interview/InterviewSummary.jsx`

## Remaining Bottlenecks Found

| Function | Estimated Tokens | Purpose | Optimization Needed |
| --- | ---: | --- | --- |
| `crew.run_interview_answer` evaluator task | 1,000-2,500 | Score every interview answer | Removed by default fast deterministic path; LLM can be re-enabled with `INTERVIEW_USE_LLM_ANSWER_EVAL=1`. |
| `crew.run_interview_answer` follow-up task | 1,200-3,000 | Generate every next question | Removed by default fast deterministic follow-up path. |
| `interview_consistency._run_ai_credibility` | 800-2,500 | Compare resume claims to interview answers | Background report uses cached/deterministic credibility; manual forced endpoint can still run AI. |
| `hiring_intelligence.compile_hiring_intelligence` synthesis | 1,800-3,500 | Assemble final report | Kept as the single optional synthesis call, timeout reduced to 8s with deterministic fallback. |

## Instrumentation Added

Structured `perf_metric` logs now emit `start_time`, `end_time`, and `elapsed_ms` for:

- `interview_answer_generation`
- `interview_completion_turn`
- `interview_manual_completion`
- `credibility_analysis`
- `hiring_intelligence_synthesis_llm`
- `hiring_intelligence_total`

Existing Phase 1 transcription timing logs are preserved.

## Optimizations Implemented

- Default answer evaluation and next-question generation no longer use CrewAI LLM calls.
- Background hiring intelligence uses cached/deterministic credibility via `allow_ai=False`.
- Final synthesis is limited to one optional LLM call with `INTERVIEW_SYNTHESIS_TIMEOUT=8.0`.
- `INTERVIEW_ENABLE_LLM_SYNTHESIS=0` enables fully deterministic report assembly for strict sub-10s environments.
- Added composite indexes for common interview/report lookup patterns:
  - `interview_sessions(user_id, status, created_at)`
  - `candidate_credibility_reports(candidate_id, created_at)`
  - `interview_intelligence_reports(candidate_id, status, overall_score)`

## Before vs After

| Metric | Before | After |
| --- | ---: | ---: |
| Per-answer transition | 2 sequential CrewAI calls | 0 default CrewAI calls |
| Background credibility | Up to 1 CrewAI call | Cached/deterministic |
| Final synthesis | 20s timeout | 8s timeout with fallback |
| Expected report path | Credibility AI + synthesis AI | Fast credibility + one synthesis or deterministic fallback |

Expected improvement: removing the two per-answer LLM calls cuts routine question latency by roughly 70-95%. Final report readiness is now bounded by the single synthesis timeout, and can be made fully deterministic under 10 seconds by setting `INTERVIEW_ENABLE_LLM_SYNTHESIS=0`.

## Validation

- Python compile checks passed for modified backend files.
- `npm run build` passed in `frontend/`.
- Full pytest remains blocked locally because PostgreSQL database `talentforge_test` is missing.
- `npm run lint` remains blocked by pre-existing repo-wide lint errors unrelated to these changed files.
