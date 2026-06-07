# RAG Sync Report

Generated: 2026-06-07

Phase 2 adds `src/services/rag/sync_service.py`, which synchronizes HRMS database entities into ChromaDB with deterministic document IDs.

## Synced Collections

- `job_descriptions`: `JobPosting` records.
- `candidate_profiles`: `CandidateApplication` plus completed `ApplicationAIAnalysis`.
- `interview_reports`: `InterviewIntelligenceReport` summaries keyed by interview session.

## Metadata Model

Every synced document includes:

- `entity_id`
- `entity_type`
- `user_id` when available
- `created_at`
- `updated_at`
- `source_collection`

Additional future-access metadata is included where available, such as `job_id`, `application_id`, `session_id`, `candidate_id`, and `report_id`.

## Idempotency

Each entity is stored with a deterministic Chroma ID:

```text
{source_collection}:{entity_type}:{entity_id}
```

Repeated sync calls upsert the same Chroma document instead of creating duplicates. Delete sync removes the same deterministic document ID.

## Workflow Hooks

Sync calls are invoked after successful HRMS commits in these narrow points:

- Job create/update/delete in `src/api/routes/jobs.py`.
- Application AI analysis persistence in `src/services/recruitment_ai.py`.
- Interview intelligence report persistence in `src/services/hiring_intelligence.py`.

Sync failures are logged and swallowed so Chroma availability never blocks primary HRMS workflows.
