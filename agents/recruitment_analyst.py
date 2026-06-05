import os

from crewai import Agent
from dotenv import load_dotenv
from src.services.llm_router import get_llm

from src.config import settings

load_dotenv()

def create_recruitment_analyst():
    model_name = settings.MODEL_NAME or "llama-3.1-8b-instant"
    llm = get_llm(temperature=0.15, provider="groq", model=model_name)

    return Agent(
        role="Recruitment Intelligence Analyst",
        goal=(
            "Evaluate candidate-job fit using only the supplied resume and job posting, "
            "then produce recruiter-friendly hiring recommendations and interview prep."
        ),
        backstory=(
            "You are a senior technical recruiter. You are careful, evidence-based, and concise. "
            "You never invent candidate skills or experience. If evidence is missing, you call it out clearly."
        ),
        verbose=False,
        allow_delegation=False,
        llm=llm,
    )
