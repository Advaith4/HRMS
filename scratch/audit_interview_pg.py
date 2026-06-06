import os
import json
from sqlalchemy import create_engine, text
from sqlmodel import Session
from dotenv import load_dotenv

load_dotenv(dotenv_path="d:/GitHub/HRMS/.env")

# Connect to PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)

def print_separator(title):
    print(f"\n{'='*50}\n{title}\n{'='*50}")

def main():
    try:
        with engine.connect() as conn:
            # 1. Locate the InterviewSession row
            print_separator("1. InterviewSession Query")
            
            # Find the most recently completed interview
            query = text("""
                SELECT id, application_id, status, avg_score, created_at, updated_at
                FROM interview_sessions
                ORDER BY updated_at DESC
                LIMIT 1
            """)
            result = conn.execute(query).fetchone()
            
            if not result:
                print("No InterviewSession records found.")
                return
                
            session_id, app_id, status, avg_score, created_at, updated_at = result
            
            print(f"ID: {session_id}")
            print(f"Application ID: {app_id}")
            print(f"Status: {status}")
            print(f"Avg Score: {avg_score}")
            print(f"Created At: {created_at}")
            print(f"Updated At: {updated_at}")
            
            # Check ai_summary/job_fit_report/competency_scores etc.
            query = text("""
                SELECT competency_scores, job_fit_report
                FROM interview_sessions
                WHERE id = :id
            """)
            result = conn.execute(query, {"id": session_id}).fetchone()
            competency_scores, job_fit_report = result
            print("\nDid compile_hiring_intelligence execute? Check for JSON payloads:")
            print(f"competency_scores populated: {bool(competency_scores)}")
            print(f"job_fit_report populated: {bool(job_fit_report)}")
            if job_fit_report:
                print(f"Job Fit Report snippet: {job_fit_report[:100]}")
            
            # 2. ApplicationAIAnalysis Query
            print_separator("2. ApplicationAIAnalysis Query")
            if app_id:
                query = text("""
                    SELECT id, application_id, fit_score, recommendation, summary, created_at, updated_at
                    FROM application_ai_analyses
                    WHERE application_id = :app_id
                """)
                result = conn.execute(query, {"app_id": app_id}).fetchone()
                if result:
                    id, app_id2, fit_score, recommendation, summary, created_at, updated_at = result
                    print(f"ID: {id}")
                    print(f"Application ID: {app_id2}")
                    print(f"Fit Score: {fit_score}")
                    print(f"Recommendation: {recommendation}")
                    print(f"Summary: {summary[:100]}...")
                    print(f"Created At: {created_at}")
                    print(f"Updated At: {updated_at}")
                else:
                    print(f"No ApplicationAIAnalysis found for application_id={app_id}")
            
    except Exception as e:
        print(f"Error querying database: {e}")

if __name__ == "__main__":
    main()
