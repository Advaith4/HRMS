import os
import json
from dotenv import load_dotenv

load_dotenv("d:/GitHub/HRMS/.env")

from src.main import app
from fastapi.testclient import TestClient
from src.database.connection import get_session
from src.models import User
from src.api.dependencies import require_roles

client = TestClient(app)

# Override dependencies to mock HR user
def override_require_roles(*allowed_roles):
    def dependency():
        # Return a mock HR user
        return User(id=1, username="admin", role="admin")
    return dependency

app.dependency_overrides[require_roles] = override_require_roles

# Wait, `require_roles` is a parameterized dependency.
# It returns a dependency function. In FastAPI, `app.dependency_overrides` matches the actual function injected.
# Since `require_roles` returns a nested function, overriding the factory itself won't work easily.
# A simpler way is to just call `hr_dashboard` directly.

def test_dashboard_directly():
    from src.api.routes.dashboard import hr_dashboard
    from sqlmodel import Session
    from sqlalchemy import create_engine

    DATABASE_URL = os.environ.get("DATABASE_URL")
    engine = create_engine(DATABASE_URL)
    
    with Session(engine) as session:
        result = hr_dashboard(session=session)
        apps = result.get("applications", [])
        print(f"Total apps fetched: {len(apps)}")
        for app_data in apps:
            print(f"\nApp ID: {app_data['id']}")
            print(f"Status: {app_data['status']}")
            
            ai_analysis = app_data.get("ai_analysis")
            if ai_analysis:
                print(f"Resume Fit Score: {ai_analysis.get('fit_score')}")
            
            interview_analysis = app_data.get("interview_analysis")
            if interview_analysis:
                print(f"Interview Status: {interview_analysis.get('status')}")
                if interview_analysis.get("job_fit_report"):
                    if isinstance(interview_analysis["job_fit_report"], str):
                        try:
                            jf = json.loads(interview_analysis["job_fit_report"])
                            print(f"Interview Job Fit: {jf.get('jobFit')}")
                            print(f"Interview Strengths: {jf.get('strengths')}")
                        except:
                            print("Failed to parse job_fit_report")
                    else:
                        print(f"Interview Job Fit: {interview_analysis['job_fit_report'].get('jobFit')}")
                        print(f"Interview Strengths: {interview_analysis['job_fit_report'].get('strengths')}")
            else:
                print("No Interview Analysis")

if __name__ == "__main__":
    test_dashboard_directly()
