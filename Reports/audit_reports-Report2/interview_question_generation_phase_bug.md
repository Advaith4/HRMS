# Interview Question Generation Phase Bug

## Root Cause

The `/api/interview/answer` flow evaluated the submitted answer and called `run_interview_answer` before calculating the deterministic phase transition. That meant the combined evaluator/question generator received `phase_name=current_phase`.

When the last Resume Validation answer was submitted, the UI correctly moved to `Technical Assessment` after the answer, but the generator had already produced a Resume Validation follow-up. In the observed case, that follow-up was an introduction clarification:

`Let me rephrase that. Could you provide a different example regarding general introduction?`

The phase-aware guard existed, but duplicate handling could still emit clarification wording instead of forcing the next technical topic.

## Trace

1. Candidate submits answer to `/api/interview/answer`.
2. Backend loads live state and determines `current_phase`.
3. Backend now predicts the post-answer phase using `next_phase_for_completed_turn(current_phase, phase_turn_count + 1)`.
4. `run_interview_answer` receives that post-answer `phase_name`, `phase_goal`, and `phase_focus`.
5. Evaluation is stored for the answered question.
6. Phase state is updated.
7. Next question is validated against the post-answer phase.
8. Invalid or duplicate questions are replaced with deterministic topic progression.

## Fix Summary

- Question generation now receives the actual next phase, not the answered phase.
- Technical Assessment rejects introduction, background, resume-validation, and clarification-loop wording.
- Technical Assessment fallback only progresses through technical topics:
  - Project Architecture
  - Technical Challenge
  - System Design
  - APIs
  - Debugging
- Duplicate detection checks the previous 3 questions and advances to the next non-duplicate topic.
- Technical Assessment no longer creates clarification fallback questions.
- Clarification attempts remain capped and reset when progression moves forward.

## Verification

Added tests for:

- Rejecting the exact bad introduction clarification in Technical Assessment.
- Replacing it with a technical architecture question.
- Progressing duplicate technical questions to the next technical topic without clarification loops.
- Verifying the generator receives `Technical Assessment` immediately after Resume Validation completes.
