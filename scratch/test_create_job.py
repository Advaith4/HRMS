import sys
from sqlmodel import Session
sys.path.append(".")
from src.database.connection import engine
from src.models import JobPosting, User
from src.api.routes.jobs import JobCreateReq, create_job

with Session(engine) as session:
    # Get HR user
    hr_user = session.query(User).filter(User.username == "Advaith").first()
    if not hr_user:
        print("HR User Advaith not found.")
        sys.exit(1)

    req = JobCreateReq(
        title="D",
        department="D",
        salary_range="D",
        experience_required="DD",
        required_skills="DDD",
        description="DDD"
    )

    try:
        res = create_job(req, session, hr_user)
        print("Success! Created job:", res)
    except Exception as e:
        print("Error during job creation:", e)
