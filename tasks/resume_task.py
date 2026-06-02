from crewai import Task

# Legacy implementation for /api/analyze UI
def create_resume_task(agent, resume_content):
    description = """
You are a Resume Optimizer.
Analyze the following resume:
---------------------
{resume}
---------------------
Provide EXACTLY 4 actionable improvement points to make this resume better.

Return ONLY JSON. Do not include any extra text.

OUTPUT FORMAT (STRICT JSON ONLY):
{{
  "improvements": ["improvement 1", "improvement 2", "improvement 3", "improvement 4"]
}}
""".format(resume=resume_content)
    return Task(
        description=description,
        expected_output="Valid JSON containing exactly 4 resume improvements.",
        agent=agent
    )

def create_resume_analysis_task(agent, resume_content, target_role=""):
    role_ctx = f"Target Role: {target_role}\n" if target_role else "Target Role: General Software Engineering\n"
    description = """
You are Jobify Resume Lab: a Senior Technical Recruiter and ATS Specialist.
Analyze the resume deeply and return ONLY strict JSON. Provide practical, real-world insights that actually attract recruiters.

---------------------
{role_ctx}
RESUME:
{resume}
---------------------

CRITICAL RULES:
- Every issue MUST map to exact real text copied from the resume in the "original" field.
- If the resume does not prove a metric, tool, result, employer, leadership scope, or achievement, DO NOT add it.
- Use action_type "replace" only for safe wording edits that preserve the exact claim.
- Use action_type "manual" when the candidate must add missing evidence themselves. In that case, "improved" must be guidance, not a fake replacement.
- The "improved" field must either be a truthful replacement OR a manual instruction that says what verified detail is needed.
- Focus strictly on business impact, ATS keyword optimization, and recruiter readability (6-second scan).
- Do not provide generic language tweaks. Only suggest changes that make the candidate look more competent or hireable.
- Do not invent fake employers, metrics, tools, or achievements.
- If a metric is missing, ask for a verified metric or honest scope detail. Never invent the number or outcome.
- Prefer high-value issues from the summary, recent experience, and key skills.
- Return at most 6-8 total issues.
- The summary feedback must sound like a real hiring manager's debrief notes.
- Each issue should include insight, guidance, and evidence_needed.

Return ONLY JSON. Do not include any extra text.

OUTPUT FORMAT (STRICT JSON ONLY):
{{
  "score": 82,
  "breakdown": {{
    "impact": 60,
    "clarity": 75,
    "structure": 85,
    "ats": 80
  }},
  "sections": [
    {{
      "section": "experience",
      "issues": [
        {{
          "original": "Worked on a chatbot to help customers",
          "problem": "The line names the project but does not prove scope, ownership, tools, or outcome.",
          "improved": "Manual edit needed: keep the chatbot claim, then add only verified details such as your role, stack, users, evaluation result, or what changed after launch.",
          "action_type": "manual",
          "severity": "high",
          "category": "impact",
          "insight": "Recruiters can see the task, but not the weight of the work.",
          "guidance": "Do not add ticket reduction or resolution-time claims unless they actually happened and you can defend them.",
          "evidence_needed": ["your exact responsibility", "tools actually used", "verified scope", "real outcome if available"]
        }}
      ]
    }}
  ],
  "summary_feedback": {{
    "strengths": ["Strong technical foundation", "Good progression of titles"],
    "weaknesses": ["Impact is buried under passive language", "Missing critical ATS keywords for senior roles"],
    "priority_fixes": ["Quantify the scale of your last two projects", "Move tech stack keywords higher up"]
  }}
}}
""".format(role_ctx=role_ctx, resume=resume_content)

    return Task(
        description=description,
        expected_output="Valid JSON matching Jobify Resume Lab schema with grounded issues and replacements.",
        agent=agent
    )


def create_bullet_rewriting_task(agent, resume_content):
    description = """
You are a Resume Rewriter.
Read the following resume content and identify 3 to 5 weak, passive, or non-quantified bullet points.

---------------------
RESUME:
{resume}
---------------------

Rewrite them to be highly impactful, action-oriented, and ATS-friendly. 
CRITICAL: Do NOT add fake metrics, numbers, or achievements. Only improve the wording, verbs, and structure. Ensure you preserve their original meaning.

Return ONLY JSON. Do not include any extra text.

OUTPUT FORMAT (STRICT JSON ONLY):
{{
  "rewritten_lines": [
    {{
      "original": "original weak line 1",
      "improved": "Improved, action-oriented line 1"
    }},
    {{
      "original": "original weak line 2",
      "improved": "Improved, action-oriented line 2"
    }}
  ]
}}
""".format(resume=resume_content)

    return Task(
        description=description,
        expected_output="Valid JSON containing original and improved rewritten bullet points.",
        agent=agent
    )
