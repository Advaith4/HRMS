import sys
from sqlmodel import Session, select
sys.path.append(".")
from src.database.connection import engine
from src.models import JobPosting, CandidateApplication, User

with Session(engine) as session:
    jobs = session.exec(select(JobPosting)).all()
    print("--- Database Jobs ---")
    for j in jobs:
        print(f"ID: {j.id} | Title: {j.title} | Department: {j.department}")

    apps = session.exec(select(CandidateApplication)).all()
    print("\n--- Database Applications ---")
    for a in apps:
        user = session.get(User, a.candidate_user_id)
        job = session.get(JobPosting, a.job_id)
        username = user.username if user else "Unknown"
        job_title = job.title if job else "Unknown"
        print(f"ID: {a.id} | Candidate: {username} | Job: {job_title} | Status: {a.status}")
