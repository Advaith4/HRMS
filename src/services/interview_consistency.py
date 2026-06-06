"""
src/services/interview_consistency.py

Compares resume claims against interview evidence to produce a credibility score.
Not lie detection — only evaluates whether skills were demonstrated during interview.
"""

import json
import logging
import re
from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from src.models import (
    CandidateApplication,
    CandidateCredibilityReport,
    InterviewSession,
    JobPosting,
    Resume,
    User,
)

logger = logging.getLogger(__name__)

RECOMMENDATIONS = ("Strongly Supported", "Well Supported", "Partially Supported", "Weakly Supported", "Insufficient Evidence")


def analyze_credibility(
    session_db: Session,
    session_id: int,
    force: bool = False,
    allow_ai: bool = True,
) -> CandidateCredibilityReport:
    interview_session = session_db.get(InterviewSession, session_id)
    if not interview_session:
        raise ValueError("Interview session not found")

    existing = session_db.exec(
        select(CandidateCredibilityReport).where(
            CandidateCredibilityReport.session_id == session_id
        )
    ).first()
    if existing and existing.status == "completed" and not force:
        return existing

    messages = _safe_load_json(interview_session.messages, [])
    avg_score = interview_session.avg_score

    resume = session_db.exec(
        select(Resume).where(Resume.user_id == interview_session.user_id)
    ).first()
    resume_text = resume.raw_text if resume else ""

    application = session_db.exec(
        select(CandidateApplication).where(
            CandidateApplication.candidate_user_id == interview_session.user_id
        )
    ).first()
    job = session_db.get(JobPosting, application.job_id) if application else None

    resume_score = _estimate_resume_score(resume_text, messages, job)

    if not allow_ai:
        logger.info("credibility_cache_miss_fast_path session_id=%s allow_ai=false", session_id)
        normalized = _fallback_credibility(resume_text, messages, avg_score, resume_score)
    else:
        try:
            result = _run_ai_credibility(resume_text, messages, job)
            normalized = _normalize_credibility(result, resume_text, messages, avg_score, resume_score, source="ai")
        except Exception as exc:
            logger.warning("AI credibility analysis failed: %s", exc)
            normalized = _fallback_credibility(resume_text, messages, avg_score, resume_score)
            normalized["error_message"] = str(exc)

    report = _upsert_report(session_db, interview_session, normalized, existing)
    return report


def credibility_payload(report: CandidateCredibilityReport | None) -> dict[str, Any] | None:
    if not report:
        return None
    return {
        "id": report.id,
        "candidate_id": report.candidate_id,
        "session_id": report.session_id,
        "credibility_score": report.credibility_score,
        "supported_claims": _safe_load_json(report.supported_claims, []),
        "weak_claims": _safe_load_json(report.weak_claims, []),
        "missing_evidence": _safe_load_json(report.missing_evidence, []),
        "followup_topics": _safe_load_json(report.followup_topics, []),
        "resume_score": report.resume_score,
        "interview_avg_score": report.interview_avg_score,
        "recommendation": report.recommendation,
        "status": report.status,
        "error_message": report.error_message,
        "source": report.source,
        "created_at": report.created_at.isoformat() if report.created_at else None,
    }


def _run_ai_credibility(
    resume_text: str,
    messages: list[dict[str, Any]],
    job: JobPosting | None,
) -> dict[str, Any]:
    from crewai import Crew
    from crewai import Agent as CrewAgent
    from crewai import Task as CrewTask

    claims = _extract_claims(resume_text)
    qa_pairs = _extract_qa_pairs(messages)
    scores_summary = _summarize_scores(qa_pairs)

    job_context = ""
    if job:
        job_context = f"""
Job Title: {job.title}
Required Skills: {job.required_skills}
Description: {job.description[:500]}
"""

    prompt = f"""You are a hiring intelligence analyst. Compare the candidate's resume claims against their interview responses.

JOB CONTEXT:
{job_context}

RESUME CLAIMS (skills claimed):
{json.dumps(claims, indent=2)}

INTERVIEW QUESTIONS AND ANSWERS WITH SCORES:
{json.dumps(qa_pairs, indent=2)}

SCORES SUMMARY:
{json.dumps(scores_summary, indent=2)}

For each claim, determine the level of evidence demonstrated in the interview:
- "strong": Candidate explained concepts clearly, gave specific examples, scored well
- "moderate": Candidate showed decent knowledge but lacked depth
- "weak": Candidate only knows terminology, no real understanding demonstrated
- "none": No interview evidence for this claim

Return ONLY valid JSON with this exact structure:
{{
  "credibility_score": <0-100>,
  "supported_claims": [{{"claim": "...", "evidence": "strong|moderate", "explanation": "..."}}],
  "weak_claims": [{{"claim": "...", "evidence": "weak", "explanation": "..."}}],
  "missing_evidence": [{{"claim": "...", "evidence": "none", "explanation": "..."}}],
  "followup_topics": ["topic1", "topic2"]
}}"""

    agent = CrewAgent(
        role="Credibility Analyst",
        goal="Compare resume claims against interview evidence objectively",
        backstory="Expert hiring analyst who evaluates whether candidates demonstrated their claimed skills during interviews.",
        verbose=False,
        allow_delegation=False,
    )
    task = CrewTask(
        description=prompt,
        expected_output="Strict JSON with credibility_score, supported_claims, weak_claims, missing_evidence, followup_topics.",
        agent=agent,
    )
    crew = Crew(agents=[agent], tasks=[task], verbose=False)
    result = crew.kickoff()
    raw = getattr(result, "raw", str(result)).strip()
    parsed = _extract_json(raw)
    if not parsed:
        raise ValueError("AI returned non-JSON output")
    return parsed


def _extract_claims(resume_text: str) -> list[str]:
    if not resume_text:
        return []
    tech_patterns = [
        r"\b(Python|JavaScript|TypeScript|Java|C#?\+?\+?|Go|Rust|Ruby|PHP|Swift|Kotlin|Scala)\b",
        r"\b(React|Angular|Vue|Svelte|Next\.?js|Nuxt|Express|Django|Flask|FastAPI|Spring|Laravel|Rails)\b",
        r"\b(AWS|Azure|GCP|Docker|Kubernetes|Terraform|Ansible|Jenkins|GitHub Actions)\b",
        r"\b(PostgreSQL|MySQL|MongoDB|Redis|Cassandra|Elasticsearch|SQLite|DynamoDB)\b",
        r"\b(Docker|Kubernetes|Podman|Nomad)\b",
        r"\b(GraphQL|REST|gRPC|WebSocket|OAuth|JWT|OpenAPI)\b",
        r"\b(Redis|RabbitMQ|Kafka|NATS|Celery)\b",
        r"\b(Git|Linux|Bash|Nginx|Apache|Prometheus|Grafana)\b",
        r"\b(TensorFlow|PyTorch|scikit-learn|Pandas|NumPy|LangChain|LLM|OpenAI)\b",
        r"\b(CI/CD|Agile|Scrum|TDD|BDD|DDD|Microservices|Serverless)\b",
    ]
    found: set[str] = set()
    for pattern in tech_patterns:
        for match in re.finditer(pattern, resume_text, re.IGNORECASE):
            found.add(match.group(0))
    return sorted(found, key=lambda x: -len(x))


def _extract_qa_pairs(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pairs = []
    current_q = None
    for msg in messages:
        role = (msg.get("role") or "").lower()
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        if role in ("interviewer", "assistant", "ai", "coach"):
            current_q = content
        elif role in ("candidate", "user") and current_q:
            pairs.append({
                "question": current_q[:200],
                "answer": content[:500],
                "score": msg.get("score"),
            })
            current_q = None
    return pairs


def _summarize_scores(qa_pairs: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [p["score"] for p in qa_pairs if p.get("score") is not None]
    if not scores:
        return {"count": 0, "avg": None, "min": None, "max": None}
    return {
        "count": len(scores),
        "avg": round(sum(scores) / len(scores), 1),
        "min": min(scores),
        "max": max(scores),
    }


def _normalize_credibility(
    payload: Any,
    resume_text: str,
    messages: list[dict[str, Any]],
    avg_score: float | None,
    resume_score: int,
    source: str,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Payload was not an object")

    fallback = _fallback_credibility(resume_text, messages, avg_score, resume_score)

    score = _clamp_int(payload.get("credibility_score"), fallback["credibility_score"])
    recommendation = _recommendation_for_score(score)

    return {
        "credibility_score": score,
        "supported_claims": _claim_list(payload.get("supported_claims")) or fallback["supported_claims"],
        "weak_claims": _claim_list(payload.get("weak_claims")) or fallback["weak_claims"],
        "missing_evidence": _claim_list(payload.get("missing_evidence")) or fallback["missing_evidence"],
        "followup_topics": _string_list(payload.get("followup_topics")) or fallback["followup_topics"],
        "resume_score": max(0, min(100, resume_score)),
        "interview_avg_score": avg_score,
        "recommendation": recommendation,
        "status": "completed",
        "source": source,
        "error_message": None,
    }


def _fallback_credibility(
    resume_text: str,
    messages: list[dict[str, Any]],
    avg_score: float | None,
    resume_score: int,
) -> dict[str, Any]:
    claims = _extract_claims(resume_text)
    qa_pairs = _extract_qa_pairs(messages)
    all_text = " ".join(p["answer"] for p in qa_pairs).lower()

    supported = []
    weak = []
    missing = []
    matched_count = 0

    for claim in claims:
        claim_lower = claim.lower()
        answer_mentions = all_text.count(claim_lower)
        relevant_scores = [
            p["score"] for p in qa_pairs
            if p["score"] is not None and claim_lower in p["answer"].lower()
        ]
        avg_claim_score = sum(relevant_scores) / len(relevant_scores) if relevant_scores else None

        if avg_claim_score and avg_claim_score >= 6 and answer_mentions > 1:
            supported.append({"claim": claim, "evidence": "strong", "explanation": f"Scored {avg_claim_score:.0f}/10 with {answer_mentions} mentions in answers."})
            matched_count += 1
        elif avg_claim_score and avg_claim_score >= 4 and answer_mentions >= 1:
            weak.append({"claim": claim, "evidence": "weak", "explanation": f"Scored only {avg_claim_score:.0f}/10, limited depth shown."})
            matched_count += 0.5
        elif answer_mentions > 0:
            weak.append({"claim": claim, "evidence": "weak", "explanation": f"Mentioned {answer_mentions} time(s) but no score recorded."})
            matched_count += 0.3
        else:
            missing.append({"claim": claim, "evidence": "none", "explanation": "No interview evidence for this claim."})

    score = int((matched_count / max(len(claims), 1)) * 100) if claims else 0
    if avg_score is not None:
        score = int(score * 0.6 + avg_score * 10 * 0.4)
    score = max(0, min(100, score))

    return {
        "credibility_score": score,
        "supported_claims": supported[:8],
        "weak_claims": weak[:8],
        "missing_evidence": missing[:8],
        "followup_topics": [c["claim"] for c in weak[:3] + missing[:3]],
        "resume_score": max(0, min(100, resume_score)),
        "interview_avg_score": avg_score,
        "recommendation": _recommendation_for_score(score),
        "status": "completed",
        "source": "fallback",
        "error_message": None,
    }


def _estimate_resume_score(resume_text: str, messages: list[dict[str, Any]], job: JobPosting | None) -> int:
    if not resume_text:
        return 0
    score = 70
    word_count = len(resume_text.split())
    if word_count < 50:
        score -= 20
    elif word_count > 200:
        score += 5
    if job and job.required_skills:
        job_skills = {s.strip().lower() for s in re.split(r"[,|;/\n]+", job.required_skills) if s.strip()}
        resume_lower = resume_text.lower()
        matched = sum(1 for s in job_skills if s in resume_lower)
        if job_skills:
            score += int((matched / len(job_skills)) * 15)
    return max(0, min(100, score))


def _upsert_report(
    session_db: Session,
    interview_session: InterviewSession,
    payload: dict[str, Any],
    existing: CandidateCredibilityReport | None,
) -> CandidateCredibilityReport:
    now = datetime.utcnow()
    report = existing or CandidateCredibilityReport(
        candidate_id=interview_session.user_id,
        session_id=interview_session.id,
        created_at=now,
    )
    report.credibility_score = _clamp_int(payload.get("credibility_score"), 0)
    report.supported_claims = _dump_json(payload.get("supported_claims", []))
    report.weak_claims = _dump_json(payload.get("weak_claims", []))
    report.missing_evidence = _dump_json(payload.get("missing_evidence", []))
    report.followup_topics = _dump_json(payload.get("followup_topics", []))
    report.resume_score = _clamp_int(payload.get("resume_score"), 0)
    report.interview_avg_score = payload.get("interview_avg_score")
    report.recommendation = str(payload.get("recommendation") or "Insufficient Evidence")[:40]
    report.status = str(payload.get("status") or "completed")[:30]
    report.error_message = payload.get("error_message")
    report.source = str(payload.get("source") or "fallback")[:40]
    report.updated_at = now
    session_db.add(report)
    session_db.commit()
    session_db.refresh(report)
    return report


def _recommendation_for_score(score: int) -> str:
    if score >= 90:
        return "Strongly Supported"
    if score >= 75:
        return "Well Supported"
    if score >= 60:
        return "Partially Supported"
    if score >= 40:
        return "Weakly Supported"
    return "Insufficient Evidence"


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


def _claim_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict) and item.get("claim")][:8]
    return []


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()][:8]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _clamp_int(value: Any, default: int = 0) -> int:
    try:
        num = int(float(value))
    except (TypeError, ValueError):
        num = default
    return max(0, min(100, num))


def _dump_json(value: Any) -> str:
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=True)
    return json.dumps([], ensure_ascii=True)


def _safe_load_json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default
