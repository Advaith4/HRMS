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
    _ensure_intro_question,
    _normalize_focus_type,
    _update_coach_memory,
    INTERVIEWER_PERSONAS,
    TRAINING_MODES,
    _save_session_state,
    _state_from_record,
    _should_end_interview_early,
    _pick_next_phase,
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
    _safe_json_load,
    INTERVIEW_PHASES,
    PHASE_SEQUENCE
)

class StartForApplicationReq(BaseModel):
    application_id: int
    difficulty: int = Field(default=5, ge=1, le=10)
    training_mode: str = Field(default="adaptive", max_length=40)
    interviewer_persona: str = Field(default="balanced", max_length=40)

class AnswerReq(BaseModel):
    session_id: str
    answer: str

@router.post("/start")
def start_interview(
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
                "messages": msgs,
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
    background_tasks: BackgroundTasks,
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

    import copy
    state = copy.deepcopy(state)
    context = state.setdefault("personalization_context", {})
    focus_mode = _choose_focus_mode(state)
    current_phase = context.get("current_phase", "Introduction")
    phase_details = _phase_meta(current_phase)

    # Claim Verification Engine
    resume_text = ""
    res_ctx = context.get("resume_context", {})
    if isinstance(res_ctx, dict):
        resume_text = res_ctx.get("summary", "") + " " + " ".join(res_ctx.get("skills", []))
    
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
        answer_lower = req.answer.lower()
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
    if verification_active:
        next_phase = current_phase
    else:
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
    _sessions[req.session_id] = state
    if next_phase == "Final Evaluation":
        rec = db.exec(select(InterviewSession).where(InterviewSession.session_token == req.session_id)).first()
        if rec:
            rec.status = "completed"
            db.add(rec)
            db.commit()
            
            # Enqueue asynchronous hiring intelligence compilation task
            from src.services.hiring_intelligence import compile_hiring_intelligence
            background_tasks.add_task(compile_hiring_intelligence, rec.id)
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
        "personalization_context": context,
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
        "competency_scores": _safe_json_load(rec.competency_scores, None),
        "job_fit_report": _safe_json_load(rec.job_fit_report, None),
        "communication_metrics": _safe_json_load(rec.communication_metrics, None),
        "behavioral_report": _safe_json_load(rec.behavioral_report, None),
        "hiring_risks": _safe_json_load(rec.hiring_risks, None),
        "timeline_replay": _safe_json_load(rec.timeline_replay, None),
        "benchmarking": _safe_json_load(rec.benchmarking, None),
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

@router.post("/{session_id}/abandon")
def abandon_interview(
    session_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    rec = db.exec(select(InterviewSession).where(InterviewSession.session_token == session_id)).first()
    if not rec or rec.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found.")
    if rec.status != "active":
        raise HTTPException(status_code=400, detail=f"Cannot abandon session. Current status is {rec.status}.")

    rec.status = "cancelled"
    rec.cancellation_reason = "candidate_exit"
    
    db.add(rec)
    db.commit()

    if session_id in _sessions:
        del _sessions[session_id]

    return {"status": "cancelled", "message": "Interview abandoned."}
