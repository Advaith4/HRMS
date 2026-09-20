"""
tasks/match_task.py
Task definition for skill matching and competency gap extraction.
"""
from crewai import Task


def create_skill_matching_task(agent, resume_text: str, required_skills: str) -> Task:
    description = f"""
Analyze the candidate's resume text and extract all technical skills matching the required skills.

REQUIRED SKILLS:
{required_skills}

RESUME TEXT:
{resume_text[:8000]}

Rules:
1. Identify all exact matches from the required skills list that are backed by resume evidence.
2. Identify all missing skills from the required skills list.
3. Calculate the match percentage (matched / total required * 100).
4. Return strict JSON with shape:
{{
  "matched_skills": ["str"],
  "missing_skills": ["str"],
  "match_percentage": float,
  "adjacent_competencies": ["str"]
}}
"""
    return Task(
        description=description,
        expected_output="JSON object containing matched skills, missing skills, match percentage, and adjacent competencies.",
        agent=agent,
    )

