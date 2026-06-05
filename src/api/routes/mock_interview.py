import uuid
import json
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from src.database.connection import get_session
from src.models import User, Resume, MockInterviewSession
from src.api.dependencies import get_current_user
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
    _format_feedback_message
)
from src.resume_lab import analyze_resume, dumps_json, load_json_field, parse_resume
from crew import run_interview_start, run_interview_answer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mock-interview", tags=["mock-interview"])

class StartMockReq(BaseModel):
    role: str = Field(default="Software Engineer")
    difficulty: int = Field(default=5, ge=1, le=10)
    training_mode: str = Field(default="adaptive")
    interviewer_persona: str = Field(default="balanced")
    domain_focus: str = Field(default="")
    interview_type: str = Field(default="mixed")
    resume_source: str = Field(default="existing")  # none, existing
    force_reanalyze: bool = False

class AnswerReq(BaseModel):
    session_id: str
    answer: str

@router.post("/start")
def start_mock_interview(
    req: StartMockReq,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    training_mode = _normalize_training_mode(req.training_mode)
    interviewer_persona = _normalize_persona(req.interviewer_persona)
    memory = _get_or_create_memory(db, current_user.id)
    
    role = req.role.strip() or current_user.target_role or "Software Engineer"
    
    context = {}
    resume_text = ""
    resume_score = 0
    weak_areas = []
    
    if req.resume_source == "existing":
        resume = db.exec(select(Resume).where(Resume.user_id == current_user.id)).first()
        resume_text, src = _latest_candidate_resume_text(db, current_user.id)
        if resume_text and len(resume_text.strip()) >= 50:
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
            resume_score = context.get("resume_score", 0)
            weak_areas = context.get("weak_areas", [])
        else:
            req.resume_source = "none"
            
    if req.resume_source == "none":
        context = {
            "source": "manual",
            "role": role,
            "weak_areas": [],
            "section_scores": {},
            "resume_context": {},
            "focus_counts": {"weak_area": 0, "general": 0, "domain": 0, "behavioral": 0},
            "training_mode": training_mode,
            "interviewer_persona": interviewer_persona,
            "domain_focus": req.domain_focus,
            "coach_memory": _memory_snapshot(memory),
        }

    focus_mode = "weak_area" if weak_areas else "general"
    if training_mode == "behavioral_only": focus_mode = "behavioral_only"
    elif training_mode == "domain_specific": focus_mode = "domain_specific"
    
    current_phase = "Introduction"
    phase_details = _phase_meta(current_phase)

    try:
        first = run_interview_start(
            role=role,
            difficulty=req.difficulty,
            weak_areas=weak_areas,
            resume_context=context.get("resume_context", {}),
            section_scores=context.get("section_scores", {}),
            focus_mode=focus_mode,
            training_mode=training_mode,
            interviewer_persona=INTERVIEWER_PERSONAS[interviewer_persona],
            coach_memory=context.get("coach_memory", {}),
            domain_focus=req.domain_focus,
            phase_name=current_phase,
            phase_goal=phase_details["goal"],
            phase_focus=phase_details["focus"],
        )
        if not isinstance(first, dict):
            first = {}
    except Exception as exc:
        logger.error("Mock interview start failed: %s", exc, exc_info=True)
        first = {
            "question": f"Tell me about yourself and why you're a good fit for this {role} role.",
            "focus_area": "general role fit",
            "focus_type": focus_mode,
            "interviewer_signal": "I will challenge vague claims.",
            "pressure_level": INTERVIEWER_PERSONAS[interviewer_persona]["pressure"],
            "answer_expectation": "Answer in 5-10 lines with context, decisions, tradeoffs, and measurable outcome.",
        }

    question = str(first.get("question") or "Tell me about your most relevant project.").strip()
    if current_phase == "Introduction":
        question = _ensure_intro_question(question, role)
        
    answer_expectation = str(first.get("answer_expectation") or "").strip()
    focus_type = _normalize_focus_type(first.get("focus_type"), focus_mode)
    if "focus_counts" in context:
        context["focus_counts"][focus_type] = context["focus_counts"].get(focus_type, 0) + 1
    context["current_focus_area"] = first.get("focus_area", "general")
    context["current_phase"] = current_phase
    context["phase_history"] = [current_phase]

    session_token = uuid.uuid4().hex
    first_msg = {
        "role": "ai",
        "content": question,
        "timestamp": datetime.utcnow().isoformat(),
        "focus_area": context["current_focus_area"],
        "focus_type": focus_type,
        "interviewer_signal": first.get("interviewer_signal", ""),
        "pressure_level": first.get("pressure_level", INTERVIEWER_PERSONAS[interviewer_persona]["pressure"]),
        "answer_expectation": answer_expectation,
        "phase": current_phase,
    }
    
    db_session = MockInterviewSession(
        user_id=current_user.id,
        session_token=session_token,
        role=role,
        difficulty=req.difficulty,
        training_mode=training_mode,
        interviewer_persona=interviewer_persona,
        interview_type=req.interview_type,
        resume_source=req.resume_source,
        messages=json.dumps([first_msg]),
        personalization_context=json.dumps(context),
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)

    _sessions[session_token] = {
        "role": role,
        "difficulty": req.difficulty,
        "weak_areas": weak_areas,
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
        f"This mock interview simulates a {persona_profile.get('label', 'Balanced')} interviewer. "
        "Treat answers like a live screening: be concise, cite specific decisions, and quantify outcomes where possible."
    )

    return {
        "session_id": session_token,
        "question": question,
        "db_id": db_session.id,
        "personalized": req.resume_source == "existing",
        "role": role,
        "difficulty": req.difficulty,
        "weak_areas": weak_areas,
        "focus_area": context["current_focus_area"],
        "training_mode": training_mode,
        "interviewer_persona": interviewer_persona,
        "persona": persona_profile,
        "session_intro": session_intro,
        "phase": current_phase,
        "messages": [first_msg],
    }

@router.post("/answer")
def submit_mock_answer(
    req: AnswerReq,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    state = _sessions.get(req.session_id)
    if not state:
        rec = db.exec(select(MockInterviewSession).where(MockInterviewSession.session_token == req.session_id)).first()
        if not rec or rec.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Session not found or unauthorized.")
        if rec.status != "active":
            raise HTTPException(status_code=400, detail="This mock interview session is no longer active.")
        # Rebuild state from DB
        context = json.loads(rec.personalization_context) if rec.personalization_context else {}
        msgs = json.loads(rec.messages) if rec.messages else []
        last_ai = next((m["content"] for m in reversed(msgs) if m.get("role") == "ai"), "")
        questions = []
        answers = []
        scores = []
        for i, m in enumerate(msgs):
            if m.get("role") == "user":
                answers.append(m.get("content", ""))
                for j in range(i - 1, -1, -1):
                    if msgs[j].get("role") == "ai":
                        questions.append(msgs[j].get("content", ""))
                        break
            if m.get("role") == "feedback" and m.get("score") is not None:
                scores.append(int(m["score"]))

        state = {
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
        _sessions[req.session_id] = state

    if not req.answer.strip():
        raise HTTPException(status_code=400, detail="Answer cannot be empty.")

    state["answers"].append(req.answer)
    state["questions"].append(state["current_question"])
    state["messages"].append({
        "role": "user",
        "content": req.answer,
        "timestamp": datetime.utcnow().isoformat()
    })

    context = state.get("personalization_context", {})
    try:
        result = run_interview_answer(
            role=state["role"],
            question=state["current_question"],
            answer=req.answer,
            current_diff=state["difficulty"],
            weak_areas=state.get("weak_areas", []),
            resume_context=context.get("resume_context", {}),
            section_scores=context.get("section_scores", {}),
            focus_mode=context.get("current_focus_area", "general"),
            training_mode=state.get("training_mode", "adaptive"),
            interviewer_persona=INTERVIEWER_PERSONAS[state.get("interviewer_persona", "balanced")],
            coach_memory=context.get("coach_memory", {}),
            domain_focus=context.get("domain_focus", ""),
            conversation_history=state["messages"][-6:],
            current_focus_area=context.get("current_focus_area", "general"),
            phase_name=context.get("current_phase", "Core Technical Round"),
            phase_goal="Assess competency",
            phase_focus="Detail and tradeoffs"
        )
    except Exception as exc:
        logger.error("Mock answer execution failed: %s", exc, exc_info=True)
        result = {
            "evaluation": {"score": 5, "what_went_well": [], "what_was_missing": [], "how_to_improve": [], "next_focus": "general"},
            "next_question": {"question": "Can you provide another example from your experience?", "focus_area": "general"},
            "new_difficulty": state["difficulty"]
        }

    eval_data = result.get("evaluation", {})
    state["scores"].append(int(eval_data.get("score", 5)))
    state["difficulty"] = int(result.get("new_difficulty", state["difficulty"]))
    
    feedback_msg = {
        "role": "feedback",
        "content": _format_feedback_message(eval_data, result.get("next_question", {}).get("focus_area")),
        "score": eval_data.get("score", 5),
        "timestamp": datetime.utcnow().isoformat(),
        "raw_eval": eval_data
    }
    state["messages"].append(feedback_msg)

    next_q = result.get("next_question", {}).get("question", "Could you elaborate more?")
    ai_msg = {
        "role": "ai",
        "content": next_q,
        "timestamp": datetime.utcnow().isoformat(),
        "focus_area": result.get("next_question", {}).get("focus_area", "general"),
        "phase": context.get("current_phase", "Core Technical Round"),
    }
    state["messages"].append(ai_msg)
    state["current_question"] = next_q
    
    # Save session state
    rec = db.get(MockInterviewSession, state["db_id"])
    if rec:
        rec.messages = json.dumps(state["messages"])
        rec.personalization_context = json.dumps(state["personalization_context"])
        rec.difficulty = state["difficulty"]
        if state["scores"]:
            rec.avg_score = sum(state["scores"]) / len(state["scores"])
        db.add(rec)
        db.commit()

    return {
        "evaluation": feedback_msg,
        "next_question": next_q,
        "new_difficulty": state["difficulty"],
        "phase": ai_msg["phase"]
    }
from src.services.mock_interview_summary import generate_mock_interview_summary

@router.post("/{session_id}/complete")
def complete_mock_interview(
    session_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    rec = db.exec(select(MockInterviewSession).where(MockInterviewSession.session_token == session_id)).first()
    if not rec or rec.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    rec.status = "completed"
    
    # Extract transcripts and calculate score
    msgs = json.loads(rec.messages) if rec.messages else []
    scores = [m["score"] for m in msgs if m.get("role") == "feedback" and m.get("score") is not None]
    avg = sum(scores)/len(scores) if scores else 0
    rec.avg_score = avg

    # Generate rich AI summary
    context = json.loads(rec.personalization_context) if rec.personalization_context else {}
    summary_data = generate_mock_interview_summary(
        transcript=msgs,
        role=rec.role,
        difficulty=rec.difficulty,
        average_score=avg,
        resume_context=context.get("resume_context", {})
    )
    
    # Format JSON response into a markdown block for the frontend
    md_summary = f"### Overall Assessment\n{summary_data.get('overall_assessment', '')}\n\n"
    md_summary += f"### Communication\n{summary_data.get('communication_feedback', '')}\n\n"
    md_summary += f"### Technical Depth\n{summary_data.get('technical_feedback', '')}\n\n"
    md_summary += "### Key Strengths\n" + "\n".join([f"- {s}" for s in summary_data.get('key_strengths', [])]) + "\n\n"
    md_summary += "### Key Weaknesses\n" + "\n".join([f"- {w}" for w in summary_data.get('key_weaknesses', [])]) + "\n\n"
    md_summary += "### Recommendations\n" + "\n".join([f"- {r}" for r in summary_data.get('improvement_recommendations', [])]) + "\n\n"
    md_summary += "### Next Practice Topics\n" + "\n".join([f"- {t}" for t in summary_data.get('suggested_next_topics', [])])

    rec.ai_summary = md_summary
    db.add(rec)
    db.commit()
    
    if session_id in _sessions:
        del _sessions[session_id]
        
    return {"status": "completed", "avg_score": avg}

@router.get("/sessions")
def list_mock_sessions(db: Session = Depends(get_session), current_user: User = Depends(get_current_user)):
    sessions = db.exec(select(MockInterviewSession).where(MockInterviewSession.user_id == current_user.id).order_by(MockInterviewSession.created_at.desc())).all()
    return [{"session_id": s.session_token, "role": s.role, "status": s.status, "avg_score": s.avg_score, "created_at": s.created_at} for s in sessions]
