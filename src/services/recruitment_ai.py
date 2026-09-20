import concurrent.futures
import json
import logging
import re
from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from src.models import (
    ApplicationAIAnalysis,
    CandidateApplication,
    InterviewSession,
    JobPosting,
    User,
)
from src.resume_lab import parse_resume
from src.services.planner_agent import plan_recruitment_workflow
from src.services.validator_agent import validate_evaluation_payload
from src.services.workflow_state import evaluate_routing_decision, RoutingDecision
from src.tools.recruitment_tools import resume_parser_tool, skill_gap_tool, ats_scorer_tool

logger = logging.getLogger(__name__)

RECOMMENDATIONS = ("Strongly Recommended", "Recommended", "Consider", "Reject")


def extract_features_parallel(resume_text: str, job: JobPosting, request_id: str = "req-features") -> dict[str, Any]:
    """
    Executes independent feature extraction subtasks in parallel using a ThreadPoolExecutor.
    Runs ResumeParserTool, SkillGapAnalyzerTool, and ATSScorerTool concurrently.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        fut_parse = executor.submit(resume_parser_tool.run, request_id=request_id, resume_text=resume_text)
        parsed_out = fut_parse.result()

        fut_gap = executor.submit(
            skill_gap_tool.run,
            request_id=request_id,
            required_skills=job.required_skills,
            detected_skills=parsed_out.skills,
            resume_text=resume_text,
        )
        fut_ats = executor.submit(
            ats_scorer_tool.run,
            request_id=request_id,
            job_title=job.title,
            required_skills=job.required_skills,
            experience_required=job.experience_required or "",
            resume_text=resume_text,
            detected_skills=parsed_out.skills,
            experience_items_count=len(parsed_out.experience) + len(parsed_out.projects),
            has_education=bool(parsed_out.education),
        )

        gap_out = fut_gap.result()
        ats_out = fut_ats.result()

    return {
        "parsed": parsed_out.model_dump(),
        "skill_gap": gap_out.model_dump(),
        "ats_score": ats_out.model_dump(),
    }


def analyze_application(session: Session, application_id: int, force: bool = False) -> ApplicationAIAnalysis:
    application = session.get(CandidateApplication, application_id)
    if not application:
        raise ValueError("Application not found")

    existing = session.exec(
        select(ApplicationAIAnalysis).where(ApplicationAIAnalysis.application_id == application_id)
    ).first()
    if existing and existing.status == "completed" and not force:
        return existing

    job = session.get(JobPosting, application.job_id)
    if not job:
        return _upsert_analysis(
            session,
            application,
            _failed_payload("Job posting was not found for this application."),
            existing,
        )

    # 1. Store plain variables to execute CrewAI analysis safely
    resume_text = application.resume_text
    
    # Store job properties to avoid database access during CrewAI run
    job_info = {
        "title": job.title,
        "description": job.description,
        "required_skills": job.required_skills,
        "department": job.department,
        "salary_range": job.salary_range,
        "experience_required": job.experience_required,
    }
    
    # 2. Execute Planner Agent before worker execution
    temp_job = JobPosting(**job_info)
    plan = plan_recruitment_workflow(
        job_title=temp_job.title,
        job_description=temp_job.description,
        required_skills=temp_job.required_skills,
        resume_text=resume_text,
        request_id=f"app-{application_id}",
    )
    
    # 3. Parallel Feature Extraction (Subtasks A, B, C)
    parallel_features = extract_features_parallel(resume_text, temp_job, request_id=f"app-{application_id}")

    # Release the SQLite lock by committing the read transaction
    session.commit()

    # 2. Run CrewAI analysis (no database transaction active during network I/O)
    # 3. Run Worker analysis (CrewAI or Deterministic Fallback)
    # 4. Run Worker analysis (CrewAI or Deterministic Fallback)
    try:
        temp_job = JobPosting(**job_info)
        payload = _run_crewai_analysis(resume_text, temp_job)
        normalized = _normalize_ai_payload(payload, resume_text, temp_job, source="ai")
    except Exception as exc:
        logger.warning("AI application analysis failed; using fallback. application_id=%s error=%s", application_id, exc)
        temp_job = JobPosting(**job_info)
        normalized = _fallback_analysis(resume_text, temp_job)
        normalized["status"] = "completed"
        normalized["source"] = "fallback"
        normalized["error_message"] = f"AI provider unavailable; deterministic fallback used. {exc}"

    # 3. Start a new transaction to write results
    # 4. Execute Reflection / Validator Agent Loop (Max 2 iterations)
    # 5. Execute Reflection / Validator Agent Loop (Max 2 iterations)
    val_result = validate_evaluation_payload(
        resume_text=resume_text,
        job_title=temp_job.title,
        required_skills=temp_job.required_skills,
        evaluation=normalized,
        iteration=1,
        confidence_threshold=0.75,
        request_id=f"app-{application_id}",
    )

    if val_result.retry_recommended:
        logger.info("Validator recommended retry for application_id=%s. Confidence=%.2f. Critique: %s", application_id, val_result.confidence_score, val_result.critique)
        # Self-correction: re-run fallback/analysis with critique
        retry_normalized = _fallback_analysis(resume_text, temp_job)
        retry_normalized["observations"].append(f"Reflection Note: {val_result.critique}")
        val_result = validate_evaluation_payload(
            resume_text=resume_text,
            job_title=temp_job.title,
            required_skills=temp_job.required_skills,
            evaluation=retry_normalized,
            iteration=2,
            confidence_threshold=0.75,
            request_id=f"app-{application_id}",
        )
        normalized = retry_normalized

    normalized["confidence_score"] = val_result.confidence_score
    normalized["validator_notes"] = val_result.critique
    normalized["execution_plan"] = plan.model_dump()
    
    # 6. Evaluate State-Based Conditional Routing Decision
    fit_score = normalized.get("fit_score", 0)
    routing = evaluate_routing_decision(
        fit_score=fit_score,
        confidence_score=val_result.confidence_score,
        hallucination_detected=val_result.hallucination_detected,
    )
    
    if routing == RoutingDecision.DIRECT_INTERVIEW_FAST_TRACK:
        normalized["hitl_status"] = "fast_track_interview"
    elif routing == RoutingDecision.HR_REVIEW_REQUIRED:
        normalized["hitl_status"] = "pending_hr_review"
    else:
        normalized["hitl_status"] = "completed"

    # 5. Start a new transaction to write results
    # 7. Start a new transaction to write results
    # Re-fetch application and existing to ensure they are attached to the current session transaction
    application = session.get(CandidateApplication, application_id)
    existing = session.exec(
        select(ApplicationAIAnalysis).where(ApplicationAIAnalysis.application_id == application_id)
    ).first()

    return _upsert_analysis(session, application, normalized, existing)


def get_analysis_for_application(session: Session, application_id: int) -> ApplicationAIAnalysis | None:
    return session.exec(
        select(ApplicationAIAnalysis).where(ApplicationAIAnalysis.application_id == application_id)
    ).first()


def rank_applications_for_job(session: Session, job_id: int) -> list[dict[str, Any]]:
    applications = session.exec(
        select(CandidateApplication).where(CandidateApplication.job_id == job_id)
    ).all()
    ranked: list[dict[str, Any]] = []
    for application in applications:
        analysis = get_analysis_for_application(session, application.id)
        if analysis is None or analysis.status in {"pending", "failed"}:
            analysis = analyze_application(session, application.id, force=False)
        candidate = session.get(User, application.candidate_user_id)
        ranked.append(
            {
                "application": application_payload(session, application, include_resume=False),
                "candidate": {
                    "id": candidate.id if candidate else application.candidate_user_id,
                    "username": candidate.username if candidate else "",
                },
                "analysis": analysis_payload(analysis),
            }
        )

    ranked.sort(
        key=lambda item: (
            int(item["analysis"].get("fit_score", 0) or 0),
            _recommendation_rank(item["analysis"].get("recommendation", "Consider")),
        ),
        reverse=True,
    )
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return ranked


def application_payload(session: Session, application: CandidateApplication, include_resume: bool = True) -> dict[str, Any]:
    job = session.get(JobPosting, application.job_id)
    candidate = session.get(User, application.candidate_user_id)
    analysis = get_analysis_for_application(session, application.id)
    interview = session.exec(select(InterviewSession).where(InterviewSession.application_id == application.id)).first()
    payload = {
        "id": application.id,
        "candidate_user_id": application.candidate_user_id,
        "candidate_username": candidate.username if candidate else "",
        "job_id": application.job_id,
        "job_title": job.title if job else "",
        "department": job.department if job else "",
        "application_date": application.application_date.isoformat() if application.application_date else None,
        "status": application.status,
        "ai_analysis": analysis_payload(analysis) if analysis else None,
        "interview_status": interview.status if interview else "pending",
        "interview_score": interview.avg_score if interview else None,
        "interview_session_id": interview.id if interview else None,
        "interview_token": interview.session_token if interview else None,
    }
    if include_resume:
        payload["resume_text"] = application.resume_text
    return payload


def analysis_payload(analysis: ApplicationAIAnalysis | None) -> dict[str, Any] | None:
    if not analysis:
        return None
    return {
        "id": analysis.id,
        "application_id": analysis.application_id,
        "fit_score": analysis.fit_score,
        "recommendation": analysis.recommendation,
        "summary": analysis.summary,
        "strengths": _load_json(analysis.strengths, []),
        "weaknesses": _load_json(analysis.weaknesses, []),
        "missing_skills": _load_json(analysis.missing_skills, []),
        "observations": _load_json(analysis.observations, []),
        "interview_prep": {
            "technical_questions": _load_json(analysis.technical_questions, []),
            "behavioral_questions": _load_json(analysis.behavioral_questions, []),
            "probing_areas": _load_json(analysis.probing_areas, []),
        },
        "status": analysis.status,
        "error_message": analysis.error_message,
        "source": analysis.source,
        "confidence_score": analysis.confidence_score,
        "validator_notes": analysis.validator_notes,
        "execution_plan": _load_json(analysis.execution_plan, None) if analysis.execution_plan else None,
        "hitl_status": analysis.hitl_status,
        "hitl_reviewed_by": analysis.hitl_reviewed_by,
        "hitl_reviewed_at": analysis.hitl_reviewed_at.isoformat() if analysis.hitl_reviewed_at else None,
        "updated_at": analysis.updated_at.isoformat() if analysis.updated_at else None,
    }


def _run_crewai_analysis(resume_text: str, job: JobPosting) -> dict[str, Any]:
    from crewai import Crew

    from agents.recruitment_analyst import create_recruitment_analyst
    from tasks.recruitment_task import create_application_analysis_task

    agent = create_recruitment_analyst()
    parsed = parse_resume(resume_text)
    task = create_application_analysis_task(
        agent,
        resume_text,
        {
            "title": job.title,
            "description": job.description,
            "required_skills": job.required_skills,
            "department": job.department,
            "salary_range": job.salary_range,
            "experience_required": job.experience_required,
        },
        parsed,
    )
    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    result = crew.kickoff()
    raw = getattr(result, "raw", str(result)).strip()
    parsed_json = _extract_json(raw)
    if not parsed_json:
        raise ValueError("AI returned non-JSON output")
    return parsed_json


def _normalize_ai_payload(
    payload: Any,
    resume_text: str,
    job: JobPosting,
    source: str,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("AI payload was not an object")

    fallback = _fallback_analysis(resume_text, job)
    score = _clamp_int(payload.get("fit_score"), fallback["fit_score"])
    recommendation = str(payload.get("recommendation") or _recommendation_for_score(score)).strip()
    if recommendation not in RECOMMENDATIONS:
        recommendation = _recommendation_for_score(score)

    prep = payload.get("interview_prep") if isinstance(payload.get("interview_prep"), dict) else {}
    
    # Check if AI explicitly returned lists (even if empty) to avoid incorrect fallback overrides
    strengths = _string_list(payload.get("strengths")) if payload.get("strengths") is not None else fallback["strengths"]
    weaknesses = _string_list(payload.get("weaknesses")) if payload.get("weaknesses") is not None else fallback["weaknesses"]
    missing_skills = _string_list(payload.get("missing_skills")) if payload.get("missing_skills") is not None else fallback["missing_skills"]
    observations = _string_list(payload.get("observations")) if payload.get("observations") is not None else fallback["observations"]
    
    tech_q = _string_list(prep.get("technical_questions")) if prep.get("technical_questions") is not None else fallback["technical_questions"]
    behav_q = _string_list(prep.get("behavioral_questions")) if prep.get("behavioral_questions") is not None else fallback["behavioral_questions"]
    prob_a = _string_list(prep.get("probing_areas")) if prep.get("probing_areas") is not None else fallback["probing_areas"]

    return {
        "fit_score": score,
        "recommendation": recommendation,
        "summary": str(payload.get("summary") or fallback["summary"]).strip()[:2000],
        "strengths": strengths,
        "weaknesses": weaknesses,
        "missing_skills": missing_skills,
        "observations": observations,
        "technical_questions": tech_q,
        "behavioral_questions": behav_q,
        "probing_areas": prob_a,
        "status": "completed",
        "source": source,
        "error_message": None,
    }


def _fallback_analysis(resume_text: str, job: JobPosting) -> dict[str, Any]:
    parsed = parse_resume(resume_text)
    resume_terms = _term_set(" ".join([
        resume_text,
        " ".join(parsed.get("skills", [])),
        " ".join(parsed.get("experience", [])),
        " ".join(parsed.get("projects", [])),
        parsed.get("summary", ""),
    ]))
    required_skills = _split_required_skills(job.required_skills)
    matched = [skill for skill in required_skills if _skill_matches(skill, resume_terms)]
    missing = [skill for skill in required_skills if skill not in matched]

    skill_score = round((len(matched) / len(required_skills)) * 45) if required_skills else 24
    experience_items = len(parsed.get("experience", [])) + len(parsed.get("projects", []))
    experience_score = min(25, experience_items * 5)
    education_score = 10 if parsed.get("education") else 4
    job_title_terms = _term_set(job.title)
    title_overlap = len(job_title_terms.intersection(resume_terms))
    relevance_score = min(20, title_overlap * 5 + (8 if matched else 0))
    score = max(0, min(100, skill_score + experience_score + education_score + relevance_score))

    strengths = []
    if matched:
        strengths.append(f"Shows evidence for key skills: {', '.join(matched[:5])}.")
    if parsed.get("projects"):
        strengths.append("Includes project experience recruiters can probe.")
    if parsed.get("experience"):
        strengths.append("Includes experience entries that can support role-fit discussion.")
    if not strengths:
        strengths.append("Resume has enough text to begin screening, but evidence is limited.")

    weaknesses = []
    if missing:
        weaknesses.append(f"Does not clearly prove: {', '.join(missing[:5])}.")
    if not parsed.get("education"):
        weaknesses.append("Education details are not clearly detected.")
    if experience_items < 2:
        weaknesses.append("Limited project or work evidence detected for deeper validation.")
    if not weaknesses:
        weaknesses.append("No major deterministic weakness detected; validate depth in interview.")

    recommendation = _recommendation_for_score(score)
    return {
        "fit_score": score,
        "recommendation": recommendation,
        "summary": (
            f"{recommendation}: candidate shows {len(matched)} of {len(required_skills)} required skills clearly. "
            "Use interview questions to validate depth, ownership, and practical application."
        ),
        "strengths": strengths[:5],
        "weaknesses": weaknesses[:5],
        "missing_skills": missing[:8],
        "observations": [
            f"Detected skills: {', '.join(parsed.get('skills', [])[:8]) or 'not clearly structured'}.",
            f"Relevant resume evidence items detected: {experience_items}.",
        ],
        "technical_questions": _technical_questions(job, matched, missing),
        "behavioral_questions": [
            "Tell me about a time you owned a task from requirement to delivery. What tradeoffs did you make?",
            "Describe a project where you had to learn a new tool or domain quickly. How did you validate your work?",
        ],
        "probing_areas": [
            "Depth behind listed technical skills",
            "Ownership and measurable impact",
            "Fit against missing or weakly proven requirements",
        ],
        "status": "completed",
        "source": "fallback",
        "error_message": None,
    }


def _technical_questions(job: JobPosting, matched: list[str], missing: list[str]) -> list[str]:
    questions = []
    focus = matched[:2] or _split_required_skills(job.required_skills)[:2]
    for skill in focus:
        questions.append(f"Walk me through a real project where you used {skill}. What design decisions mattered?")
    for skill in missing[:2]:
        questions.append(f"This role needs {skill}. What adjacent experience do you have, and how would you ramp up?")
    questions.append(f"How would you approach the first 30 days in this {job.title} role?")
    return questions[:5]


def _upsert_analysis(
    session: Session,
    application: CandidateApplication,
    payload: dict[str, Any],
    existing: ApplicationAIAnalysis | None,
) -> ApplicationAIAnalysis:
    now = datetime.utcnow()
    analysis = existing or ApplicationAIAnalysis(application_id=application.id, created_at=now)
    analysis.fit_score = _clamp_int(payload.get("fit_score"), 0)
    analysis.recommendation = str(payload.get("recommendation") or "Consider")[:40]
    analysis.summary = str(payload.get("summary") or "")[:4000]
    analysis.strengths = _dump_json(payload.get("strengths", []))
    analysis.weaknesses = _dump_json(payload.get("weaknesses", []))
    analysis.missing_skills = _dump_json(payload.get("missing_skills", []))
    analysis.observations = _dump_json(payload.get("observations", []))
    analysis.technical_questions = _dump_json(payload.get("technical_questions", []))
    analysis.behavioral_questions = _dump_json(payload.get("behavioral_questions", []))
    analysis.probing_areas = _dump_json(payload.get("probing_areas", []))
    analysis.status = str(payload.get("status") or "completed")[:30]
    analysis.error_message = payload.get("error_message")
    analysis.source = str(payload.get("source") or "fallback")[:40]
    analysis.confidence_score = payload.get("confidence_score")
    analysis.validator_notes = payload.get("validator_notes")
    exec_plan = payload.get("execution_plan")
    analysis.execution_plan = exec_plan if isinstance(exec_plan, str) else _dump_json(exec_plan) if exec_plan else None
    analysis.hitl_status = str(payload.get("hitl_status") or "pending")[:30]
    analysis.hitl_reviewed_by = payload.get("hitl_reviewed_by")
    analysis.hitl_reviewed_at = payload.get("hitl_reviewed_at")
    analysis.updated_at = now
    session.add(analysis)
    session.commit()
    session.refresh(analysis)
    _sync_candidate_profile_to_rag(session, application, analysis)
    return analysis


def _sync_candidate_profile_to_rag(
    session: Session,
    application: CandidateApplication,
    analysis: ApplicationAIAnalysis,
) -> None:
    try:
        from src.services.rag.sync_service import RAGSyncService

        job = session.get(JobPosting, application.job_id)
        RAGSyncService().sync_candidate_profile(application, analysis, job)
    except Exception as exc:  # noqa: BLE001
        logger.warning("RAG candidate profile sync failed application_id=%s error=%s", application.id, exc)


def _failed_payload(message: str) -> dict[str, Any]:
    return {
        "fit_score": 0,
        "recommendation": "Consider",
        "summary": "AI analysis could not be completed.",
        "strengths": [],
        "weaknesses": [message],
        "missing_skills": [],
        "observations": [],
        "technical_questions": [],
        "behavioral_questions": [],
        "probing_areas": [],
        "status": "failed",
        "source": "system",
        "error_message": message,
    }


def _recommendation_for_score(score: int) -> str:
    if score >= 85:
        return "Strongly Recommended"
    if score >= 70:
        return "Recommended"
    if score >= 45:
        return "Consider"
    return "Reject"


def _recommendation_rank(value: str) -> int:
    return {
        "Strongly Recommended": 4,
        "Recommended": 3,
        "Consider": 2,
        "Reject": 1,
    }.get(value, 0)


def _split_required_skills(value: str) -> list[str]:
    parts = re.split(r"[,|;/\n]+", value or "")
    return _dedupe([part.strip(" .:-") for part in parts if part.strip(" .:-")])


FILLER_WORDS = {
    "experience", "with", "knowledge", "of", "strong", "understanding", "in",
    "skills", "ability", "to", "demonstrated", "proven", "hands-on", "using",
    "exposure", "familiarity", "practical"
}


def _skill_matches(skill: str, resume_terms: set[str]) -> bool:
    skill_terms = _term_set(skill)
    # Remove common filler words to focus on the actual skill name
    core_terms = {term for term in skill_terms if term not in FILLER_WORDS}
    if not core_terms:
        core_terms = skill_terms
    return bool(core_terms and core_terms.issubset(resume_terms))


def _term_set(text: str) -> set[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9+.#-]{1,}", text or "")
    terms = set()
    for w in words:
        w_low = w.lower().rstrip(".")
        if not w_low:
            continue
        # Simple singularization to avoid singular/plural mismatches (e.g. apis -> api)
        if w_low.endswith("s") and len(w_low) > 3 and not w_low.endswith("ss"):
            w_low = w_low[:-1]
        terms.add(w_low)
    return terms


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


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return _dedupe([str(item).strip() for item in value if str(item).strip()])[:8]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        key = item.lower()
        if key and key not in seen:
            seen.add(key)
            output.append(item)
    return output


def _clamp_int(value: Any, default: int = 0) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = default
    return max(0, min(100, number))


def _dump_json(value: Any) -> str:
    if isinstance(value, list):
        return json.dumps([str(item) for item in value if str(item).strip()], ensure_ascii=True)
    return json.dumps([], ensure_ascii=True)


def _load_json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default
