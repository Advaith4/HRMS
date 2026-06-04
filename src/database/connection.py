import logging

from sqlmodel import SQLModel, create_engine, Session, text
from src.config import settings

logger = logging.getLogger(__name__)


def _normalize_db_url(url: str) -> str:
    url = (url or "").strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    sslmode = settings.PGSSLMODE.strip()
    if sslmode and "sslmode=" not in url.lower() and url.startswith("postgresql://"):
        url = f"{url}{'&' if '?' in url else '?'}sslmode={sslmode}"

    return url


_db_url = _normalize_db_url(settings.DATABASE_URL)
if not _db_url:
    raise RuntimeError("DATABASE_URL is required. Configure the Supabase PostgreSQL connection string in .env.")

# SQLite and PostgreSQL use different driver connection arguments.
_connect_args = {"check_same_thread": False} if _db_url.startswith("sqlite") else {}
if _db_url.startswith("postgresql"):
    _connect_args["connect_timeout"] = settings.DATABASE_CONNECT_TIMEOUT

engine = create_engine(
    _db_url,
    echo=settings.DEBUG,
    connect_args=_connect_args,
    # Keep more connections open so requests don't wait for Supabase handshakes
    pool_size=10,
    max_overflow=20,
    pool_timeout=15,      # fail fast instead of waiting 30s (default)
    pool_pre_ping=True,   # drop stale connections before reuse
    pool_recycle=300,     # recycle connections every 5 min
)


def create_db_and_tables() -> None:
    import src.models  # noqa: F401

    if _db_url.startswith("sqlite") or settings.AUTO_CREATE_DB_SCHEMA:
        SQLModel.metadata.create_all(engine)
    _ensure_user_role_column()
    _ensure_application_ai_analysis_table()
    _ensure_resume_lab_columns()
    _ensure_interview_context_columns()
    _ensure_career_coach_memory_table()
    _ensure_phase1_employee_columns()
    _ensure_phase2_talent_tables()
    _ensure_profile_completion_tables()


def _ensure_user_role_column() -> None:
    """Lightweight migration for TalentForge role-based access."""
    try:
        if _db_url.startswith("sqlite"):
            _ensure_sqlite_user_role_column()
        else:
            _ensure_postgres_user_role_column()
    except Exception as exc:
        logger.warning("User role column migration skipped: %s", exc)


def _ensure_sqlite_user_role_column() -> None:
    with Session(engine) as session:
        existing = {row[1] for row in session.exec(text("PRAGMA table_info(users)")).all()}
        if not existing:
            return
        if "role" not in existing:
            session.exec(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'candidate'"))
        session.exec(text("UPDATE users SET role = 'candidate' WHERE role IS NULL OR role = ''"))
        session.commit()


def _ensure_postgres_user_role_column() -> None:
    statements = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'candidate'",
        "UPDATE users SET role = 'candidate' WHERE role IS NULL OR role = ''",
    ]
    with Session(engine) as session:
        for statement in statements:
            session.exec(text(statement))
        session.commit()


def _ensure_application_ai_analysis_table() -> None:
    """Create Day 2 AI analysis table where supported."""
    try:
        if _db_url.startswith("sqlite") or settings.AUTO_CREATE_DB_SCHEMA:
            SQLModel.metadata.create_all(engine)
        elif not _db_url.startswith("sqlite"):
            _ensure_postgres_application_ai_analysis_table()
    except Exception as exc:
        logger.warning("Application AI analysis migration skipped: %s", exc)


def _ensure_postgres_application_ai_analysis_table() -> None:
    statement = """
    CREATE TABLE IF NOT EXISTS application_ai_analyses (
        id SERIAL PRIMARY KEY,
        application_id INTEGER UNIQUE NOT NULL REFERENCES candidate_applications(id),
        fit_score INTEGER DEFAULT 0,
        recommendation VARCHAR(40) DEFAULT 'Consider',
        summary TEXT DEFAULT '',
        strengths TEXT DEFAULT '[]',
        weaknesses TEXT DEFAULT '[]',
        missing_skills TEXT DEFAULT '[]',
        observations TEXT DEFAULT '[]',
        technical_questions TEXT DEFAULT '[]',
        behavioral_questions TEXT DEFAULT '[]',
        probing_areas TEXT DEFAULT '[]',
        status VARCHAR(30) DEFAULT 'pending',
        error_message TEXT,
        source VARCHAR(40) DEFAULT 'fallback',
        created_at TIMESTAMP,
        updated_at TIMESTAMP
    )
    """
    with Session(engine) as session:
        session.exec(text(statement))
        session.commit()


def _ensure_resume_lab_columns() -> None:
    """Lightweight migration for the interactive Resume Lab fields."""
    try:
        if _db_url.startswith("sqlite"):
            _ensure_sqlite_resume_lab_columns()
        else:
            _ensure_postgres_resume_lab_columns()
    except Exception as exc:
        logger.warning("Resume Lab column migration skipped: %s", exc)


def _ensure_sqlite_resume_lab_columns() -> None:
    columns = {
        "original_text": "TEXT",
        "current_text": "TEXT",
        "parsed_resume": "TEXT",
        "last_analysis": "TEXT",
        "applied_fixes": "TEXT DEFAULT '[]'",
        "updated_at": "DATETIME",
    }
    with Session(engine) as session:
        existing = {row[1] for row in session.exec(text("PRAGMA table_info(resumes)")).all()}
        if not existing:
            return
        for name, definition in columns.items():
            if name not in existing:
                session.exec(text(f"ALTER TABLE resumes ADD COLUMN {name} {definition}"))
        session.exec(text("UPDATE resumes SET original_text = raw_text WHERE original_text IS NULL"))
        session.exec(text("UPDATE resumes SET current_text = raw_text WHERE current_text IS NULL"))
        session.exec(text("UPDATE resumes SET applied_fixes = '[]' WHERE applied_fixes IS NULL OR applied_fixes = ''"))
        session.commit()


def _ensure_postgres_resume_lab_columns() -> None:
    statements = [
        "ALTER TABLE resumes ADD COLUMN IF NOT EXISTS original_text TEXT",
        "ALTER TABLE resumes ADD COLUMN IF NOT EXISTS current_text TEXT",
        "ALTER TABLE resumes ADD COLUMN IF NOT EXISTS parsed_resume TEXT",
        "ALTER TABLE resumes ADD COLUMN IF NOT EXISTS last_analysis TEXT",
        "ALTER TABLE resumes ADD COLUMN IF NOT EXISTS applied_fixes TEXT DEFAULT '[]'",
        "ALTER TABLE resumes ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",
        "UPDATE resumes SET original_text = raw_text WHERE original_text IS NULL",
        "UPDATE resumes SET current_text = raw_text WHERE current_text IS NULL",
        "UPDATE resumes SET applied_fixes = '[]' WHERE applied_fixes IS NULL OR applied_fixes = ''",
    ]
    with Session(engine) as session:
        for statement in statements:
            session.exec(text(statement))
        session.commit()


def _ensure_interview_context_columns() -> None:
    """Lightweight migration for resume-aware interview sessions."""
    try:
        if _db_url.startswith("sqlite"):
            _ensure_sqlite_interview_context_columns()
        else:
            _ensure_postgres_interview_context_columns()
    except Exception as exc:
        logger.warning("Interview context column migration skipped: %s", exc)


def _ensure_sqlite_interview_context_columns() -> None:
    columns = {
        "personalization_context": "TEXT DEFAULT '{}'",
        "training_mode": "VARCHAR(40) DEFAULT 'adaptive'",
        "interviewer_persona": "VARCHAR(40) DEFAULT 'balanced'",
    }
    with Session(engine) as session:
        existing = {row[1] for row in session.exec(text("PRAGMA table_info(interview_sessions)")).all()}
        if not existing:
            return
        for name, definition in columns.items():
            if name not in existing:
                session.exec(text(f"ALTER TABLE interview_sessions ADD COLUMN {name} {definition}"))
        session.exec(text("UPDATE interview_sessions SET personalization_context = '{}' WHERE personalization_context IS NULL OR personalization_context = ''"))
        session.exec(text("UPDATE interview_sessions SET training_mode = 'adaptive' WHERE training_mode IS NULL OR training_mode = ''"))
        session.exec(text("UPDATE interview_sessions SET interviewer_persona = 'balanced' WHERE interviewer_persona IS NULL OR interviewer_persona = ''"))
        session.commit()


def _ensure_postgres_interview_context_columns() -> None:
    statements = [
        "ALTER TABLE interview_sessions ADD COLUMN IF NOT EXISTS personalization_context TEXT DEFAULT '{}'",
        "ALTER TABLE interview_sessions ADD COLUMN IF NOT EXISTS training_mode VARCHAR(40) DEFAULT 'adaptive'",
        "ALTER TABLE interview_sessions ADD COLUMN IF NOT EXISTS interviewer_persona VARCHAR(40) DEFAULT 'balanced'",
        "UPDATE interview_sessions SET personalization_context = '{}' WHERE personalization_context IS NULL OR personalization_context = ''",
        "UPDATE interview_sessions SET training_mode = 'adaptive' WHERE training_mode IS NULL OR training_mode = ''",
        "UPDATE interview_sessions SET interviewer_persona = 'balanced' WHERE interviewer_persona IS NULL OR interviewer_persona = ''",
    ]
    with Session(engine) as session:
        for statement in statements:
            session.exec(text(statement))
        session.commit()


def _ensure_career_coach_memory_table() -> None:
    """Create long-term coach memory table where supported."""
    try:
        if _db_url.startswith("sqlite") or settings.AUTO_CREATE_DB_SCHEMA:
            SQLModel.metadata.create_all(engine)
        elif not _db_url.startswith("sqlite"):
            _ensure_postgres_career_coach_memory_table()
    except Exception as exc:
        logger.warning("Career coach memory migration skipped: %s", exc)


def _ensure_postgres_career_coach_memory_table() -> None:
    statement = """
    CREATE TABLE IF NOT EXISTS career_coach_memory (
        id SERIAL PRIMARY KEY,
        user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
        recurring_weak_areas TEXT DEFAULT '[]',
        score_trend TEXT DEFAULT '[]',
        session_history TEXT DEFAULT '[]',
        daily_plan TEXT,
        preferred_persona VARCHAR(40) DEFAULT 'balanced',
        preferred_training_mode VARCHAR(40) DEFAULT 'adaptive',
        session_count INTEGER DEFAULT 0,
        avg_answer_score DOUBLE PRECISION,
        created_at TIMESTAMP,
        updated_at TIMESTAMP
    )
    """
    with Session(engine) as session:
        session.exec(text(statement))
        session.commit()


def _ensure_phase1_employee_columns() -> None:
    """Lightweight migration to add Phase 1 Employee fields."""
    try:
        if _db_url.startswith("sqlite"):
            _ensure_sqlite_phase1_employee_columns()
        else:
            _ensure_postgres_phase1_employee_columns()
    except Exception as exc:
        logger.warning("Phase 1 Employee columns migration skipped: %s", exc)


def _ensure_sqlite_phase1_employee_columns() -> None:
    columns = {
        "full_name": "VARCHAR(200)",
        "email": "VARCHAR(200)",
        "phone": "VARCHAR(30)",
        "address": "VARCHAR(500)",
        "date_of_birth": "DATE",
        "emergency_contact": "VARCHAR(200)",
        "status": "VARCHAR(30) DEFAULT 'Active'",
        "work_location": "VARCHAR(100)",
        "manager_id": "INTEGER",
        "department_id": "INTEGER",
        "designation_id": "INTEGER",
        "certifications": "VARCHAR(1000) DEFAULT ''",
        "years_of_experience": "REAL",
    }
    with Session(engine) as session:
        existing = {row[1] for row in session.exec(text("PRAGMA table_info(employees)")).all()}
        if not existing:
            return
        for name, definition in columns.items():
            if name not in existing:
                session.exec(text(f"ALTER TABLE employees ADD COLUMN {name} {definition}"))
        session.exec(text("UPDATE employees SET status = 'Active' WHERE status IS NULL OR status = ''"))
        session.exec(text("UPDATE employees SET certifications = '' WHERE certifications IS NULL"))
        session.commit()


def _ensure_postgres_phase1_employee_columns() -> None:
    statements = [
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS full_name VARCHAR(200)",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS email VARCHAR(200)",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS phone VARCHAR(30)",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS address VARCHAR(500)",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS date_of_birth DATE",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS emergency_contact VARCHAR(200)",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS status VARCHAR(30) DEFAULT 'Active'",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS work_location VARCHAR(100)",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS manager_id INTEGER REFERENCES users(id)",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS department_id INTEGER REFERENCES departments(id)",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS designation_id INTEGER REFERENCES designations(id)",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS certifications VARCHAR(1000) DEFAULT ''",
        "ALTER TABLE employees ADD COLUMN IF NOT EXISTS years_of_experience DOUBLE PRECISION",
        "UPDATE employees SET status = 'Active' WHERE status IS NULL OR status = ''",
        "UPDATE employees SET certifications = '' WHERE certifications IS NULL",
    ]
    with Session(engine) as session:
        for statement in statements:
            session.exec(text(statement))
        session.commit()


def _ensure_phase2_talent_tables() -> None:
    """Create Phase 2A onboarding and training tables for managed PostgreSQL deployments."""
    try:
        if _db_url.startswith("sqlite") or settings.AUTO_CREATE_DB_SCHEMA:
            SQLModel.metadata.create_all(engine)
        else:
            _ensure_postgres_phase2_talent_tables()
    except Exception as exc:
        logger.warning("Phase 2A talent tables migration skipped: %s", exc)


def _ensure_postgres_phase2_talent_tables() -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS onboarding_templates (
            id SERIAL PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            description VARCHAR(1000) DEFAULT '',
            is_active BOOLEAN DEFAULT TRUE,
            created_by INTEGER NOT NULL REFERENCES users(id),
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS onboarding_tasks (
            id SERIAL PRIMARY KEY,
            template_id INTEGER NOT NULL REFERENCES onboarding_templates(id),
            title VARCHAR(200) NOT NULL,
            description VARCHAR(1000) DEFAULT '',
            order_index INTEGER DEFAULT 0,
            is_required BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS employee_onboarding (
            id SERIAL PRIMARY KEY,
            employee_id INTEGER NOT NULL REFERENCES employees(id),
            template_id INTEGER NOT NULL REFERENCES onboarding_templates(id),
            assigned_by INTEGER NOT NULL REFERENCES users(id),
            status VARCHAR(30) DEFAULT 'Active',
            due_date DATE,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS employee_onboarding_tasks (
            id SERIAL PRIMARY KEY,
            employee_onboarding_id INTEGER NOT NULL REFERENCES employee_onboarding(id),
            task_title VARCHAR(200) NOT NULL,
            task_description VARCHAR(1000) DEFAULT '',
            order_index INTEGER DEFAULT 0,
            is_required BOOLEAN DEFAULT TRUE,
            status VARCHAR(30) DEFAULT 'Pending',
            completed_at TIMESTAMP,
            notes VARCHAR(500) DEFAULT '',
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS training_programs (
            id SERIAL PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            description VARCHAR(2000) DEFAULT '',
            category VARCHAR(100) DEFAULT 'General',
            skills_covered VARCHAR(500) DEFAULT '',
            duration_hours INTEGER DEFAULT 1,
            difficulty VARCHAR(30) DEFAULT 'Beginner',
            status VARCHAR(20) DEFAULT 'Draft',
            created_by INTEGER NOT NULL REFERENCES users(id),
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS training_assignments (
            id SERIAL PRIMARY KEY,
            program_id INTEGER NOT NULL REFERENCES training_programs(id),
            employee_id INTEGER NOT NULL REFERENCES employees(id),
            assigned_by INTEGER NOT NULL REFERENCES users(id),
            status VARCHAR(30) DEFAULT 'Not Started',
            progress_percent INTEGER DEFAULT 0,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            due_date DATE,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        """,
    ]
    with Session(engine) as session:
        for statement in statements:
            session.exec(text(statement))
        session.commit()


def _ensure_profile_completion_tables() -> None:
    try:
        if _db_url.startswith("sqlite") or settings.AUTO_CREATE_DB_SCHEMA:
            SQLModel.metadata.create_all(engine)
        else:
            _ensure_postgres_profile_completion_tables()
    except Exception as exc:
        logger.warning("Profile completion tables migration skipped: %s", exc)


def _ensure_postgres_profile_completion_tables() -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS candidate_profiles (
            id SERIAL PRIMARY KEY,
            user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
            full_name VARCHAR(200) DEFAULT '',
            phone VARCHAR(30) DEFAULT '',
            date_of_birth DATE,
            gender VARCHAR(40) DEFAULT '',
            location VARCHAR(100) DEFAULT '',
            address VARCHAR(500) DEFAULT '',
            linkedin_url VARCHAR(500) DEFAULT '',
            portfolio_url VARCHAR(500) DEFAULT '',
            current_status VARCHAR(60) DEFAULT '',
            current_company VARCHAR(200) DEFAULT '',
            current_role VARCHAR(200) DEFAULT '',
            years_of_experience DOUBLE PRECISION,
            expected_salary VARCHAR(100) DEFAULT '',
            notice_period VARCHAR(100) DEFAULT '',
            degree VARCHAR(200) DEFAULT '',
            institution VARCHAR(200) DEFAULT '',
            graduation_year VARCHAR(20) DEFAULT '',
            cgpa_percentage VARCHAR(40) DEFAULT '',
            technical_skills VARCHAR(1000) DEFAULT '',
            soft_skills VARCHAR(1000) DEFAULT '',
            certifications VARCHAR(1000) DEFAULT '',
            is_complete BOOLEAN DEFAULT FALSE,
            completion_percent INTEGER DEFAULT 0,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS employee_profiles (
            id SERIAL PRIMARY KEY,
            user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
            employee_id INTEGER REFERENCES employees(id),
            phone VARCHAR(30) DEFAULT '',
            address VARCHAR(500) DEFAULT '',
            emergency_contact VARCHAR(200) DEFAULT '',
            blood_group VARCHAR(20) DEFAULT '',
            marital_status VARCHAR(40) DEFAULT '',
            previous_experience VARCHAR(1000) DEFAULT '',
            skills VARCHAR(1000) DEFAULT '',
            certifications VARCHAR(1000) DEFAULT '',
            career_interests VARCHAR(1000) DEFAULT '',
            career_goals VARCHAR(1000) DEFAULT '',
            is_complete BOOLEAN DEFAULT FALSE,
            completion_percent INTEGER DEFAULT 0,
            verification_status VARCHAR(40) DEFAULT 'Pending Review',
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS candidate_documents (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            document_type VARCHAR(80) NOT NULL,
            original_filename VARCHAR(255) NOT NULL,
            stored_path VARCHAR(700) NOT NULL,
            verification_status VARCHAR(40) DEFAULT 'Pending Review',
            rejection_comment VARCHAR(1000) DEFAULT '',
            uploaded_at TIMESTAMP,
            reviewed_at TIMESTAMP,
            reviewed_by INTEGER REFERENCES users(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS employee_documents (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            employee_id INTEGER REFERENCES employees(id),
            document_type VARCHAR(80) NOT NULL,
            original_filename VARCHAR(255) NOT NULL,
            stored_path VARCHAR(700) NOT NULL,
            verification_status VARCHAR(40) DEFAULT 'Pending Review',
            rejection_comment VARCHAR(1000) DEFAULT '',
            uploaded_at TIMESTAMP,
            reviewed_at TIMESTAMP,
            reviewed_by INTEGER REFERENCES users(id)
        )
        """,
    ]
    with Session(engine) as session:
        for statement in statements:
            session.exec(text(statement))
        session.commit()


def get_session():
    with Session(engine) as session:
        yield session

