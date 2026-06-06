import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models import InterviewSession, User
from src.database.connection import get_session
import json
import uuid

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
        
        try:
            submit_answer(req, bg, db, user)
            print("Finished successfully")
        except Exception as e:
            import traceback
            print("--- TRACEBACK CAUGHT ---")
            traceback.print_exc()

if __name__ == "__main__":
    test_reproduce_direct()
