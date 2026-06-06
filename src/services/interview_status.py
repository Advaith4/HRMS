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
        "min_turns": 3,
        "max_turns": 3,
    },
    {
        "name": "Technical Assessment",
        "goal": "Measure real implementation skill against the job requirements.",
        "focus": "Architecture, APIs, databases, debugging, and production tradeoffs.",
        "min_turns": 5,
        "max_turns": 5,
    },
    {
        "name": "Behavioral Assessment",
        "goal": "Evaluate communication, ownership, collaboration, and judgment using STAR answers.",
        "focus": "Situation, task, action, result, reflection, and accountability.",
        "min_turns": 3,
        "max_turns": 3,
    },
    {
        "name": "Final Evaluation",
        "goal": "Ask one closing question before generating the final report.",
        "focus": "Closing motivation, role alignment, and final candidate signal.",
        "min_turns": 1,
        "max_turns": 1,
    },
]

PHASE_SEQUENCE_V2 = [str(phase["name"]) for phase in INTERVIEW_PHASES_V2]
PHASE_TURN_TARGETS_V2 = {str(phase["name"]): int(phase["max_turns"]) for phase in INTERVIEW_PHASES_V2}
TOTAL_INTERVIEW_TURNS_V2 = sum(PHASE_TURN_TARGETS_V2.values())

INTERVIEW_STATE_MACHINE_V2: dict[str, dict[str, object]] = {
    "CREATED": {
        "allowed_transitions": ["SETUP"],
        "required_data": ["user_id", "role", "resume_text"],
    },
    "SETUP": {
        "allowed_transitions": ["RESUME_VALIDATION"],
        "required_data": ["session_token", "first_question", "personalization_context"],
    },
    "RESUME_VALIDATION": {
        "allowed_transitions": ["TECHNICAL_ASSESSMENT"],
        "required_data": ["current_question", "answer", "evaluation"],
    },
    "TECHNICAL_ASSESSMENT": {
        "allowed_transitions": ["BEHAVIORAL_ASSESSMENT"],
        "required_data": ["current_question", "answer", "evaluation"],
    },
    "BEHAVIORAL_ASSESSMENT": {
        "allowed_transitions": ["FINAL_EVALUATION"],
        "required_data": ["current_question", "answer", "evaluation"],
    },
    "FINAL_EVALUATION": {
        "allowed_transitions": ["COMPLETED"],
        "required_data": ["current_question", "answer", "evaluation"],
    },
    "COMPLETED": {
        "allowed_transitions": ["REPORT_GENERATION"],
        "required_data": ["messages", "avg_score"],
    },
    "REPORT_GENERATION": {
        "allowed_transitions": ["REPORT_READY"],
        "required_data": ["session_id"],
    },
    "REPORT_READY": {
        "allowed_transitions": [],
        "required_data": ["hiring_intelligence_report"],
    },
}

PHASE_TO_STATE_V2 = {
    "Resume Validation": "RESUME_VALIDATION",
    "Technical Assessment": "TECHNICAL_ASSESSMENT",
    "Behavioral Assessment": "BEHAVIORAL_ASSESSMENT",
    "Final Evaluation": "FINAL_EVALUATION",
}


def normalize_interview_status(status: str | None) -> str:
    normalized = str(status or INTERVIEW_STATUS_PENDING).strip().lower()
    return normalized if normalized in INTERVIEW_STATUSES else INTERVIEW_STATUS_PENDING


def is_successful_interview_status(status: str | None) -> bool:
    return normalize_interview_status(status) in SUCCESSFUL_INTERVIEW_STATUSES


def is_visible_interview_status(status: str | None) -> bool:
    return normalize_interview_status(status) in VISIBLE_INTERVIEW_STATUSES


def phase_turn_requirements() -> dict[str, int]:
    return dict(PHASE_TURN_TARGETS_V2)


def completed_turns_by_phase(messages: list[dict]) -> dict[str, int]:
    counts = {phase: 0 for phase in PHASE_SEQUENCE_V2}
    for index, message in enumerate(messages):
        if message.get("role") != "user":
            continue
        phase = None
        for prev in reversed(messages[:index]):
            if prev.get("role") == "ai":
                phase = prev.get("phase") or PHASE_SEQUENCE_V2[0]
                break
        if phase in counts:
            counts[phase] += 1
    return counts


def has_completed_required_turns(messages: list[dict]) -> bool:
    counts = completed_turns_by_phase(messages)
    return all(counts.get(phase, 0) >= PHASE_TURN_TARGETS_V2[phase] for phase in PHASE_SEQUENCE_V2)


def next_phase_for_completed_turn(current_phase: str, phase_turn_count: int) -> tuple[str, bool]:
    target = PHASE_TURN_TARGETS_V2.get(current_phase, 1)
    if current_phase == PHASE_SEQUENCE_V2[-1] and phase_turn_count >= target:
        return current_phase, True
    if phase_turn_count < target:
        return current_phase, False
    try:
        index = PHASE_SEQUENCE_V2.index(current_phase)
    except ValueError:
        return PHASE_SEQUENCE_V2[0], False
    return PHASE_SEQUENCE_V2[min(index + 1, len(PHASE_SEQUENCE_V2) - 1)], False
