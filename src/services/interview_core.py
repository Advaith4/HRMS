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
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from src.database.connection import get_session
from src.models import CareerCoachMemory, CandidateApplication, InterviewSession, Resume, User, CandidateCredibilityReport, HRNotification, JobPosting
from src.api.dependencies import get_current_user
from src.resume_lab import analyze_resume, dumps_json, load_json_field, parse_resume
from src.services.interview_status import INTERVIEW_PHASES_V2, PHASE_SEQUENCE_V2

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/interview", tags=["interview"])

# In-memory state for active sessions (fast access during live interview)
_sessions: dict[str, dict[str, Any]] = {}

INTERVIEW_PHASES: list[dict[str, Any]] = [dict(phase) for phase in INTERVIEW_PHASES_V2]
PHASE_SEQUENCE = list(PHASE_SEQUENCE_V2)

TRAINING_MODES = {
    "adaptive": "Mix weak-area drilling with general role coverage.",
    "weak_area_only": "Spend every question on recurring weaknesses and low-scoring resume areas.",
    "domain_specific": "Prioritize domain and technical depth for the target role.",
    "behavioral_only": "Use behavioral, communication, ownership, and story-structure questions only.",
}

INTERVIEWER_PERSONAS = {
    "balanced": {
        "label": "Balanced",
        "tone": "professional, realistic, direct but supportive",
        "pressure": "medium",
        "behavior": "Ask crisp questions, press once for specificity, then coach through gaps.",
    },
    "strict": {
        "label": "Strict",
        "tone": "demanding, time-conscious, skeptical of vague answers",
        "pressure": "high",
        "behavior": "Interrupt generic answers, push for precision, and challenge weak assumptions quickly.",
    },
    "technical": {
        "label": "Technical",
        "tone": "technical, precise, skeptical of vague claims",
        "pressure": "medium-high",
        "behavior": "Challenge tradeoffs, architecture choices, debugging depth, and implementation details.",
    },
    "friendly": {
        "label": "Friendly",
        "tone": "warm, encouraging, still rigorous",
        "pressure": "low-medium",
        "behavior": "Normalize mistakes, ask guided follow-ups, and turn gaps into practice tasks.",
    },
    "behavioral": {
        "label": "Behavioral",
        "tone": "people-focused, evidence-driven",
        "pressure": "medium",
        "behavior": "Probe ownership, conflict, collaboration, ambiguity, and STAR-quality storytelling.",
    },
}

PERSONA_ALIASES = {
    "senior_engineer": "technical",
    "pressure_panel": "strict",
    "friendly_coach": "friendly",
    "behavioral_lead": "behavioral",
}


class StartReq(BaseModel):
    role: str = Field(min_length=1, max_length=100)
    difficulty: int = Field(default=5, ge=1, le=10)
    weak_areas: list[str] = Field(default_factory=list)
    training_mode: str = Field(default="adaptive", max_length=40)
    interviewer_persona: str = Field(default="balanced", max_length=40)
    domain_focus: str = Field(default="", max_length=120)


class StartFromResumeReq(BaseModel):
    role: str = Field(default="", max_length=100)
    difficulty: int = Field(default=5, ge=1, le=10)
    force_reanalyze: bool = False
    training_mode: str = Field(default="adaptive", max_length=40)
    interviewer_persona: str = Field(default="balanced", max_length=40)
    domain_focus: str = Field(default="", max_length=120)


class StartForApplicationReq(BaseModel):
    application_id: int
    difficulty: int = Field(default=5, ge=1, le=10)
    training_mode: str = Field(default="domain_specific", max_length=40)
    interviewer_persona: str = Field(default="balanced", max_length=40)


class ViolationReq(BaseModel):
    violation_type: str
    detail: str


class AnswerReq(BaseModel):
    session_id: str
    answer: str = Field(min_length=1, max_length=5000)


class CompareReq(BaseModel):
    candidate_ids: list[int] = Field(min_length=1, max_length=20)


def _latest_candidate_resume_text(db: Session, user_id: int) -> tuple[str, str]:
    resume = db.exec(select(Resume).where(Resume.user_id == user_id)).first()
    if resume:
        text = resume.current_text or resume.raw_text or ""
        if text.strip():
            return text, "resume_lab"

    application = db.exec(
        select(CandidateApplication)
        .where(CandidateApplication.candidate_user_id == user_id)
        .order_by(CandidateApplication.application_date.desc())
    ).first()
    if application and application.resume_text.strip():
        return application.resume_text, "application"

    return "", ""


def _safe_json_load(value: str | None, default):
    try:
        return json.loads(value) if value else default
    except (TypeError, json.JSONDecodeError):
        return default


def _normalize_training_mode(value: str | None) -> str:
    normalized = str(value or "adaptive").strip().lower().replace("-", "_").replace(" ", "_")
    return normalized if normalized in TRAINING_MODES else "adaptive"


def _normalize_persona(value: str | None) -> str:
    normalized = str(value or "balanced").strip().lower().replace("-", "_").replace(" ", "_")
    normalized = PERSONA_ALIASES.get(normalized, normalized)
    return normalized if normalized in INTERVIEWER_PERSONAS else "balanced"


def _question_mix_for_mode(training_mode: str) -> dict[str, float]:
    if training_mode == "weak_area_only":
        return {"weak_area": 1.0, "general": 0.0, "domain": 0.0, "behavioral": 0.0}
    if training_mode == "domain_specific":
        return {"weak_area": 0.3, "general": 0.0, "domain": 0.7, "behavioral": 0.0}
    if training_mode == "behavioral_only":
        return {"weak_area": 0.0, "general": 0.0, "domain": 0.0, "behavioral": 1.0}
    return {"weak_area": 0.6, "general": 0.4, "domain": 0.0, "behavioral": 0.0}


def _phase_meta(phase_name: str) -> dict[str, Any]:
    for phase in INTERVIEW_PHASES:
        if phase["name"] == phase_name:
            return phase
    return INTERVIEW_PHASES[0]


def _phase_index(phase_name: str) -> int:
    try:
        return PHASE_SEQUENCE.index(phase_name)
    except ValueError:
        return 0


def _should_end_interview_early(answer_count: int, scores: list[int], resume_score: float | None = None) -> bool:
    if answer_count >= 10:
        return True
    if answer_count < 6 or len(scores) < 3:
        return False
    recent = scores[-3:]
    avg = sum(recent) / len(recent)
    if max(recent) - min(recent) <= 1 and (avg >= 8 or avg <= 4):
        return True
    return False


def _pick_next_phase(current_phase: str, answer_count: int, scores: list[int], resume_score: float | None = None) -> str:
    if current_phase == "Final Evaluation":
        return "Final Evaluation"
    if _should_end_interview_early(answer_count, scores, resume_score):
        return "Final Evaluation"

    if answer_count < 3:
        return "Resume Validation"
    if answer_count < 8:
        return "Technical Assessment"
    if answer_count < 10:
        return "Behavioral Assessment"

    idx = _phase_index(current_phase)
    next_idx = min(idx + 1, len(PHASE_SEQUENCE) - 1)
    return PHASE_SEQUENCE[next_idx]


def _ensure_intro_question(question: str, role: str) -> str:
    text = str(question or "").strip()
    lowered = text.lower()
    if "tell me about yourself" in lowered:
        return text
    return (
        f"Tell me about yourself and why you're a good fit for this {role} role. "
        "Keep it concise, specific, and grounded in your actual work."
    )


def _get_or_create_memory(db: Session, user_id: int) -> CareerCoachMemory:
    memory = db.exec(select(CareerCoachMemory).where(CareerCoachMemory.user_id == user_id)).first()
    if memory:
        return memory
    now = datetime.utcnow()
    memory = CareerCoachMemory(user_id=user_id, created_at=now, updated_at=now)
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def _memory_snapshot(memory: CareerCoachMemory | None) -> dict[str, Any]:
    if not memory:
        return {
            "recurring_weak_areas": [],
            "score_trend": [],
            "session_history": [],
            "session_count": 0,
            "avg_answer_score": None,
        }
    return {
        "recurring_weak_areas": _safe_json_load(memory.recurring_weak_areas, [])[:8],
        "score_trend": _safe_json_load(memory.score_trend, [])[-12:],
        "session_history": _safe_json_load(memory.session_history, [])[-6:],
        "session_count": memory.session_count,
        "avg_answer_score": memory.avg_answer_score,
        "preferred_persona": _normalize_persona(memory.preferred_persona),
        "preferred_training_mode": memory.preferred_training_mode,
    }


def _save_messages(db: Session, session_token: str, messages: list, avg_score: float | None = None):
    """Persist updated message list to DB."""
    rec = db.exec(select(InterviewSession).where(InterviewSession.session_token == session_token)).first()
    if rec:
        rec.messages = json.dumps(messages)
        rec.avg_score = avg_score
        rec.updated_at = datetime.utcnow()
        db.add(rec)
        db.commit()


def _save_session_state(db: Session, session_token: str, state: dict[str, Any], avg_score: float | None = None) -> None:
    """Persist live adaptive interview state to DB."""
    rec = db.exec(select(InterviewSession).where(InterviewSession.session_token == session_token)).first()
    if not rec:
        return
    rec.messages = json.dumps(state.get("messages", []))
    rec.avg_score = avg_score
    rec.difficulty = int(state.get("difficulty", rec.difficulty))
    rec.training_mode = _normalize_training_mode(state.get("training_mode", rec.training_mode))
    rec.interviewer_persona = _normalize_persona(state.get("interviewer_persona", rec.interviewer_persona))
    rec.personalization_context = json.dumps(state.get("personalization_context", {}))
    rec.updated_at = datetime.utcnow()
    db.add(rec)
    db.commit()


def _unique_strings(items: list[str], limit: int = 8) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        cleaned = " ".join(str(item).strip().split())
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            output.append(cleaned)
        if len(output) >= limit:
            break
    return output


def _recurring_area_label(area: str) -> str:
    text = " ".join(str(area or "").split())
    if ":" in text:
        return text.split(":", 1)[0].strip()
    if " section " in text.lower():
        return text.split(" section ", 1)[0].strip().title()
    return text[:120] or "General interview depth"


def _notify_hr(session: Session, title: str, message: str, event_type: str, related_id: Optional[int] = None):
    hr_users = session.exec(select(User).where(User.role.in_(["hr", "admin"]))).all()
    for u in hr_users:
        notif = HRNotification(
            user_id=u.id,
            title=title,
            message=message,
            event_type=event_type,
            related_id=related_id,
            is_read=False
        )
        session.add(notif)


def _upsert_weak_area_counts(existing: list[dict[str, Any]], areas: list[str]) -> list[dict[str, Any]]:
    now = datetime.utcnow().isoformat()
    by_area = {str(item.get("area", "")).lower(): dict(item) for item in existing if item.get("area")}
    for area in areas:
        label = _recurring_area_label(area)
        key = label.lower()
        item = by_area.get(key, {"area": label, "count": 0, "last_seen": now})
        item["count"] = int(item.get("count", 0) or 0) + 1
        item["last_seen"] = now
        by_area[key] = item
    return sorted(by_area.values(), key=lambda item: (-int(item.get("count", 0) or 0), item.get("area", "")))[:12]


def _update_coach_memory(
    db: Session,
    user_id: int,
    state: dict[str, Any],
    score: int | None = None,
) -> CareerCoachMemory:
    memory = _get_or_create_memory(db, user_id)
    context = state.get("personalization_context") or {}
    weak_areas = context.get("weak_areas", [])
    focus_area = context.get("current_focus_area")
    if focus_area:
        weak_areas = [*weak_areas, focus_area]

    raw_eval = context.get("evaluation", {})
    normalized_eval = _normalize_and_repair_evaluation(raw_eval, focus_area)
    recurring = _upsert_weak_area_counts(_safe_json_load(memory.recurring_weak_areas, []), weak_areas)
    trend = _safe_json_load(memory.score_trend, [])
    if score is not None:
        trend.append({
            "date": datetime.utcnow().isoformat(),
            "score": score,
            "difficulty": state.get("difficulty"),
            "focus_area": focus_area,
            "training_mode": context.get("training_mode", state.get("training_mode", "adaptive")),
            "persona": context.get("interviewer_persona", state.get("interviewer_persona", "balanced")),
        })
    trend = trend[-60:]

    session_history = _safe_json_load(memory.session_history, [])
    summary = {
        "session_token": state.get("session_token"),
        "date": datetime.utcnow().isoformat(),
        "role": state.get("role"),
        "difficulty": state.get("difficulty"),
        "training_mode": context.get("training_mode", state.get("training_mode", "adaptive")),
        "persona": context.get("interviewer_persona", state.get("interviewer_persona", "balanced")),
        "answers": len(state.get("answers", [])),
        "latest_score": score,
        "focus_area": focus_area,
    }
    if not session_history or session_history[-1].get("session_token") != summary["session_token"]:
        session_history.append(summary)
    else:
        session_history[-1].update(summary)
    session_history = session_history[-30:]

    scored = [int(item["score"]) for item in trend if isinstance(item.get("score"), int)]
    memory.recurring_weak_areas = json.dumps(recurring)
    memory.score_trend = json.dumps(trend)
    memory.session_history = json.dumps(session_history)
    memory.session_count = len({item.get("session_token") for item in session_history if item.get("session_token")})
    memory.avg_answer_score = round(sum(scored) / len(scored), 2) if scored else memory.avg_answer_score
    memory.preferred_persona = _normalize_persona(context.get("interviewer_persona", memory.preferred_persona))
    memory.preferred_training_mode = context.get("training_mode", memory.preferred_training_mode)
    memory.updated_at = datetime.utcnow()
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def _derive_section_scores(analysis: dict[str, Any]) -> dict[str, int]:
    explicit_scores = analysis.get("section_scores")
    if isinstance(explicit_scores, dict) and explicit_scores:
        scores: dict[str, int] = {}
        for key, value in explicit_scores.items():
            try:
                numeric = int(value or 0)
            except (TypeError, ValueError):
                numeric = 0
            scores[str(key).lower()] = max(0, min(100, numeric))
        return scores

    breakdown = analysis.get("breakdown") or {}
    base = int(sum(int(breakdown.get(key, 60) or 60) for key in ("impact", "clarity", "structure", "ats")) / 4)
    scores: dict[str, int] = {}
    for section in analysis.get("sections", []):
        name = str(section.get("section") or "resume").lower()
        issue_count = len(section.get("issues") or [])
        scores[name] = max(35, min(95, base - issue_count * 9))
    return scores


def _derive_weak_areas(analysis: dict[str, Any], section_scores: dict[str, int]) -> list[str]:
    weak_areas: list[str] = []
    low_sections = sorted(
        ((name, score) for name, score in section_scores.items() if score < 72),
        key=lambda item: item[1],
    )
    for name, score in low_sections:
        weak_areas.append(f"{name.title()} section is low-scoring at {score}/100 and needs interview drilling.")

    for section in analysis.get("sections", []):
        section_name = str(section.get("section") or "resume").title()
        for issue in (section.get("issues") or [])[:2]:
            problem = issue.get("problem") or "Needs stronger evidence and specificity"
            original = issue.get("original") or ""
            weak_areas.append(f"{section_name}: {problem}. Resume line: {original[:160]}")

    if not weak_areas and analysis.get("breakdown"):
        weakest_metric = min(analysis["breakdown"].items(), key=lambda item: int(item[1] or 0))
        weak_areas.append(f"{weakest_metric[0].title()} is the weakest resume dimension at {weakest_metric[1]}/100.")

    return _unique_strings(weak_areas, limit=6)


def _build_resume_context(resume_text: str, analysis: dict[str, Any], role: str) -> dict[str, Any]:
    parsed = parse_resume(resume_text)
    return {
        "role": role,
        "resume_score": analysis.get("score", 0),
        "summary": parsed.get("summary", "")[:700],
        "skills": (parsed.get("skills") or [])[:15],
        "experience_samples": (parsed.get("experience") or [])[:5],
        "project_samples": (parsed.get("projects") or [])[:4],
    }


def _build_personalization_context(
    resume_text: str,
    analysis: dict[str, Any],
    role: str,
    difficulty: int,
    training_mode: str,
    interviewer_persona: str,
    domain_focus: str,
    coach_memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    section_scores = _derive_section_scores(analysis)
    weak_areas = _derive_weak_areas(analysis, section_scores)
    training_mode = _normalize_training_mode(training_mode)
    interviewer_persona = _normalize_persona(interviewer_persona)
    return {
        "source": "resume_lab",
        "role": role,
        "difficulty": difficulty,
        "training_mode": training_mode,
        "training_mode_description": TRAINING_MODES[training_mode],
        "interviewer_persona": interviewer_persona,
        "persona_profile": INTERVIEWER_PERSONAS[interviewer_persona],
        "domain_focus": domain_focus,
        "weak_areas": weak_areas,
        "section_scores": section_scores,
        "resume_context": _build_resume_context(resume_text, analysis, role),
        "resume_score": analysis.get("score", 0),
        "question_mix": _question_mix_for_mode(training_mode),
        "focus_counts": {"weak_area": 0, "general": 0, "domain": 0, "behavioral": 0},
        "coach_memory": coach_memory or {},
    }


def _normalize_focus_type(value: Any, fallback: str) -> str:
    text = str(value or fallback or "").lower()
    if "behavior" in text:
        return "behavioral"
    if "domain" in text or "technical" in text:
        return "domain"
    if "weak" in text or "simplify" in text:
        return "weak_area"
    return "general"


def _choose_focus_mode(state: dict[str, Any]) -> str:
    context = state.get("personalization_context") or {}
    training_mode = _normalize_training_mode(context.get("training_mode", state.get("training_mode", "adaptive")))
    if training_mode == "weak_area_only":
        return "weak_area"
    if training_mode == "domain_specific":
        return "domain_specific"
    if training_mode == "behavioral_only":
        return "behavioral_only"
    if not context.get("weak_areas"):
        return "general"
    counts = context.setdefault("focus_counts", {"weak_area": 0, "general": 0, "domain": 0, "behavioral": 0})
    weak_count = int(counts.get("weak_area", 0) or 0)
    general_count = int(counts.get("general", 0) or 0)
    total = weak_count + general_count
    if total == 0 or (weak_count / total) < 0.6:
        return "weak_area"
    return "general"


def _format_feedback_message(evaluation: dict[str, Any], focus_area: str = "") -> dict[str, Any]:
    # Expect a normalized evaluation schema and produce a UI-friendly feedback map.
    score = evaluation.get("score", "--")
    confidence = evaluation.get("confidence")
    what_went_well = [str(x) for x in (evaluation.get("what_went_well") or [])][:3]
    what_was_missing = [str(x) for x in (evaluation.get("what_was_missing") or [])][:3]
    how_to_improve = [str(x) for x in (evaluation.get("how_to_improve") or [])][:3]
    next_focus = str(evaluation.get("next_focus") or focus_area or "specific evidence")
    final_verdict = evaluation.get("final_verdict")
    verdict_explanation = str(evaluation.get("verdict_explanation") or "")

    text_lines = [f"Score: {score}/10"]
    if confidence is not None:
        text_lines.append(f"Evaluator confidence: {confidence}/10")
    text_lines.append(f"What went well: {what_went_well[0] if what_went_well else 'You addressed the prompt and attempted a structured response.'}")
    text_lines.append(f"What was missing: {what_was_missing[0] if what_was_missing else 'More concrete evidence, metrics, or tradeoffs were needed.'}")
    if len(what_was_missing) > 1:
        text_lines.append(f"Other gaps: {', '.join(what_was_missing[1:])}")
    if how_to_improve:
        text_lines.append(f"How to improve: {how_to_improve[0]}")
    text_lines.append(f"Next focus: {next_focus}")
    if final_verdict:
        text_lines.append(f"Verdict: {final_verdict} - {verdict_explanation}")

    feedback = {
        "score": score,
        "confidence": confidence,
        "what_went_well": what_went_well,
        "what_was_missing": what_was_missing,
        "how_to_improve": how_to_improve,
        "next_focus": next_focus,
        "final_verdict": final_verdict,
        "verdict_explanation": verdict_explanation,
        "text": "\n".join([line for line in text_lines if line]),
    }
    return feedback


def _normalize_and_repair_evaluation(raw_eval: Any, focus_area: str = "") -> dict[str, Any]:
    """Normalize evaluator output into the strict schema, repairing missing or malformed fields."""
    eval_obj: dict[str, Any] = {}
    # If raw_eval is a string containing JSON, try to load it
    if isinstance(raw_eval, str):
        try:
            eval_obj = json.loads(raw_eval)
        except Exception:
            # Try to extract JSON blob
            import re

            m = re.search(r"\{.*\}", raw_eval, re.DOTALL)
            if m:
                try:
                    eval_obj = json.loads(m.group())
                except Exception:
                    eval_obj = {}
            else:
                eval_obj = {}
    elif isinstance(raw_eval, dict):
        eval_obj = dict(raw_eval)
    else:
        eval_obj = {}

    def _get_list(key, legacy_keys=()):
        for k in (key, *legacy_keys):
            v = eval_obj.get(k)
            if isinstance(v, list):
                return [str(x).strip() for x in v if x is not None]
            if isinstance(v, str) and v.strip():
                # split into sentences as fallback
                parts = [s.strip() for s in re.split(r"[\n\.]+", v) if s.strip()]
                if parts:
                    return parts
        return []

    import re

    # Score and confidence
    try:
        score = int(eval_obj.get("score", eval_obj.get("overall_score", 5)))
    except Exception:
        score = 5
    score = max(0, min(10, score))

    try:
        confidence = int(eval_obj.get("confidence", round(score)))
    except Exception:
        confidence = max(0, min(10, int(score)))

    what_went_well = _get_list("what_went_well", ("strengths", "strength"))[:3]
    what_was_missing = _get_list("what_was_missing", ("weaknesses", "weakness"))[:3]
    how_to_improve = _get_list("how_to_improve", ("improvement", "improvements"))[:3]
    next_focus = str(eval_obj.get("next_focus", eval_obj.get("next_answer_focus", focus_area or "specific evidence")))
    final_verdict = eval_obj.get("final_verdict") or None
    verdict_explanation = str(eval_obj.get("verdict_explanation", eval_obj.get("verdict_explanation", "")))

    # Ensure minimum list lengths with sensible, targeted fillers
    if len(what_went_well) < 3:
        fillers = [
            "Provided a direct attempt to answer the question",
            "Used domain-relevant terminology",
            "Outlined a concrete decision or step taken",
        ]
        for f in fillers:
            if len(what_went_well) >= 3:
                break
            if f not in what_went_well:
                what_went_well.append(f)

    if len(what_was_missing) < 3:
        fillers = [
            "Missing a concrete metric or measurable result",
            "Needed clearer tradeoffs or constraints",
            "Lacked precise ownership or role clarity",
        ]
        for f in fillers:
            if len(what_was_missing) >= 3:
                break
            if f not in what_was_missing:
                what_was_missing.append(f)

    if len(how_to_improve) < 3:
        # If a single long improvement string exists, split it
        if isinstance(eval_obj.get("how_to_improve"), str) and len(how_to_improve) < 3:
            parts = [s.strip() for s in re.split(r"[\n\.]+", eval_obj.get("how_to_improve")) if s.strip()]
            for p in parts:
                if len(how_to_improve) >= 3:
                    break
                how_to_improve.append(p)
        fillers = [
            "Use one concrete example with the decision and the result",
            "State the measurable outcome (metric or impact)",
            "Describe tradeoffs and why you chose that approach",
        ]
        for f in fillers:
            if len(how_to_improve) >= 3:
                break
            if f not in how_to_improve:
                how_to_improve.append(f)

    # Derive final verdict if missing
    if final_verdict not in ("Not Ready", "Borderline", "Ready"):
        if score < 5:
            final_verdict = "Not Ready"
            verdict_explanation = verdict_explanation or "Solidify fundamentals and focus on weak-area drills before applying."
        elif score < 7.5:
            final_verdict = "Borderline"
            verdict_explanation = verdict_explanation or "Some strong answers but inconsistent; prioritize specificity and measurable outcomes."
        else:
            final_verdict = "Ready"
            verdict_explanation = verdict_explanation or "Consistent depth and clarity — you're approaching interview-ready quality."

    normalized = {
        "score": score,
        "confidence": confidence,
        "what_went_well": what_went_well,
        "what_was_missing": what_was_missing,
        "how_to_improve": how_to_improve,
        "next_focus": next_focus,
        "final_verdict": final_verdict,
        "verdict_explanation": verdict_explanation,
    }
    return normalized


def _state_from_record(rec: InterviewSession) -> dict[str, Any]:
    context = _safe_json_load(rec.personalization_context, {})
    if isinstance(context, dict) and context.get("interviewer_persona"):
        context["interviewer_persona"] = _normalize_persona(context.get("interviewer_persona"))
    if isinstance(context, dict) and not context.get("current_phase"):
        context["current_phase"] = "Resume Validation"
        context["phase_history"] = context.get("phase_history") or ["Resume Validation"]
    msgs = _safe_json_load(rec.messages, [])
    last_ai = next((m["content"] for m in reversed(msgs) if m.get("role") == "ai"), "")

    questions: list[str] = []
    answers: list[str] = []
    scores: list[int] = []
    for i, m in enumerate(msgs):
        if m.get("role") == "user":
            answers.append(m.get("content", ""))
            for j in range(i - 1, -1, -1):
                if msgs[j].get("role") == "ai":
                    questions.append(msgs[j].get("content", ""))
                    break
        if m.get("role") == "feedback" and m.get("score") is not None:
            scores.append(int(m["score"]))

    return {
        "role": rec.role,
        "difficulty": rec.difficulty,
        "weak_areas": context.get("weak_areas", []),
        "questions": questions,
        "answers": answers,
        "scores": scores,
        "messages": msgs,
        "current_question": last_ai,
        "db_id": rec.id,
        "session_token": rec.session_token,
        "user_id": rec.user_id,
        "training_mode": rec.training_mode,
        "interviewer_persona": _normalize_persona(rec.interviewer_persona),
        "personalization_context": context,
    }


def _generate_daily_plan(memory: CareerCoachMemory, resume_analysis: dict[str, Any] | None = None) -> dict[str, Any]:
    snapshot = _memory_snapshot(memory)
    recurring = snapshot.get("recurring_weak_areas", [])
    trend = snapshot.get("score_trend", [])
    latest_score = trend[-1]["score"] if trend and isinstance(trend[-1].get("score"), int) else None
    weakest_area = recurring[0]["area"] if recurring else "resume storytelling"

    resume_score = resume_analysis.get("score") if resume_analysis else None
    tasks = [
        {
            "title": f"10-minute weak-area drill: {weakest_area}",
            "type": "interview_practice",
            "duration_minutes": 10,
            "why": "This is your most recurring interview gap across recent sessions.",
        },
        {
            "title": "Rewrite one answer using STAR + metrics",
            "type": "communication",
            "duration_minutes": 12,
            "why": "Structured stories make resume claims feel credible under pressure.",
        },
        {
            "title": "Run one resume-aware mock interview",
            "type": "mock_interview",
            "duration_minutes": 15,
            "why": "Short daily reps compound faster than occasional long practice.",
        },
    ]

    if latest_score is not None and latest_score <= 4:
        tasks.insert(0, {
            "title": "Recovery drill: explain the missed concept from first principles",
            "type": "foundation",
            "duration_minutes": 8,
            "why": "Your last answer struggled, so today starts with a simpler base layer.",
        })
    elif latest_score is not None and latest_score >= 8:
        tasks.insert(0, {
            "title": "Depth drill: add tradeoffs, constraints, and edge cases",
            "type": "advanced_depth",
            "duration_minutes": 10,
            "why": "Your last answer was strong; the next gain is senior-level depth.",
        })

    if resume_score is not None and resume_score < 70:
        tasks.append({
            "title": "Apply one Resume Lab fix before interviewing",
            "type": "resume_improvement",
            "duration_minutes": 7,
            "why": "A stronger resume gives the interviewer better evidence to probe.",
        })

    plan = {
        "date": datetime.utcnow().date().isoformat(),
        "headline": "Today, train the weakness that keeps repeating.",
        "coach_note": f"Focus on {weakest_area}. Keep answers concise, specific, and evidence-backed.",
        "target_score": min(10, max(6, int((latest_score or 5) + 1))),
        "tasks": tasks[:4],
        "based_on": {
            "session_count": snapshot.get("session_count", 0),
            "avg_answer_score": snapshot.get("avg_answer_score"),
            "recurring_weak_areas": recurring[:5],
        },
    }
    memory.daily_plan = json.dumps(plan)
    memory.updated_at = datetime.utcnow()
    return plan


