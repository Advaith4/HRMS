import json
import logging
import litellm
# Ensure the router is imported so the monkey-patch is active
import src.services.llm_router 

logger = logging.getLogger(__name__)

def generate_mock_interview_summary(
    transcript: list[dict],
    role: str,
    difficulty: int,
    average_score: float,
    resume_context: dict
) -> dict:
    """
    Generates a structured post-interview summary using a single LLM completion.
    Bypasses CrewAI overhead and relies on litellm + our llm_router patch.
    """
    
    # Format the transcript into a readable string
    chat_log = ""
    for msg in transcript:
        r = "Interviewer" if msg.get("role") == "ai" else ("Candidate" if msg.get("role") == "user" else "System")
        if r in ["Interviewer", "Candidate"]:
            chat_log += f"{r}: {msg.get('content', '')}\n\n"

    system_prompt = f"""
You are an expert technical recruiter and interview coach.
Analyze the provided MOCK INTERVIEW TRANSCRIPT.
Role: {role}
Difficulty Level: {difficulty}/10
Candidate Average Score: {average_score:.1f}/10

CANDIDATE RESUME CONTEXT:
{json.dumps(resume_context, indent=2)}

Generate a candidate-facing, constructive, and actionable summary of their performance.

STRICT INSTRUCTIONS:
- Return ONLY valid JSON matching the exact schema below.
- Do not output markdown code blocks wrapping the JSON.
- Ensure all arrays have at least 2 specific items based on the actual transcript.
- Avoid generic advice; quote or refer to specific answers given by the candidate.

REQUIRED JSON SCHEMA:
{{
  "overall_assessment": "1-2 paragraphs summarizing the performance",
  "communication_feedback": "1 paragraph on structure, clarity, and conciseness",
  "technical_feedback": "1 paragraph on technical depth and accuracy",
  "key_strengths": ["string"],
  "key_weaknesses": ["string"],
  "improvement_recommendations": ["string"],
  "suggested_next_topics": ["string"]
}}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"INTERVIEW TRANSCRIPT:\n{chat_log}"}
    ]

    try:
        response = litellm.completion(
            model="groq/llama-3.1-8b-instant",
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1500
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        logger.error(f"Failed to generate mock interview summary: {e}")
        # Fallback dictionary if LLM fails
        return {
            "overall_assessment": f"The mock interview concluded with an average score of {average_score:.1f}/10.",
            "communication_feedback": "Review the transcript for areas to improve clarity.",
            "technical_feedback": "Ensure all technical claims are backed by specific examples.",
            "key_strengths": ["Completed the practice session"],
            "key_weaknesses": ["Review transcript for missed opportunities"],
            "improvement_recommendations": ["Practice with different interviewer personas"],
            "suggested_next_topics": ["General role fundamentals"]
        }
