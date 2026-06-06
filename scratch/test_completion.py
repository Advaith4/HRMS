import sys
import os
import json
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models import InterviewSession, User
from src.database.connection import get_session
from src.api.routes.interview import submit_answer, complete_interview, AnswerReq
from fastapi import BackgroundTasks

def run_multi_round():
    session_token = uuid.uuid4().hex
    bg = BackgroundTasks()

    with next(get_session()) as db:
        user = db.query(User).filter_by(username="admin").first()
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

        print("--- Testing Multi-round Submission ---")
        for i in range(1, 4):
            print(f"Round {i}...")
            req = AnswerReq(session_id=session_token, answer=f"Short answer for round {i}.")
            # Using real litellm/crewai, might take a few seconds
            res = submit_answer(req, bg, db, user)
            print(f"  Success! Score: {res.get('evaluation', {}).get('score', 'N/A')}")
        
        print("--- Testing Early Completion Flow ---")
        comp_res = complete_interview(session_token, bg, db, user)
        print("Completion Response:", comp_res)

if __name__ == "__main__":
    run_multi_round()
