"""
src/core/prompts/prompt_registry.py
Centralized Prompt Versioning Registry for TalentForge AI.
Enables auditable prompt version tracking (v1 vs v2), A/B testing, and deterministic rollback.
"""
from typing import Any, Literal

PROMPT_V1_RECRUITMENT = """
You are an AI recruitment assistant.
Analyze this candidate application against the job posting.

JOB POSTING:
Title: {title}
Department: {department}
Required Skills: {required_skills}
Description: {description}

CANDIDATE RESUME:
{resume_text}

Provide an evaluation in JSON format with fit_score (0-100), recommendation, summary, strengths, weaknesses, and missing_skills.
"""

PROMPT_V2_RECRUITMENT = """
You are TalentForge AI's Lead Recruitment Intelligence Specialist.
Analyze the candidate application using strict Chain-of-Thought (CoT) and evidence-grounded rubric evaluation.

### STEP 1: CONTEXT PARSING
JOB TITLE: {title}
DEPARTMENT: {department}
EXPERIENCE REQUIRED: {experience_required}
REQUIRED SKILLS: {required_skills}
JOB DESCRIPTION:
{description}

CANDIDATE RESUME TEXT:
{resume_text}

STRUCTURED RESUME DATA:
{parsed_resume}

### STEP 2: EVALUATION CRITERIA & RUBRIC
1. Skill Coverage (45% weight): Count exact and semantic matches of required skills found in the resume.
2. Experience Depth (25% weight): Assess years and project complexity directly supported by evidence.
3. Education & Certification (10% weight): Validate relevant degrees or accredited certifications.
4. Role Relevance (20% weight): Evaluate domain alignment and title similarity.

### STEP 3: STRICT GUARDRAILS
- Never invent skills, employers, or metrics.
- Flag a skill as "missing_skills" ONLY if it does not appear anywhere in the resume text.
- If a skill is mentioned in passing without project depth, list it under "weaknesses" or "probing_areas".
- Recommendations must strictly follow calibrated score boundaries:
  * 85-100: "Strongly Recommended"
  * 70-84:  "Recommended"
  * 50-69:  "Consider"
  * 0-49:   "Reject"

### STRICT JSON OUTPUT FORMAT:
{{
  "fit_score": <int 0-100>,
  "recommendation": "Strongly Recommended" | "Recommended" | "Consider" | "Reject",
  "summary": "<recruiter-friendly synthesis>",
  "strengths": ["<grounded strength with resume citation>"],
  "weaknesses": ["<evidence-based improvement area>"],
  "missing_skills": ["<job skill completely absent in resume>"],
  "observations": ["<notable screening signals>"],
  "interview_prep": {{
    "technical_questions": ["<probing question targeting key required skill>"],
    "behavioral_questions": ["<scenario question validating team leadership/collaboration>"],
    "probing_areas": ["<area of uncertainty needing recruiter depth check>"]
  }}
}}
"""


class PromptRegistry:
    """Registry maintaining active and historical prompt templates."""

    @staticmethod
    def get_prompt(
        prompt_name: str,
        version: Literal["v1", "v2"] = "v2",
        **kwargs: Any,
    ) -> str:
        if prompt_name == "recruitment_analysis":
            template = PROMPT_V2_RECRUITMENT if version == "v2" else PROMPT_V1_RECRUITMENT
            return template.format(**kwargs)
        raise KeyError(f"Unknown prompt template: '{prompt_name}'")

    @staticmethod
    def list_versions() -> list[dict[str, Any]]:
        return [
            {
                "prompt_name": "recruitment_analysis",
                "version": "v1",
                "description": "Baseline zero-shot recruitment analysis prompt without explicit CoT rubric.",
                "created_date": "2026-06-01",
                "status": "legacy_comparative",
            },
            {
                "prompt_name": "recruitment_analysis",
                "version": "v2",
                "description": "Production Chain-of-Thought prompt with weighted rubric criteria and grounding guardrails.",
                "created_date": "2026-09-20",
                "status": "production_active",
            },
        ]

