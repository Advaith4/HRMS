from typing import Optional
from datetime import date, datetime
from sqlmodel import Field, SQLModel

USER_ROLES = {"candidate", "employee", "hr", "manager", "admin"}
APPLICATION_STATUSES = {"Applied", "Under Review", "Shortlisted", "Selected", "Rejected", "Hired"}
LEAVE_STATUSES = {"Pending", "Approved", "Rejected"}


class User(SQLModel, table=True):
    """Registered user. Password stored as bcrypt hash."""
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=50)
    hashed_password: str
    role: str = Field(default="candidate", max_length=20, index=True)
    target_role: Optional[str] = Field(default=None, max_length=100)
    location: Optional[str] = Field(default="India", max_length=100)
    experience: Optional[str] = Field(default="Entry-level", max_length=50)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Resume(SQLModel, table=True):
    """Latest resume text and interactive Resume Lab state for a user."""
    __tablename__ = "resumes"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    raw_text: str
    original_text: Optional[str] = None
    current_text: Optional[str] = None
    parsed_resume: Optional[str] = None
    last_analysis: Optional[str] = None
    applied_fixes: str = Field(default="[]")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class JobApplication(SQLModel, table=True):
    """Tracked job with AI-tailored resume bullets."""
    __tablename__ = "job_applications"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    company_name: Optional[str] = Field(default=None, max_length=200)
    job_title: str = Field(max_length=200)
    job_description_url: Optional[str] = Field(default=None, max_length=500)
    status: str = Field(default="Bookmarked", max_length=50)
    tailored_resume_bullets: Optional[str] = None  # JSON array stored as text
    created_at: datetime = Field(default_factory=datetime.utcnow)


class InterviewSession(SQLModel, table=True):
    """Persisted mock interview session with full chat history."""
    __tablename__ = "interview_sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    session_token: str = Field(index=True, unique=True)   # UUID hex — links to in-memory state
    role: str = Field(max_length=100)
    difficulty: int = Field(default=5)
    training_mode: str = Field(default="adaptive", max_length=40)
    interviewer_persona: str = Field(default="balanced", max_length=40)
    messages: str = Field(default="[]")  # JSON: [{role, content, score?, timestamp}]
    personalization_context: str = Field(default="{}")  # JSON: resume weaknesses, section scores, focus mix
    avg_score: Optional[float] = None
    status: str = Field(default="active", max_length=20)  # active | completed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CareerCoachMemory(SQLModel, table=True):
    """Long-term coaching memory synthesized from resume analysis and interview sessions."""
    __tablename__ = "career_coach_memory"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, unique=True)
    recurring_weak_areas: str = Field(default="[]")  # JSON: [{area, count, last_seen}]
    score_trend: str = Field(default="[]")  # JSON: recent answer scores and focus areas
    session_history: str = Field(default="[]")  # JSON: compact session summaries
    daily_plan: Optional[str] = None  # JSON: latest generated coaching plan
    preferred_persona: str = Field(default="balanced", max_length=40)
    preferred_training_mode: str = Field(default="adaptive", max_length=40)
    session_count: int = Field(default=0)
    avg_answer_score: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class JobPosting(SQLModel, table=True):
    """Internal HR-created job opening for TalentForge AI."""
    __tablename__ = "job_postings"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    description: str
    required_skills: str = Field(default="")
    department: str = Field(default="", max_length=120)
    salary_range: str = Field(default="", max_length=120)
    experience_required: str = Field(default="", max_length=120)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: int = Field(foreign_key="users.id", index=True)


class CandidateApplication(SQLModel, table=True):
    """Candidate application with parsed resume text."""
    __tablename__ = "candidate_applications"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_user_id: int = Field(foreign_key="users.id", index=True)
    job_id: int = Field(foreign_key="job_postings.id", index=True)
    resume_text: str
    application_date: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="Applied", max_length=30, index=True)


class ApplicationAIAnalysis(SQLModel, table=True):
    """AI recruitment intelligence output for a candidate application."""
    __tablename__ = "application_ai_analyses"

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="candidate_applications.id", index=True, unique=True)
    fit_score: int = Field(default=0)
    recommendation: str = Field(default="Consider", max_length=40, index=True)
    summary: str = Field(default="")
    strengths: str = Field(default="[]")
    weaknesses: str = Field(default="[]")
    missing_skills: str = Field(default="[]")
    observations: str = Field(default="[]")
    technical_questions: str = Field(default="[]")
    behavioral_questions: str = Field(default="[]")
    probing_areas: str = Field(default="[]")
    status: str = Field(default="pending", max_length=30, index=True)
    error_message: Optional[str] = None
    source: str = Field(default="fallback", max_length=40)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Employee(SQLModel, table=True):
    """Employee profile created after a candidate is hired."""
    __tablename__ = "employees"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, unique=True)
    employee_code: str = Field(index=True, unique=True, max_length=40)
    department: str = Field(default="", max_length=120)
    designation: str = Field(default="", max_length=120)
    salary: Optional[float] = None
    joining_date: Optional[date] = None
    skills: str = Field(default="")


class AttendanceRecord(SQLModel, table=True):
    """Daily employee attendance check-in/check-out record."""
    __tablename__ = "attendance_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employees.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    work_date: date = Field(default_factory=date.today, index=True)
    check_in: datetime = Field(default_factory=datetime.utcnow)
    check_out: Optional[datetime] = None
    status: str = Field(default="Checked In", max_length=30, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LeaveRequest(SQLModel, table=True):
    """Employee leave request with HR/manager decision state."""
    __tablename__ = "leave_requests"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employees.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    leave_type: str = Field(default="General", max_length=60)
    start_date: date = Field(index=True)
    end_date: date = Field(index=True)
    reason: str = Field(default="")
    status: str = Field(default="Pending", max_length=30, index=True)
    manager_note: Optional[str] = None
    decided_by: Optional[int] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SkillGapAnalysis(SQLModel, table=True):
    """Latest employee skill gap analysis against role expectations."""
    __tablename__ = "skill_gap_analyses"

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employees.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    role_expectations: str = Field(default="")
    missing_skills: str = Field(default="[]")
    growth_areas: str = Field(default="[]")
    learning_suggestions: str = Field(default="[]")
    summary: str = Field(default="")
    source: str = Field(default="fallback", max_length=40)
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
