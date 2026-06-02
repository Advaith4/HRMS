import json
import logging
import re
from typing import Any

from src.models import Employee

logger = logging.getLogger(__name__)


POLICY_KNOWLEDGE = {
    "leave": "Employees can submit leave requests from the portal. HR or managers approve or reject pending requests.",
    "attendance": "Employees should check in at the start of the workday and check out when they finish.",
    "hours": "Standard working hours depend on company policy. Confirm team-specific timing with HR.",
    "payroll": "Payroll details are handled by HR and are not part of the current self-service portal.",
    "default": "TalentForge currently supports employee profile, attendance, leave requests, and skill development workflows.",
}


def analyze_skill_gap(employee: Employee, role_expectations: str = "") -> dict[str, Any]:
    expectations = role_expectations.strip() or employee.designation or "Current role"
    try:
        ai_payload = _run_ai_skill_gap(employee, expectations)
        return _normalize_skill_gap(ai_payload, employee, expectations, source="ai")
    except Exception as exc:
        logger.warning("Skill gap AI failed; using fallback. employee_id=%s error=%s", employee.id, exc)
        payload = _fallback_skill_gap(employee, expectations)
        payload["error_message"] = f"AI provider unavailable; deterministic fallback used. {exc}"
        return payload


def answer_hr_question(question: str) -> dict[str, str]:
    normalized = question.strip()
    if not normalized:
        return {
            "answer": "Please ask a question about attendance, leave, working hours, or HR support.",
            "source": "fallback",
        }

    lowered = normalized.lower()
    if any(token in lowered for token in ("leave", "vacation", "sick")):
        topic = "leave"
    elif any(token in lowered for token in ("attendance", "check in", "check-in", "check out", "check-out")):
        topic = "attendance"
    elif any(token in lowered for token in ("hour", "timing", "shift")):
        topic = "hours"
    elif any(token in lowered for token in ("salary", "payroll", "payslip")):
        topic = "payroll"
    else:
        topic = "default"

    return {
        "answer": POLICY_KNOWLEDGE[topic],
        "source": "fallback",
    }


def _run_ai_skill_gap(employee: Employee, role_expectations: str) -> dict[str, Any]:
    from crewai import Agent, Crew, Task
    from src.config import settings

    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured")

    agent = Agent(
        role="TalentForge Employee Development Analyst",
        goal="Compare employee skills with role expectations and produce practical development guidance.",
        backstory="You are an HR development analyst who gives concise, grounded upskilling recommendations.",
        verbose=False,
        allow_delegation=False,
    )
    task = Task(
        description=(
            "Return strict JSON with keys: missing_skills, growth_areas, learning_suggestions, summary.\n"
            f"Employee designation: {employee.designation}\n"
            f"Employee skills: {employee.skills}\n"
            f"Role expectations: {role_expectations}\n"
        ),
        expected_output="Strict JSON only.",
        agent=agent,
    )
    result = Crew(agents=[agent], tasks=[task], verbose=False).kickoff()
    raw = getattr(result, "raw", str(result)).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError("AI returned non-JSON output")
        return json.loads(match.group())


def _normalize_skill_gap(payload: Any, employee: Employee, expectations: str, source: str) -> dict[str, Any]:
    fallback = _fallback_skill_gap(employee, expectations)
    if not isinstance(payload, dict):
        return fallback
    return {
        "role_expectations": expectations,
        "missing_skills": _string_list(payload.get("missing_skills")) or fallback["missing_skills"],
        "growth_areas": _string_list(payload.get("growth_areas")) or fallback["growth_areas"],
        "learning_suggestions": _string_list(payload.get("learning_suggestions")) or fallback["learning_suggestions"],
        "summary": str(payload.get("summary") or fallback["summary"]).strip()[:2000],
        "source": source,
        "error_message": None,
    }


def _fallback_skill_gap(employee: Employee, expectations: str) -> dict[str, Any]:
    current = _term_set(employee.skills)
    expected = _term_set(expectations)
    missing = sorted(expected - current)[:8]
    growth = missing[:4] or ["role-specific depth", "documentation", "cross-functional communication"]
    suggestions = [
        f"Build a small work sample or internal note covering {skill}." for skill in growth[:3]
    ]
    if not suggestions:
        suggestions = ["Review role expectations with HR and define one measurable growth target."]
    summary = (
        "Skill gap analysis is based on stored employee skills and role expectations. "
        f"{len(missing)} potential gaps were detected."
    )
    return {
        "role_expectations": expectations,
        "missing_skills": missing,
        "growth_areas": growth,
        "learning_suggestions": suggestions,
        "summary": summary,
        "source": "fallback",
        "error_message": None,
    }


def _term_set(text: str) -> set[str]:
    return {
        word.lower()
        for word in re.findall(r"[A-Za-z][A-Za-z0-9+.#-]{1,}", text or "")
        if len(word) > 1
    }


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()][:8]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []
