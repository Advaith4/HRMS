import os
import sys
import uuid
import time
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import app
from sqlmodel import Session, select
from src.database.connection import get_session, engine
from src.models import User, JobPosting, CandidateApplication

# Monkeypatch extract_text_from_pdf to avoid needing a real PDF file
import src.api.routes.applications as applications_route
applications_route.extract_text_from_pdf = lambda path: "Summary\nBackend engineer focused on FastAPI and React.\nSkills\nPython, FastAPI, SQLModel, React"

client = TestClient(app)

def _register(username: str, role: str) -> str:
    pwd = "password123"
    res = client.post("/api/auth/register", json={"username": username, "password": pwd})
    assert res.status_code == 201, res.text
    
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        user.role = role
        session.commit()
        
    res = client.post("/api/auth/login", json={"username": username, "password": pwd})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]

def run_simulation():
    print("Running 10-round interview simulation...")
    
    # 1. Setup users
    candidate_token = _register(f"candidate_sim_{uuid.uuid4().hex[:8]}", "candidate")
    hr_token = _register(f"hr_sim_{uuid.uuid4().hex[:8]}", "hr")
    
    cand_headers = {"Authorization": f"Bearer {candidate_token}"}
    hr_headers = {"Authorization": f"Bearer {hr_token}"}
    
    # 2. Create job
    job_res = client.post("/api/jobs", headers=hr_headers, json={"title": "Senior Engineer", "description": "Build things."})
    assert job_res.status_code == 201, job_res.text
    job_id = job_res.json()["id"]
    
    # 3. Apply
    app_res = client.post(
        "/api/applications/apply",
        headers=cand_headers,
        data={"job_id": str(job_id)},
        files={"file": ("resume.pdf", b"%PDF-1.4 mock resume content with Python and React.", "application/pdf")},
    )
    assert app_res.status_code == 201, app_res.text
    app_id = app_res.json()["application"]["id"]
    
    print(f"Created Application ID: {app_id}")
    
    # Wait a bit for async tasks if any
    time.sleep(1)
    
    # 4. Start Interview
    start_res = client.post(
        "/api/interview/start-for-application",
        headers=cand_headers,
        json={"application_id": app_id, "difficulty": 5}
    )
    assert start_res.status_code == 200, start_res.text
    session_id = start_res.json()["session_id"]
    print(f"Started Interview Session: {session_id}")
    
    # 5. Answer 10 rounds
    for round_num in range(1, 11):
        print(f"Submitting Answer {round_num}/10...")
        answer_res = client.post(
            "/api/interview/answer",
            headers=cand_headers,
            json={
                "session_id": session_id,
                "answer": f"This is my detailed mock answer for round {round_num}. I have great experience with Python."
            }
        )
        assert answer_res.status_code == 200, answer_res.text
        
        # Check if the interview should end
        if answer_res.json().get("end_interview"):
            print(f"Interview ended early at round {round_num}")
            break
            
    # 6. Complete Interview
    print("Completing interview...")
    complete_res = client.post(
        f"/api/interview/{session_id}/complete",
        headers=cand_headers
    )
    assert complete_res.status_code == 200, complete_res.text
    
    print("Simulation finished successfully!")

if __name__ == "__main__":
    run_simulation()
