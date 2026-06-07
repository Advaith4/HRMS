import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlmodel import Session, select

from src.database.connection import engine
from src.models import (
    ApplicationAIAnalysis,
    CandidateApplication,
    Employee,
    InterviewIntelligenceReport,
    InterviewSession,
    JobPosting,
    User,
    AttendanceRecord,
    LeaveRequest,
    TrainingAssignment,
    TrainingProgram,
    EmployeeTicket,
    EmployeeProfile,
    Department,
    Designation,
)
from src.services.rag.access_control import HR_ROLES

logger = logging.getLogger(__name__)

DATABASE_KEYWORDS = {
    "application status",
    "applications status",
    "status of my application",
    "how many",
    "count",
    "counts",
    "metric",
    "metrics",
    "pipeline",
    "statistics",
    "stats",
    "open jobs",
    "active jobs",
    "interview status",
    "interview progress",
    "employee statistics",
    "employee count",
}

HYBRID_KEYWORDS = {
    "strongest",
    "compare",
    "shortlisted",
    "next round",
    "move forward",
    "move to the next",
    "hiring risks",
    "risk",
    "match this jd",
    "matches this jd",
    "best match",
    "best candidates",
    "recommend",
    "recommendation",
    "summarize active candidates",
    "candidate ranking",
    "ranking",
}

CANDIDATE_INTELLIGENCE_KEYWORDS = {
    "my application",
    "application status",
    "interview progress",
    "skills should i improve",
    "skill gap",
    "improve",
    "prepare",
    "preparation",
    "feedback",
    "role require",
    "job require",
}


@dataclass(frozen=True)
class QueryRoute:
    mode: str
    database_context: str = ""
    database_sources: list[dict[str, Any]] = field(default_factory=list)


class QueryRouter:
    def route(self, query: str, user: User) -> QueryRoute:
        clean_query = (query or "").strip()
        lowered = clean_query.lower()
        is_hr = user.role in HR_ROLES

        if is_hr and self._contains_any(lowered, HYBRID_KEYWORDS):
            return QueryRoute(
                mode="hybrid",
                database_context=self._build_hr_decision_context(clean_query),
                database_sources=self._sources(
                    "Database",
                    "Hybrid hiring decision context from pipeline, resume analysis, and interview intelligence",
                ),
            )

        if user.role == "candidate" and self._contains_any(lowered, CANDIDATE_INTELLIGENCE_KEYWORDS):
            return QueryRoute(
                mode="hybrid",
                database_context=self._build_candidate_context(user),
                database_sources=self._sources("Database", "Candidate applications and interview progress"),
            )

        if user.role == "employee":
            personal_query_indicators = {
                "my", "i", "me", "we", "us", "am i", "do i", "have i", "how many", "how much",
                "balance", "remaining", "used", "status", "assigned", "open", "manager", "department",
                "designation", "salary", "joining", "code", "profile"
            }
            has_db_subject = self._contains_any(lowered, {"leave", "vacation", "sick", "casual", "training", "course", "ticket", "attendance", "manager", "department", "designation", "salary", "joining", "profile"})
            has_personal_indicator = self._contains_any(lowered, personal_query_indicators)
            
            if has_db_subject and has_personal_indicator:
                return QueryRoute(
                    mode="hybrid",
                    database_context=self._build_employee_context(user),
                    database_sources=self._sources("Database", "Live Employee Data"),
                )

        if self._contains_any(lowered, DATABASE_KEYWORDS):
            if is_hr:
                return QueryRoute(
                    mode="database",
                    database_context=self._build_hr_metrics_context(),
                    database_sources=self._sources("Database", "Live HRMS metrics"),
                )
            if user.role == "candidate":
                return QueryRoute(
                    mode="database",
                    database_context=self._build_candidate_context(user),
                    database_sources=self._sources("Database", "Candidate applications and interview progress"),
                )

        return QueryRoute(mode="rag")

    def _build_hr_metrics_context(self) -> str:
        with Session(engine) as session:
            jobs = session.exec(select(JobPosting)).all()
            applications = session.exec(select(CandidateApplication)).all()
            interviews = session.exec(select(InterviewSession)).all()
            employees = session.exec(select(Employee)).all()

        app_counts = self._count_by(applications, "status")
        interview_counts = self._count_by(interviews, "status")
        department_counts = self._count_by(jobs, "department")
        active_jobs = len(jobs)

        return "\n".join(
            [
                "SOURCE: Database",
                "TYPE: Live HRMS metrics",
                f"Active jobs: {active_jobs}",
                f"Total applications: {len(applications)}",
                f"Application status counts: {self._format_counts(app_counts)}",
                f"Interview status counts: {self._format_counts(interview_counts)}",
                f"Employee count: {len(employees)}",
                f"Jobs by department: {self._format_counts(department_counts)}",
            ]
        )

    def _build_hr_decision_context(self, query: str) -> str:
        role_terms = self._query_terms(query)
        with Session(engine) as session:
            jobs = session.exec(select(JobPosting)).all()
            applications = session.exec(select(CandidateApplication)).all()
            analyses = {item.application_id: item for item in session.exec(select(ApplicationAIAnalysis)).all()}
            reports = {item.application_id: item for item in session.exec(select(InterviewIntelligenceReport)).all()}
            users = {item.id: item for item in session.exec(select(User)).all()}

        jobs_by_id = {job.id: job for job in jobs}
        rows = []
        for application in applications:
            job = jobs_by_id.get(application.job_id)
            if not job:
                continue
            if role_terms and not self._job_matches_terms(job, role_terms):
                continue
            analysis = analyses.get(application.id)
            report = reports.get(application.id)
            candidate = users.get(application.candidate_user_id)
            ranking_score = self._ranking_score(analysis, report)
            rows.append((ranking_score, application, job, analysis, report, candidate))

        if not rows and role_terms:
            rows = [
                (self._ranking_score(analyses.get(app.id), reports.get(app.id)), app, jobs_by_id.get(app.job_id), analyses.get(app.id), reports.get(app.id), users.get(app.candidate_user_id))
                for app in applications
                if jobs_by_id.get(app.job_id)
            ]

        rows.sort(key=lambda row: row[0], reverse=True)
        lines = [
            "SOURCE: Database + Resume Analysis + Interview Reports + Job Descriptions",
            "TYPE: Hybrid hiring decision context",
            "Ranking score combines stored resume fit score and interview overall score for decision support only; it does not alter HRMS scoring.",
        ]
        for rank, (score, application, job, analysis, report, candidate) in enumerate(rows[:8], start=1):
            lines.extend(
                [
                    f"Candidate {rank}: {candidate.username if candidate else f'user {application.candidate_user_id}'}",
                    f"- Job: {job.title} ({job.department or 'department unavailable'})",
                    f"- Application status: {application.status}",
                    f"- Decision support score: {score:.1f}",
                    f"- Resume analysis: {self._analysis_summary(analysis)}",
                    f"- Interview intelligence: {self._report_summary(report)}",
                    f"- Job requirements: {job.required_skills or 'No required skills listed'}",
                ]
            )
        if len(lines) == 3:
            lines.append("No candidate records were found for this decision query.")
        return "\n".join(lines)

    def _build_candidate_context(self, user: User) -> str:
        with Session(engine) as session:
            applications = session.exec(
                select(CandidateApplication).where(CandidateApplication.candidate_user_id == user.id)
            ).all()
            jobs = {job.id: job for job in session.exec(select(JobPosting)).all()}
            analyses = {item.application_id: item for item in session.exec(select(ApplicationAIAnalysis)).all()}
            reports = {item.application_id: item for item in session.exec(select(InterviewIntelligenceReport)).all()}
            sessions = session.exec(select(InterviewSession).where(InterviewSession.user_id == user.id)).all()

        sessions_by_app: dict[int, list[InterviewSession]] = {}
        for session in sessions:
            if session.application_id:
                sessions_by_app.setdefault(session.application_id, []).append(session)

        lines = [
            "SOURCE: Database + Resume Analysis + Interview Reports + Job Descriptions",
            "TYPE: Candidate-owned guidance context",
        ]
        for application in applications:
            job = jobs.get(application.job_id)
            analysis = analyses.get(application.id)
            report = reports.get(application.id)
            app_sessions = sessions_by_app.get(application.id, [])
            lines.extend(
                [
                    f"Application {application.id}: {job.title if job else f'job {application.job_id}'}",
                    f"- Application status: {application.status}",
                    f"- Job requirements: {job.required_skills if job else 'Unavailable'}",
                    f"- Resume analysis: {self._analysis_summary(analysis)}",
                    f"- Interview progress: {self._session_summary(app_sessions)}",
                    f"- Interview feedback: {self._report_summary(report)}",
                ]
            )
        if len(lines) == 2:
            lines.append("No candidate-owned application records were found.")
        return "\n".join(lines)

    def _build_employee_context(self, user: User) -> str:
        with Session(engine) as session:
            employee = session.exec(select(Employee).where(Employee.user_id == user.id)).first()
            if not employee:
                return "SOURCE: Database\nTYPE: Employee live personal data\nNo employee profile record found for this user."
            
            # Optimized query path: load related records in single queries
            attendance_records = session.exec(
                select(AttendanceRecord)
                .where(AttendanceRecord.employee_id == employee.id)
                .order_by(AttendanceRecord.work_date.desc())
            ).all()
            
            leaves = session.exec(
                select(LeaveRequest)
                .where(LeaveRequest.employee_id == employee.id)
                .order_by(LeaveRequest.created_at.desc())
            ).all()
            
            training_assignments = session.exec(
                select(TrainingAssignment)
                .where(TrainingAssignment.employee_id == employee.id)
            ).all()
            
            # Batch fetch programs to avoid N+1 queries
            program_ids = list({ta.program_id for ta in training_assignments if ta.program_id})
            programs_by_id = {}
            if program_ids:
                programs = session.exec(select(TrainingProgram).where(TrainingProgram.id.in_(program_ids))).all()
                programs_by_id = {p.id: p for p in programs}
                
            tickets = session.exec(
                select(EmployeeTicket)
                .where(EmployeeTicket.user_id == user.id)
                .order_by(EmployeeTicket.created_at.desc())
            ).all()
            
            profile = session.exec(select(EmployeeProfile).where(EmployeeProfile.user_id == user.id)).first()
            profile_completion = profile.completion_percent if profile else 0
            
            manager_username = "Not Assigned"
            if employee.manager_id:
                mgr = session.get(User, employee.manager_id)
                manager_username = mgr.username if mgr else "Not Assigned"
                
            dept_name = employee.department
            if employee.department_id:
                dept = session.get(Department, employee.department_id)
                if dept:
                    dept_name = dept.name
                    
            desig_name = employee.designation
            if employee.designation_id:
                desig = session.get(Designation, employee.designation_id)
                if desig:
                    desig_name = desig.name

            # Today's attendance
            today_record = None
            for rec in attendance_records:
                if rec.work_date == date.today():
                    today_record = rec
                    break
            attendance_status = today_record.status if today_record else "Not Checked In"
            total_checkins = len(attendance_records)
            
            # Leave Balance (deterministic calculation matching backend/frontend)
            allocations = {"Annual": 15, "Sick": 12, "Casual": 7}
            used = {"Annual": 0, "Sick": 0, "Casual": 0}
            for leave in leaves:
                if leave.status == "Approved" and leave.start_date and leave.end_date:
                    days = max(0, (leave.end_date - leave.start_date).days + 1)
                    key = leave.leave_type.strip().title() if leave.leave_type else "General"
                    if key in used:
                        used[key] += days
            remaining = {key: max(0, allocations[key] - used[key]) for key in allocations}
            
            assigned_trainings = []
            for ta in training_assignments:
                prog = programs_by_id.get(ta.program_id)
                prog_title = prog.title if prog else f"Program {ta.program_id}"
                assigned_trainings.append(f"{prog_title} (Status: {ta.status}, Progress: {ta.progress_percent}%)")
                
            open_tickets = [t for t in tickets if t.status.lower() != "closed"]
            ticket_summaries = [f"Title: {t.title} (Priority: {t.priority}, Status: {t.status})" for t in open_tickets]
            
            lines = [
                "SOURCE: Database",
                "TYPE: Employee live personal data",
                f"Employee ID: {employee.id}",
                f"Employee Code: {employee.employee_code}",
                f"Full Name: {employee.full_name or user.username}",
                f"Department: {dept_name or 'Not Assigned'}",
                f"Designation: {desig_name or 'Not Assigned'}",
                f"Manager: {manager_username}",
                f"Join Date: {employee.joining_date.isoformat() if employee.joining_date else 'Not set'}",
                f"Profile Completion: {profile_completion}%",
                f"Today's Attendance Status: {attendance_status}",
                f"Total Attendance Check-ins: {total_checkins}",
                f"Leave Balance (Annual): Allocation=15, Used={used['Annual']}, Remaining={remaining['Annual']}",
                f"Leave Balance (Sick): Allocation=12, Used={used['Sick']}, Remaining={remaining['Sick']}",
                f"Leave Balance (Casual): Allocation=7, Used={used['Casual']}, Remaining={remaining['Casual']}",
                f"Assigned Trainings: {', '.join(assigned_trainings) if assigned_trainings else 'None'}",
                f"Open Tickets: {', '.join(ticket_summaries) if ticket_summaries else 'None'}",
                f"All leave types available: Annual (15 days/year), Sick (12 days/year), Casual (7 days/year)."
            ]
            return "\n".join(lines)

    def _analysis_summary(self, analysis: ApplicationAIAnalysis | None) -> str:
        if not analysis:
            return "No completed resume analysis available."
        parts = [
            f"fit_score={analysis.fit_score}",
            f"recommendation={analysis.recommendation}",
            f"summary={analysis.summary or 'No summary'}",
            f"strengths={self._json_list(analysis.strengths)}",
            f"weaknesses={self._json_list(analysis.weaknesses)}",
            f"missing_skills={self._json_list(analysis.missing_skills)}",
        ]
        return "; ".join(parts)

    def _report_summary(self, report: InterviewIntelligenceReport | None) -> str:
        if not report:
            return "No completed interview intelligence report available."
        parts = [
            f"overall_score={report.overall_score}",
            f"technical_score={report.technical_score}",
            f"behavioral_score={report.behavioral_score}",
            f"recommendation={report.recommendation}",
            f"summary={report.executive_summary or 'No summary'}",
            f"strengths={self._json_list(report.strengths)}",
            f"weaknesses={self._json_list(report.weaknesses)}",
        ]
        return "; ".join(parts)

    def _session_summary(self, sessions: list[InterviewSession]) -> str:
        if not sessions:
            return "No interview session found."
        return ", ".join(
            f"session {session.id}: status={session.status}, avg_score={session.avg_score if session.avg_score is not None else 'n/a'}"
            for session in sorted(sessions, key=lambda item: item.updated_at, reverse=True)[:3]
        )

    def _ranking_score(
        self,
        analysis: ApplicationAIAnalysis | None,
        report: InterviewIntelligenceReport | None,
    ) -> float:
        scores = []
        if analysis:
            scores.append(float(analysis.fit_score))
        if report:
            scores.append(float(report.overall_score))
        return sum(scores) / len(scores) if scores else 0.0

    def _job_matches_terms(self, job: JobPosting, terms: set[str]) -> bool:
        haystack = " ".join([job.title, job.department, job.description, job.required_skills]).lower()
        return any(term in haystack for term in terms)

    def _query_terms(self, query: str) -> set[str]:
        ignored = {
            "which",
            "candidate",
            "candidates",
            "strongest",
            "compare",
            "best",
            "role",
            "round",
            "should",
            "move",
            "next",
            "hiring",
            "risks",
            "exist",
            "match",
            "this",
        }
        return {term for term in re.findall(r"[a-z0-9]+", query.lower()) if len(term) > 2 and term not in ignored}

    def _json_list(self, raw: str | None) -> str:
        if not raw:
            return "[]"
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        if isinstance(parsed, list):
            return ", ".join(str(item) for item in parsed) if parsed else "[]"
        return str(parsed)

    def _contains_any(self, query: str, keywords: set[str]) -> bool:
        return any(keyword in query for keyword in keywords)

    def _count_by(self, records: list[Any], attr: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in records:
            value = str(getattr(record, attr, "") or "Unspecified")
            counts[value] = counts.get(value, 0) + 1
        return counts

    def _format_counts(self, counts: dict[str, int]) -> str:
        if not counts:
            return "none"
        return ", ".join(f"{key}: {value}" for key, value in sorted(counts.items()))

    def _sources(self, source: str, detail: str) -> list[dict[str, Any]]:
        return [
            {
                "collection": "database",
                "source": source,
                "filename": None,
                "chunk_index": None,
                "entity_id": None,
                "entity_type": "live_hrms_data",
                "user_id": None,
                "source_collection": detail,
                "distance": None,
            }
        ]
