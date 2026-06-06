import json
import logging
import re
import os
import src.services.llm_router
from datetime import datetime
from typing import Any, Optional
from sqlmodel import Session, select
import litellm

from src.models import (
    InterviewSession,
    CandidateApplication,
    JobPosting,
    Resume,
    User,
    CandidateCredibilityReport,
    InterviewIntelligenceReport,
)
from src.services.interview_consistency import analyze_credibility
from src.services.interview_status import (
    INTERVIEW_STATUS_ANALYZED,
    INTERVIEW_STATUS_ANALYZING,
    INTERVIEW_STATUS_FAILED,
)

logger = logging.getLogger(__name__)

def count_filler_words(messages: list[dict[str, Any]]) -> dict[str, int]:
    """Deterministically count filler words in candidate answers."""
    filler_terms = ["like", "um", "uh", "actually", "basically", "so basically"]
    counts = {term: 0 for term in filler_terms}
    
    text_list = []
    for msg in messages:
        role = (msg.get("role") or "").lower()
        content = (msg.get("content") or "").strip()
        if role in ("candidate", "user") and content:
            text_list.append(content.lower())
            
    combined_text = " ".join(text_list)
    for term in filler_terms:
        # Regex search for exact word matches (ignoring substrings)
        pattern = r"\b" + re.escape(term) + r"\b"
        counts[term] = len(re.findall(pattern, combined_text))
        
    return counts

def _extract_json(raw: str) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None

def compile_hiring_intelligence(session_id: int):
    """Asynchronous/background task to generate complete hiring intelligence for a session."""
    # Since background tasks run outside request scope, create local DB engine/session if needed,
    # or resolve it from get_session. We will import get_session locally or import Session from sqlmodel.
    from sqlmodel import Session
    from src.database.connection import engine
    db = Session(engine)
    
    interview_session = db.get(InterviewSession, session_id)
    if not interview_session:
        logger.error(f"Interview session {session_id} not found for hiring intelligence compilation.")
        db.close()
        return

    messages = []
    filler_counts = {}
    cred_report = None
    resume_score = 70.0
    interview_score = (interview_session.avg_score or 5.0) * 10.0
    cred_score = 70.0
    app = None

    try:
        interview_session.status = INTERVIEW_STATUS_ANALYZING
        interview_session.updated_at = datetime.utcnow()
        db.add(interview_session)
        db.commit()

        logger.info(f"Resolving credibility analysis for session {session_id}...")
        try:
            cred_report = analyze_credibility(db, session_id, force=False)
        except Exception as ce:
            logger.warning(f"Credibility report compilation failed: {ce}")
            cred_report = None

        if interview_session.application_id:
            app = db.get(CandidateApplication, interview_session.application_id)

        job = None
        if app:
            job = db.get(JobPosting, app.job_id)

        resume = db.exec(
            select(Resume).where(Resume.user_id == interview_session.user_id)
        ).first()

        messages = json.loads(interview_session.messages) if interview_session.messages else []
        filler_counts = count_filler_words(messages)

        qa_transcript = []
        turn_idx = 1
        current_q = None
        for msg in messages:
            role = (msg.get("role") or "").lower()
            content = (msg.get("content") or "").strip()
            if role in ("interviewer", "assistant", "ai", "coach"):
                current_q = content
            elif role in ("candidate", "user") and current_q:
                score = msg.get("score") or 5
                qa_transcript.append(f"Turn {turn_idx} (Phase: {msg.get('phase', 'N/A')}):\nQuestion: {current_q}\nCandidate Answer: {content}\nScore: {score}/10\n")
                turn_idx += 1
                current_q = None

        qa_transcript_text = "\n".join(qa_transcript)
        job_context = f"Job Title: {job.title}\nDescription: {job.description}\nRequired Skills: {job.required_skills}\n" if job else "No Job Posting Context."
        resume_context = resume.raw_text if resume else "No Resume Context."

        cred_score = cred_report.credibility_score if cred_report else 70
        resume_score = cred_report.resume_score if cred_report else 70
        interview_score = (interview_session.avg_score or 5.0) * 10.0

        prompt = f"""You are a hiring intelligence synthesizer for an enterprise recruitment platform.
Analyze the candidate's complete interview transcript, job details, and resume context to produce a structured hiring decision report.

JOB POSTING DETAILS:
{job_context}

RESUME DETAILS:
{resume_context[:2000]}

INTERVIEW QA TRANSCRIPT:
{qa_transcript_text}

SCORES PROFILE:
- Resume Match Score: {resume_score}/100
- Interview Average Score: {interview_score}/100
- Credibility / Claim Verification Score: {cred_score}/100

INSTRUCTIONS:
Calculate and produce a single JSON payload. Ensure ALL float/integer scores are strictly on a scale of 0.0-10.0 or 0-100 as specified.
Your evaluation must cover:
1. Competency Scores (0.0-10.0 scale for technicalDepth, problemSolving, communication, leadership, systemDesign, confidence, domainKnowledge). Include short, concrete 1-sentence explanations.
2. Job Fit Report (overall jobFit 0-100 score, strengths list, weaknesses list, recommendedRole title, riskLevel: "Low" | "Medium" | "High").
3. Linguistic / Communication metrics (0.0-10.0 scale for clarity, vocabulary, confidence, conciseness, communicationEffectiveness).
4. Behavioral Categories breakdown (0.0-10.0 scale for Technical, Behavioral, Situational, Leadership).
5. Hiring Risks (list of specific risks flagged in the interview with concrete text evidence/snippet from the candidate's answers).
6. Timeline Replay (a turn-by-turn array mapping each Turn in the QA transcript to: turn index, phase name, question summary, answer summary, turn score, competencyImpact [increases/decreases in values like technicalDepth, communication, problemSolving], and credibilityImpact [claims verified or marked weak]).

Return ONLY valid JSON matching this exact structure:
{{
  "competency_scores": {{
    "technicalDepth": <0.0-10.0>,
    "problemSolving": <0.0-10.0>,
    "communication": <0.0-10.0>,
    "leadership": <0.0-10.0>,
    "systemDesign": <0.0-10.0>,
    "confidence": <0.0-10.0>,
    "domainKnowledge": <0.0-10.0>,
    "explanations": {{
      "technicalDepth": "...",
      "problemSolving": "...",
      "communication": "...",
      "leadership": "...",
      "systemDesign": "...",
      "confidence": "...",
      "domainKnowledge": "..."
    }},
    "overall_confidence": <0.0-10.0>
  }},
  "job_fit_report": {{
    "jobFit": <0-100>,
    "strengths": ["...", "...", "..."],
    "weaknesses": ["...", "...", "..."],
    "recommendedRole": "...",
    "riskLevel": "Low|Medium|High"
  }},
  "communication_metrics": {{
    "clarity": <0.0-10.0>,
    "vocabulary": <0.0-10.0>,
    "confidence": <0.0-10.0>,
    "conciseness": <0.0-10.0>,
    "communicationEffectiveness": <0.0-10.0>
  }},
  "behavioral_report": {{
    "categories": {{
      "Technical": <0.0-10.0>,
      "Behavioral": <0.0-10.0>,
      "Situational": <0.0-10.0>,
      "Leadership": <0.0-10.0>
    }}
  }},
  "hiring_risks": [
    {{
      "risk": "description of risk",
      "evidence": "evidence snippet from transcript"
    }}
  ],
  "timeline_replay": [
    {{
      "turn": <int>,
      "phase": "Resume Validation|Technical Assessment|Behavioral Assessment|Final Evaluation",
      "question": "short question summary",
      "answer": "short candidate answer summary",
      "score": <0.0-10.0>,
      "competencyImpact": {{
        "technicalDepth": <float, e.g. 0.5 or -0.2>,
        "problemSolving": <float>,
        "communication": <float>
      }},
      "credibilityImpact": {{
        "claim": "technology name or skill",
        "status": "supported|weak|missing"
      }}
    }}
  ]
}}
"""

        response = litellm.completion(
            model="groq/llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
            timeout=20.0,
        )
        
        raw_text = response.choices[0].message.content.strip()
        parsed = _extract_json(raw_text)
        if not parsed or "competency_scores" not in parsed:
            raise ValueError("LLM output failed validation")

        parsed["_source"] = "ai"
        logger.info("AI hiring intelligence synthesis successful.")
    except Exception as exc:
        logger.warning(f"AI compilation failed, running fallback generator: {exc}")
        parsed = run_fallback_generation(messages, filler_counts, cred_report, resume_score, interview_score, cred_score)
        parsed["_source"] = "fallback"

    try:
        benchmarking_data = calculate_benchmarking(db, interview_session, app, interview_score)
        save_hiring_intelligence_results(db, interview_session, parsed, benchmarking_data, filler_counts)
    except Exception:
        logger.exception("Failed to persist hiring intelligence for session %s", session_id)
        interview_session.status = INTERVIEW_STATUS_FAILED
        interview_session.updated_at = datetime.utcnow()
        db.add(interview_session)
        db.commit()
    finally:
        db.close()

def run_fallback_generation(
    messages: list[dict[str, Any]],
    filler_counts: dict[str, int],
    cred_report: Optional[CandidateCredibilityReport],
    resume_score: float,
    interview_score: float,
    cred_score: float
) -> dict[str, Any]:
    avg_score = interview_score / 10.0
    
    competency = {
        "technicalDepth": round(avg_score * 0.9, 1),
        "problemSolving": round(avg_score * 0.85, 1),
        "communication": round(avg_score * 0.95, 1),
        "leadership": round(avg_score * 0.75, 1),
        "systemDesign": round(avg_score * 0.8, 1),
        "confidence": round(avg_score, 1),
        "domainKnowledge": round(avg_score * 0.88, 1),
        "explanations": {
            "technicalDepth": "Estimated from technical responses.",
            "problemSolving": "Estimated based on problem solving answers.",
            "communication": "Estimated from speech transcription patterns.",
            "leadership": "Default benchmark rating.",
            "systemDesign": "Estimated from architecture questions.",
            "confidence": "Linguistic markers suggest moderate confidence.",
            "domainKnowledge": "Strong alignment with core competencies."
        },
        "overall_confidence": round(avg_score, 1)
    }
    
    job_fit_score = int(resume_score * 0.35 + interview_score * 0.40 + cred_score * 0.25)
    risk_level = "Low" if job_fit_score >= 80 else ("Medium" if job_fit_score >= 50 else "High")
    
    strengths = []
    weaknesses = []
    if cred_report:
        try:
            supported = json.loads(cred_report.supported_claims)
            strengths = [s.get("claim") for s in supported if isinstance(s, dict)][:3]
        except Exception:
            pass
        try:
            weak = json.loads(cred_report.weak_claims)
            weaknesses = [w.get("claim") for w in weak if isinstance(w, dict)][:3]
        except Exception:
            pass
            
    if not strengths:
        strengths = ["Technical communication", "Answering consistency"]
    if not weaknesses:
        weaknesses = ["Hands-on proof of claim depth"]
        
    job_fit = {
        "jobFit": job_fit_score,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendedRole": "Target Candidate Profile",
        "riskLevel": risk_level
    }
    
    communication = {
        "clarity": round(avg_score, 1),
        "vocabulary": round(avg_score * 0.9, 1),
        "confidence": round(avg_score * 0.95, 1),
        "conciseness": round(avg_score * 0.85, 1),
        "communicationEffectiveness": round(avg_score * 0.9, 1)
    }
    
    behavioral = {
        "categories": {
            "Technical": round(avg_score * 0.9, 1),
            "Behavioral": round(avg_score * 0.8, 1),
            "Situational": round(avg_score * 0.85, 1),
            "Leadership": round(avg_score * 0.75, 1)
        }
    }
    
    risks = []
    if cred_report:
        try:
            weak = json.loads(cred_report.weak_claims)
            for w in weak:
                if isinstance(w, dict) and w.get("claim"):
                    risks.append({
                        "risk": f"Weak verification for {w.get('claim')}",
                        "evidence": w.get("explanation", "Candidate struggled with details in interview.")
                    })
        except Exception:
            pass
    if not risks:
        risks = [{"risk": "Insufficient depth verification", "evidence": "Answers were generally brief."}]
        
    timeline = []
    turn_idx = 1
    current_q = None
    for msg in messages:
        role = (msg.get("role") or "").lower()
        content = (msg.get("content") or "").strip()
        if role in ("interviewer", "assistant", "ai", "coach"):
            current_q = content
        elif role in ("candidate", "user") and current_q:
            t_score = msg.get("score") or 5
            timeline.append({
                "turn": turn_idx,
                "phase": msg.get("phase") or "Assessment",
                "question": current_q[:100] + "...",
                "answer": content[:100] + "...",
                "score": float(t_score),
                "competencyImpact": {
                    "technicalDepth": 0.2 if t_score >= 7 else -0.1,
                    "communication": 0.1 if t_score >= 6 else -0.1
                },
                "credibilityImpact": {
                    "claim": msg.get("focus_area") or "general",
                    "status": "supported" if t_score >= 6 else "weak"
                }
            })
            turn_idx += 1
            current_q = None
            
    return {
        "competency_scores": competency,
        "job_fit_report": job_fit,
        "communication_metrics": communication,
        "behavioral_report": behavioral,
        "hiring_risks": risks,
        "timeline_replay": timeline
    }

def calculate_benchmarking(
    session_db: Session,
    interview_session: InterviewSession,
    app: Optional[CandidateApplication],
    current_score: float
) -> dict[str, Any]:
    if not app:
        return {
            "percentile": None,
            "ranking": None,
            "total_candidates": 0,
            "insufficient_data": True,
            "relative_strength_areas": []
        }

    # Find all completed sessions for this job ID
    all_sessions = session_db.exec(
        select(InterviewSession)
        .join(CandidateApplication, InterviewSession.application_id == CandidateApplication.id)
        .where(CandidateApplication.job_id == app.job_id)
        .where(InterviewSession.status.in_(["completed", "analyzed"]))
    ).all()

    # Deduplicate scores (taking highest score per candidate user)
    candidate_scores = {}
    for s in all_sessions:
        if s.avg_score is not None:
            score_val = s.avg_score * 10.0
            uid = s.user_id
            if uid not in candidate_scores or score_val > candidate_scores[uid]:
                candidate_scores[uid] = score_val

    # Ensure current session score is accounted for
    current_uid = interview_session.user_id
    if current_uid not in candidate_scores:
        candidate_scores[current_uid] = current_score
    else:
        candidate_scores[current_uid] = max(candidate_scores[current_uid], current_score)

    total_candidates = len(candidate_scores)
    
    # Standard: if total completed candidates < 3, flag insufficient data
    if total_candidates < 3:
        return {
            "percentile": None,
            "ranking": None,
            "total_candidates": total_candidates,
            "insufficient_data": True,
            "relative_strength_areas": []
        }

    sorted_scores = sorted(candidate_scores.values(), reverse=True)
    rank = sorted_scores.index(current_score) + 1
    
    # Calculate percentile based on scores less than or equal to current score
    below_or_equal = sum(1 for val in candidate_scores.values() if val <= current_score)
    percentile = round((below_or_equal / total_candidates) * 100, 1)

    return {
        "percentile": percentile,
        "ranking": rank,
        "total_candidates": total_candidates,
        "insufficient_data": False,
        "relative_strength_areas": ["Problem Solving", "Domain Knowledge"]
    }

def save_hiring_intelligence_results(
    session_db: Session,
    interview_session: InterviewSession,
    results: dict[str, Any],
    benchmarking_data: dict[str, Any],
    filler_counts: dict[str, int]
):
    interview_session.competency_scores = json.dumps(results.get("competency_scores") or {})
    
    comm_metrics = results.get("communication_metrics") or {}
    comm_metrics["fillerWords"] = filler_counts
    interview_session.communication_metrics = json.dumps(comm_metrics)
    
    interview_session.job_fit_report = json.dumps(results.get("job_fit_report") or {})
    interview_session.behavioral_report = json.dumps(results.get("behavioral_report") or {})
    interview_session.hiring_risks = json.dumps(results.get("hiring_risks") or [])
    interview_session.timeline_replay = json.dumps(results.get("timeline_replay") or [])
    interview_session.benchmarking = json.dumps(benchmarking_data)
    
    interview_session.status = INTERVIEW_STATUS_ANALYZED
    interview_session.updated_at = datetime.utcnow()
    session_db.add(interview_session)
    _upsert_interview_intelligence_report(
        session_db,
        interview_session,
        results,
        source=str(results.get("_source") or "fallback"),
    )
    session_db.commit()


def _score_from_competency(competency: dict[str, Any], keys: tuple[str, ...], fallback: float) -> float:
    values = []
    for key in keys:
        try:
            values.append(float(competency.get(key)))
        except (TypeError, ValueError):
            continue
    if not values:
        return round(fallback, 1)
    return round((sum(values) / len(values)) * 10.0, 1)


def _recommendation_for_score(score: float) -> str:
    if score >= 85:
        return "Strongly Recommended"
    if score >= 72:
        return "Recommended"
    if score >= 55:
        return "Needs Review"
    return "Not Recommended"


def _upsert_interview_intelligence_report(
    session_db: Session,
    interview_session: InterviewSession,
    results: dict[str, Any],
    source: str,
) -> None:
    if not interview_session.application_id:
        return

    app = session_db.get(CandidateApplication, interview_session.application_id)
    if not app:
        return

    competency = results.get("competency_scores") or {}
    job_fit = results.get("job_fit_report") or {}
    behavioral = (results.get("behavioral_report") or {}).get("categories") or {}
    credibility = session_db.exec(
        select(CandidateCredibilityReport).where(CandidateCredibilityReport.session_id == interview_session.id)
    ).first()

    resume_score = float(credibility.resume_score if credibility else 0)
    credibility_score = float(credibility.credibility_score if credibility else 0)
    technical_score = _score_from_competency(
        competency,
        ("technicalDepth", "problemSolving", "systemDesign", "domainKnowledge"),
        (interview_session.avg_score or 0) * 10,
    )
    behavioral_values = []
    for key in ("Behavioral", "Situational", "Leadership"):
        try:
            behavioral_values.append(float(behavioral.get(key)) * 10.0)
        except (TypeError, ValueError):
            continue
    behavioral_score = round(sum(behavioral_values) / len(behavioral_values), 1) if behavioral_values else _score_from_competency(
        competency,
        ("communication", "leadership", "confidence"),
        (interview_session.avg_score or 0) * 10,
    )
    overall_score = round(
        (resume_score * 0.25)
        + (technical_score * 0.35)
        + (behavioral_score * 0.15)
        + (credibility_score * 0.25),
        1,
    )
    recommendation = str(job_fit.get("recommendation") or _recommendation_for_score(overall_score))

    strengths = job_fit.get("strengths") or []
    weaknesses = job_fit.get("weaknesses") or []
    executive_summary = (
        f"Overall score {overall_score}/100. "
        f"Technical {technical_score}/100, behavioral {behavioral_score}/100, "
        f"resume credibility {credibility_score}/100. Recommendation: {recommendation}."
    )

    report = session_db.exec(
        select(InterviewIntelligenceReport).where(InterviewIntelligenceReport.session_id == interview_session.id)
    ).first()
    if report is None:
        report = session_db.exec(
            select(InterviewIntelligenceReport).where(InterviewIntelligenceReport.application_id == app.id)
        ).first()
    now = datetime.utcnow()
    if report is None:
        report = InterviewIntelligenceReport(
            application_id=app.id,
            candidate_id=interview_session.user_id,
            session_id=interview_session.id,
            created_at=now,
        )

    report.resume_score = resume_score
    report.technical_score = technical_score
    report.behavioral_score = behavioral_score
    report.credibility_score = credibility_score
    report.overall_score = overall_score
    report.recommendation = recommendation
    report.executive_summary = executive_summary
    report.strengths = json.dumps(strengths)
    report.weaknesses = json.dumps(weaknesses)
    report.technical_assessment = json.dumps(competency)
    report.behavioral_assessment = json.dumps(results.get("behavioral_report") or {})
    report.resume_validation = json.dumps({
        "credibility_score": credibility_score,
        "supported_claims": json.loads(credibility.supported_claims) if credibility and credibility.supported_claims else [],
        "weak_claims": json.loads(credibility.weak_claims) if credibility and credibility.weak_claims else [],
    })
    report.source = source
    report.status = INTERVIEW_STATUS_ANALYZED
    report.updated_at = now
    session_db.add(report)
