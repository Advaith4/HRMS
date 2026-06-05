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

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from src.database.connection import get_session
from src.models import CareerCoachMemory, CandidateApplication, InterviewSession, Resume, User, CandidateCredibilityReport, HRNotification, JobPosting
from src.api.dependencies import get_current_user
from src.resume_lab import analyze_resume, dumps_json, load_json_field, parse_resume

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/interview", tags=["interview"])

# In-memory state for active sessions (fast access during live interview)
_sessions: dict[str, dict[str, Any]] = {}

INTERVIEW_PHASES: list[dict[str, Any]] = [
    {
        "name": "Introduction",
        "goal": "Set context, confirm target role fit, and establish communication baseline.",
        "focus": "Candidate background, role motivation, and concise self-positioning.",
        "min_turns": 1,
    },
    {
        "name": "Resume Deep Dive",
        "goal": "Validate resume claims with concrete examples and measurable outcomes.",
        "focus": "Projects, ownership, decisions, and impact.",
        "min_turns": 1,
    },
    {
        "name": "Core Technical Round",
        "goal": "Probe technical depth, tradeoffs, and implementation reasoning.",
        "focus": "Architecture, debugging, APIs, data structures, and systems thinking.",
        "min_turns": 2,
    },
    {
        "name": "Problem Solving",
        "goal": "Test structured thinking under constraints and ambiguity.",
        "focus": "Approach, edge cases, complexity, and iterative refinement.",
        "min_turns": 1,
    },
    {
        "name": "Behavioral Round",
        "goal": "Assess collaboration, ownership, conflict handling, and communication maturity.",
        "focus": "STAR narratives with concrete outcomes.",
        "min_turns": 1,
    },
    {
        "name": "Pressure / Cross-questioning",
        "goal": "Stress-test consistency, clarity, and defense of prior decisions.",
        "focus": "Interruptions, pushback, and evidence-backed responses.",
        "min_turns": 1,
    },
    {
        "name": "Candidate Questions",
        "goal": "Evaluate curiosity, role understanding, and decision criteria.",
        "focus": "Questions about team, product, scope, and growth.",
        "min_turns": 1,
    },
    {
        "name": "Final Evaluation",
        "goal": "Summarize performance, strengths, gaps, and next-step readiness.",
        "focus": "Clear verdict and improvement plan.",
        "min_turns": 0,
    },
]

PHASE_SEQUENCE = [phase["name"] for phase in INTERVIEW_PHASES]

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
    if answer_count >= 15:
        return True
    if answer_count < 5:
        return False
    
    # Analyze consistency of the last 3 answers
    last_three = scores[-3:]
    avg_last_three = sum(last_three) / len(last_three)
    score_range = max(last_three) - min(last_three)
    
    # Case 1: Consistently Excellent
    if avg_last_three >= 8.0 and all(s >= 7 for s in last_three) and score_range <= 2:
        return True
        
    # Case 2: Consistently Poor
    if avg_last_three <= 4.0 and all(s <= 5 for s in last_three) and score_range <= 2:
        return True
        
    return False


def _pick_next_phase(current_phase: str, answer_count: int, scores: list[int], resume_score: float | None = None) -> str:
    if current_phase == "Final Evaluation":
        return "Final Evaluation"
    if _should_end_interview_early(answer_count, scores, resume_score):
        return "Final Evaluation"

    # Adaptive pacing: if struggling, stay longer in technical/problem rounds before pressure.
    avg_score = sum(scores) / len(scores) if scores else None
    if avg_score is not None and avg_score <= 4.5 and current_phase in {"Core Technical Round", "Problem Solving"}:
        return current_phase
    if avg_score is not None and avg_score >= 8.0 and current_phase == "Behavioral Round":
        return "Pressure / Cross-questioning"

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
        context["current_phase"] = "Introduction"
        context["phase_history"] = context.get("phase_history") or ["Introduction"]
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


@router.post("/start")
def start_interview(
    req: StartReq,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    training_mode = _normalize_training_mode(req.training_mode)
    interviewer_persona = _normalize_persona(req.interviewer_persona)
    memory = _get_or_create_memory(db, current_user.id)
    focus_mode = "weak_area" if req.weak_areas else "general"
    if training_mode == "behavioral_only":
        focus_mode = "behavioral_only"
    elif training_mode == "domain_specific":
        focus_mode = "domain_specific"
    current_phase = "Introduction"
    phase_details = _phase_meta(current_phase)

    try:
        from crew import run_interview_start

        first = run_interview_start(
            role=req.role,
            difficulty=req.difficulty,
            weak_areas=req.weak_areas,
            resume_context={},
            section_scores={},
            focus_mode=focus_mode,
            training_mode=training_mode,
            interviewer_persona=INTERVIEWER_PERSONAS[interviewer_persona],
            coach_memory=_memory_snapshot(memory),
            domain_focus=req.domain_focus,
            phase_name=current_phase,
            phase_goal=phase_details["goal"],
            phase_focus=phase_details["focus"],
        )
        if not isinstance(first, dict):
            logger.warning("run_interview_start returned non-dict payload; using fallback question.")
            first = {}
    except Exception as exc:
        logger.error("Manual interview start failed: %s", exc, exc_info=True)
        first = {
            "question": f"Tell me about yourself and why you're a good fit for this {req.role} role.",
            "focus_area": req.weak_areas[0] if req.weak_areas else "general role fit",
            "focus_type": focus_mode,
            "interviewer_signal": "I will challenge vague claims.",
            "pressure_level": INTERVIEWER_PERSONAS[interviewer_persona]["pressure"],
            "answer_expectation": "Answer in 5-10 lines with context, decisions, tradeoffs, and measurable outcome.",
        }

    question = str(first.get("question") or "").strip()
    if current_phase == "Introduction":
        question = _ensure_intro_question(question, req.role)
    answer_expectation = str(first.get("answer_expectation") or "Answer in 5-10 lines with context, decisions, tradeoffs, and measurable outcome.").strip()
    focus_type = _normalize_focus_type(first.get("focus_type"), focus_mode)
    session_token = uuid.uuid4().hex

    # Persist to DB
    first_msg = {
        "role": "ai",
        "content": question,
        "timestamp": datetime.utcnow().isoformat(),
        "focus_area": first.get("focus_area", req.weak_areas[0] if req.weak_areas else "general role fit"),
        "focus_type": focus_type,
        "interviewer_signal": first.get("interviewer_signal", ""),
        "pressure_level": first.get("pressure_level", INTERVIEWER_PERSONAS[interviewer_persona]["pressure"]),
        "answer_expectation": answer_expectation,
        "phase": current_phase,
    }
    context = {
        "source": "manual",
        "role": req.role,
        "weak_areas": req.weak_areas,
        "section_scores": {},
        "resume_context": {},
        "question_mix": _question_mix_for_mode(training_mode),
        "focus_counts": {"weak_area": 0, "general": 0, "domain": 0, "behavioral": 0},
        "training_mode": training_mode,
        "training_mode_description": TRAINING_MODES[training_mode],
        "interviewer_persona": interviewer_persona,
        "persona_profile": INTERVIEWER_PERSONAS[interviewer_persona],
        "domain_focus": req.domain_focus,
        "coach_memory": _memory_snapshot(memory),
        "current_focus_area": first_msg["focus_area"],
        "current_phase": current_phase,
        "phase_history": [current_phase],
    }
    db_session = InterviewSession(
        user_id=current_user.id,
        session_token=session_token,
        role=req.role,
        difficulty=req.difficulty,
        training_mode=training_mode,
        interviewer_persona=interviewer_persona,
        messages=json.dumps([first_msg]),
        personalization_context=json.dumps(context),
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    # Keep live state in memory
    _sessions[session_token] = {
        "role": req.role,
        "difficulty": req.difficulty,
        "weak_areas": req.weak_areas,
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
    persona_profile = INTERVIEWER_PERSONAS.get(interviewer_persona, INTERVIEWER_PERSONAS["balanced"])
    session_intro = (
        f"This mock interview simulates a {persona_profile.get('label', 'Balanced')} interviewer under {first_msg.get('pressure_level', persona_profile.get('pressure', 'medium'))} pressure. "
        "Treat answers like a live screening: be concise, cite specific decisions, and quantify outcomes where possible."
    )

    return {
        "session_id": session_token,
        "question": question,
        "db_id": db_session.id,
        "focus_area": first_msg["focus_area"],
        "focus_type": focus_type,
        "interviewer_signal": first_msg["interviewer_signal"],
        "pressure_level": first_msg["pressure_level"],
        "answer_expectation": answer_expectation,
        "training_mode": training_mode,
        "interviewer_persona": interviewer_persona,
        "persona": persona_profile,
        "coach_memory": context["coach_memory"],
        "session_intro": session_intro,
        "phase": current_phase,
        "phase_goal": phase_details["goal"],
    }


@router.post("/start-from-resume")
def start_interview_from_resume(
    req: StartFromResumeReq,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    training_mode = _normalize_training_mode(req.training_mode)
    interviewer_persona = _normalize_persona(req.interviewer_persona)
    memory = _get_or_create_memory(db, current_user.id)
    resume = db.exec(select(Resume).where(Resume.user_id == current_user.id)).first()
    resume_text, resume_source = _latest_candidate_resume_text(db, current_user.id)
    if not resume_text:
        raise HTTPException(status_code=400, detail="Please upload a resume or apply to a job with your resume before starting a resume-aware interview.")

    if len(resume_text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Stored resume is too short for personalized interview training.")

    role = req.role.strip() or current_user.target_role or "Software Engineer"
    analysis = load_json_field(resume.last_analysis, None) if resume else None
    if req.force_reanalyze or not analysis:
        analysis = analyze_resume(resume_text, role)
        if resume:
            resume.last_analysis = dumps_json(analysis)
            resume.parsed_resume = dumps_json(parse_resume(resume_text))
            resume.updated_at = datetime.utcnow()
            db.add(resume)
            db.commit()

    context = _build_personalization_context(
        resume_text,
        analysis,
        role,
        req.difficulty,
        training_mode,
        interviewer_persona,
        req.domain_focus.strip(),
        _memory_snapshot(memory),
    )
    focus_mode = "weak_area" if context["weak_areas"] else "general"
    if training_mode == "behavioral_only":
        focus_mode = "behavioral_only"
    elif training_mode == "domain_specific":
        focus_mode = "domain_specific"
    current_phase = "Introduction"
    phase_details = _phase_meta(current_phase)

    try:
        from crew import run_interview_start
        first = run_interview_start(
            role=role,
            difficulty=req.difficulty,
            weak_areas=context["weak_areas"],
            resume_context=context["resume_context"],
            section_scores=context["section_scores"],
            focus_mode=focus_mode,
            training_mode=training_mode,
            interviewer_persona=INTERVIEWER_PERSONAS[interviewer_persona],
            coach_memory=context["coach_memory"],
            domain_focus=context["domain_focus"],
            phase_name=current_phase,
            phase_goal=phase_details["goal"],
            phase_focus=phase_details["focus"],
        )
        if not isinstance(first, dict):
            logger.warning("run_interview_start returned non-dict payload for resume-aware start; using fallback.")
            first = {}
    except Exception as exc:
        logger.error("Resume-aware interview start failed: %s", exc, exc_info=True)
        first = {
            "question": f"Tell me about yourself and why you're a good fit for this {role} role.",
            "focus_area": context["weak_areas"][0] if context["weak_areas"] else "general resume walkthrough",
            "focus_type": focus_mode,
            "interviewer_signal": "I will press for evidence, not generic claims.",
            "pressure_level": INTERVIEWER_PERSONAS[interviewer_persona]["pressure"],
            "answer_expectation": "Answer in 5-10 lines with context, decisions, tradeoffs, and measurable outcome.",
        }

    question = str(first.get("question") or "Tell me about your most relevant project and what you would improve.").strip()
    if current_phase == "Introduction":
        question = _ensure_intro_question(question, role)
    answer_expectation = str(first.get("answer_expectation") or "Answer in 5-10 lines with context, decisions, tradeoffs, and measurable outcome.").strip()
    focus_type = _normalize_focus_type(first.get("focus_type"), focus_mode)
    context["focus_counts"][focus_type] = context["focus_counts"].get(focus_type, 0) + 1
    context["current_focus_area"] = first.get("focus_area", context["weak_areas"][0] if context["weak_areas"] else "general")
    context["current_phase"] = current_phase
    context["phase_history"] = [current_phase]

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
        f"This mock interview simulates a {persona_profile.get('label', 'Balanced')} interviewer under {first_msg.get('pressure_level', persona_profile.get('pressure', 'medium'))} pressure. "
        "Treat answers like a live screening: be concise, cite specific decisions, and quantify outcomes where possible."
    )

    return {
        "session_id": session_token,
        "question": question,
        "db_id": db_session.id,
        "personalized": True,
        "resume_source": resume_source,
        "role": role,
        "difficulty": req.difficulty,
        "weak_areas": context["weak_areas"],
        "section_scores": context["section_scores"],
        "resume_score": context["resume_score"],
        "focus_area": context["current_focus_area"],
        "focus_type": focus_type,
        "interviewer_signal": first_msg["interviewer_signal"],
        "pressure_level": first_msg["pressure_level"],
        "answer_expectation": answer_expectation,
        "question_mix": context["question_mix"],
        "training_mode": training_mode,
        "interviewer_persona": interviewer_persona,
        "persona": persona_profile,
        "session_intro": session_intro,
        "phase": current_phase,
        "phase_goal": phase_details["goal"],
    }


@router.post("/start-for-application")
def start_interview_for_application(
    req: StartForApplicationReq,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
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
        .where(InterviewSession.status.in_(["active", "completed", "cancelled"]))
    ).first()
    if existing_session:
        if existing_session.status == "active":
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
                "message": "Resuming existing active interview session."
            }
        elif existing_session.status == "cancelled":
            return {
                "session_id": existing_session.session_token,
                "db_id": existing_session.id,
                "status": "cancelled",
                "cancellation_reason": existing_session.cancellation_reason,
                "message": "This interview has been cancelled due to proctoring violations."
            }
        else:
            raise HTTPException(status_code=400, detail="You have already completed the interview for this application.")

    job = db.exec(select(JobPosting).where(JobPosting.id == app.job_id)).first()
    role = job.title if job else "Software Engineer"

    resume_text = app.resume_text
    if not resume_text or len(resume_text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Application resume text is missing or too short.")

    resume = db.exec(select(Resume).where(Resume.user_id == current_user.id)).first()
    analysis = load_json_field(resume.last_analysis, None) if resume else None
    if not analysis:
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
        "",
        _memory_snapshot(memory),
    )
    focus_mode = "weak_area" if context["weak_areas"] else "general"
    if training_mode == "behavioral_only":
        focus_mode = "behavioral_only"
    elif training_mode == "domain_specific":
        focus_mode = "domain_specific"
    current_phase = "Introduction"
    phase_details = _phase_meta(current_phase)

    try:
        from crew import run_interview_start
        first = run_interview_start(
            role=role,
            difficulty=req.difficulty,
            weak_areas=context["weak_areas"],
            resume_context=context["resume_context"],
            section_scores=context["section_scores"],
            focus_mode=focus_mode,
            training_mode=training_mode,
            interviewer_persona=INTERVIEWER_PERSONAS[interviewer_persona],
            coach_memory=context["coach_memory"],
            domain_focus=context["domain_focus"],
            phase_name=current_phase,
            phase_goal=phase_details["goal"],
            phase_focus=phase_details["focus"],
        )
        if not isinstance(first, dict):
            first = {}
    except Exception as exc:
        logger.error("start_interview_for_application crew start failed: %s", exc, exc_info=True)
        first = {
            "question": f"Tell me about yourself and why you're a good fit for this {role} role.",
            "focus_area": context["weak_areas"][0] if context["weak_areas"] else "general resume walkthrough",
            "focus_type": focus_mode,
            "interviewer_signal": "I will press for evidence, not generic claims.",
            "pressure_level": INTERVIEWER_PERSONAS[interviewer_persona]["pressure"],
            "answer_expectation": "Answer in 5-10 lines with context, decisions, tradeoffs, and measurable outcome.",
        }

    question = str(first.get("question") or "Tell me about your most relevant project and what you would improve.").strip()
    if current_phase == "Introduction":
        question = _ensure_intro_question(question, role)
    answer_expectation = str(first.get("answer_expectation") or "Answer in 5-10 lines with context, decisions, tradeoffs, and measurable outcome.").strip()
    focus_type = _normalize_focus_type(first.get("focus_type"), focus_mode)
    context["focus_counts"][focus_type] = context["focus_counts"].get(focus_type, 0) + 1
    context["current_focus_area"] = first.get("focus_area", context["weak_areas"][0] if context["weak_areas"] else "general")
    context["current_phase"] = current_phase
    context["phase_history"] = [current_phase]

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
        application_id=req.application_id,
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
        f"This mock interview simulates a {persona_profile.get('label', 'Balanced')} interviewer under {first_msg.get('pressure_level', persona_profile.get('pressure', 'medium'))} pressure. "
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
        "focus_area": context["current_focus_area"],
        "focus_type": focus_type,
        "interviewer_signal": first_msg["interviewer_signal"],
        "pressure_level": first_msg["pressure_level"],
        "answer_expectation": answer_expectation,
        "question_mix": context["question_mix"],
        "training_mode": training_mode,
        "interviewer_persona": interviewer_persona,
        "persona": persona_profile,
        "coach_memory": context["coach_memory"],
        "session_intro": session_intro,
        "phase": current_phase,
        "phase_goal": phase_details["goal"],
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
    if rec.status != "active":
        try:
            violations_list = json.loads(rec.violations) if rec.violations else []
        except Exception:
            violations_list = []
        return {
            "success": False,
            "cancelled": rec.status == "cancelled",
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
        "timestamp": datetime.utcnow().isoformat()
    }
    violations_list.append(new_violation)
    rec.violations = json.dumps(violations_list)
    rec.violations_count = len(violations_list)

    cancelled = False
    if rec.violations_count >= 3:
        rec.status = "cancelled"
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
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    state = _sessions.get(req.session_id)
    if state is None:
        rec = db.exec(select(InterviewSession).where(InterviewSession.session_token == req.session_id)).first()
        if rec is None or rec.user_id != current_user.id:
            raise HTTPException(status_code=400, detail="Invalid session ID. Please start a new interview.")
        state = _state_from_record(rec)
        _sessions[req.session_id] = state
    elif state.get("user_id") is not None and state.get("user_id") != current_user.id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    focus_mode = _choose_focus_mode(state)
    context = state.get("personalization_context") or {}
    current_phase = context.get("current_phase", "Introduction")
    phase_details = _phase_meta(current_phase)
    try:
        from crew import run_interview_answer
        result = run_interview_answer(
            role=state["role"],
            question=state["current_question"],
            answer=req.answer,
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
            phase_name=current_phase,
            phase_goal=phase_details["goal"],
            phase_focus=phase_details["focus"],
        )
        if not isinstance(result, dict):
            logger.warning("run_interview_answer returned non-dict payload; using safe fallback.")
            result = {}
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

    # Update in-memory state
    state["questions"].append(state["current_question"])
    state["answers"].append(req.answer)
    score = result.get("evaluation", {}).get("score", 5)
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
    state["current_question"] = result.get("next_question") or "Can you explain that with a specific example from your resume?"

    focus_type = _normalize_focus_type(result.get("focus_type"), focus_mode)
    context.setdefault("focus_counts", {"weak_area": 0, "general": 0, "domain": 0, "behavioral": 0})
    context["focus_counts"][focus_type] = int(context["focus_counts"].get(focus_type, 0) or 0) + 1
    context["current_focus_area"] = result.get("focus_area", context.get("current_focus_area", "general"))
    context["difficulty"] = state["difficulty"]
    context["last_score"] = score
    context["last_adaptive_mode"] = result.get("adaptive_mode", focus_mode)
    resume_score = context.get("resume_score")
    next_phase = _pick_next_phase(current_phase, len(state["answers"]), state["scores"], resume_score)
    context["current_phase"] = next_phase
    phase_history = context.get("phase_history") or []
    if not phase_history:
        phase_history = [current_phase]
    if phase_history[-1] != next_phase:
        phase_history.append(next_phase)
    context["phase_history"] = phase_history
    state["personalization_context"] = context

    now = datetime.utcnow().isoformat()
    # Normalize and repair evaluator output into the strict schema
    raw_eval = result.get("evaluation", {})
    normalized_eval = _normalize_and_repair_evaluation(raw_eval, context.get("current_focus_area", ""))
    feedback = _format_feedback_message(normalized_eval, context.get("current_focus_area", ""))
    feedback_text = feedback.get("text") if isinstance(feedback, dict) else str(feedback)
    state["messages"].append({"role": "user", "content": req.answer, "timestamp": now})
    state["messages"].append({
        "role": "feedback",
        "content": feedback_text,
        "score": score,
        "focus_area": context.get("current_focus_area"),
        "timestamp": now,
        "meta": normalized_eval,
    })
    state["messages"].append({
        "role": "ai",
        "content": state["current_question"],
        "score": score,
        "difficulty": state["difficulty"],
        "focus_area": context["current_focus_area"],
        "focus_type": focus_type,
        "adaptive_mode": result.get("adaptive_mode", focus_mode),
        "interviewer_signal": result.get("interviewer_signal", ""),
        "pressure_level": result.get("pressure_level", INTERVIEWER_PERSONAS.get(context.get("interviewer_persona", "balanced"), INTERVIEWER_PERSONAS["balanced"]).get("pressure", "medium")),
        "answer_expectation": result.get("answer_expectation", ""),
        "phase": next_phase,
        "timestamp": now,
    })

    memory = _update_coach_memory(db, current_user.id, state, score)
    context["coach_memory"] = _memory_snapshot(memory)
    _save_session_state(db, req.session_id, state, avg)
    if next_phase == "Final Evaluation":
        rec = db.exec(select(InterviewSession).where(InterviewSession.session_token == req.session_id)).first()
        if rec:
            rec.status = "completed"
            db.add(rec)
            db.commit()
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
    if next_phase == "Final Evaluation":
        final_feedback = {
            "overall_score": round(avg, 2) if avg is not None else score,
            "strengths": normalized_eval.get("what_went_well", [])[:3],
            "weaknesses": normalized_eval.get("what_was_missing", [])[:3],
            "improvement_plan": normalized_eval.get("how_to_improve", [])[:3],
            "verdict": final_verdict,
            "verdict_explanation": verdict_explanation,
        }

    return {
        **result,
        "evaluation": normalized_eval,
        "difficulty": state["difficulty"],
        "focus_area": context["current_focus_area"],
        "focus_type": focus_type,
        "weak_areas": context.get("weak_areas", []),
        "question_mix": context.get("question_mix", _question_mix_for_mode("adaptive")),
        "training_mode": context.get("training_mode", state.get("training_mode", "adaptive")),
        "interviewer_persona": context.get("interviewer_persona", state.get("interviewer_persona", "balanced")),
        "persona": INTERVIEWER_PERSONAS.get(context.get("interviewer_persona", "balanced"), INTERVIEWER_PERSONAS["balanced"]),
        "feedback_message": feedback_text,
        "feedback": feedback,
        "answer_expectation": result.get("answer_expectation", ""),
        "session_turn": len(state["answers"]),
        "coach_memory": context["coach_memory"],
        "avg_score": avg,
        "phase": next_phase,
        "phase_goal": _phase_meta(next_phase)["goal"],
        "phase_focus": _phase_meta(next_phase)["focus"],
        "phase_history": context.get("phase_history", [next_phase]),
        "interview_complete": next_phase == "Final Evaluation",
        "final_feedback": final_feedback,
        "final_verdict": final_verdict,
        "verdict_explanation": verdict_explanation,
    }

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
    return {
        "id": rec.id,
        "session_token": rec.session_token,
        "role": rec.role,
        "difficulty": rec.difficulty,
        "training_mode": _normalize_training_mode(rec.training_mode),
        "interviewer_persona": _normalize_persona(rec.interviewer_persona),
        "avg_score": rec.avg_score,
        "status": rec.status,
        "violations_count": rec.violations_count,
        "violations": violations_list,
        "cancellation_reason": rec.cancellation_reason,
        "application_id": rec.application_id,
        "messages": _safe_json_load(rec.messages, []),
        "personalization_context": _safe_json_load(rec.personalization_context, {}),
        "created_at": rec.created_at.isoformat(),
    }


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
        select(InterviewSession).where(InterviewSession.status.in_(["completed", "cancelled"])).order_by(InterviewSession.created_at.desc())
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
    completed = [s for s in sessions if s.status == "completed"]
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
                    "violations": json.loads(s.violations) if s.violations else [],
                    "cancellation_reason": s.cancellation_reason,
                    "created_at": s.created_at.isoformat() if s.created_at else None
                }
                for s in sessions
            ],
        },
        "hiring": {
            "hiring_score": hiring_score,
            "recommendation": _recommendation_label(hiring_score),
            "resume_weight": round(0.35 * resume_score, 1),
            "interview_weight": round(0.40 * interview_avg * 10, 1),
            "credibility_weight": round(0.25 * credibility_score, 1),
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
            completed = [s for s in sessions if s.status == "completed"]
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
    app = db.exec(
        select(CandidateApplication).where(CandidateApplication.candidate_user_id == session.user_id).order_by(CandidateApplication.application_date.desc())
    ).first()

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
    app = db.exec(
        select(CandidateApplication).where(CandidateApplication.candidate_user_id == session.user_id).order_by(CandidateApplication.application_date.desc())
    ).first()

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
        select(InterviewSession).where(InterviewSession.status == "completed").order_by(InterviewSession.created_at.desc())
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
async def transcribe_audio(audio_file: UploadFile = File(...)):
    """Transcribe an audio file using Groq Whisper."""
    import tempfile

    from src.services.transcription_service import transcribe_audio as do_transcribe

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
        transcript = do_transcribe(tmp_path)
        return {"transcript": transcript}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
