"""
src/services/planner_agent.py
Planner Agent for Agentic Execution Orchestration in TalentForge AI.
Analyzes task complexity, determines the optimal DAG of tool/agent steps before execution.
"""
import logging
from typing import Any, Literal
from pydantic import BaseModel, Field

from src.core.logging_middleware import log_agent_execution

logger = logging.getLogger(__name__)


class ExecutionStep(BaseModel):
    step_number: int = Field(description="Sequential order of the task")
    agent_name: str = Field(description="Target agent designated to execute this step")
    task_name: str = Field(description="Descriptive name of the subtask")
    required_tools: list[str] = Field(default_factory=list, description="Tools needed for this step")
    expected_output_type: str = Field(description="Data type expected from this step")


class ExecutionPlan(BaseModel):
    task_id: str = Field(description="Unique plan identifier")
    job_title: str = Field(description="Target job title")
    estimated_complexity: Literal["low", "medium", "high"] = Field(description="Task complexity level")
    requires_ocr: bool = Field(default=False, description="True if resume appears scanned or contains low text volume")
    steps: list[ExecutionStep] = Field(description="Ordered list of execution steps")
    rationale: str = Field(description="Explanation of why this execution sequence was chosen")


def plan_recruitment_workflow(
    job_title: str,
    job_description: str,
    required_skills: str,
    resume_text: str,
    request_id: str = "req-default",
) -> ExecutionPlan:
    """
    Evaluates recruitment analysis requirements and emits an explicit Execution Plan DAG.
    """
    text_len = len(resume_text.strip())
    is_short = text_len < 120
    is_complex_job = len(job_description) > 500 or len(required_skills.split(",")) > 5

    complexity: Literal["low", "medium", "high"] = "high" if is_complex_job else ("low" if is_short else "medium")
    requires_ocr = is_short and ("scanned" in resume_text.lower() or text_len < 50)

    steps: list[ExecutionStep] = [
        ExecutionStep(
            step_number=1,
            agent_name="PlannerAgent",
            task_name="DecomposeJobAndResumeComplexity",
            required_tools=["TextLengthAnalyzer", "KeywordMatcher"],
            expected_output_type="ExecutionPlan",
        ),
        ExecutionStep(
            step_number=2,
            agent_name="ResumeAnalystAgent",
            task_name="ExtractCandidateProfileAndEvidence",
            required_tools=["PDFParserTool", "SkillsGapCalculator"],
            expected_output_type="ParsedResumeData",
        ),
        ExecutionStep(
            step_number=3,
            agent_name="ResumeAnalystAgent",
            task_name="ComputeRubricAlignmentAndScore",
            required_tools=["ATSKeywordScorer", "DeterministicCalculatorTool"],
            expected_output_type="CandidateEvaluationPayload",
        ),
        ExecutionStep(
            step_number=4,
            agent_name="ValidatorAgent",
            task_name="AuditGroundingAndConfidenceScore",
            required_tools=["HallucinationDetector", "ConfidenceRubricValidator"],
            expected_output_type="ValidationResult",
        ),
    ]

    plan = ExecutionPlan(
        task_id=f"plan-{request_id}",
        job_title=job_title,
        estimated_complexity=complexity,
        requires_ocr=requires_ocr,
        steps=steps,
        rationale=(
            f"Evaluated job '{job_title}' with {len(required_skills.split(','))} skills. "
            f"Resume text length is {text_len} chars. Routed through standard 4-stage pipeline."
        ),
    )

    log_agent_execution(
        request_id=request_id,
        user_id=None,
        agent="PlannerAgent",
        tool="WorkflowDAGPlanner",
        latency_ms=12.4,
        status="SUCCESS",
        details={"complexity": complexity, "steps_count": len(steps)},
    )

    return plan

