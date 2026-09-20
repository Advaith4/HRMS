"""
agents/skill_matcher.py
Specialized Skill Matcher Agent for taxonomy normalization and skill gap analysis.
"""
from crewai import Agent
from dotenv import load_dotenv

from src.config import settings
from src.services.llm_router import get_llm

load_dotenv()


def create_skill_matcher() -> Agent:
    model_name = settings.MODEL_NAME or "llama-3.1-8b-instant"
    llm = get_llm(temperature=0.1, provider="groq", model=model_name)

    return Agent(
        role="Skill Alignment & Competency Specialist",
        goal=(
            "Extract, normalize, and match technical competencies from candidate resumes against job requisitions "
            "with zero hallucination and strict taxonomic fidelity."
        ),
        backstory=(
            "You are an expert ATS data scientist and technical taxonomy architect. You identify exact "
            "and adjacent technical skills, mapping candidate experience directly to job requirements."
        ),
        verbose=False,
        allow_delegation=False,
        llm=llm,
    )

