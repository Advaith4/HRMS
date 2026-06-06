import sys
import os
import json
import logging
from pprint import pprint

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set up logging to capture stack traces
logging.basicConfig(level=logging.ERROR)

from src.database.connection import get_session
from src.api.routes.interview import submit_answer, AnswerReq
from fastapi import BackgroundTasks
from src.models import User, InterviewSession
import datetime
import uuid

def test_fallback():
    # We will simulate the exact submit_answer logic but force the LLM fallback
    # by passing a huge answer or just mocking run_interview_answer to raise Exception.
    
    # 1. Create a mock user and session in the database
    with next(get_session()) as db:
        user = db.query(User).filter_by(username="admin").first()
        if not user:
            print("Admin user not found. Creating temporary user.")
            user = User(username="test_user", password_hash="hash", email="test@test.com", role="candidate")
            db.add(user)
            db.commit()
            db.refresh(user)

        session_token = uuid.uuid4().hex
        context = {
            "weak_areas": ["Testing"],
            "resume_context": {"summary": "Experienced dev"},
            "section_scores": {},
            "training_mode": "adaptive",
            "interviewer_persona": "balanced",
            "coach_memory": {},
            "domain_focus": "backend",
            "current_focus_area": "Testing",
            "current_phase": "Core Technical Round"
        }
        
        first_msg = {
            "role": "ai",
            "content": "Tell me about a time you used testing.",
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "focus_area": "Testing",
            "focus_type": "weak_area",
            "phase": "Core Technical Round",
        }
        
        db_session = InterviewSession(
            user_id=user.id,
            application_id=None,
            session_token=session_token,
            role="Backend Engineer",
            difficulty=5,
            training_mode="adaptive",
            interviewer_persona="balanced",
            messages=json.dumps([first_msg]),
            personalization_context=json.dumps(context),
            status="active"
        )
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        
        # 2. Mock crew.run_interview_answer to throw an exception
        import src.api.routes.interview
        original_run = getattr(src.api.routes.interview, "run_interview_answer", None)
        
        def mock_run_interview_answer(*args, **kwargs):
            raise Exception("Mock Rate Limit Exception!")
            
        src.api.routes.interview.run_interview_answer = mock_run_interview_answer
        
        # 3. Call submit_answer
        req = AnswerReq(session_id=session_token, answer="This is my test answer.")
        bg_tasks = BackgroundTasks()
        
        try:
            print("Calling submit_answer...")
            res = submit_answer(req=req, background_tasks=bg_tasks, db=db, current_user=user)
            print("Success! Response:", res)
        except Exception as e:
            print("\n--- CRASH REPRODUCED ---")
            logging.exception("Exception in submit_answer:")
            print("------------------------\n")
            
test_fallback()
