import os
import sys
# Add current directory to path for imports
sys.path.append(os.getcwd())

from src.services.mock_interview_summary import generate_mock_interview_summary
from crew import run_interview_answer

# 1. Test Mock Summary
transcript = [
    {"role": "ai", "content": "Tell me about a time you optimized a slow database query."},
    {"role": "user", "content": "I noticed our Postgres DB was taking 5 seconds for a user search. I added an index on the email column and it dropped to 10ms."},
    {"role": "feedback", "content": "Good concrete answer.", "score": 8},
    {"role": "ai", "content": "Did you consider any tradeoffs when adding the index?"},
    {"role": "user", "content": "Well, indexes take up space and slow down writes, but since it was a read-heavy table, it was worth it."},
    {"role": "feedback", "content": "Excellent understanding of tradeoffs.", "score": 9}
]

summary = generate_mock_interview_summary(
    transcript=transcript,
    role="Backend Engineer",
    difficulty=6,
    average_score=8.5,
    resume_context={"skills": ["PostgreSQL", "Python"]}
)
print("=== MOCK SUMMARY ===")
print(summary)

# 2. Test Evaluator (Resume Context effect)
print("\n=== EVALUATOR ===")
# We will run run_interview_answer with and without resume_context

# Simulated answer
q = "How do you handle container orchestration?"
a = "I write the deployment scripts and manage the scaling rules using the native API."

print("Without resume context:")
res_no_resume = run_interview_answer(
    role="DevOps Engineer",
    question=q,
    answer=a,
    current_diff=5,
    resume_context={},
    focus_mode="general",
    current_focus_area="orchestration"
)
print(res_no_resume["evaluation"])

print("\nWith resume context:")
res_with_resume = run_interview_answer(
    role="DevOps Engineer",
    question=q,
    answer=a,
    current_diff=5,
    resume_context={"skills": ["Kubernetes", "EKS", "Helm"]},
    focus_mode="general",
    current_focus_area="orchestration"
)
print(res_with_resume["evaluation"])
