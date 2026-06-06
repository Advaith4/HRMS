from __future__ import annotations

INTERVIEW_STATUS_PENDING = "pending"
INTERVIEW_STATUS_ACTIVE = "active"
INTERVIEW_STATUS_COMPLETED = "completed"
INTERVIEW_STATUS_ANALYZING = "analyzing"
INTERVIEW_STATUS_ANALYZED = "analyzed"
INTERVIEW_STATUS_CANCELLED = "cancelled"
INTERVIEW_STATUS_FAILED = "failed"

INTERVIEW_STATUSES = {
    INTERVIEW_STATUS_PENDING,
    INTERVIEW_STATUS_ACTIVE,
    INTERVIEW_STATUS_COMPLETED,
    INTERVIEW_STATUS_ANALYZING,
    INTERVIEW_STATUS_ANALYZED,
    INTERVIEW_STATUS_CANCELLED,
    INTERVIEW_STATUS_FAILED,
}

TERMINAL_INTERVIEW_STATUSES = {
    INTERVIEW_STATUS_COMPLETED,
    INTERVIEW_STATUS_ANALYZING,
    INTERVIEW_STATUS_ANALYZED,
    INTERVIEW_STATUS_CANCELLED,
    INTERVIEW_STATUS_FAILED,
}

SUCCESSFUL_INTERVIEW_STATUSES = {
    INTERVIEW_STATUS_COMPLETED,
    INTERVIEW_STATUS_ANALYZING,
    INTERVIEW_STATUS_ANALYZED,
}

VISIBLE_INTERVIEW_STATUSES = {
    INTERVIEW_STATUS_COMPLETED,
    INTERVIEW_STATUS_ANALYZING,
    INTERVIEW_STATUS_ANALYZED,
    INTERVIEW_STATUS_CANCELLED,
}

INTERVIEW_PHASES_V2: list[dict[str, object]] = [
    {
        "name": "Resume Validation",
        "goal": "Validate resume claims with concrete ownership, technical decisions, and outcomes.",
        "focus": "Recent projects, personal contribution, credibility, and evidence.",
        "min_turns": 2,
        "max_turns": 3,
    },
    {
        "name": "Technical Assessment",
        "goal": "Measure real implementation skill against the job requirements.",
        "focus": "Architecture, APIs, databases, debugging, and production tradeoffs.",
        "min_turns": 3,
        "max_turns": 5,
    },
    {
        "name": "Behavioral Assessment",
        "goal": "Evaluate communication, ownership, collaboration, and judgment using STAR answers.",
        "focus": "Situation, task, action, result, reflection, and accountability.",
        "min_turns": 2,
        "max_turns": 3,
    },
    {
        "name": "Final Evaluation",
        "goal": "Generate the final report without asking another candidate question.",
        "focus": "Strengths, weaknesses, technical signal, behavior signal, credibility, and recommendation.",
        "min_turns": 0,
        "max_turns": 0,
    },
]

PHASE_SEQUENCE_V2 = [str(phase["name"]) for phase in INTERVIEW_PHASES_V2]


def normalize_interview_status(status: str | None) -> str:
    normalized = str(status or INTERVIEW_STATUS_PENDING).strip().lower()
    return normalized if normalized in INTERVIEW_STATUSES else INTERVIEW_STATUS_PENDING


def is_successful_interview_status(status: str | None) -> bool:
    return normalize_interview_status(status) in SUCCESSFUL_INTERVIEW_STATUSES


def is_visible_interview_status(status: str | None) -> bool:
    return normalize_interview_status(status) in VISIBLE_INTERVIEW_STATUSES
