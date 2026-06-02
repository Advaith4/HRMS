from crewai import Task


def create_application_analysis_task(agent, resume_text: str, job: dict, parsed_resume: dict):
    description = """
You are TalentForge AI's recruitment intelligence layer.

Analyze this candidate application against the job posting. Use only the evidence supplied.
Return strict JSON only. No markdown. No prose outside JSON.

JOB POSTING:
Title: {title}
Department: {department}
Experience Required: {experience_required}
Required Skills: {required_skills}
Description:
{description}

CANDIDATE RESUME TEXT:
{resume_text}

PARSED RESUME:
{parsed_resume}

Rules:
- Score candidate fit from 0 to 100.
- Recommendation must be exactly one of: Strongly Recommended, Recommended, Consider, Reject.
- Missing skills must include important job requirements not clearly proven in the resume.
- Strengths and weaknesses must be recruiter-friendly and evidence-based.
- Generate practical interview questions that probe uncertainty and validate claims.
- Do not invent employers, metrics, degrees, skills, or experience.

STRICT JSON SHAPE:
{{
  "fit_score": 78,
  "recommendation": "Recommended",
  "summary": "Short recruiter-facing summary.",
  "strengths": ["strength 1", "strength 2"],
  "weaknesses": ["weakness 1", "weakness 2"],
  "missing_skills": ["missing skill"],
  "observations": ["observation 1", "observation 2"],
  "interview_prep": {{
    "technical_questions": ["question 1", "question 2", "question 3"],
    "behavioral_questions": ["question 1", "question 2"],
    "probing_areas": ["area 1", "area 2"]
  }}
}}
""".format(
        title=job.get("title", ""),
        department=job.get("department", ""),
        experience_required=job.get("experience_required", ""),
        required_skills=job.get("required_skills", ""),
        description=job.get("description", ""),
        resume_text=resume_text[:12000],
        parsed_resume=parsed_resume,
    )

    return Task(
        description=description,
        expected_output="Strict JSON with fit score, recommendation, explainability, and interview prep.",
        agent=agent,
    )
