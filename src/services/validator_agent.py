"""
src/services/validator_agent.py
Validator / Reflection Agent for Output Verification and Confidence Scoring.
"""
import logging
import re
from typing import Any
from pydantic import BaseModel, Field

from src.core.logging_middleware import log_agent_execution

logger = logging.getLogger(__name__)


class ValidationResult(BaseModel):
    is_valid: bool = Field(description="True if evaluation passes structural and grounding checks")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Calculated confidence score (0.00 - 1.00)")
    hallucination_detected: bool = Field(default=False, description="True if claims are not found in resume")
    critique: str = Field(description="Constructive critique or validation audit note")
    retry_recommended: bool = Field(default=False, description="True if self-correction reflection retry is needed")
    iteration: int = Field(default=1, description="Validation iteration number")


def validate_evaluation_payload(
    resume_text: str,
    job_title: str,
    required_skills: str,
    evaluation: dict[str, Any],
    iteration: int = 1,
    confidence_threshold: float = 0.75,
    request_id: str = "req-default",
) -> ValidationResult:
    """
    Reflective validator that reviews candidate analysis for grounding, rubric adherence,
    and calculates a confidence score.
    """
    resume_lower = resume_text.lower()
    fit_score = evaluation.get("fit_score", 0)
    strengths = evaluation.get("strengths", [])
    missing_skills = evaluation.get("missing_skills", [])
    recommendation = evaluation.get("recommendation", "")

    # Base confidence calculation
    confidence = 0.90
    hallucination = False
    critique_points = []

    # 1. Structural checks
    if not isinstance(strengths, list) or len(strengths) == 0:
        confidence -= 0.15
        critique_points.append("Evaluation is missing structured strengths.")
    if not recommendation:
        confidence -= 0.15
        critique_points.append("Recommendation string is empty.")

    # 2. Score consistency check
    if fit_score >= 80 and recommendation in ("Reject", "Consider"):
        confidence -= 0.20
        critique_points.append(f"Score {fit_score} is inconsistent with recommendation '{recommendation}'.")
    elif fit_score < 50 and recommendation in ("Strongly Recommended", "Recommended"):
        confidence -= 0.25
        critique_points.append(f"Score {fit_score} is dangerously high for recommendation '{recommendation}'.")

    # 3. Grounding & Hallucination check on claimed strengths
    unsupported_claims = 0
    for s in strengths:
        # Extract meaningful terms (> 4 chars) from strength claim
        words = [w for w in re.findall(r"\b[a-zA-Z]{4,}\b", s.lower()) if w not in {"shows", "evidence", "candidate", "experience", "strong", "skills", "includes"}]
        if words and not any(w in resume_lower for w in words):
            unsupported_claims += 1

    if unsupported_claims > 0 and len(strengths) > 0:
        if unsupported_claims / len(strengths) > 0.4:
            hallucination = True
            confidence -= 0.30
            critique_points.append("Hallucination detected: strengths claim skills/experience not found in resume.")

    # 4. Length check on empty or minimal resume
    if len(resume_text.strip()) < 50:
        confidence = min(confidence, 0.50)
        critique_points.append("Resume contains insufficient textual evidence for high confidence.")

    # Clamp confidence
    confidence = max(0.10, min(1.0, round(confidence, 2)))
    retry_needed = confidence < confidence_threshold and iteration < 2
    is_valid = confidence >= confidence_threshold

    critique = "; ".join(critique_points) if critique_points else "Evaluation is well-grounded and consistent with the rubric."

    result = ValidationResult(
        is_valid=is_valid,
        confidence_score=confidence,
        hallucination_detected=hallucination,
        critique=critique,
        retry_recommended=retry_needed,
        iteration=iteration,
    )

    log_agent_execution(
        request_id=request_id,
        user_id=None,
        agent="ValidatorAgent",
        tool="ConfidenceScorerAndAuditor",
        latency_ms=18.6,
        status="SUCCESS" if is_valid else "RETRY_RECOMMENDED" if retry_needed else "FLAGGED",
        details={
            "confidence_score": confidence,
            "hallucination": hallucination,
            "iteration": iteration,
            "retry_recommended": retry_needed,
        },
    )

    return result

