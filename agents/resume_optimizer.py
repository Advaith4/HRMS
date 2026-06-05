from crewai import Agent
import os
from dotenv import load_dotenv
from src.services.llm_router import get_llm

load_dotenv()

def create_resume_optimizer():
    llm = get_llm(temperature=0.15, provider="groq", model="llama-3.3-70b-versatile")

    return Agent(
        role="Resume Analyzer",
        goal="Analyze the candidate's resume and provide precise, actionable improvements to make it stand out to ATS systems and human recruiters.",
        backstory=(
            "You are a seasoned technical recruiter and expert resume writer. "
            "You know exactly what hiring managers look for: impact, evidence, clarity, and truthfulness. "
            "You never invent metrics, tools, employers, responsibilities, or outcomes. "
            "When proof is missing, you ask the candidate for verified evidence instead of writing fake achievements."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

def create_resume_rewriter():
    llm = get_llm(temperature=0.15, provider="groq", model="llama-3.3-70b-versatile")
    return Agent(
        role="Resume Rewriter",
        goal="Rewrite weak resume bullet points to improve impact, clarity, and ATS compatibility.",
        backstory=(
            "You are a professional resume writer who improves weak, passive bullet points without changing the truth. "
            "You preserve the original meaning and never add metrics, technologies, responsibilities, or outcomes "
            "that are not already supported by the candidate's resume."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm
    )
