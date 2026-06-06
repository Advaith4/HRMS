import os
import time
import json
from dotenv import load_dotenv

load_dotenv("d:/GitHub/HRMS/.env")

from fastapi.testclient import TestClient
from sqlmodel import Session, select
from sqlalchemy import create_engine
from src.main import app
from src.models import User, CandidateApplication, JobPosting, InterviewSession, ApplicationAIAnalysis
from src.api.dependencies import get_current_user, require_roles

engine = create_engine(os.environ.get("DATABASE_URL"))

def print_separator(title):
    print(f"\n{'='*60}\n{title}\n{'='*60}")

def run_e2e_validation():
    # We will use TestClient for API calls
    client = TestClient(app)

    with Session(engine) as db:
        # Ensure we have a candidate user
        candidate = db.exec(select(User).where(User.username == "e2e_candidate")).first()
        if not candidate:
            candidate = User(username="e2e_candidate", email="e2e@example.com", hashed_password="pw", role="candidate")
            db.add(candidate)
            db.commit()
            db.refresh(candidate)
            
        # Ensure we have an HR user
        hr_user = db.exec(select(User).where(User.username == "e2e_hr")).first()
        if not hr_user:
            hr_user = User(username="e2e_hr", email="hr@example.com", hashed_password="pw", role="hr")
            db.add(hr_user)
            db.commit()
            db.refresh(hr_user)
            
        # Ensure a Job Posting exists
        job = db.exec(select(JobPosting).where(JobPosting.title == "E2E Software Engineer")).first()
        if not job:
            job = JobPosting(title="E2E Software Engineer", description="E2E Test Job", required_skills="Python, React", department="Engineering", created_by=hr_user.id)
            db.add(job)
            db.commit()
            db.refresh(job)

        # Create 3 Applications
        print("Creating 3 Candidate Applications...")
        apps = []
        for i in ["A", "B", "C"]:
            appl = CandidateApplication(candidate_user_id=candidate.id, job_id=job.id, resume_text=f"Resume {i} " * 50)
            db.add(appl)
            db.commit()
            db.refresh(appl)
            apps.append(appl)
            
            # Create dummy ApplicationAIAnalysis
            ai_analysis = ApplicationAIAnalysis(
                application_id=appl.id,
                fit_score=70 + len(apps),
                recommendation="Consider",
                summary=f"Summary for App {i}",
                strengths='["Python"]',
                weaknesses='["C++"]'
            )
            db.add(ai_analysis)
            db.commit()

        app_A_id, app_B_id, app_C_id = [a.id for a in apps]
        cand_id = candidate.id
        hr_id = hr_user.id

    # Mock candidate login
    app.dependency_overrides[get_current_user] = lambda: User(id=cand_id, username="e2e_candidate", role="candidate")

    # Scenario B: Completed Interview
    print_separator("Scenario B: Starting & Completing Interview")
    start_res = client.post("/api/interview/start", json={
        "application_id": app_B_id,
        "difficulty": 5,
        "training_mode": "domain_specific",
        "interviewer_persona": "balanced"
    })
    
    if start_res.status_code != 200:
        print(f"Failed to start interview: {start_res.json()}")
        return
        
    session_id_B = start_res.json()["session_id"]
    print(f"Interview B started: {session_id_B}")
    
    # Answer 3 questions
    for i in range(3):
        ans_res = client.post(f"/api/interview/{session_id_B}/answer", json={"answer": f"This is my answer {i+1} to the question. I have good experience in Python and React. I built many applications."})
        print(f"Answer {i+1} submitted.")
        
    # Complete interview
    comp_res = client.post(f"/api/interview/{session_id_B}/complete")
    print("Interview B completed.")
    
    # Wait for Background Task
    print("Waiting for Hiring Intelligence Generation...")
    for _ in range(15):
        time.sleep(2)
        with Session(engine) as db:
            sess = db.exec(select(InterviewSession).where(InterviewSession.session_token == session_id_B)).first()
            if sess.status == "analyzed":
                print("Generation complete!")
                break
    else:
        print("Timeout waiting for generation.")

    # Scenario C: Active Interview
    print_separator("Scenario C: Starting Active Interview")
    start_c_res = client.post("/api/interview/start", json={
        "application_id": app_C_id,
        "difficulty": 5,
        "training_mode": "domain_specific",
        "interviewer_persona": "balanced"
    })
    session_id_C = start_c_res.json()["session_id"]
    print(f"Interview C started: {session_id_C} (Leaving Active)")

    # HR Dashboard Check
    print_separator("HR Dashboard Visibility Validation")
    
    # Mock HR login
    def hr_require_roles(*roles):
        return lambda: User(id=hr_id, username="e2e_hr", role="hr")
    app.dependency_overrides[require_roles] = hr_require_roles
    
    from src.api.routes.dashboard import hr_dashboard
    with Session(engine) as db:
        dashboard_data = hr_dashboard(session=db)
        hr_apps = dashboard_data["applications"]
        
        # Filter to our test apps
        test_apps = [a for a in hr_apps if a["id"] in [app_A_id, app_B_id, app_C_id]]
        test_apps.sort(key=lambda x: x["id"])
        
        print("\n--- Payload Verification ---")
        for a in test_apps:
            print(f"\nApp ID: {a['id']}")
            print(f"Resume Score (ai_analysis): {a['ai_analysis']['fit_score']}")
            int_ana = a.get("interview_analysis")
            if int_ana:
                print(f"Interview Status: {int_ana['status']}")
                if int_ana.get("job_fit_report"):
                    try:
                        jf = json.loads(int_ana["job_fit_report"]) if isinstance(int_ana["job_fit_report"], str) else int_ana["job_fit_report"]
                        print(f"Interview Job Fit: {jf.get('jobFit')}")
                        print(f"Interview Strengths: {jf.get('strengths')}")
                    except:
                        pass
            else:
                print("Interview Analysis: None")
                
        # Matrix Check
        print_separator("E. Multi-application Validation Matrix")
        
        matrix = []
        for a in test_apps:
            is_A = a["id"] == app_A_id
            is_B = a["id"] == app_B_id
            is_C = a["id"] == app_C_id
            
            res_score_ok = a['ai_analysis'] is not None
            
            if is_A:
                int_ok = a.get('interview_analysis') is None
                matrix.append(("App A (Resume Only)", "Pass" if int_ok and res_score_ok else "Fail"))
            elif is_B:
                int_ok = a.get('interview_analysis') is not None and a['interview_analysis']['status'] == "analyzed"
                matrix.append(("App B (Completed Interview)", "Pass" if int_ok and res_score_ok else "Fail"))
            elif is_C:
                int_ok = a.get('interview_analysis') is not None and a['interview_analysis']['status'] == "active"
                matrix.append(("App C (Active Interview)", "Pass" if int_ok and res_score_ok else "Fail"))
                
        for m in matrix:
            print(f"{m[0]}: {m[1]}")

if __name__ == "__main__":
    run_e2e_validation()
