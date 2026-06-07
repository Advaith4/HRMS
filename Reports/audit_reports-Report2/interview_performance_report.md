# TalentForge Interview Performance Report

## Startup Latency Sources

1. Dashboard application load before start.
2. Application/job/resume DB reads.
3. Resume analysis if `Resume.last_analysis` is missing.
4. Personalization context construction.
5. CrewAI first question generation.
6. DB insert/commit and coach memory update.

## Per-Answer Latency Sources

1. Optional audio transcription call.
2. `run_interview_answer()` LLM call.
3. Duplicate question similarity scan.
4. Memory update.
5. DB serialization of full message array.
6. Optional background intelligence trigger on final phase.

## Estimated API Calls Per Interview

Assuming 8 answered questions and voice mode:

- 1 candidate dashboard call.
- 1 interview start LLM call.
- 8 transcription calls.
- 8 answer/evaluation/follow-up LLM workflows.
- 1 credibility analysis call.
- 1 hiring intelligence synthesis call.
- Multiple HR dashboard/report reads.

Estimated LLM/API calls: 11 without voice, 19 with voice. If `run_interview_answer()` internally splits evaluation and follow-up, answer-related LLM calls may double.

## Estimated Token Usage

Approximate per 8-question application interview:

- Start prompt: 1.5k-3k input, 200-500 output.
- Each answer prompt: 1.5k-3.5k input, 400-900 output because it includes resume context, section scores, coach memory, and recent messages.
- Credibility prompt: 2k-5k input, 500-1k output.
- Hiring intelligence prompt: up to 2k resume plus full transcript, commonly 4k-8k input and 1k-2k output.

Estimated total: 20k-45k input tokens and 5k-11k output tokens per completed interview, excluding Whisper.

## Cost Reduction Opportunities

| Opportunity | Estimated Reduction |
|---|---:|
| Combine answer evaluation and next-question generation into one strict JSON call if currently split in CrewAI. | 25-40% |
| Cache resume analysis per application and role, not only latest user resume. | 5-15% |
| Use compressed context snapshots instead of sending rich resume context every turn. | 15-30% |
| Limit interview to 8-10 total questions. | 20-50% depending current turns |
| Run hiring intelligence from already-normalized turn records, not full raw prompt every time. | 10-20% |
| Skip transcription for typed answers and avoid automatic re-transcription on retry. | Variable |

## Bottlenecks

- `run_interview_start()` during startup is the main perceived delay.
- `run_interview_answer()` blocks the response and has a 60s frontend timeout.
- Full `messages` JSON is rewritten on every answer.
- Hiring intelligence uses background tasks but still competes for DB/LLM resources.
- HR intelligence leaderboard has looped DB queries.

## Recommendations

1. Make interview startup return immediately with deterministic first question or queued AI preparation.
2. Precompute resume context during application analysis.
3. Store turns as rows or JSONB patches rather than rewriting full message logs.
4. Add timing logs around resume analysis, start question, answer evaluation, transcription, credibility, and intelligence compilation.
5. Add a hard question budget of 8-10.
