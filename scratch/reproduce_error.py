import sys
import os

# Ensure we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from crew import run_interview_answer
from src.services.llm_router import key_manager
from dotenv import load_dotenv

load_dotenv()

print("Testing run_interview_answer with increasing history length...")

history = []
for i in range(15):
    history.append({"role": "ai", "content": f"Question {i}: Can you explain the architecture?"})
    history.append({"role": "user", "content": f"Answer {i}: " * 100})
    history.append({"role": "feedback", "content": f"Feedback {i}."})
    
try:
    print(f"Running with history length: {len(history)}")
    result = run_interview_answer(
        role="Backend Engineer",
        question="Can you explain how you would scale a database?",
        answer="I would use sharding and read replicas." * 100, # Large answer
        current_diff=5,
        weak_areas=["Scalability", "System Design"],
        resume_context={"summary": "Backend developer with 5 years experience.", "skills": ["Python", "SQL"]},
        section_scores={"backend": 8},
        focus_mode="weak_area",
        training_mode="adaptive",
        interviewer_persona={"style": "technical", "pressure": "high"},
        coach_memory={"past_weaknesses": []},
        domain_focus="backend",
        conversation_history=history[-15:], # Try with 15 messages
        current_focus_area="Scalability",
        phase_name="Core Technical Round",
        phase_goal="Assess technical depth",
        phase_focus="System Design"
    )
    print("Success. Result keys:", result.keys() if isinstance(result, dict) else type(result))
except Exception as e:
    import traceback
    print("FAILED!")
    traceback.print_exc()
