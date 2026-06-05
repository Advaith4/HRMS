import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
import logging
from src.services.llm_router import get_llm
from crew import run_interview_answer

logging.basicConfig(level=logging.INFO)

def benchmark():
    times = []
    answers = [
        "I built a React frontend and Node backend.",
        "I used Redis to cache the responses, which reduced latency by 50%.",
        "We had a microservices architecture, but we faced issues with distributed tracing.",
        "I resolved a conflict by gathering data and presenting an objective tradeoff matrix.",
        "I optimized a PostgreSQL query by adding a composite index.",
        "We migrated from REST to GraphQL to avoid over-fetching.",
        "My greatest strength is my ability to quickly learn new technologies.",
        "A time I failed was when I underestimated the effort for a refactor. We missed the deadline.",
        "I communicate clearly and make sure stakeholders are aligned weekly.",
        "I'm looking for a role where I can take ownership of scalable systems."
    ]

    print("Starting Benchmark...")
    for i, ans in enumerate(answers):
        start = time.time()
        result = run_interview_answer(
            role="Software Engineer",
            question="Tell me about your experience.",
            answer=ans,
            current_diff=5,
            weak_areas=[],
            resume_context={},
            section_scores={},
            focus_mode="general",
            training_mode="adaptive",
            interviewer_persona={"pressure": "medium"},
            coach_memory={},
            domain_focus="",
            conversation_history=[],
            current_focus_area="general",
            phase_name="Core Technical Round",
            phase_goal="Assess technical depth",
            phase_focus="Architecture and tradeoffs"
        )
        duration = time.time() - start
        times.append(duration)
        print(f"Round {i+1} took {duration:.2f}s")
        print(f"Next diff: {result.get('new_difficulty')}")
    
    avg = sum(times) / len(times)
    p95 = sorted(times)[int(len(times) * 0.95)]
    print("\n--- Benchmark Results ---")
    print(f"Average Response Time: {avg:.2f}s")
    print(f"P95 Response Time: {p95:.2f}s")

if __name__ == '__main__':
    benchmark()
