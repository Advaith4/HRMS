from crewai import Agent
import os
from dotenv import load_dotenv
from src.services.llm_router import get_llm

load_dotenv()

def create_interviewer():
    return Agent(
        role="Interviewer",
        goal="Ask precisely ONE challenging but realistic interview question tailored to the candidate's resume and target role, considering the current difficulty level.",
        backstory="You are an elite technical interviewer at a top-tier tech company. You test candidates on problem-solving, system design, and behavioral adaptability.",
        verbose=True,
        allow_delegation=False,
        llm=get_llm(0.6)
    )

def create_evaluator():
    return Agent(
        role="Evaluator",
        goal="Evaluate the user's interview answer and provide a strict score and constructive feedback.",
        backstory="You are a strict but fair interview panelist who looks for depth, clarity, and structural soundness in a candidate's answer.",
        verbose=True,
        allow_delegation=False,
        llm=get_llm(0.3)
    )

def create_followup_coach():
    return Agent(
        role="Follow-up Interviewer",
        goal="Generate a deeper, specific follow-up question based on the user's previous answer.",
        backstory="You dig deep into a candidate's stated knowledge to test the edges of their understanding. You don't accept superficial answers.",
        verbose=True,
        allow_delegation=False,
        llm=get_llm(0.6)
    )

def create_interview_coach():
    return Agent(
        role="Interview Coach",
        goal="Generate challenging but realistic technical and behavioral interview questions tailored to the candidate's core skills.",
        backstory=(
            "You are an elite technical interviewer at a top-tier tech company. "
            "You test candidates not just on syntax, but on problem-solving, system design, and behavioral adaptability based on their past experiences."
        ),
        verbose=True,
        allow_delegation=False,
        llm=get_llm(0.4)
    )
