# TalentForge API/LLM Usage Audit

## LLM Interaction Table

| Location | Purpose | Calls Made | Necessary? | Optimization Potential |
|---|---|---:|---|---|
| `src/api/routes/interview.py:146` | Resume analysis at interview start if missing. | 0-1/start | Sometimes | Cache per application/role. |
| `crew.py:642` | First interview question. | 1/start | Yes | Precompute or deterministic first question. |
| `crew.py:688` | Answer evaluation and next question. | 1-2/answer depending internal CrewAI tasks | Yes | Force single JSON call. |
| `src/api/routes/interview.py:1270` | Audio transcription. | 0-1/answer | Optional | Client-side opt-in; typed mode no call. |
| `src/services/interview_consistency.py:30` | Credibility/claim verification report. | 1/session | Useful | Merge with final synthesis using tracked evidence. |
| `src/services/hiring_intelligence.py:58` | Final hiring intelligence synthesis. | 1/session | Yes | Use smaller normalized transcript. |
| `src/services/mock_interview_summary.py` | Mock summary. | 1/mock completion | Useful | Only for practice sessions. |
| `src/services/recruitment_ai.py` | Application AI analysis. | 1/application | Yes | Cache and avoid forced reruns. |

## Duplicate Work

- Resume analysis can happen during application analysis, resume upload, mock interview start, and official interview start.
- Credibility analysis can be requested manually and also forced by hiring intelligence compilation.
- Interview answer flow sends recent history and context every turn.
- HR candidate report recomputes derived aggregates on every request.

## Estimated Calls During One Official Voice Interview

For 8 answers:

- Resume analysis: 0-1
- Start question: 1
- Transcription: 8
- Answer evaluation/follow-up: 8-16
- Credibility: 1
- Hiring intelligence: 1

Total: 19-28 external AI/API calls.

## Eliminable Calls

- Eliminate repeated resume analysis by persisting application-level analysis/context.
- Eliminate separate credibility LLM call by tracking claim evidence during turns and synthesizing once.
- Eliminate any separate answer-evaluation and follow-up calls by requiring one combined output.
- Eliminate voice transcription when candidate types or browser speech recognition is acceptable.

## Potential Reduction

- Conservative: 25-35% fewer LLM calls.
- Aggressive: 45-60% fewer LLM calls for voice-heavy interviews.
- Token reduction: 30-50% if prompts use compact context snapshots and normalized turn evidence.

## Governance Recommendations

1. Log model, input/output token estimates, latency, fallback flag, and request purpose for every LLM call.
2. Add per-user/session rate limits.
3. Add max prompt size guards.
4. Store AI source and confidence in HR-facing payloads.
