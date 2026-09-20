"""
src/services/workflow_state.py
State Management & Conditional Decision Routing Engine for Multi-Agent Workflows.
"""
import logging
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RoutingDecision(str, Enum):
    DIRECT_INTERVIEW_FAST_TRACK = "DIRECT_INTERVIEW_FAST_TRACK"
    HR_REVIEW_REQUIRED = "HR_REVIEW_REQUIRED"
    RETRY_REFLECTION = "RETRY_REFLECTION"
    REJECT_RECOMMENDED = "REJECT_RECOMMENDED"


class WorkflowState(BaseModel):
    """Immutable state snapshot passed across agents during recruitment evaluation."""
    application_id: int
    candidate_id: int
    job_id: int
    job_title: str
    required_skills: str
    resume_text: str
    extracted_features: dict[str, Any] = Field(default_factory=dict)
    fit_score: int = Field(default=0, ge=0, le=100)
    recommendation: str = Field(default="Consider")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    hallucination_detected: bool = Field(default=False)
    routing_decision: RoutingDecision = Field(default=RoutingDecision.HR_REVIEW_REQUIRED)
    iteration_count: int = Field(default=1)
    execution_timeline: list[dict[str, Any]] = Field(default_factory=list)


def evaluate_routing_decision(
    fit_score: int,
    confidence_score: float,
    hallucination_detected: bool = False,
    iteration: int = 1,
) -> RoutingDecision:
    """
    Conditional routing engine evaluating candidate trajectory based on
    objective score thresholds and reflection confidence.
    """
    # 1. Low confidence or hallucination -> trigger self-correction retry
    if (confidence_score < 0.75 or hallucination_detected) and iteration < 2:
        return RoutingDecision.RETRY_REFLECTION

    # 2. High fit score & verified confidence -> Fast track to interview
    if fit_score >= 80 and confidence_score >= 0.85:
        return RoutingDecision.DIRECT_INTERVIEW_FAST_TRACK

    # 3. Moderate fit score -> Flag for HR review
    if fit_score >= 60:
        return RoutingDecision.HR_REVIEW_REQUIRED

    # 4. Low fit score -> Recommended for rejection
    return RoutingDecision.REJECT_RECOMMENDED

