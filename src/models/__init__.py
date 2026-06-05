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
    application_id: Optional[int] = Field(default=None, foreign_key="candidate_applications.id", index=True)
    violations_count: int = Field(default=0)
    violations: str = Field(default="[]")  # JSON: [{type, detail, timestamp}]
    cancellation_reason: Optional[str] = None
    status: str = Field(default="active", max_length=20)  # active | completed | cancelled
    
    # Phase 6 & 7 Hiring Intelligence JSON payloads (stored as text)
    competency_scores: Optional[str] = Field(default=None)
    job_fit_report: Optional[str] = Field(default=None)
    communication_metrics: Optional[str] = Field(default=None)
    behavioral_report: Optional[str] = Field(default=None)
    hiring_risks: Optional[str] = Field(default=None)
    timeline_replay: Optional[str] = Field(default=None)
    benchmarking: Optional[str] = Field(default=None)

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
    full_name: Optional[str] = Field(default=None, max_length=200)
    email: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=30)
    address: Optional[str] = Field(default=None, max_length=500)
    date_of_birth: Optional[date] = None
    emergency_contact: Optional[str] = Field(default=None, max_length=200)
    status: str = Field(default="Active", max_length=30)
    work_location: Optional[str] = Field(default=None, max_length=100)
    manager_id: Optional[int] = Field(default=None, foreign_key="users.id")
    department_id: Optional[int] = Field(default=None, foreign_key="departments.id")
    designation_id: Optional[int] = Field(default=None, foreign_key="designations.id")
    certifications: str = Field(default="", max_length=1000)
    years_of_experience: Optional[float] = None



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


class Department(SQLModel, table=True):
    __tablename__ = "departments"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=120, unique=True)
    description: str = Field(default="", max_length=500)
    head_user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Designation(SQLModel, table=True):
    __tablename__ = "designations"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=120)
    department_id: Optional[int] = Field(default=None, foreign_key="departments.id")
    level: int = Field(default=1)
    description: str = Field(default="", max_length=500)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EmployeeLifecycleEvent(SQLModel, table=True):
    __tablename__ = "employee_lifecycle_events"
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employees.id", index=True)
    event_type: str = Field(max_length=60)
    event_date: date = Field(default_factory=date.today)
    description: str = Field(default="", max_length=1000)
    created_by: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EmployeeTicket(SQLModel, table=True):
    __tablename__ = "employee_tickets"
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employees.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    title: str = Field(max_length=200)
    description: str = Field(max_length=3000)
    category: str = Field(max_length=60)
    priority: str = Field(default="Medium", max_length=20)
    status: str = Field(default="Open", max_length=30)
    assigned_to: Optional[int] = Field(default=None, foreign_key="users.id")
    resolution_note: Optional[str] = Field(default=None, max_length=2000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SalaryHistory(SQLModel, table=True):
    __tablename__ = "salary_history"
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employees.id", index=True)
    previous_salary: Optional[float] = None
    new_salary: float
    increment_percent: Optional[float] = None
    reason: str = Field(default="", max_length=500)
    approved_by: int = Field(foreign_key="users.id")
    effective_date: date = Field(default_factory=date.today)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PromotionHistory(SQLModel, table=True):
    __tablename__ = "promotion_history"
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employees.id", index=True)
    old_designation: str = Field(max_length=120)
    new_designation: str = Field(max_length=120)
    promotion_date: date = Field(default_factory=date.today)
    reason: str = Field(default="", max_length=500)
    approved_by: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class IncrementHistory(SQLModel, table=True):
    __tablename__ = "increment_history"
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employees.id", index=True)
    previous_salary: float
    new_salary: float
    increment_percent: float
    reason: str = Field(default="", max_length=500)
    effective_date: date = Field(default_factory=date.today)
    approved_by: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class HRNotification(SQLModel, table=True):
    __tablename__ = "hr_notifications"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    title: str = Field(max_length=200)
    message: str = Field(max_length=1000)
    event_type: str = Field(max_length=60)
    related_id: Optional[int] = None
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CandidateProfile(SQLModel, table=True):
    __tablename__ = "candidate_profiles"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, unique=True)
    full_name: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=30)
    date_of_birth: Optional[date] = None
    gender: str = Field(default="", max_length=40)
    location: str = Field(default="", max_length=100)
    address: str = Field(default="", max_length=500)
    linkedin_url: str = Field(default="", max_length=500)
    portfolio_url: str = Field(default="", max_length=500)
    current_status: str = Field(default="", max_length=60)
    current_company: str = Field(default="", max_length=200)
    current_role: str = Field(default="", max_length=200)
    years_of_experience: Optional[float] = None
    expected_salary: str = Field(default="", max_length=100)
    notice_period: str = Field(default="", max_length=100)
    degree: str = Field(default="", max_length=200)
    institution: str = Field(default="", max_length=200)
    graduation_year: str = Field(default="", max_length=20)
    cgpa_percentage: str = Field(default="", max_length=40)
    technical_skills: str = Field(default="", max_length=1000)
    soft_skills: str = Field(default="", max_length=1000)
    certifications: str = Field(default="", max_length=1000)
    is_complete: bool = Field(default=False)
    completion_percent: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EmployeeProfile(SQLModel, table=True):
    __tablename__ = "employee_profiles"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, unique=True)
    employee_id: Optional[int] = Field(default=None, foreign_key="employees.id", index=True)
    phone: str = Field(default="", max_length=30)
    address: str = Field(default="", max_length=500)
    emergency_contact: str = Field(default="", max_length=200)
    blood_group: str = Field(default="", max_length=20)
    marital_status: str = Field(default="", max_length=40)
    previous_experience: str = Field(default="", max_length=1000)
    skills: str = Field(default="", max_length=1000)
    certifications: str = Field(default="", max_length=1000)
    career_interests: str = Field(default="", max_length=1000)
    career_goals: str = Field(default="", max_length=1000)
    is_complete: bool = Field(default=False)
    completion_percent: int = Field(default=0)
    verification_status: str = Field(default="Pending Review", max_length=40)
    pre_populated: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CandidateDocument(SQLModel, table=True):
    __tablename__ = "candidate_documents"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    document_type: str = Field(max_length=80)
    original_filename: str = Field(max_length=255)
    stored_path: str = Field(max_length=700)
    verification_status: str = Field(default="Pending Review", max_length=40)
    rejection_comment: str = Field(default="", max_length=1000)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[int] = Field(default=None, foreign_key="users.id")


class EmployeeDocument(SQLModel, table=True):
    __tablename__ = "employee_documents"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    employee_id: Optional[int] = Field(default=None, foreign_key="employees.id", index=True)
    document_type: str = Field(max_length=80)
    original_filename: str = Field(max_length=255)
    stored_path: str = Field(max_length=700)
    verification_status: str = Field(default="Pending Review", max_length=40)
    rejection_comment: str = Field(default="", max_length=1000)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[int] = Field(default=None, foreign_key="users.id")


class OnboardingTemplate(SQLModel, table=True):
    """HR-created onboarding template with a set of tasks."""
    __tablename__ = "onboarding_templates"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=200)
    description: str = Field(default="", max_length=1000)
    is_active: bool = Field(default=True)
    created_by: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class OnboardingTask(SQLModel, table=True):
    """A task within an onboarding template."""
    __tablename__ = "onboarding_tasks"
    id: Optional[int] = Field(default=None, primary_key=True)
    template_id: int = Field(foreign_key="onboarding_templates.id", index=True)
    title: str = Field(max_length=200)
    description: str = Field(default="", max_length=1000)
    order_index: int = Field(default=0)
    is_required: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EmployeeOnboarding(SQLModel, table=True):
    """An onboarding plan instance assigned to one employee."""
    __tablename__ = "employee_onboarding"
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employees.id", index=True)
    template_id: int = Field(foreign_key="onboarding_templates.id")
    assigned_by: int = Field(foreign_key="users.id")
    status: str = Field(default="Active", max_length=30)  # Active, Completed, Overdue
    due_date: Optional[date] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EmployeeOnboardingTask(SQLModel, table=True):
    """Per-employee clone of a template task with completion state."""
    __tablename__ = "employee_onboarding_tasks"
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_onboarding_id: int = Field(foreign_key="employee_onboarding.id", index=True)
    task_title: str = Field(max_length=200)
    task_description: str = Field(default="", max_length=1000)
    order_index: int = Field(default=0)
    is_required: bool = Field(default=True)
    status: str = Field(default="Pending", max_length=30)  # Pending, In Progress, Completed
    completed_at: Optional[datetime] = None
    notes: str = Field(default="", max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TrainingProgram(SQLModel, table=True):
    """An HR-created training program that can be assigned to employees."""
    __tablename__ = "training_programs"
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    description: str = Field(default="", max_length=2000)
    category: str = Field(default="General", max_length=100)
    skills_covered: str = Field(default="", max_length=500)  # comma-separated
    duration_hours: int = Field(default=1)
    difficulty: str = Field(default="Beginner", max_length=30)  # Beginner, Intermediate, Advanced
    status: str = Field(default="Draft", max_length=20)  # Draft, Active, Archived
    created_by: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CandidateCredibilityReport(SQLModel, table=True):
    """AI analysis comparing resume claims against interview evidence."""
    __tablename__ = "candidate_credibility_reports"

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(foreign_key="users.id", index=True)
    session_id: int = Field(foreign_key="interview_sessions.id", index=True, unique=True)
    credibility_score: int = Field(default=0)
    supported_claims: str = Field(default="[]")
    weak_claims: str = Field(default="[]")
    missing_evidence: str = Field(default="[]")
    followup_topics: str = Field(default="[]")
    resume_score: int = Field(default=0)
    interview_avg_score: Optional[float] = None
    recommendation: str = Field(default="Insufficient Evidence", max_length=40)
    status: str = Field(default="pending", max_length=30, index=True)
    error_message: Optional[str] = None
    source: str = Field(default="fallback", max_length=40)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TrainingAssignment(SQLModel, table=True):
    """Assignment of a training program to one employee."""
    __tablename__ = "training_assignments"
    id: Optional[int] = Field(default=None, primary_key=True)
    program_id: int = Field(foreign_key="training_programs.id", index=True)
    employee_id: int = Field(foreign_key="employees.id", index=True)
    assigned_by: int = Field(foreign_key="users.id")
    status: str = Field(default="Not Started", max_length=30)  # Not Started, In Progress, Completed
    progress_percent: int = Field(default=0)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    due_date: Optional[date] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class OnboardingRequiredDocument(SQLModel, table=True):
    __tablename__ = "onboarding_required_documents"
    id: Optional[int] = Field(default=None, primary_key=True)
    template_id: int = Field(foreign_key="onboarding_templates.id", index=True)
    document_type: str = Field(max_length=80)
    created_at: datetime = Field(default_factory=datetime.utcnow)

