import sys
import os
import json
import uuid
import time
from sqlalchemy import select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models import InterviewSession, User
from src.database.connection import get_session
from src.api.routes.interview import submit_answer, complete_interview, AnswerReq
from fastapi import BackgroundTasks

def run_audit():
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

        print("--- Testing 10-Round Interview ---")
        long_answer = "This is a very long and detailed answer. " * 30
        latencies = []
        for i in range(1, 11):
            start = time.time()
            try:
                req = AnswerReq(session_id=session_token, answer=f"{long_answer} (Round {i})")
                res = submit_answer(req, bg, db, user)
                latency = time.time() - start
                latencies.append(latency)
                print(f"Round {i} Success - Latency: {latency:.2f}s - Phase: {res.get('phase', 'Unknown')}")
            except Exception as e:
                print(f"Round {i} FAILED: {str(e)}")
                break
        
        print(f"\nAverage Latency: {sum(latencies)/len(latencies):.2f}s")
        print("\n--- Verifying Database State ---")
        rec = db.exec(select(InterviewSession).where(InterviewSession.session_token == session_token)).first()
        msgs = json.loads(rec.messages)
        print(f"Status: {rec.status}")
        print(f"Message Count: {len(msgs)}")
        print(f"Average Score Field: {rec.avg_score}")
        
        print("\n--- Testing Early Completion Flow ---")
        try:
            comp_res = complete_interview(session_token, bg, db, user)
            print("Completion Response:", comp_res)
            db.refresh(rec)
            print(f"Status After Complete: {rec.status}")
        except Exception as e:
            print(f"Completion FAILED: {str(e)}")

if __name__ == "__main__":
    run_audit()
