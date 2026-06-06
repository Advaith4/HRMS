import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fastapi.testclient import TestClient
from src.main import app
from src.models import InterviewSession, User
from src.database.connection import get_session
import json
import uuid

client = TestClient(app)

def test_reproduce_500():
    # 1. Create user and active session in the test DB
    with next(get_session()) as db:
        user = db.query(User).filter_by(username="admin").first()
        if not user:
            user = User(username="admin", password_hash="hash", email="admin@test.com", role="admin")
            db.add(user)
            db.commit()
            db.refresh(user)
            
        session_token = uuid.uuid4().hex
        db_session = InterviewSession(
            user_id=user.id,
            session_token=session_token,
            role="Backend",
            difficulty=5,
            training_mode="adaptive",
            interviewer_persona="balanced",
            status="active",
            messages=json.dumps([]),
            personalization_context=json.dumps({
                "weak_areas": [],
                "resume_context": {},
                "section_scores": {},
                "current_phase": "Core Technical Round"
            })
        )
        db.add(db_session)
        db.commit()

    # 2. Mock crew to raise exception so fallback is used
    import src.api.routes.interview
    def mock_run_interview_answer(*args, **kwargs):
        raise Exception("Mock Rate Limit Exception!")
    src.api.routes.interview.run_interview_answer = mock_run_interview_answer
    
    # 3. Authenticate and POST to answer
    # We need a valid token for the admin user.
    from src.core.security import create_access_token
    token = create_access_token({"sub": str(user.id)})
    
    response = client.post(
        "/api/interview/answer",
        json={"session_id": session_token, "answer": "Here is a huge answer..."},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 500:
        print("REPRODUCED 500!")
        print(response.json())
        # To get the traceback, we can just call the route handler directly instead
    else:
        print("Status code:", response.status_code)
        print("Response:", response.json())
        
def test_reproduce_direct():
    with next(get_session()) as db:
        user = db.query(User).filter_by(username="admin").first()
        session_token = uuid.uuid4().hex
        db_session = InterviewSession(
            user_id=user.id,
            session_token=session_token,
            role="Backend",
            difficulty=5,
            training_mode="adaptive",
            interviewer_persona="balanced",
            status="active",
            messages=json.dumps([]),
            personalization_context=json.dumps({})
        )
        db.add(db_session)
        db.commit()

    import src.api.routes.interview
    def mock_run_interview_answer(*args, **kwargs):
        raise Exception("Mock Rate Limit Exception!")
    src.api.routes.interview.run_interview_answer = mock_run_interview_answer
    
    from src.api.routes.interview import submit_answer, AnswerReq
    from fastapi import BackgroundTasks
    req = AnswerReq(session_id=session_token, answer="Huge answer")
    bg = BackgroundTasks()
    
    with next(get_session()) as db:
        try:
            submit_answer(req, bg, db, user)
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise e
