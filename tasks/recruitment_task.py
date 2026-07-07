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
- Missing skills must only include job requirements that are completely absent from the resume. If a skill is listed anywhere on the resume (e.g. in the skills section), do not flag it as missing; instead, list it as a weakness or probing area if it lacks supporting project or work experience evidence.
- Strengths and weaknesses must be recruiter-friendly and evidence-based.
- Generate practical interview questions that probe uncertainty and validate claims.
- Do not invent employers, metrics, degrees, skills, or experience.

STRICT JSON SHAPE:
{{
  "fit_score": number,                   // 0-100 integer; calculated fit score based on candidate-job match
  "recommendation": "Strongly Recommended" | "Recommended" | "Consider" | "Reject", // recommendation based on the calculated fit_score
  "summary": "str",                      // short recruiter-facing summary
  "strengths": ["str"],                  // key candidate strengths
  "weaknesses": ["str"],                 // potential candidate weaknesses
  "missing_skills": ["str"],             // skills from job description missing in the resume
  "observations": ["str"],               // other relevant screening observations
  "interview_prep": {{
    "technical_questions": ["str"],      // tailored technical questions
    "behavioral_questions": ["str"],     // tailored behavioral questions
    "probing_areas": ["str"]             // topics needing deeper validation
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
