"""
tests/test_phase2_multiagent.py
Phase 2: CrewAI Multi-Agent Workflow & Tool Abstraction Comprehensive Test Suite.
Tests Agent Role Definitions, BaseHRMSTool Abstraction with Pydantic Schemas,
Prompt Registry Versioning, Workflow State Management, Conditional Decision Routing,
and Parallel Subtask Feature Extraction.
"""
import time
import pytest
from pydantic import ValidationError

from agents.interview_coach import create_interview_coach
from agents.recruitment_analyst import create_recruitment_analyst
from agents.skill_matcher import create_skill_matcher
from src.core.prompts.prompt_registry import PromptRegistry
from src.models import JobPosting
from src.services.planner_agent import plan_recruitment_workflow
from src.services.recruitment_ai import extract_features_parallel
from src.services.validator_agent import validate_evaluation_payload
from src.services.workflow_state import RoutingDecision, WorkflowState, evaluate_routing_decision
from src.tools.base_tool import BaseHRMSTool
from src.tools.recruitment_tools import (
    ATSScorerTool,
    ResumeParserTool,
    SkillGapAnalyzerTool,
    ats_scorer_tool,
    resume_parser_tool,
    skill_gap_tool,
)


def test_all_agent_roles_and_configurations():
    """Task 2.1: Verify all 5 agent roles instantiate with distinct roles, goals, and backstories."""
    analyst = create_recruitment_analyst()
    assert "Recruitment" in analyst.role
    assert len(analyst.goal) > 20
    assert len(analyst.backstory) > 30

    matcher = create_skill_matcher()
    assert "Skill" in matcher.role
    assert len(matcher.goal) > 20
    assert len(matcher.backstory) > 30

    coach = create_interview_coach()
    assert "Coach" in coach.role or "Interviewer" in coach.role

    # Planner & Validator verification
    plan = plan_recruitment_workflow(
        job_title="Fullstack Developer",
        job_description="React and Python development",
        required_skills="React, Python",
        resume_text="Alice Vance - React and Python developer.",
    )
    assert plan.steps[0].agent_name == "PlannerAgent"
    assert plan.steps[-1].agent_name == "ValidatorAgent"


def test_tool_abstraction_input_output_validation():
    """Task 2.2: Verify BaseHRMSTool enforces Pydantic schemas and executes successfully."""
    # 1. ResumeParserTool
    parser_out = resume_parser_tool.run(
        resume_text="Alice Vance\nSkills: Python, FastAPI, Docker\nExperience: 5 years backend development.\nEducation: B.S. in Computer Science"
    )
    assert "Python" in parser_out.skills or "python" in str(parser_out.skills).lower()
    assert bool(parser_out.education) is True

    # 2. SkillGapAnalyzerTool
    gap_out = skill_gap_tool.run(
        required_skills="Python, FastAPI, Kubernetes, GraphQL",
        detected_skills=["Python", "FastAPI"],
        resume_text="Python and FastAPI developer.",
    )
    assert "Python" in gap_out.matched_skills
    assert "Fastapi" in gap_out.matched_skills or "FastAPI" in [s.title() for s in gap_out.matched_skills]
    assert "Kubernetes" in gap_out.missing_skills
    assert gap_out.match_percentage == 50.0

    # 3. ATSScorerTool
    ats_out = ats_scorer_tool.run(
        job_title="Senior Python Engineer",
        required_skills="Python, FastAPI",
        experience_required="5 years",
        resume_text="Senior Python Engineer with FastAPI experience.",
        detected_skills=["Python", "FastAPI"],
        experience_items_count=3,
        has_education=True,
    )
    assert ats_out.fit_score >= 70
    assert ats_out.recommendation in {"Recommended", "Strongly Recommended"}


def test_tool_abstraction_rejects_invalid_inputs():
    """Task 2.2: Verify BaseHRMSTool rejects invalid types or missing fields."""
    with pytest.raises(ValueError):
        # Missing required parameter 'job_title' and 'resume_text'
        ats_scorer_tool.run(required_skills="Python")


def test_prompt_registry_versions():
    """Task 2.3: Verify PromptRegistry supports versioned templates and metadata listing."""
    v1_prompt = PromptRegistry.get_prompt(
        "recruitment_analysis",
        version="v1",
        title="ML Engineer",
        department="AI",
        required_skills="PyTorch, CUDA",
        description="Build LLM inference models.",
        resume_text="ML Engineer with PyTorch experience.",
    )
    assert "AI recruitment assistant" in v1_prompt
    assert "PyTorch" in v1_prompt

    v2_prompt = PromptRegistry.get_prompt(
        "recruitment_analysis",
        version="v2",
        title="ML Engineer",
        department="AI",
        experience_required="4 years",
        required_skills="PyTorch, CUDA",
        description="Build LLM inference models.",
        resume_text="ML Engineer with PyTorch experience.",
        parsed_resume="{}",
    )
    assert "Chain-of-Thought" in v2_prompt
    assert "EVALUATION CRITERIA & RUBRIC" in v2_prompt
    assert "Skill Coverage (45% weight)" in v2_prompt

    versions = PromptRegistry.list_versions()
    assert len(versions) == 2
    assert {v["version"] for v in versions} == {"v1", "v2"}


def test_workflow_state_and_conditional_routing():
    """Tasks 2.4 & 2.5: Verify state container and conditional decision routing logic."""
    # High score + High confidence -> Fast track interview
    decision_fast = evaluate_routing_decision(fit_score=88, confidence_score=0.90)
    assert decision_fast == RoutingDecision.DIRECT_INTERVIEW_FAST_TRACK

    # Moderate score -> HR review required
    decision_review = evaluate_routing_decision(fit_score=68, confidence_score=0.80)
    assert decision_review == RoutingDecision.HR_REVIEW_REQUIRED

    # High score but low confidence / hallucination -> Retry reflection
    decision_retry = evaluate_routing_decision(fit_score=92, confidence_score=0.60)
    assert decision_retry == RoutingDecision.RETRY_REFLECTION

    # Low score -> Reject recommended
    decision_reject = evaluate_routing_decision(fit_score=40, confidence_score=0.90)
    assert decision_reject == RoutingDecision.REJECT_RECOMMENDED


def test_parallel_feature_extraction():
    """Task 2.6: Verify parallel subtask feature extraction returns consolidated outputs."""
    job = JobPosting(
        title="Backend Architect",
        description="Design scalable microservices with Python, FastAPI, and Postgres.",
        department="Engineering",
        required_skills="Python, FastAPI, Postgres, Docker",
        created_by=1,
    )
    resume = (
        "Alice Vance - Senior Backend Architect with 7 years experience in Python, FastAPI, PostgreSQL, and Docker. "
        "Built high-throughput distributed systems. B.S. in Computer Engineering."
    )

    start_time = time.perf_counter()
    features = extract_features_parallel(resume_text=resume, job=job, request_id="req-parallel-test")
    duration = time.perf_counter() - start_time

    assert "parsed" in features
    assert "skill_gap" in features
    assert "ats_score" in features
    assert features["skill_gap"]["match_percentage"] >= 75.0
    assert features["ats_score"]["fit_score"] >= 75
    assert duration < 1.0  # Fast parallel execution

