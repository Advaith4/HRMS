# TalentForge Interview Design Review

## Current Phases

`INTERVIEW_PHASES` and `PHASE_SEQUENCE` are defined in `src/services/interview_core.py` and include:

- Introduction
- Resume Deep Dive
- Core Technical Round
- Problem Solving
- Behavioral Round
- Pressure / Cross-questioning
- Candidate Questions
- Final Evaluation

## Current Strategy

- First question is generated from resume analysis, weak areas, role, difficulty, training mode, persona, coach memory, domain focus, and phase metadata.
- Each answer is evaluated and used to generate a next question.
- Duplicate detection can force phase advancement.
- Claim verification can override focus and keep the candidate in verification mode for multiple turns.
- Final evaluation is phase-driven rather than strictly question-budget-driven.

## Value Assessment

| Phase | Value | Risk |
|---|---|---|
| Introduction | Medium | Can be too generic if AI output is weak. |
| Resume Deep Dive | High | Good for claim verification. |
| Core Technical Round | High | Core signal. |
| Problem Solving | High | Strong predictor if role aligned. |
| Behavioral Round | Medium | Useful but should be short. |
| Pressure / Cross-questioning | Medium | Useful for senior roles; can fatigue candidates. |
| Candidate Questions | Low for AI screening | Adds time without much scoring value. |
| Final Evaluation | High as report step | Should not be presented as another candidate question. |

## Redundant/Costly Pieces

- Candidate Questions phase is not necessary for mandatory screening.
- Pressure phase should be conditional, not always part of the sequence.
- Claim verification can add hidden extra turns and inflate cost.
- Re-sending large context every answer increases token usage.

## Recommended Interview Structure

Target: 8-10 total questions.

1. Intro and role-fit: 1 question.
2. Resume claim deep dive: 2 questions.
3. Technical fundamentals: 2 questions.
4. Applied problem solving: 2 questions.
5. Behavioral/situational: 1 question.
6. Adaptive follow-up or pressure question: 1 optional question.
7. Final evaluation: backend-only report generation.

## Scoring Strategy

- Score each answer on a fixed rubric: relevance, specificity, technical depth, communication, evidence.
- Keep separate normalized dimensions and compute final weights once.
- Avoid changing candidate-facing phase labels too often.
- Cap follow-ups per claim to one unless a high-value contradiction is detected.

## Optimal API Usage

- One LLM call at start.
- One LLM call per answer returning both evaluation and next question.
- One final synthesis call.
- Credibility analysis can be folded into final synthesis if claim evidence was tracked per turn.
