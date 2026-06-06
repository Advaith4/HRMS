"""
src/api/routes/interview.py
POST /api/interview/start         – start new session (persisted to DB)
POST /api/interview/answer        – submit answer, get eval + next question (persisted)
GET  /api/interview/sessions      – list all past sessions for current user
GET  /api/interview/sessions/{id} – get full message history of a session
"""
import uuid
import json
import logging
import os
import time
import hashlib
from difflib import SequenceMatcher
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Form
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from src.database.connection import get_session
from src.models import CareerCoachMemory, CandidateApplication, InterviewSession, Resume, User, CandidateCredibilityReport, HRNotification, JobPosting, InterviewIntelligenceReport
from src.api.dependencies import get_current_user
from src.resume_lab import analyze_resume, dumps_json, load_json_field, parse_resume
from src.services.interview_status import (
    INTERVIEW_STATUS_ACTIVE,
    INTERVIEW_STATUS_ANALYZING,
    INTERVIEW_STATUS_CANCELLED,
    SUCCESSFUL_INTERVIEW_STATUSES,
    TERMINAL_INTERVIEW_STATUSES,
    VISIBLE_INTERVIEW_STATUSES,
    completed_turns_by_phase,
    has_completed_required_turns,
    is_successful_interview_status,
    next_phase_for_completed_turn,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/interview", tags=["interview"])

from src.services.interview_core import (
    _sessions,
    _normalize_training_mode,
    _normalize_persona,
    _get_or_create_memory,
    _latest_candidate_resume_text,
    _build_personalization_context,
    _memory_snapshot,
    _phase_meta,
    _normalize_focus_type,
    _update_coach_memory,
    INTERVIEWER_PERSONAS,
    TRAINING_MODES,
    _save_session_state,
    _state_from_record,
    _ensure_live_state,
    _is_interview_complete_after_answer,
    _phase_entry_question,
    _format_feedback_message,
    _generate_daily_plan,
    _unique_strings,
    _recurring_area_label,
    _upsert_weak_area_counts,
    _derive_section_scores,
    _derive_weak_areas,
    _build_resume_context,
    _choose_focus_mode,
    _normalize_and_repair_evaluation,
    _question_mix_for_mode,
    _safe_json_load,
    INTERVIEW_PHASES,
    PHASE_SEQUENCE,
    PHASE_TURN_TARGETS,
    _notify_hr
)

class StartForApplicationReq(BaseModel):
    application_id: Optional[int] = None
    role: str = Field(default="", max_length=120)
    force_reanalyze: bool = False
    domain_focus: str = Field(default="", max_length=120)
    difficulty: int = Field(default=5, ge=1, le=10)
    training_mode: str = Field(default="adaptive", max_length=40)
    interviewer_persona: str = Field(default="balanced", max_length=40)

class AnswerReq(BaseModel):
    session_id: str
    answer: str = Field(min_length=1, max_length=5000)

class ViolationReq(BaseModel):
    violation_type: str
    detail: str
    duration_ms: Optional[int] = None
    severity: str = Field(default="medium", max_length=20)

class CompareReq(BaseModel):
    candidate_ids: list[int]


def _safe_load_list(value: str | None) -> list[Any]:
    loaded = _safe_json_load(value, [])
    return loaded if isinstance(loaded, list) else []


def _utc_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _log_perf(metric: str, started: float, **fields: Any) -> None:
    ended = time.perf_counter()
    logger.info(
        "perf_metric metric=%s start_time=%s end_time=%s elapsed_ms=%s %s",
        metric,
        fields.pop("start_time", ""),
        _utc_iso(),
        int((ended - started) * 1000),
        " ".join(f"{key}={value}" for key, value in fields.items()),
    )


def _log_interview_event(event: str, session_id: str | int | None = None, phase: str | None = None, question_number: int | None = None, **fields: Any) -> None:
    logger.info(
        "interview_event event=%s session_id=%s phase=%s question_number=%s timestamp=%s %s",
        event,
        session_id or "",
        phase or "",
        question_number if question_number is not None else "",
        _utc_iso(),
        " ".join(f"{key}={value}" for key, value in fields.items()),
    )


PHASE_TOPIC_PROGRESSIONS = {
    "Resume Validation": [
        ("introduction", "Give me a concise introduction for this role, focusing on your background and strongest fit."),
        ("background", "Walk me through the background, education, or experience that prepared you for this role."),
        ("resume_project", "Choose one resume project or claim and explain your ownership, evidence, and outcome."),
    ],
    "Technical Assessment": [
        ("project_architecture", "Walk me through the architecture of a project you built, including the major components and why you designed it that way."),
        ("technical_challenge", "Describe a difficult technical challenge you faced in that project and the engineering decision that resolved it."),
        ("system_design", "Design a production-ready system for a core feature in this role. Cover data flow, scale, reliability, and tradeoffs."),
        ("apis", "Explain an API or integration you built or would design here, including endpoints, data contracts, validation, and failure handling."),
        ("debugging", "Tell me about a production bug or complex debugging scenario. How did you isolate the cause and prevent recurrence?"),
    ],
    "Behavioral Assessment": [
        ("teamwork", "Tell me about a time you worked with a team to deliver something difficult. What was your role and impact?"),
        ("conflict", "Describe a conflict or disagreement on a project. How did you handle it and what changed afterward?"),
        ("leadership", "Give me an example of leadership, ownership, or initiative when the path forward was unclear."),
    ],
    "Final Evaluation": [
        ("closing_signal", "Before we wrap up, what is the strongest technical and role-fit evidence you want the hiring team to remember?"),
    ],
}

PHASE_ALLOWED_KEYWORDS = {
    "Resume Validation": (
        "introduction", "background", "education", "resume", "claim", "experience", "project", "ownership", "outcome",
    ),
    "Technical Assessment": (
        "project", "architecture", "coding", "api", "apis", "database", "databases", "system", "design", "debug", "debugging",
        "engineering", "technical", "components", "data", "scale", "reliability", "tradeoff", "production", "integration",
        "failure", "endpoint", "decision", "decisions",
    ),
    "Behavioral Assessment": (
        "team", "teamwork", "conflict", "leadership", "ownership", "collaboration", "stakeholder", "communication", "ambiguity",
    ),
    "Final Evaluation": (
        "wrap", "closing", "strongest", "evidence", "remember", "fit", "role",
    ),
}

CLARIFICATION_MARKERS = (
    "clarification",
    "clarify",
    "let me rephrase",
    "could you provide a different example",
    "different example regarding",
    "try again with",
)

TECHNICAL_FORBIDDEN_MARKERS = (
    "tell me about yourself",
    "general introduction",
    "background and strongest fit",
    "your background fits",
    "why you're a good fit",
    "resume validation",
)


def _question_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, str(a or "").lower(), str(b or "").lower()).ratio()


def _recent_question_similarity(question: str, previous_questions: list[str], window: int = 3) -> tuple[bool, float]:
    max_similarity = 0.0
    for old_q in previous_questions[-window:]:
        similarity = _question_similarity(question, old_q)
        max_similarity = max(max_similarity, similarity)
        if similarity >= 0.82:
            return True, max_similarity
    return False, max_similarity


def _is_clarification_question(question: str) -> bool:
    text = str(question or "").lower()
    return any(marker in text for marker in CLARIFICATION_MARKERS)


def _question_matches_phase(question: str, phase: str) -> bool:
    text = str(question or "").lower()
    if not text.strip():
        return False
    allowed = PHASE_ALLOWED_KEYWORDS.get(phase, ())
    if phase == "Technical Assessment":
        if any(marker in text for marker in TECHNICAL_FORBIDDEN_MARKERS):
            return False
        if _is_clarification_question(text):
            return False
    return any(keyword in text for keyword in allowed)


def _topic_for_phase_turn(phase: str, phase_question_count: int) -> tuple[str, str]:
    progression = PHASE_TOPIC_PROGRESSIONS.get(phase) or PHASE_TOPIC_PROGRESSIONS["Resume Validation"]
    index = min(max(int(phase_question_count or 0), 0), len(progression) - 1)
    return progression[index]


def _next_progression_question(phase: str, phase_question_count: int, previous_questions: list[str]) -> tuple[str, str, bool, float]:
    progression = PHASE_TOPIC_PROGRESSIONS.get(phase) or PHASE_TOPIC_PROGRESSIONS["Resume Validation"]
    start = min(max(int(phase_question_count or 0), 0), len(progression) - 1)
    best_type, best_question = progression[start]
    best_duplicate, best_similarity = _recent_question_similarity(best_question, previous_questions)
    for offset in range(len(progression)):
        question_type, question = progression[(start + offset) % len(progression)]
        is_duplicate, similarity = _recent_question_similarity(question, previous_questions)
        if not is_duplicate:
            return question_type, question, False, similarity
        if similarity < best_similarity:
            best_type, best_question = question_type, question
            best_duplicate, best_similarity = is_duplicate, similarity
    return best_type, best_question, best_duplicate, best_similarity


def _phase_aware_question(
    phase: str,
    phase_question_count: int,
    role: str,
    generated_question: str,
    previous_questions: list[str],
    clarification_attempts: dict[str, int],
) -> tuple[str, str, bool, float, bool]:
    """Return final question, question type, duplicate flag, similarity, and whether generated text was replaced."""
    generated_question = str(generated_question or "").strip()
    question_type, fallback_question = _topic_for_phase_turn(phase, phase_question_count)
    is_duplicate, max_similarity = _recent_question_similarity(generated_question, previous_questions)
    phase_valid = _question_matches_phase(generated_question, phase)
    replaced = False

    if phase_valid and not is_duplicate:
        final_question = generated_question
    else:
        replaced = True
        question_type, final_question, is_duplicate, max_similarity = _next_progression_question(
            phase,
            phase_question_count,
            previous_questions,
        )

    if is_duplicate:
        attempts = int(clarification_attempts.get(phase, 0) or 0)
        if attempts < 1 and phase != "Technical Assessment":
            clarification_attempts[phase] = attempts + 1
            final_question = (
                f"One brief clarification before we move on: answer with a different {question_type.replace('_', ' ')} "
                f"example for the {role or 'target'} role, including your decision and outcome."
            )
            replaced = True
        else:
            question_type, final_question, is_duplicate, max_similarity = _next_progression_question(
                phase,
                phase_question_count + 1,
                previous_questions,
            )
            clarification_attempts[phase] = 0
            replaced = True
        is_duplicate, max_similarity = _recent_question_similarity(final_question, previous_questions)

    if not is_duplicate:
        clarification_attempts[phase] = 0

    return final_question, question_type, is_duplicate, max_similarity, replaced


_CANDIDATE_HIDDEN_MESSAGE_KEYS = {
    "score", "meta", "difficulty", "focus_area", "focus_type",
    "adaptive_mode", "interviewer_signal", "pressure_level", "answer_expectation",
}


def _candidate_visible_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only candidate-safe messages. Feedback/evaluation is stored but never shown."""
    visible: list[dict[str, Any]] = []
    for message in messages:
        if message.get("role") == "feedback":
            continue
        item = {key: value for key, value in message.items() if key not in _CANDIDATE_HIDDEN_MESSAGE_KEYS}
        visible.append(item)
    return visible


def _sanitize_candidate_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Strip evaluation artifacts from live interview API responses."""
    sanitized = dict(payload)
    sanitized["feedback_message"] = "Your answer has been recorded."
    sanitized.pop("avg_score", None)
    sanitized.pop("final_feedback", None)
    sanitized.pop("final_verdict", None)
    sanitized.pop("verdict_explanation", None)
    sanitized.pop("final_feedback_ready", None)
    sanitized["messages"] = _candidate_visible_messages(sanitized.get("messages") or [])
    if sanitized.get("interview_complete"):
        sanitized["next_question"] = ""
        sanitized["interviewer_response"] = "Interview completed. Generating final report."
    context = sanitized.get("personalization_context")
    if isinstance(context, dict):
        ctx = dict(context)
        ctx.pop("last_score", None)
        ctx.pop("coach_memory", None)
        sanitized["personalization_context"] = ctx
    sanitized.pop("coach_memory", None)
    return sanitized


def _latest_live_response_from_state(
    state: dict[str, Any],
    status: str = INTERVIEW_STATUS_ACTIVE,
    duplicate: bool = False,
) -> dict[str, Any]:
    context = state.get("personalization_context") or {}
    messages = state.get("messages") or []
    current_phase = context.get("current_phase", "Resume Validation")
    last_feedback = next((m for m in reversed(messages) if m.get("role") == "feedback"), {})
    interview_complete = status != INTERVIEW_STATUS_ACTIVE
    current_question = "" if interview_complete else str(state.get("current_question") or "")
    return _sanitize_candidate_response({
        "next_question": current_question,
        "difficulty": state.get("difficulty", 5),
        "focus_area": context.get("current_focus_area", "general"),
        "focus_type": context.get("last_adaptive_mode", "general"),
        "weak_areas": context.get("weak_areas", []),
        "question_mix": context.get("question_mix") or _question_mix_for_mode(context.get("training_mode", state.get("training_mode", "adaptive"))),
        "training_mode": context.get("training_mode", state.get("training_mode", "adaptive")),
        "interviewer_persona": context.get("interviewer_persona", state.get("interviewer_persona", "balanced")),
        "persona": INTERVIEWER_PERSONAS.get(context.get("interviewer_persona", "balanced"), INTERVIEWER_PERSONAS["balanced"]),
        "feedback_message": last_feedback.get("content", "Thank you, I have your answer."),
        "interviewer_response": "Interview completed. Generating final report." if interview_complete else current_question,
        "evaluation_stored": True,
        "answer_expectation": "",
        "session_turn": len(state.get("answers", [])),
        "coach_memory": context.get("coach_memory", {}),
        "phase": current_phase,
        "phase_goal": _phase_meta(current_phase)["goal"],
        "phase_focus": _phase_meta(current_phase)["focus"],
        "phase_history": context.get("phase_history", [current_phase]),
        "status": status,
        "interview_complete": interview_complete,
        "personalization_context": context,
        "messages": messages,
        "db_id": state.get("db_id"),
        "duplicate_submission": duplicate,
    })


def _enqueue_hiring_intelligence_if_needed(
    db: Session,
    background_tasks: BackgroundTasks,
    rec: InterviewSession,
) -> bool:
    if rec.status == "analyzed" and rec.competency_scores and rec.job_fit_report:
        logger.info("hiring_intelligence_enqueue_skipped session_id=%s reason=cached", rec.id)
        return False
    if rec.status == INTERVIEW_STATUS_ANALYZING:
        logger.info("hiring_intelligence_enqueue_skipped session_id=%s reason=already_analyzing", rec.id)
        return False
    rec.status = INTERVIEW_STATUS_ANALYZING
    rec.updated_at = datetime.utcnow()
    db.add(rec)
    db.commit()
    from src.services.hiring_intelligence import compile_hiring_intelligence
    background_tasks.add_task(compile_hiring_intelligence, rec.id)
    context = _safe_json_load(rec.personalization_context, {})
    phase = context.get("current_phase") if isinstance(context, dict) else None
    _log_interview_event("report_generation", rec.id, phase, None, status=rec.status)
    logger.info("hiring_intelligence_enqueued session_id=%s", rec.id)
    return True

@router.post("/start")
@router.post("/start-for-application")
@router.post("/start-from-resume")
def start_interview(
    req: StartForApplicationReq,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    app = None
    if req.application_id is not None:
        app = db.exec(
            select(CandidateApplication)
            .where(CandidateApplication.id == req.application_id)
        ).first()
        if not app:
            raise HTTPException(status_code=404, detail="Application not found.")
        if app.candidate_user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized access to this application.")

        existing_session = db.exec(
            select(InterviewSession)
            .where(InterviewSession.application_id == req.application_id)
            .where(InterviewSession.status.in_(list({INTERVIEW_STATUS_ACTIVE, *TERMINAL_INTERVIEW_STATUSES})))
        ).first()
    else:
        existing_session = db.exec(
            select(InterviewSession)
            .where(InterviewSession.user_id == current_user.id)
            .where(InterviewSession.application_id.is_(None))
            .where(InterviewSession.status == INTERVIEW_STATUS_ACTIVE)
        ).first()
    if existing_session:
        if existing_session.status == INTERVIEW_STATUS_ACTIVE:
            state = _sessions.get(existing_session.session_token)
            if state is None:
                state = _state_from_record(existing_session)
                _sessions[existing_session.session_token] = state
            
            msgs = json.loads(existing_session.messages) if existing_session.messages else []
            last_ai = next((m for m in reversed(msgs) if m.get("role") == "ai"), None)
            question = last_ai.get("content") if last_ai else "Can you describe your most relevant experience?"
            
            return {
                "session_id": existing_session.session_token,
                "question": question,
                "db_id": existing_session.id,
                "personalized": True,
                "role": existing_session.role,
                "difficulty": existing_session.difficulty,
                "training_mode": existing_session.training_mode,
                "interviewer_persona": existing_session.interviewer_persona,
                "status": existing_session.status,
                "messages": msgs,
                "message": "Resuming existing active interview session."
            }
        elif existing_session.status == INTERVIEW_STATUS_CANCELLED:
            return {
                "session_id": existing_session.session_token,
                "db_id": existing_session.id,
                "status": "cancelled",
                "cancellation_reason": existing_session.cancellation_reason,
                "message": "This interview has been cancelled due to proctoring violations."
            }
        else:
            raise HTTPException(status_code=400, detail="You have already completed the interview for this application.")

    job = db.exec(select(JobPosting).where(JobPosting.id == app.job_id)).first() if app else None
    role = (job.title if job else req.role.strip()) or current_user.target_role or "Software Engineer"

    resume_source = "application"
    resume_text = app.resume_text if app else ""
    if not app:
        resume_text, resume_source = _latest_candidate_resume_text(db, current_user.id)
    if not resume_text or len(resume_text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Resume text is missing or too short.")

    resume = db.exec(select(Resume).where(Resume.user_id == current_user.id)).first()
    analysis = load_json_field(resume.last_analysis, None) if resume else None
    if req.force_reanalyze or not analysis:
        analysis = analyze_resume(resume_text, role)
        if resume:
            resume.last_analysis = dumps_json(analysis)
            resume.parsed_resume = dumps_json(parse_resume(resume_text))
            resume.updated_at = datetime.utcnow()
            db.add(resume)
            db.commit()

    training_mode = _normalize_training_mode(req.training_mode)
    interviewer_persona = _normalize_persona(req.interviewer_persona)
    memory = _get_or_create_memory(db, current_user.id)

    context = _build_personalization_context(
        resume_text,
        analysis,
        role,
        req.difficulty,
        training_mode,
        interviewer_persona,
        req.domain_focus,
        _memory_snapshot(memory),
    )
    focus_mode = "weak_area" if context["weak_areas"] else "general"
    if training_mode == "behavioral_only":
        focus_mode = "behavioral_only"
    elif training_mode == "domain_specific":
        focus_mode = "domain_specific"
    current_phase = "Resume Validation"
    phase_details = _phase_meta(current_phase)

    first = {
        "question": f"Tell me about yourself as it relates to this {role} role.",
        "focus_area": "general introduction",
        "focus_type": "general",
        "interviewer_signal": "I want to hear how your background fits this role and what you can contribute.",
        "pressure_level": INTERVIEWER_PERSONAS[interviewer_persona]["pressure"],
        "answer_expectation": "Share your background, role-relevant strengths, and a brief example of your most relevant experience.",
    }

    question = str(first.get("question") or f"Tell me about yourself as it relates to this {role} role.").strip()
    answer_expectation = str(first.get("answer_expectation") or "Answer in 5-10 lines with context, decisions, tradeoffs, and measurable outcome.").strip()
    focus_type = _normalize_focus_type(first.get("focus_type"), focus_mode)
    context["focus_counts"][focus_type] = context["focus_counts"].get(focus_type, 0) + 1
    context["current_focus_area"] = first.get("focus_area", context["weak_areas"][0] if context["weak_areas"] else "general")
    context["current_phase"] = current_phase
    context["phase_history"] = [current_phase]
    context["phase_turn_count"] = 0

    session_token = uuid.uuid4().hex
    first_msg = {
        "role": "ai",
        "content": question,
        "timestamp": datetime.utcnow().isoformat(),
        "focus_area": context["current_focus_area"],
        "focus_type": focus_type,
        "source": "resume_lab",
        "interviewer_signal": first.get("interviewer_signal", ""),
        "pressure_level": first.get("pressure_level", INTERVIEWER_PERSONAS[interviewer_persona]["pressure"]),
        "answer_expectation": answer_expectation,
        "phase": current_phase,
    }
    db_session = InterviewSession(
        user_id=current_user.id,
        application_id=app.id if app else None,
        session_token=session_token,
        role=role,
        difficulty=req.difficulty,
        training_mode=training_mode,
        interviewer_persona=interviewer_persona,
        messages=json.dumps([first_msg]),
        personalization_context=json.dumps(context),
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    _sessions[session_token] = {
        "role": role,
        "difficulty": req.difficulty,
        "weak_areas": context["weak_areas"],
        "questions": [],
        "answers": [],
        "scores": [],
        "messages": [first_msg],
        "current_question": question,
        "db_id": db_session.id,
        "session_token": session_token,
        "user_id": current_user.id,
        "training_mode": training_mode,
        "interviewer_persona": interviewer_persona,
        "personalization_context": context,
    }
    _update_coach_memory(db, current_user.id, _sessions[session_token])
    persona_profile = INTERVIEWER_PERSONAS.get(interviewer_persona, INTERVIEWER_PERSONAS["balanced"])
    session_intro = (
        f"This proctored interview simulates a {persona_profile.get('label', 'Balanced')} interviewer under {first_msg.get('pressure_level', persona_profile.get('pressure', 'medium'))} pressure. "
        "Treat answers like a live screening: be concise, cite specific decisions, and quantify outcomes where possible."
    )

    return {
        "session_id": session_token,
        "question": question,
        "db_id": db_session.id,
        "personalized": True,
        "role": role,
        "difficulty": req.difficulty,
        "weak_areas": context["weak_areas"],
        "section_scores": context["section_scores"],
        "resume_score": context["resume_score"],
        "resume_source": resume_source,
        "focus_area": context["current_focus_area"],
        "focus_type": focus_type,
        "interviewer_signal": first_msg["interviewer_signal"],
        "pressure_level": first_msg["pressure_level"],
        "answer_expectation": answer_expectation,
        "question_mix": context["question_mix"],
        "training_mode": training_mode,
        "interviewer_persona": interviewer_persona,
        "status": INTERVIEW_STATUS_ACTIVE,
        "persona": persona_profile,
        "coach_memory": context["coach_memory"],
        "session_intro": session_intro,
        "phase": current_phase,
        "phase_goal": phase_details["goal"],
        "messages": [first_msg],
    }


@router.post("/{session_id}/violation")
def record_proctoring_violation(
    session_id: str,
    req: ViolationReq,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    rec = db.exec(select(InterviewSession).where(InterviewSession.session_token == session_id)).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    if rec.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized access to this session.")
    if rec.status != INTERVIEW_STATUS_ACTIVE:
        try:
            violations_list = json.loads(rec.violations) if rec.violations else []
        except Exception:
            violations_list = []
        return {
            "success": False,
            "cancelled": rec.status == INTERVIEW_STATUS_CANCELLED,
            "cancellation_reason": rec.cancellation_reason,
            "violations_count": rec.violations_count,
            "violations": violations_list,
            "message": f"Interview session is already in '{rec.status}' status."
        }

    try:
        violations_list = json.loads(rec.violations) if rec.violations else []
    except Exception:
        violations_list = []

    new_violation = {
        "type": req.violation_type,
        "detail": req.detail,
        "timestamp": datetime.utcnow().isoformat(),
        "duration_ms": max(0, int(req.duration_ms or 0)),
        "severity": req.severity if req.severity in ("low", "medium", "high") else "medium",
    }
    violations_list.append(new_violation)
    rec.violations = json.dumps(violations_list)
    rec.violations_count = len(violations_list)

    cancelled = False
    if rec.violations_count >= 3:
        rec.status = INTERVIEW_STATUS_CANCELLED
        rec.cancellation_reason = f"Proctoring violation limit exceeded (3). Last violation: {req.detail}"
        cancelled = True
        
        if rec.session_token in _sessions:
            del _sessions[rec.session_token]

        try:
            job_title = rec.role or "Software Engineer"
            _notify_hr(
                db,
                title="Interview Cancelled (Proctoring)",
                message=f"Candidate '{current_user.username}''s interview for the '{job_title}' role has been cancelled due to excessive proctoring violations ({rec.violations_count}).",
                event_type="interview_cancelled",
                related_id=rec.id
            )
        except Exception as e:
            logger.error("Failed to notify HR about interview cancellation: %s", e)

    rec.updated_at = datetime.utcnow()
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return {
        "success": True,
        "cancelled": cancelled,
        "violations_count": rec.violations_count,
        "cancellation_reason": rec.cancellation_reason,
        "violations": violations_list
    }


@router.post("/answer")
def submit_answer(
    req: AnswerReq,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    try:
        return _submit_answer_impl(req, background_tasks, db, current_user)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "submit_answer_unhandled session_id=%s error=%s",
            req.session_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to process your answer. Please try again.",
        ) from exc


def _submit_answer_impl(
    req: AnswerReq,
    background_tasks: BackgroundTasks,
    db: Session,
    current_user: User,
):
    request_started = time.perf_counter()
    request_start_iso = _utc_iso()
    answer_text = str(req.answer or "").strip()
    if not answer_text:
        raise HTTPException(status_code=422, detail="Answer cannot be empty.")
    if len(answer_text) > 5000:
        raise HTTPException(status_code=422, detail="Answer must be 5000 characters or fewer.")

    rec = db.exec(select(InterviewSession).where(InterviewSession.session_token == req.session_id)).first()
    if rec is None or rec.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Invalid session ID. Please start a new interview.")
    if rec.status != INTERVIEW_STATUS_ACTIVE:
        state = _ensure_live_state(_sessions.get(req.session_id) or _state_from_record(rec))
        return _latest_live_response_from_state(state, status=rec.status, duplicate=True)

    state = _sessions.get(req.session_id)
    if state is None:
        state = _ensure_live_state(_state_from_record(rec))
        _sessions[req.session_id] = state
    else:
        state = _ensure_live_state(state)
    if state.get("user_id") is not None and state.get("user_id") != current_user.id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if state.get("answers") and str(state["answers"][-1]).strip() == answer_text:
        _log_interview_event("answer_submit_duplicate", req.session_id, (state.get("personalization_context") or {}).get("current_phase"), len(state.get("answers", [])))
        return _latest_live_response_from_state(state, status=rec.status, duplicate=True)

    import copy
    state = copy.deepcopy(state)
    context = state.setdefault("personalization_context", {})
    focus_mode = _choose_focus_mode(state)
    current_phase = context.get("current_phase", "Resume Validation")
    question_number = len(state.get("answers", [])) + 1
    phase_turn_count_for_answer = int(context.get("phase_turn_count", 0)) + 1
    generation_phase, generation_complete = next_phase_for_completed_turn(current_phase, phase_turn_count_for_answer)
    phase_details = _phase_meta(generation_phase)
    _log_interview_event("answer_submit", req.session_id, current_phase, question_number, answer_chars=len(answer_text))

    # Claim Verification Engine — use full resume text when available for claim extraction
    resume_text = ""
    res_ctx = context.get("resume_context", {})
    if isinstance(res_ctx, dict):
        resume_text = (
            res_ctx.get("raw_text")
            or res_ctx.get("summary", "")
            or ""
        )
        if res_ctx.get("skills"):
            resume_text = f"{resume_text} {' '.join(res_ctx.get('skills', []))}".strip()
    
    from src.services.interview_consistency import _extract_claims
    resume_claims = _extract_claims(resume_text)
    
    if "verified_claims" not in context:
        context["verified_claims"] = []
        
    verification_active = context.get("verification_active", False)
    current_verification_claim = context.get("current_verification_claim", None)
    verification_depth = context.get("verification_depth", 0)

    if verification_active:
        verification_depth += 1
        if verification_depth >= 2:
            context["verified_claims"].append(current_verification_claim)
            verification_active = False
            current_verification_claim = None
            verification_depth = 0
            context["current_focus_area"] = "general"
        else:
            context["verification_depth"] = verification_depth
            context["current_focus_area"] = f"claim verification: {current_verification_claim}"
    else:
        detected_claim = None
        answer_lower = answer_text.lower()
        for claim in resume_claims:
            if claim.lower() in answer_lower and claim not in context["verified_claims"]:
                detected_claim = claim
                break
        if detected_claim:
            verification_active = True
            current_verification_claim = detected_claim
            verification_depth = 0
            context["verification_active"] = True
            context["current_verification_claim"] = current_verification_claim
            context["verification_depth"] = verification_depth
            context["current_focus_area"] = f"claim verification: {current_verification_claim}"

    context["verification_active"] = verification_active
    context["current_verification_claim"] = current_verification_claim
    import math

    def _clean_nans(obj):
        if isinstance(obj, float) and math.isnan(obj):
            return None
        elif isinstance(obj, dict):
            return {k: _clean_nans(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_clean_nans(i) for i in obj]
        return obj

    try:
        from crew import run_interview_answer
        
        logger.debug(
            "run_interview_answer trace - session_id=%s current_phase=%s generation_phase=%s answer_count=%s difficulty=%s phase_history=%s",
            req.session_id,
            current_phase,
            generation_phase,
            len(state.get("answers", [])),
            state["difficulty"],
            context.get("phase_history", []),
        )
        
        result = run_interview_answer(
            role=state["role"],
            question=state["current_question"],
            answer=answer_text,
            current_diff=state["difficulty"],
            weak_areas=context.get("weak_areas", state.get("weak_areas", [])),
            resume_context=context.get("resume_context", {}),
            section_scores=context.get("section_scores", {}),
            focus_mode=focus_mode,
            training_mode=context.get("training_mode", state.get("training_mode", "adaptive")),
            interviewer_persona=INTERVIEWER_PERSONAS.get(
                context.get("interviewer_persona", state.get("interviewer_persona", "balanced")),
                INTERVIEWER_PERSONAS["balanced"],
            ),
            coach_memory=context.get("coach_memory", {}),
            domain_focus=context.get("domain_focus", ""),
            conversation_history=state.get("messages", [])[-8:],
            current_focus_area=context.get("current_focus_area", ""),
            phase_name=generation_phase,
            phase_goal=phase_details["goal"],
            phase_focus=phase_details["focus"],
        )
        if not isinstance(result, dict):
            logger.warning("run_interview_answer returned non-dict payload; using safe fallback.")
            result = {}
        result = _clean_nans(result)
    except Exception as exc:
        logger.error("Interview answer failed: %s", exc, exc_info=True)
        result = {
            "next_question": f"Let's try a different angle. Can you tell me about a specific project where you demonstrated {context.get('current_focus_area', 'your skills')}?",
            "evaluation": {"score": 5, "what_went_well": ["Answered under pressure"], "what_was_missing": ["Detail and specificity"], "how_to_improve": ["Try again with a concrete example"], "next_focus": context.get("current_focus_area", "general role fit")},
            "focus_area": context.get("current_focus_area", "general"),
            "focus_type": "general",
            "adaptive_mode": focus_mode,
            "new_difficulty": state["difficulty"],
            "interviewer_signal": "Let's keep going.",
            "pressure_level": "medium",
            "answer_expectation": "Answer with a specific example.",
        }
    finally:
        _log_perf("interview_answer_generation", request_started, start_time=request_start_iso, session_token=req.session_id)

    # Update in-memory state
    state["questions"].append(state["current_question"])
    state["answers"].append(answer_text)
    phase_turn_count = phase_turn_count_for_answer
    
    raw_eval = result.get("evaluation", {})
    if isinstance(raw_eval, str):
        try:
            import json
            raw_eval = json.loads(raw_eval)
        except Exception:
            raw_eval = {"score": 5}
    if not isinstance(raw_eval, dict):
        raw_eval = {"score": 5}
        
    score = raw_eval.get("score", 5)
    try:
        score = int(score)
    except (TypeError, ValueError):
        score = 5
    state["scores"].append(score)
    avg = sum(state["scores"]) / len(state["scores"]) if state["scores"] else None

    new_diff = result.get("new_difficulty", state["difficulty"])
    try:
        new_diff = int(new_diff)
    except (TypeError, ValueError):
        new_diff = state["difficulty"]
    state["difficulty"] = max(1, min(10, new_diff))
    generated_next_q = result.get("next_question") or ""

    focus_type = _normalize_focus_type(result.get("focus_type"), focus_mode)
    context.setdefault("focus_counts", {"weak_area": 0, "general": 0, "domain": 0, "behavioral": 0})
    context["focus_counts"][focus_type] = int(context["focus_counts"].get(focus_type, 0) or 0) + 1
    context["current_focus_area"] = result.get("focus_area", context.get("current_focus_area", "general"))
    context["difficulty"] = state["difficulty"]
    context["last_score"] = score
    context["last_adaptive_mode"] = result.get("adaptive_mode", focus_mode)
    next_phase, deterministic_complete = generation_phase, generation_complete
    if next_phase == current_phase:
        context["phase_turn_count"] = phase_turn_count
        next_phase_question_count = phase_turn_count
    else:
        context["phase_turn_count"] = 0
        next_phase_question_count = 0
        _log_interview_event("phase_transition", req.session_id, next_phase, len(state["answers"]) + 1, from_phase=current_phase)

    interview_complete = deterministic_complete and _is_interview_complete_after_answer(current_phase, phase_turn_count)
    if interview_complete:
        next_q = ""
        question_type = "complete"
        is_duplicate = False
        max_similarity = 0.0
        question_replaced = False
        state["current_question"] = ""
        context["phase_turn_count"] = phase_turn_count
    else:
        clarification_attempts = context.setdefault("clarification_attempts_by_phase", {})
        next_q, question_type, is_duplicate, max_similarity, question_replaced = _phase_aware_question(
            phase=next_phase,
            phase_question_count=next_phase_question_count,
            role=state.get("role", ""),
            generated_question=generated_next_q,
            previous_questions=state.get("questions", []),
            clarification_attempts=clarification_attempts,
        )
        state["current_question"] = next_q
        _log_interview_event(
            "question_generation_decision",
            req.session_id,
            next_phase,
            len(state["answers"]) + 1,
            current_phase=current_phase,
            question_count=len(state["answers"]) + 1,
            phase_question_count=next_phase_question_count + 1,
            generated_question=generated_next_q,
            final_question=next_q,
            question_type=question_type,
            duplicate=is_duplicate,
            max_similarity=round(max_similarity, 3),
            replaced=question_replaced,
        )

    logger.debug(
        "Interview lifecycle trace - session_id=%s current_phase=%s answer_count=%s phase_turn_count=%s next_phase=%s is_complete=%s next_question_generated=%s phase_history=%s",
        req.session_id,
        current_phase,
        len(state["answers"]),
        phase_turn_count,
        next_phase,
        interview_complete,
        bool(next_q),
        context.get("phase_history", []),
    )

    context["current_phase"] = next_phase
    phase_history = context.get("phase_history") or []
    if not phase_history:
        phase_history = [current_phase]
    if phase_history[-1] != next_phase:
        phase_history.append(next_phase)
    context["phase_history"] = phase_history
    state["current_question"] = next_q
    state["personalization_context"] = context

    now = datetime.utcnow().isoformat()
    # Normalize and repair evaluator output into the strict schema
    normalized_eval = _normalize_and_repair_evaluation(raw_eval, context.get("current_focus_area", ""))
    feedback = _format_feedback_message(
        normalized_eval,
        context.get("current_focus_area", ""),
        interview_complete=interview_complete,
    )
    feedback_text = feedback.get("text") if isinstance(feedback, dict) else str(feedback)
    state["messages"].append({"role": "user", "content": answer_text, "timestamp": now})
    state["messages"].append({
        "role": "feedback",
        "content": feedback_text,
        "score": score,
        "focus_area": context.get("current_focus_area"),
        "timestamp": now,
        "meta": normalized_eval,
    })
    if not interview_complete and next_q:
        state["messages"].append({
            "role": "ai",
            "content": next_q,
            "score": score,
            "difficulty": state["difficulty"],
            "focus_area": context["current_focus_area"],
            "focus_type": focus_type,
            "adaptive_mode": result.get("adaptive_mode", focus_mode),
            "question_type": question_type,
            "interviewer_signal": result.get("interviewer_signal", ""),
            "pressure_level": result.get("pressure_level", INTERVIEWER_PERSONAS.get(context.get("interviewer_persona", "balanced"), INTERVIEWER_PERSONAS["balanced"]).get("pressure", "medium")),
            "answer_expectation": result.get("answer_expectation", ""),
            "phase": next_phase,
            "timestamp": now,
        })
        _log_interview_event(
            "question_generate",
            req.session_id,
            next_phase,
            len(state["answers"]) + 1,
            current_phase=current_phase,
            question_count=len(state["answers"]) + 1,
            phase_question_count=next_phase_question_count + 1,
            generated_question=generated_next_q,
            question_type=question_type,
            duplicate=is_duplicate,
            replaced=question_replaced,
        )

    memory = _update_coach_memory(db, current_user.id, state, score)
    context["coach_memory"] = _memory_snapshot(memory)
    _save_session_state(db, req.session_id, state, avg)
    _sessions[req.session_id] = state
    if interview_complete:
        rec = db.exec(select(InterviewSession).where(InterviewSession.session_token == req.session_id)).first()
        if rec:
            _enqueue_hiring_intelligence_if_needed(db, background_tasks, rec)
        _log_interview_event("interview_complete", req.session_id, next_phase, len(state["answers"]))
    state["personalization_context"] = context

    # Derive a compact final verdict from rolling scores
    final_verdict = None
    verdict_explanation = ""
    try:
        if avg is not None:
            if avg < 5:
                final_verdict = "Not Ready"
                verdict_explanation = "Solidify fundamentals and focus on weak-area drills before applying."
            elif avg < 7.5:
                final_verdict = "Borderline"
                verdict_explanation = "Some strong answers but inconsistent; prioritize specificity and measurable outcomes."
            else:
                final_verdict = "Ready"
                verdict_explanation = "Consistent depth and clarity — you're approaching interview-ready quality."
    except Exception:
        final_verdict = None

    final_feedback = None
    if interview_complete:
        final_feedback = {
            "overall_score": round(avg, 2) if avg is not None else score,
            "strengths": normalized_eval.get("what_went_well", [])[:3],
            "weaknesses": normalized_eval.get("what_was_missing", [])[:3],
            "improvement_plan": normalized_eval.get("how_to_improve", [])[:3],
            "verdict": final_verdict,
            "verdict_explanation": verdict_explanation,
        }

    response = {
        "next_question": "" if interview_complete else next_q,
        "difficulty": state["difficulty"],
        "focus_area": context["current_focus_area"],
        "focus_type": focus_type,
        "weak_areas": context.get("weak_areas", []),
        "question_mix": context.get("question_mix") or _question_mix_for_mode(context.get("training_mode", state.get("training_mode", "adaptive"))),
        "training_mode": context.get("training_mode", state.get("training_mode", "adaptive")),
        "interviewer_persona": context.get("interviewer_persona", state.get("interviewer_persona", "balanced")),
        "persona": INTERVIEWER_PERSONAS.get(context.get("interviewer_persona", "balanced"), INTERVIEWER_PERSONAS["balanced"]),
        "feedback_message": feedback_text,
        "interviewer_response": "Interview completed. Generating final report." if interview_complete else next_q,
        "evaluation_stored": True,
        "answer_expectation": result.get("answer_expectation", ""),
        "session_turn": len(state["answers"]),
        "coach_memory": context["coach_memory"],
        "phase": next_phase,
        "phase_goal": _phase_meta(next_phase)["goal"],
        "phase_focus": _phase_meta(next_phase)["focus"],
        "phase_history": context.get("phase_history", [next_phase]),
        "status": INTERVIEW_STATUS_ANALYZING if interview_complete else INTERVIEW_STATUS_ACTIVE,
        "interview_complete": interview_complete,
        "personalization_context": context,
        "messages": state["messages"],
        "db_id": state.get("db_id"),
    }
    if interview_complete:
        response["final_feedback_ready"] = False
        response["avg_score"] = round(avg, 2) if avg is not None else None
        response["final_feedback"] = final_feedback
        response["final_verdict"] = final_verdict
        response["verdict_explanation"] = verdict_explanation
    _log_perf("interview_completion_turn", request_started, start_time=request_start_iso, session_token=req.session_id, complete=interview_complete)
    return _sanitize_candidate_response(response)

@router.get("/coach-memory")
def get_coach_memory(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    memory = _get_or_create_memory(db, current_user.id)
    return {
        "success": True,
        "memory": _memory_snapshot(memory),
        "training_modes": TRAINING_MODES,
        "personas": INTERVIEWER_PERSONAS,
    }


@router.get("/daily-plan")
def get_daily_plan(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    memory = _get_or_create_memory(db, current_user.id)
    resume = db.exec(select(Resume).where(Resume.user_id == current_user.id)).first()
    resume_analysis = load_json_field(resume.last_analysis, None) if resume else None
    plan = _generate_daily_plan(memory, resume_analysis)
    db.add(memory)
    db.commit()
    return {
        "success": True,
        "plan": plan,
        "memory": _memory_snapshot(memory),
    }


@router.get("/modes")
def get_interview_modes():
    return {
        "training_modes": TRAINING_MODES,
        "personas": INTERVIEWER_PERSONAS,
    }


@router.get("/sessions")
def list_sessions(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Return all past interview sessions for the sidebar, newest first."""
    records = db.exec(
        select(InterviewSession)
        .where(InterviewSession.user_id == current_user.id)
        .order_by(InterviewSession.created_at.desc())
    ).all()
    return [
        {
            "id": r.id,
            "session_token": r.session_token,
            "role": r.role,
            "difficulty": r.difficulty,
            "training_mode": _normalize_training_mode(r.training_mode),
            "interviewer_persona": _normalize_persona(r.interviewer_persona),
            "avg_score": r.avg_score,
            "status": r.status,
            "message_count": len(_safe_json_load(r.messages, [])),
            "personalized": _safe_json_load(r.personalization_context, {}).get("source") == "resume_lab",
            "weak_areas": _safe_json_load(r.personalization_context, {}).get("weak_areas", [])[:3],
            "violations_count": r.violations_count,
            "cancellation_reason": r.cancellation_reason,
            "application_id": r.application_id,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


@router.get("/sessions/{session_id}")
def get_session_history(
    session_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Return the full message log for a specific past session."""
    rec = db.get(InterviewSession, session_id)
    if not rec or rec.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found.")
    try:
        violations_list = json.loads(rec.violations) if rec.violations else []
    except Exception:
        violations_list = []
    is_hr_viewer = current_user.role in {"hr", "admin", "manager"}
    raw_messages = _safe_json_load(rec.messages, [])
    payload = {
        "id": rec.id,
        "session_token": rec.session_token,
        "role": rec.role,
        "difficulty": rec.difficulty,
        "training_mode": _normalize_training_mode(rec.training_mode),
        "interviewer_persona": _normalize_persona(rec.interviewer_persona),
        "status": rec.status,
        "violations_count": rec.violations_count,
        "violations": violations_list,
        "cancellation_reason": rec.cancellation_reason,
        "application_id": rec.application_id,
        "messages": raw_messages if is_hr_viewer else _candidate_visible_messages(raw_messages),
        "personalization_context": _safe_json_load(rec.personalization_context, {}),
        "created_at": rec.created_at.isoformat(),
    }
    if is_hr_viewer:
        payload.update({
            "avg_score": rec.avg_score,
            "competency_scores": _safe_json_load(rec.competency_scores, None),
            "job_fit_report": _safe_json_load(rec.job_fit_report, None),
            "communication_metrics": _safe_json_load(rec.communication_metrics, None),
            "behavioral_report": _safe_json_load(rec.behavioral_report, None),
            "hiring_risks": _safe_json_load(rec.hiring_risks, None),
            "timeline_replay": _safe_json_load(rec.timeline_replay, None),
            "benchmarking": _safe_json_load(rec.benchmarking, None),
        })
    return payload


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Delete a specific interview session."""
    rec = db.get(InterviewSession, session_id)
    if not rec or rec.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Remove from memory if active
    if rec.session_token in _sessions:
        del _sessions[rec.session_token]

    db.delete(rec)
    db.commit()
    return {"message": "Session deleted"}


@router.post("/{session_id}/credibility")
def get_credibility_report(
    session_id: int,
    force: bool = False,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Run credibility analysis comparing resume claims against interview evidence."""
    from src.services.interview_consistency import analyze_credibility, credibility_payload

    rec = db.get(InterviewSession, session_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    if current_user.role not in ("hr", "manager", "admin") and rec.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized access to this credibility report.")

    try:
        report = analyze_credibility(db, session_id, force=force)
        return credibility_payload(report)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Intelligence Dashboard Endpoints ──────────────────────────────────────────


def _compute_hiring_score(resume_score: float, interview_score: float, credibility_score: float) -> float:
    """Composite hiring score: 35% resume + 40% interview + 25% credibility."""
    return round(0.35 * resume_score + 0.40 * interview_score + 0.25 * credibility_score, 1)


def _recommendation_label(score: float) -> str:
    if score >= 92:
        return "Strongly Recommended"
    if score >= 80:
        return "Recommended"
    if score >= 65:
        return "Needs Review"
    return "Not Recommended"


@router.get("/intelligence/leaderboard")
def intelligence_leaderboard(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Ranked candidate leaderboard combining resume, interview, and credibility scores."""
    if current_user.role not in ("hr", "manager", "admin"):
        raise HTTPException(status_code=403, detail="HR/manager access required")

    from src.models import CandidateApplication, ApplicationAIAnalysis, CandidateApplication as CA

    sessions = db.exec(
        select(InterviewSession).where(InterviewSession.status.in_(list(VISIBLE_INTERVIEW_STATUSES))).order_by(InterviewSession.created_at.desc())
    ).all()

    results = []
    seen_candidates = set()

    for session in sessions:
        uid = session.user_id
        if uid in seen_candidates:
            continue
        seen_candidates.add(uid)

        user = db.get(User, uid)
        if not user:
            continue

        app = db.exec(
            select(CandidateApplication).where(CandidateApplication.candidate_user_id == uid).order_by(CandidateApplication.application_date.desc())
        ).first()
        if not app:
            continue

        analysis = db.exec(
            select(ApplicationAIAnalysis).where(ApplicationAIAnalysis.application_id == app.id)
        ).first()

        credibility_report = db.exec(
            select(CandidateCredibilityReport).where(CandidateCredibilityReport.candidate_id == uid)
        ).first()

        interview_avg = session.avg_score or 0
        resume_score = analysis.fit_score if analysis else 0
        credibility_score = credibility_report.credibility_score if credibility_report else 0
        hiring_score = _compute_hiring_score(resume_score, interview_avg * 10, credibility_score)

        strengths = json.loads(analysis.strengths) if analysis and analysis.strengths else []
        weaknesses = json.loads(analysis.weaknesses) if analysis and analysis.weaknesses else []

        results.append({
            "candidate_id": uid,
            "candidate_name": user.username,
            "application_id": app.id,
            "job_id": app.job_id,
            "resume_score": resume_score,
            "interview_score": round(interview_avg * 10, 1),
            "credibility_score": credibility_score,
            "hiring_score": hiring_score,
            "recommendation": _recommendation_label(hiring_score),
            "skill_match": round(resume_score, 1),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "status": app.status,
            "interview_status": session.status,
            "cancellation_reason": session.cancellation_reason,
            "session_id": session.id,
            "last_interview": session.created_at.isoformat() if session.created_at else None,
        })

    results.sort(key=lambda r: r["hiring_score"], reverse=True)
    return {"leaderboard": results, "total": len(results)}


@router.get("/intelligence/report/{candidate_id}")
def intelligence_candidate_report(
    candidate_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Full intelligence report for a single candidate."""
    if current_user.role not in ("hr", "manager", "admin"):
        raise HTTPException(status_code=403, detail="HR/manager access required")

    from src.models import CandidateApplication, ApplicationAIAnalysis

    candidate = db.get(User, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    app = db.exec(
        select(CandidateApplication).where(CandidateApplication.candidate_user_id == candidate_id).order_by(CandidateApplication.application_date.desc())
    ).first()

    analysis = None
    if app:
        analysis = db.exec(select(ApplicationAIAnalysis).where(ApplicationAIAnalysis.application_id == app.id)).first()

    sessions = db.exec(
        select(InterviewSession).where(InterviewSession.user_id == candidate_id).order_by(InterviewSession.created_at.desc())
    ).all()

    credibility_report = db.exec(
        select(CandidateCredibilityReport).where(CandidateCredibilityReport.candidate_id == candidate_id).order_by(CandidateCredibilityReport.created_at.desc())
    ).first()
    intelligence_report = None
    if app:
        intelligence_report = db.exec(
            select(InterviewIntelligenceReport).where(InterviewIntelligenceReport.application_id == app.id)
        ).first()

    # Build timeline from interview messages
    timeline = []
    for s in sessions:
        msgs = json.loads(s.messages) if s.messages else []
        for i, m in enumerate(msgs):
            if m.get("role") == "feedback" and m.get("score") is not None:
                question = ""
                for j in range(i - 1, -1, -1):
                    prev = msgs[j]
                    if prev.get("role") == "ai":
                        question = prev.get("content", "")[:200]
                        break
                next_diff = s.difficulty
                for j in range(i + 1, min(i + 3, len(msgs))):
                    nxt = msgs[j]
                    if nxt.get("role") == "ai" and nxt.get("difficulty"):
                        next_diff = nxt["difficulty"]
                        break
                timeline.append({
                    "question": question,
                    "score": m["score"],
                    "difficulty": next_diff,
                    "feedback": m.get("content", ""),
                    "timestamp": m.get("timestamp", s.created_at.isoformat() if s.created_at else ""),
                })

    interview_avg = 0
    completed = [s for s in sessions if is_successful_interview_status(s.status)]
    if completed:
        interview_avg = sum(s.avg_score or 0 for s in completed) / len(completed)

    resume_score = analysis.fit_score if analysis else 0
    credibility_score = credibility_report.credibility_score if credibility_report else 0
    hiring_score = _compute_hiring_score(resume_score, interview_avg * 10, credibility_score)

    strengths = json.loads(analysis.strengths) if analysis and analysis.strengths else []
    weaknesses = json.loads(analysis.weaknesses) if analysis and analysis.weaknesses else []
    observations = json.loads(analysis.observations) if analysis and analysis.observations else []
    missing_skills = json.loads(analysis.missing_skills) if analysis and analysis.missing_skills else []

    supported_claims = json.loads(credibility_report.supported_claims) if credibility_report and credibility_report.supported_claims else []
    weak_claims = json.loads(credibility_report.weak_claims) if credibility_report and credibility_report.weak_claims else []
    missing_evidence = json.loads(credibility_report.missing_evidence) if credibility_report and credibility_report.missing_evidence else []
    followup_topics = json.loads(credibility_report.followup_topics) if credibility_report and credibility_report.followup_topics else []

    return {
        "candidate": {"id": candidate.id, "username": candidate.username, "role": candidate.role, "target_role": candidate.target_role},
        "application": {"id": app.id, "job_id": app.job_id, "status": app.status, "resume_text": (app.resume_text[:500] + "...") if app and len(app.resume_text) > 500 else (app.resume_text if app else "")} if app else None,
        "analysis": {
            "fit_score": resume_score,
            "recommendation": analysis.recommendation if analysis else "N/A",
            "summary": analysis.summary if analysis else "",
            "strengths": strengths,
            "weaknesses": weaknesses,
            "observations": observations,
            "missing_skills": missing_skills,
        } if analysis else None,
        "credibility": {
            "credibility_score": credibility_score,
            "recommendation": credibility_report.recommendation if credibility_report else "N/A",
            "supported_claims": supported_claims,
            "weak_claims": weak_claims,
            "missing_evidence": missing_evidence,
            "followup_topics": followup_topics,
            "source": credibility_report.source if credibility_report else None,
        } if credibility_report else None,
        "interview": {
            "avg_score": round(interview_avg * 10, 1),
            "sessions_count": len(sessions),
            "completed_count": len(completed),
            "timeline": timeline,
            "sessions": [
                {
                    "id": s.id,
                    "difficulty": s.difficulty,
                    "training_mode": s.training_mode,
                    "avg_score": s.avg_score,
                    "status": s.status,
                    "violations_count": s.violations_count,
                    "violations": _safe_load_list(s.violations),
                    "cancellation_reason": s.cancellation_reason,
                    "competency_scores": _safe_json_load(s.competency_scores, None),
                    "job_fit_report": _safe_json_load(s.job_fit_report, None),
                    "communication_metrics": _safe_json_load(s.communication_metrics, None),
                    "behavioral_report": _safe_json_load(s.behavioral_report, None),
                    "hiring_risks": _safe_json_load(s.hiring_risks, None),
                    "timeline_replay": _safe_json_load(s.timeline_replay, None),
                    "benchmarking": _safe_json_load(s.benchmarking, None),
                    "created_at": s.created_at.isoformat() if s.created_at else None
                }
                for s in sessions
            ],
        },
        "hiring": {
            "hiring_score": intelligence_report.overall_score if intelligence_report else hiring_score,
            "recommendation": intelligence_report.recommendation if intelligence_report else _recommendation_label(hiring_score),
            "resume_weight": round(0.35 * resume_score, 1),
            "interview_weight": round(0.40 * interview_avg * 10, 1),
            "credibility_weight": round(0.25 * credibility_score, 1),
            "report": {
                "id": intelligence_report.id,
                "overall_score": intelligence_report.overall_score,
                "technical_score": intelligence_report.technical_score,
                "behavioral_score": intelligence_report.behavioral_score,
                "credibility_score": intelligence_report.credibility_score,
                "resume_score": intelligence_report.resume_score,
                "recommendation": intelligence_report.recommendation,
                "executive_summary": intelligence_report.executive_summary,
                "source": intelligence_report.source,
                "status": intelligence_report.status,
            } if intelligence_report else None,
        },
    }


@router.post("/intelligence/compare")
def intelligence_compare(
    req: CompareReq,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Compare two or more candidates side-by-side."""
    if current_user.role not in ("hr", "manager", "admin"):
        raise HTTPException(status_code=403, detail="HR/manager access required")

    reports = []
    for cid in req.candidate_ids:
        try:
            # Reuse the report logic inline
            candidate = db.get(User, cid)
            if not candidate:
                continue

            from src.models import CandidateApplication, ApplicationAIAnalysis
            app = db.exec(
                select(CandidateApplication).where(CandidateApplication.candidate_user_id == cid).order_by(CandidateApplication.application_date.desc())
            ).first()
            analysis = db.exec(select(ApplicationAIAnalysis).where(ApplicationAIAnalysis.application_id == app.id)).first() if app else None

            sessions = db.exec(select(InterviewSession).where(InterviewSession.user_id == cid).order_by(InterviewSession.created_at.desc())).all()
            cred = db.exec(select(CandidateCredibilityReport).where(CandidateCredibilityReport.candidate_id == cid).order_by(CandidateCredibilityReport.created_at.desc())).first()

            interview_avg = 0
            completed = [s for s in sessions if is_successful_interview_status(s.status)]
            if completed:
                interview_avg = sum(s.avg_score or 0 for s in completed) / len(completed)

            resume_score = analysis.fit_score if analysis else 0
            credibility_score = cred.credibility_score if cred else 0
            hiring_score = _compute_hiring_score(resume_score, interview_avg * 10, credibility_score)

            reports.append({
                "candidate_id": cid,
                "candidate_name": candidate.username,
                "target_role": candidate.target_role,
                "resume_score": resume_score,
                "interview_score": round(interview_avg * 10, 1),
                "credibility_score": credibility_score,
                "hiring_score": hiring_score,
                "recommendation": _recommendation_label(hiring_score),
                "strengths": json.loads(analysis.strengths) if analysis and analysis.strengths else [],
                "weaknesses": json.loads(analysis.weaknesses) if analysis and analysis.weaknesses else [],
                "supported_claims": json.loads(cred.supported_claims) if cred and cred.supported_claims else [],
                "weak_claims": json.loads(cred.weak_claims) if cred and cred.weak_claims else [],
                "followup_topics": json.loads(cred.followup_topics) if cred and cred.followup_topics else [],
                "session_count": len(sessions),
            })
        except Exception as e:
            reports.append({"candidate_id": cid, "error": str(e)})

    return {"comparison": reports}


@router.post("/intelligence/{session_id}/advance")
def intelligence_advance_candidate(
    session_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Advance a candidate to the next stage (HR only)."""
    if current_user.role not in ("hr", "admin"):
        raise HTTPException(status_code=403, detail="HR admin access required")

    session = db.get(InterviewSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    from src.models import CandidateApplication
    app = db.get(CandidateApplication, session.application_id) if session.application_id else None

    if app and app.status == "Under Review":
        app.status = "Shortlisted"
        db.add(app)
        db.commit()
        return {"success": True, "message": "Candidate advanced to Shortlisted", "status": app.status}

    if app and app.status == "Applied":
        app.status = "Under Review"
        db.add(app)
        db.commit()
        return {"success": True, "message": "Candidate advanced to Under Review", "status": app.status}

    return {"success": True, "message": f"Candidate already at {app.status if app else 'unknown'} stage", "status": app.status if app else "unknown"}


@router.post("/intelligence/{session_id}/reject")
def intelligence_reject_candidate(
    session_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Reject a candidate (HR only)."""
    if current_user.role not in ("hr", "admin"):
        raise HTTPException(status_code=403, detail="HR admin access required")

    session = db.get(InterviewSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    from src.models import CandidateApplication
    app = db.get(CandidateApplication, session.application_id) if session.application_id else None

    if app:
        app.status = "Rejected"
        db.add(app)
        db.commit()
        return {"success": True, "message": "Candidate rejected", "status": "Rejected"}

    return {"success": True, "message": "No application found, but recorded as rejected"}


@router.get("/intelligence/top-candidates")
def intelligence_top_candidates(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Top 5/10 candidates by various metrics."""
    if current_user.role not in ("hr", "manager", "admin"):
        raise HTTPException(status_code=403, detail="HR/manager access required")

    from src.models import CandidateApplication, ApplicationAIAnalysis

    sessions = db.exec(
        select(InterviewSession).where(InterviewSession.status.in_(list(SUCCESSFUL_INTERVIEW_STATUSES))).order_by(InterviewSession.created_at.desc())
    ).all()

    candidates_data = []
    seen = set()
    for session in sessions:
        uid = session.user_id
        if uid in seen:
            continue
        seen.add(uid)
        user = db.get(User, uid)
        if not user:
            continue

        app = db.exec(select(CandidateApplication).where(CandidateApplication.candidate_user_id == uid).order_by(CandidateApplication.application_date.desc())).first()
        analysis = db.exec(select(ApplicationAIAnalysis).where(ApplicationAIAnalysis.application_id == app.id)).first() if app else None
        cred = db.exec(select(CandidateCredibilityReport).where(CandidateCredibilityReport.candidate_id == uid)).first()

        interview_avg = session.avg_score or 0
        resume_score = analysis.fit_score if analysis else 0
        credibility_score = cred.credibility_score if cred else 0
        hiring_score = _compute_hiring_score(resume_score, interview_avg * 10, credibility_score)

        candidates_data.append({
            "candidate_id": uid,
            "candidate_name": user.username,
            "hiring_score": hiring_score,
            "credibility_score": credibility_score,
            "interview_score": round(interview_avg * 10, 1),
            "resume_score": resume_score,
            "recommendation": _recommendation_label(hiring_score),
        })

    candidates_data.sort(key=lambda r: r["hiring_score"], reverse=True)

    return {
        "top_5": candidates_data[:5],
        "top_10": candidates_data[:10],
        "highest_credibility": sorted(candidates_data, key=lambda r: r["credibility_score"], reverse=True)[:5],
        "highest_interview_score": sorted(candidates_data, key=lambda r: r["interview_score"], reverse=True)[:5],
        "highest_overall": candidates_data[:5],
    }


@router.get("/intelligence/followup-questions/{session_id}")
def intelligence_followup_questions(
    session_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate follow-up questions from credibility analysis for the next interview round."""
    if current_user.role not in ("hr", "manager", "admin"):
        raise HTTPException(status_code=403, detail="HR/manager access required")

    cred = db.exec(
        select(CandidateCredibilityReport).where(CandidateCredibilityReport.session_id == session_id)
    ).first()

    if not cred:
        return {"followup_questions": [], "message": "No credibility data available for this session"}

    followup_topics = json.loads(cred.followup_topics) if cred.followup_topics else []
    weak_claims = json.loads(cred.weak_claims) if cred.weak_claims else []
    missing_evidence = json.loads(cred.missing_evidence) if cred.missing_evidence else []

    questions = list(followup_topics)

    for wc in weak_claims:
        claim = wc.get("claim", "") if isinstance(wc, dict) else wc
        if claim and claim not in questions:
            questions.append(f"Can you provide more detail about your experience with {claim}?")

    for me in missing_evidence:
        claim = me.get("claim", "") if isinstance(me, dict) else me
        if claim and claim not in questions:
            questions.append(f"Please elaborate on: {claim}")

    return {"followup_questions": questions, "source": cred.source}


@router.post("/transcribe")
async def transcribe_audio(
    audio_file: UploadFile = File(...),
    duration_seconds: Optional[float] = Form(default=None),
    request_id: Optional[str] = Form(default=None),
    current_user: User = Depends(get_current_user),
):
    """Transcribe an audio file using Groq Whisper."""
    import tempfile

    from src.services.transcription_service import transcribe_audio_metadata

    _log_interview_event(
        "transcription_start",
        current_user.id,
        None,
        None,
        filename=audio_file.filename,
        duration_seconds=duration_seconds,
        request_id=request_id,
    )

    suffix = ".webm"
    if audio_file.filename:
        _, ext = os.path.splitext(audio_file.filename)
        if ext:
            suffix = ext

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await audio_file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        cache_key = hashlib.sha256(content).hexdigest()[:16]
        logger.info(
            "transcription_request_received request_id=%s filename=%s content_type=%s suffix=%s file_size_bytes=%s client_duration_seconds=%s cache_key=%s cache_hit=false",
            request_id,
            audio_file.filename,
            audio_file.content_type,
            suffix,
            len(content),
            duration_seconds,
            cache_key,
        )
        metadata = transcribe_audio_metadata(
            tmp_path,
            mime_type=audio_file.content_type,
            client_duration_seconds=duration_seconds,
            request_cache_key=cache_key,
        )
        if duration_seconds is not None and metadata.get("duration") is None:
            metadata["duration"] = duration_seconds
        metadata["request_id"] = request_id
        logger.info(
            "transcription_response_ready request_id=%s cache_key=%s transcript_chars=%s processing_time_ms=%s",
            request_id,
            cache_key,
            len(metadata.get("transcript") or ""),
            metadata.get("processing_time_ms"),
        )
        _log_interview_event(
            "transcription_complete",
            current_user.id,
            None,
            None,
            transcript_chars=len(metadata.get("transcript") or ""),
            processing_time_ms=metadata.get("processing_time_ms"),
            request_id=request_id,
        )
        return metadata
    except RuntimeError as e:
        logger.error(
            "transcription_endpoint_failed request_id=%s filename=%s content_type=%s suffix=%s file_size_bytes=%s client_duration_seconds=%s reason=%s",
            request_id,
            audio_file.filename,
            audio_file.content_type,
            suffix,
            len(content),
            duration_seconds,
            e,
        )
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

@router.post("/{session_id}/abandon")
def abandon_interview(
    session_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    rec = db.exec(select(InterviewSession).where(InterviewSession.session_token == session_id)).first()
    if not rec or rec.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found.")
    if rec.status != INTERVIEW_STATUS_ACTIVE:
        raise HTTPException(status_code=400, detail=f"Cannot abandon session. Current status is {rec.status}.")

    rec.status = INTERVIEW_STATUS_CANCELLED
    rec.cancellation_reason = "candidate_exit"
    
    db.add(rec)
    db.commit()

    if session_id in _sessions:
        del _sessions[session_id]

    return {"status": "cancelled", "message": "Interview abandoned."}

@router.post("/{session_id}/complete")
def complete_interview(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    completion_started = time.perf_counter()
    completion_start_iso = _utc_iso()
    rec = db.exec(select(InterviewSession).where(InterviewSession.session_token == session_id)).first()
    if not rec or rec.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found.")
    if rec.status != INTERVIEW_STATUS_ACTIVE:
        raise HTTPException(status_code=400, detail=f"Cannot complete session. Current status is {rec.status}.")

    import json
    msgs = json.loads(rec.messages) if rec.messages else []
    if not has_completed_required_turns(msgs):
        counts = completed_turns_by_phase(msgs)
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Interview cannot be completed until all deterministic phases are finished.",
                "required_turns": PHASE_TURN_TARGETS,
                "completed_turns": counts,
            },
        )
    scores = [m["score"] for m in msgs if m.get("role") == "feedback" and m.get("score") is not None]
    if scores:
        rec.avg_score = sum(scores) / len(scores)

    db.add(rec)
    db.commit()

    _enqueue_hiring_intelligence_if_needed(db, background_tasks, rec)

    if session_id in _sessions:
        del _sessions[session_id]

    _log_perf("interview_manual_completion", completion_started, start_time=completion_start_iso, session_id=rec.id)
    return {"status": INTERVIEW_STATUS_ANALYZING, "avg_score": rec.avg_score, "db_id": rec.id}
