import os
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from src.main import app
from src.database.connection import get_session
from src.models import User, CandidateApplication, InterviewSession, JobPosting
from src.api.dependencies import get_current_user

# Setup isolated DB for test
os.environ["DATABASE_URL"] = "sqlite:///data/test_failures.db"
engine = create_engine("sqlite:///data/test_failures.db")
SQLModel.metadata.drop_all(engine)
SQLModel.metadata.create_all(engine)

def get_test_session():
    with Session(engine) as session:
        yield session

app.dependency_overrides[get_session] = get_test_session

def create_mock_user(role="candidate"):
    user = User(username=f"test_{role}", email=f"test_{role}@example.com", hashed_password="pw", role=role)
    with Session(engine) as db:
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

client = TestClient(app)

def setup_interview():
    user = create_mock_user()
    app.dependency_overrides[get_current_user] = lambda: user
    with Session(engine) as db:
        job = JobPosting(title="Test Job", description="Test", required_skills="Test", department="Test", created_by=user.id)
        db.add(job)
        db.commit()
        db.refresh(job)
        
        appl = CandidateApplication(candidate_user_id=user.id, job_id=job.id, resume_text="Test resume " * 20)
        db.add(appl)
        db.commit()
        db.refresh(appl)
        
    start_res = client.post("/api/interview/start", json={
        "application_id": appl.id,
        "difficulty": 5,
        "training_mode": "domain_specific",
        "interviewer_persona": "balanced"
    })
    if start_res.status_code != 200:
        print(f"Error starting interview: {start_res.status_code} - {start_res.json()}")
    assert start_res.status_code == 200
    session_id = start_res.json()["session_id"]
    return session_id

def test_failure_nan_fields():
    print("\n--- Test 1: NaN fields ---")
    session_id = setup_interview()
    
    with patch("src.api.routes.interview.litellm.completion") as mock_comp:
        mock_res = MagicMock()
        mock_res.choices[0].message.content = json.dumps({
            "score": "NaN",
            "what_went_well": ["NaN", "test"],
            "what_was_missing": [],
            "how_to_improve": [],
            "focus_area": "NaN"
        })
        mock_comp.return_value = mock_res
        
        res = client.post(f"/api/interview/{session_id}/answer", json={"answer": "My answer"})
        print(f"Backend result status: {res.status_code}")
        print(f"Response: {res.json()}")

def test_failure_null_nested():
    print("\n--- Test 2: Null nested objects ---")
    session_id = setup_interview()
    
    with patch("src.api.routes.interview.litellm.completion") as mock_comp:
        mock_res = MagicMock()
        mock_res.choices[0].message.content = json.dumps({
            "score": None,
            "what_went_well": None,
            "what_was_missing": None,
            "how_to_improve": None,
            "focus_area": None
        })
        mock_comp.return_value = mock_res
        
        res = client.post(f"/api/interview/{session_id}/answer", json={"answer": "My answer"})
        print(f"Backend result status: {res.status_code}")
        print(f"Response: {res.json()}")

def test_failure_followup_failure():
    print("\n--- Test 3: Followup generator failure ---")
    session_id = setup_interview()
    
    with patch("src.api.routes.interview.litellm.completion") as mock_comp:
        # First call is evaluator, second is followup
        eval_mock = MagicMock()
        eval_mock.choices[0].message.content = json.dumps({"score": 8})
        
        mock_comp.side_effect = [eval_mock, Exception("Followup LLM crashed")]
        
        res = client.post(f"/api/interview/{session_id}/answer", json={"answer": "My answer"})
        print(f"Backend result status: {res.status_code}")
        print(f"Response: {res.json()}")

def test_failure_timeout():
    print("\n--- Test 4: Groq timeout ---")
    session_id = setup_interview()
    
    with patch("src.api.routes.interview.litellm.completion") as mock_comp:
        import litellm
        mock_comp.side_effect = litellm.Timeout("Timeout")
        
        res = client.post(f"/api/interview/{session_id}/answer", json={"answer": "My answer"})
        print(f"Backend result status: {res.status_code}")
        print(f"Response: {res.json()}")

def test_failure_rate_limit():
    print("\n--- Test 5: Groq rate limit ---")
    session_id = setup_interview()
    
    with patch("src.api.routes.interview.litellm.completion") as mock_comp:
        import litellm
        mock_comp.side_effect = litellm.RateLimitError("Rate limit", llm_provider="groq", model="test")
        
        res = client.post(f"/api/interview/{session_id}/answer", json={"answer": "My answer"})
        print(f"Backend result status: {res.status_code}")
        print(f"Response: {res.json()}")

def test_failure_malformed_json():
    print("\n--- Test 6: Malformed JSON ---")
    session_id = setup_interview()
    
    with patch("src.api.routes.interview.litellm.completion") as mock_comp:
        mock_res = MagicMock()
        mock_res.choices[0].message.content = "This is not JSON at all {broken"
        mock_comp.return_value = mock_res
        
        res = client.post(f"/api/interview/{session_id}/answer", json={"answer": "My answer"})
        print(f"Backend result status: {res.status_code}")
        print(f"Response: {res.json()}")

def test_failure_duplicate_question():
    print("\n--- Test 7: Duplicate question generation ---")
    session_id = setup_interview()
    
    with patch("src.api.routes.interview.litellm.completion") as mock_comp:
        eval_mock = MagicMock()
        eval_mock.choices[0].message.content = json.dumps({"score": 8})
        
        followup_mock = MagicMock()
        # Same question twice
        followup_mock.choices[0].message.content = json.dumps({"next_question": "Tell me about yourself."})
        
        mock_comp.side_effect = [eval_mock, followup_mock, eval_mock, followup_mock]
        
        res1 = client.post(f"/api/interview/{session_id}/answer", json={"answer": "Answer 1"})
        res2 = client.post(f"/api/interview/{session_id}/answer", json={"answer": "Answer 2"})
        print(f"Second answer response: {res2.json()}")

def test_failure_partial_completion():
    print("\n--- Test 8: Force interview completion after partial interview ---")
    session_id = setup_interview()
    res = client.post(f"/api/interview/{session_id}/complete")
    print(f"Partial completion response: {res.status_code} - {res.json()}")
    with Session(engine) as db:
        s = db.exec(select(InterviewSession).where(InterviewSession.session_token == session_id)).first()
        print(f"DB status: {s.status}")

if __name__ == "__main__":
    from sqlmodel import select
    test_failure_nan_fields()
    test_failure_null_nested()
    test_failure_followup_failure()
    test_failure_timeout()
    test_failure_rate_limit()
    test_failure_malformed_json()
    test_failure_duplicate_question()
    test_failure_partial_completion()
