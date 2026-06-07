# Performance Improvement Report

## Startup Improvements
- Removed the CrewAI startup call for the first production interview question.
- First question generation is now deterministic and immediate.
- Resume-only compatibility still analyzes resume content when needed, but application interview startup avoids unnecessary LLM dependency.

## AI Call Reduction
- Hiring intelligence now reuses credibility analysis with `force=False` instead of forcing duplicate credibility work.
- Final analysis runs in background after status changes to `analyzing`.
- Resume validation and phase metadata are now local constants instead of generated per startup.

## Frontend
- Axios GET cache keys now include request params, preventing stale cached responses across different queries.
- Summary polling stops when the session reaches any terminal non-pending state.
