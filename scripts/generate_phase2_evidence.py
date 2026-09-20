"""
scripts/generate_phase2_evidence.py
Automated Evidence Generator for Phase 2: CrewAI Multi-Agent Workflow & Tool Abstraction.
Captures agent roles, tool schemas, latency benchmarks (parallel vs sequential), and routing decisions.
"""
import json
import logging
import time
from pathlib import Path

from agents.interview_coach import create_interview_coach
from agents.recruitment_analyst import create_recruitment_analyst
from agents.skill_matcher import create_skill_matcher
from src.core.prompts.prompt_registry import PromptRegistry
from src.models import JobPosting
from src.services.recruitment_ai import extract_features_parallel
from src.services.workflow_state import RoutingDecision, evaluate_routing_decision
from src.tools.recruitment_tools import (
    ats_scorer_tool,
    resume_parser_tool,
    skill_gap_tool,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("Phase2Evidence")

EVIDENCE_PLANNER_DIR = Path("evidence/planner")
EVIDENCE_TOOLS_DIR = Path("evidence/tools")
EVIDENCE_METRICS_DIR = Path("evidence/metrics")


def run_phase2_evidence_collection():
    logger.info("==================================================")
    logger.info("Generating Phase 2 Multi-Agent Workflow Evidence")
    logger.info("==================================================")

    EVIDENCE_PLANNER_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_METRICS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Document Agent Roles (Task 2.1)
    logger.info("[1/4] Capturing Multi-Agent Roles and Backstories...")
    agents_info = [
        {
            "agent_name": "PlannerAgent",
            "role": "Execution DAG Architect & Workflow Router",
            "goal": "Decompose recruitment requirements into optimal sequential and parallel subtasks.",
            "backstory": "Autonomous scheduler ensuring task decomposition and tool readiness before worker execution.",
        },
        {
            "agent_name": "RecruitmentAnalystAgent",
            "role": create_recruitment_analyst().role,
            "goal": create_recruitment_analyst().goal,
            "backstory": create_recruitment_analyst().backstory,
        },
        {
            "agent_name": "SkillMatcherAgent",
            "role": create_skill_matcher().role,
            "goal": create_skill_matcher().goal,
            "backstory": create_skill_matcher().backstory,
        },
        {
            "agent_name": "InterviewCoachAgent",
            "role": create_interview_coach().role,
            "goal": create_interview_coach().goal,
            "backstory": create_interview_coach().backstory,
        },
        {
            "agent_name": "ValidatorAgent",
            "role": "Quality Assurance & Hallucination Auditor",
            "goal": "Verify grounding, check rubric alignment, and compute confidence scores.",
            "backstory": "Reflective auditor preventing hallucinations and enforcing calibrated hiring rubrics.",
        },
    ]

    roles_file = EVIDENCE_PLANNER_DIR / "agent_roles.json"
    with open(roles_file, "w", encoding="utf-8") as f:
        json.dump(agents_info, f, indent=2)
    logger.info("✓ Agent roles documented at %s", roles_file)

    # 2. Document Tool Abstractions (Task 2.2)
    logger.info("[2/4] Capturing Tool Input/Output Schemas...")
    tools_info = [
        {
            "tool_name": resume_parser_tool.name,
            "description": resume_parser_tool.description,
            "input_schema": resume_parser_tool.args_schema.model_json_schema(),
            "output_schema": resume_parser_tool.return_schema.model_json_schema(),
        },
        {
            "tool_name": skill_gap_tool.name,
            "description": skill_gap_tool.description,
            "input_schema": skill_gap_tool.args_schema.model_json_schema(),
            "output_schema": skill_gap_tool.return_schema.model_json_schema(),
        },
        {
            "tool_name": ats_scorer_tool.name,
            "description": ats_scorer_tool.description,
            "input_schema": ats_scorer_tool.args_schema.model_json_schema(),
            "output_schema": ats_scorer_tool.return_schema.model_json_schema(),
        },
    ]

    tools_file = EVIDENCE_TOOLS_DIR / "tool_schemas.json"
    with open(tools_file, "w", encoding="utf-8") as f:
        json.dump(tools_info, f, indent=2)
    logger.info("✓ Tool schemas saved at %s", tools_file)

    # 3. Benchmark Parallel vs Sequential Execution (Task 2.6)
    logger.info("[3/4] Measuring Parallel vs Sequential Execution Latency...")
    job = JobPosting(
        title="Senior Distributed Systems Architect",
        description="Lead cloud infrastructure architecture using Kubernetes, Go, FastAPI, and Kafka.",
        department="Engineering",
        required_skills="Go, Kubernetes, FastAPI, Kafka, PostgreSQL, Docker",
        created_by=1,
    )
    resume = (
        "Senior Systems Architect with 8 years experience in Go, Kubernetes, Docker, FastAPI, and Kafka. "
        "Built distributed event-driven pipelines processing 50k events/sec. B.S. in Computer Science."
    )

    # Sequential execution benchmark (10 iterations)
    seq_times = []
    for _ in range(10):
        t0 = time.perf_counter()
        p = resume_parser_tool.run(resume_text=resume)
        g = skill_gap_tool.run(required_skills=job.required_skills, detected_skills=p.skills, resume_text=resume)
        a = ats_scorer_tool.run(
            job_title=job.title,
            required_skills=job.required_skills,
            experience_required=job.experience_required or "",
            resume_text=resume,
            detected_skills=p.skills,
            experience_items_count=len(p.experience) + len(p.projects),
            has_education=bool(p.education),
        )
        seq_times.append((time.perf_counter() - t0) * 1000.0)

    # Parallel execution benchmark (10 iterations)
    par_times = []
    for _ in range(10):
        t0 = time.perf_counter()
        _ = extract_features_parallel(resume_text=resume, job=job, request_id="req-par-bench")
        par_times.append((time.perf_counter() - t0) * 1000.0)

    avg_seq = round(sum(seq_times) / len(seq_times), 2)
    avg_par = round(sum(par_times) / len(par_times), 2)
    speedup = round(((avg_seq - avg_par) / avg_seq) * 100.0, 1) if avg_seq > 0 else 0.0

    latency_benchmark = {
        "iterations": 10,
        "sequential_avg_ms": avg_seq,
        "parallel_avg_ms": avg_par,
        "latency_reduction_percentage": speedup,
        "efficiency_gain": f"{speedup}% faster subtask execution",
    }

    latency_file = EVIDENCE_METRICS_DIR / "parallel_vs_sequential_latency.json"
    with open(latency_file, "w", encoding="utf-8") as f:
        json.dump(latency_benchmark, f, indent=2)
    logger.info("✓ Latency benchmark saved at %s (Speedup: %s%%)", latency_file, speedup)

    # 4. Document Conditional Routing Decisions (Task 2.5)
    logger.info("[4/4] Documenting Conditional Decision Routing Scenarios...")
    routing_scenarios = [
        {
            "scenario": "High Score & High Grounded Confidence",
            "fit_score": 92,
            "confidence": 0.92,
            "decision": evaluate_routing_decision(92, 0.92).value,
            "action": "Automatically advance candidate to Fast-Track Interview",
        },
        {
            "scenario": "Moderate Score / Qualified with Gaps",
            "fit_score": 72,
            "confidence": 0.85,
            "decision": evaluate_routing_decision(72, 0.85).value,
            "action": "Route to HR Dashboard for Human-in-the-Loop review",
        },
        {
            "scenario": "High Score with Low Confidence / Hallucination Detected",
            "fit_score": 90,
            "confidence": 0.60,
            "decision": evaluate_routing_decision(90, 0.60, hallucination_detected=True).value,
            "action": "Trigger Validator reflection self-correction retry",
        },
        {
            "scenario": "Low Skill Match & Underqualified",
            "fit_score": 42,
            "confidence": 0.90,
            "decision": evaluate_routing_decision(42, 0.90).value,
            "action": "Archive application and recommend polite rejection",
        },
    ]

    routing_file = EVIDENCE_PLANNER_DIR / "routing_decisions.json"
    with open(routing_file, "w", encoding="utf-8") as f:
        json.dump(routing_scenarios, f, indent=2)
    logger.info("✓ Routing scenarios saved at %s", routing_file)

    logger.info("==================================================")
    logger.info("Phase 2 Evidence Generation Complete!")
    logger.info("==================================================")


if __name__ == "__main__":
    run_phase2_evidence_collection()

