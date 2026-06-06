# Interview Refactor Report

## What Changed
- Replaced the old eight-phase interview progression with four production phases:
  - Resume Validation
  - Technical Assessment
  - Behavioral Assessment
  - Final Evaluation
- Reduced target interview length by ending at 10 answered turns, with stable-score early completion after enough signal is collected.
- Startup no longer calls CrewAI just to create the first question. The first question is deterministic and resume-validation oriented.
- `Final Evaluation` no longer asks another candidate question; it switches the session to `analyzing` and queues the HR intelligence compiler.
- Claim verification now freezes phase advancement until the active claim is verified, including duplicate-question safeguards.

## Compatibility
- `/api/interview/start-for-application` remains the production path.
- `/api/interview/start` and `/api/interview/start-from-resume` still work when clients send a resume-only payload.
- Existing active sessions resume instead of creating duplicate sessions.

## Frontend
- Interview progress stepper now renders the four-phase model.
- Summary screen polls while status is `active`, `completed`, or `analyzing`, and stops on `analyzed`, `cancelled`, or `failed`.
- Candidate exit flow calls the backend abandon endpoint before redirecting.
