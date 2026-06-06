import sys
import os
sys.path.append(os.getcwd())

from sqlmodel import Session, select
from src.database.connection import engine
from src.models import CandidateApplication, JobPosting, ApplicationAIAnalysis, InterviewSession

def main():
    with Session(engine) as session:
        apps = session.exec(select(CandidateApplication, JobPosting).join(JobPosting)).all()
        for app, job in apps:
            analysis = session.exec(select(ApplicationAIAnalysis).where(ApplicationAIAnalysis.application_id == app.id)).first()
            interview = session.exec(select(InterviewSession).where(InterviewSession.application_id == app.id)).first()
            
            print(f"Job: {job.title}")
            print(f"  App ID: {app.id}")
            print(f"  Status: {app.status}")
            print(f"  Analysis Score: {analysis.fit_score if analysis else 'None'}")
            
            if interview:
                print(f"  Interview Session Exists: Yes")
                print(f"  Session Status: {interview.status}")
            else:
                print(f"  Interview Session Exists: No")
            print("-" * 40)

if __name__ == "__main__":
    main()
