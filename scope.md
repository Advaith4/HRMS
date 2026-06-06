# TalentForge AI - Application Scope Documentation

This document outlines the detailed functional scope and comprehensive feature set of the TalentForge AI Human Resource Management System (HRMS). The application provides end-to-end recruitment screening, AI-powered interviewing, background verification, onboarding, training, core HR management, ticketing, and organizational structures.

---

## 1. Authentication and Authorization (RBAC)

TalentForge AI utilizes a strict Role-Based Access Control (RBAC) mechanism governed by JSON Web Tokens (JWT) to secure all backend endpoints and control frontend views.

### Workflows & Permissions
- **Public Access**:
  - Registration (`POST /api/auth/register`): Creates a new user. Public registrations default to the `candidate` role.
  - Login (`POST /api/auth/login`): Validates credentials, returns a JWT containing the user ID and role, and flags whether the user has uploaded a resume.
- **Hierarchical Roles**:
  - `candidate`: External applicants who manage profiles, upload resumes, apply to jobs, take mock interviews, and complete official interviews.
  - `employee`: Hired personnel who track attendance, submit leaves, complete onboarding checklists, undergo training, and open helpdesk tickets.
  - `manager`: Review team dashboards, approve/reject leaves, and review training progress.
  - `hr`: Manage job postings, templates, training programs, review candidates, verify documents, and hire applicants.
  - `admin`: Superuser that bypasses all role checks.

### Active Endpoints (`src/api/routes/auth.py`)
- `POST /api/auth/register` -> Register a user (`candidate` by default).
- `POST /api/auth/login` -> Authenticate credentials, return JWT access token, and user metadata.

---

## 2. Profile Management

Comprehensive management of personal details, achievements, and status tracking for candidates and employees.

### Workflows & Features
- **Candidate Profiles**:
  - Personal Details: Demographics, location, gender, contact number, education, institution, CGPA/percentage, graduation year.
  - Experience: Demographics, notice period, expected salary, current role, current company, years of experience, portfolio & LinkedIn URLs, certifications, technical & soft skills list.
  - Completion Metrics: Frontend calculates and tracks candidate profile completion percentage.
- **Employee Profiles**:
  - Demographics: Phone, address, emergency contact, blood group, marital status.
  - Development Details: Previous experience outline, skills, certifications, career interests, and career goals.
  - Pre-Populated Profiles: Automatically populated during hiring using candidate profile data.

### Active Endpoints (`src/api/routes/profile.py`)
- `GET /api/profile/me` -> Retrieve the current user's profile context.
- `PUT /api/profile/candidate` -> Update candidate profile fields (updates completion percentage).
- `PUT /api/profile/employee` -> Update employee profile completion detail.

---

## 3. Resume Management (Resume Lab)

An interactive, AI-driven suite that allows candidates to upload resumes, extract text, and modify content using AI suggestions.

### Workflows & Features
- **Resume Upload & Parsing**: Ingestion of PDF resume files up to 5MB. Spacing and spelling correction algorithms resolve formatting issues arising from PDF text extraction.
- **Interactive Resume Lab**:
  - AI Analysis: Evaluates the resume across four dimensions (Clarity, Structure, ATS compliance, Impact) and returns a score (0-100).
  - Issue Mapping: Sections are analyzed, highlighting bullet points with issues categorized by severity (high, medium, low) and type (replace, manual).
  - One-Click Repair: For auto-fixable issues (`action_type="replace"`), the platform replaces the original text with AI-suggested improvements.
  - Manual Checks (`action_type="manual"`): Guides users on how to update sections where verification or proof of metrics is needed (e.g., adding numbers or outcomes).

### Active Endpoints (`src/api/routes/resume.py`)
- `POST /api/resume/upload` -> Process and parse PDF resume files.
- `GET /api/resume/me` -> Fetch parsed resume sections and repair state.

---

## 4. Job Posting Management

Allows the internal HR/Admin team to create, publish, and structure internal job openings.

### Workflows & Features
- **Job Creation & Structure**: Define job titles, descriptions, required skills, department, salary range, and required years of experience.
- **Job Boards**: Candidates view jobs, track active vacancies, and submit applications.

### Active Endpoints (`src/api/routes/jobs.py`)
- `GET /api/jobs` -> List all active job postings.
- `GET /api/jobs/{job_id}` -> View details of a specific job posting.
- `POST /api/jobs` -> Create a new job posting (HR/Admin only).
- `PUT /api/jobs/{job_id}` -> Modify details of an active job (HR/Admin only).
- `DELETE /api/jobs/{job_id}` -> Remove a job opening from boards (HR/Admin only).

---

## 5. Application Tracking and AI Screening

Governs the screening of candidates and evaluates candidates using automated recruitment intelligence.

### Workflows & Features
- **Application Submission**: Candidates submit an application to a job posting by uploading a PDF resume.
- **Background AI Analysis**:
  - An asynchronous background worker triggers a CrewAI pipeline (or fallback scorer) immediately upon application.
  - Evaluates resume text against the job description to calculate a Fit Score (0-100) and recommendation (Consider, Reject).
  - Highlights Strengths, Weaknesses, Missing Skills, and General Observations.
  - Automatically drafts a list of custom Technical, Behavioral, and Probing Questions for subsequent interview rounds.
- **Resume Tailoring**: AI generates custom bullet points that candidates can use to tailor their resumes for specific job descriptions.
- **Leaderboards & Rankings**: HR and managers can view job postings and retrieve candidates ranked by AI fit scores.

### Active Endpoints (`src/api/routes/applications.py`)
- `POST /api/applications/apply` -> Candidate submits application + PDF resume (triggers background AI).
- `GET /api/applications/me` -> Candidate fetches their submitted applications and status history.
- `GET /api/applications` -> HR/Manager fetches a list of all candidates' applications.
- `POST /api/applications/{application_id}/analyze` -> Force a re-analysis of a candidate application.
- `GET /api/applications/rankings/{job_id}` -> Retrieve candidate lists sorted by AI fit scores.
- `GET /api/applications/{application_id}/credibility` -> Retrieve candidate credibility report comparing resume claims vs interview answers.

---

## 6. AI Interview and Assessment Engine

A comprehensive mock and formal interview environment using LLMs to host interactive chats, score candidate performance, and generate intelligence reports.

### Workflows & Features
- **Proctored Assessments**:
  - Live socket-like API endpoint for chat message submission.
  - Tab Switch Detection: Captures and logs proctoring violations during official candidate interviews.
- **Interview Mock Setup**: Candidates can configure:
  - Selectable personas (e.g., balanced, technical, behavioral, system design).
  - Selected training modes (e.g., adaptive, baseline, custom).
  - Target role description and difficulty settings (1 to 10).
- **Hiring Intelligence Reporting**:
  - Competency Scores & Job Fit Reports.
  - Communication Metrics & Behavioral Reports.
  - Candidate Credibility Report: Compares claim data in candidate resumes with evidence provided in chat answers, highlighting discrepancies or unverified details.
  - Ranked Leaderboard: Compiles resume, interview, and credibility scores to create an overall hiring leaderboard.
  - Comparative Analysis: Side-by-side assessment of multiple candidates.
  - Follow-up Engine: Auto-generates follow-up interview questions from credibility reports.
- **Career Coach Memory**: Synthesizes score trends and recurring weak areas across mock interviews to auto-generate daily training plans.

### Active Endpoints (`src/api/routes/interview.py` & `src/api/routes/mock_interview.py`)
- `POST /api/interview/start` -> Start a new application interview.
- `POST /api/interview/start-for-application` -> Start an interview from a job application.
- `POST /api/interview/start-from-resume` -> Start a personalized interview from a candidate's resume.
- `POST /api/interview/{session_id}/violation` -> Record screen navigation/tab-switch violations.
- `POST /api/interview/answer` -> Submit an answer to the interviewer and receive the next question + real-time scoring feedback.
- `POST /api/interview/{session_id}/complete` -> Formally complete an interview, calculating overall scores and reports.
- `POST /api/interview/{session_id}/abandon` -> Cancel and flag a session as abandoned.
- `GET /api/interview/sessions` -> List past interview sessions.
- `GET /api/interview/sessions/{session_id}` -> Fetch message history and scores for a specific interview.
- `DELETE /api/interview/sessions/{session_id}` -> Remove interview session records.
- `GET /api/interview/coach-memory` -> Fetch candidate career coach summary dashboard.
- `GET /api/interview/daily-plan` -> Retrieve personalized career plans and tasks.
- `GET /api/interview/intelligence/leaderboard` -> Compilation of all candidate assessments sorted by performance.
- `GET /api/interview/intelligence/report/{candidate_id}` -> Compile full competency profile.
- `POST /api/interview/intelligence/compare` -> Side-by-side comparison matrix of candidates.
- `POST /api/interview/intelligence/{session_id}/advance` -> Mark candidate advanced to the next level.
- `POST /api/interview/intelligence/{session_id}/reject` -> Mark candidate rejected.
- `GET /api/interview/intelligence/followup-questions/{session_id}` -> Generate follow-up questions from credibility reports.

---

## 7. Employee Hiring and Onboarding Transition

The workflow that converts a candidate into an employee, migrates documents, and initiates onboarding programs.

### Workflows & Features
- **The Hiring Action (`POST /api/applications/{application_id}/hire`)**:
  - Updates the candidate's account role to `employee` and sets their target role designation.
  - Creates the new core `Employee` profile.
  - Pre-populates the employee profile fields (full name, phone, address, DOB, experience, skills, certifications) from the candidate's profile context.
  - Records a "Joined" event in the Employee Lifecycle log.
  - Migrates all verified Candidate Documents to Employee Documents without file duplication.
  - **Smart Onboarding Assignment**: Automatically matches the employee's new department to onboarding template names and builds a custom onboarding plan with checklist items.
  - Notifies the employee and logs the "Onboarding Started" event.

---

## 8. Onboarding Management System

Allows HR to construct structured checklists and verify mandatory documentation during employee check-ins.

### Workflows & Features
- **Onboarding Templates**: Reusable templates created by HR/Admin outlining tasks, descriptions, and order index values.
- **Required Documents Checklist**: Add verification requirements (e.g., Passport, PAN, Degree Certificate, Experience Letter) to onboarding template lists.
- **Plan Assignment & Checklist Tracking**:
  - Employees view their personalized onboarding task list.
  - Update task progress statuses (Pending, In Progress, Completed) and add comments.
  - HR reviews onboarding metrics and overdue summary trackers.

### Active Endpoints (`src/api/routes/onboarding.py`)
- `GET /api/onboarding/templates` -> List reusable templates.
- `POST /api/onboarding/templates` -> Create onboarding templates.
- `PUT /api/onboarding/templates/{template_id}` -> Modify onboarding template metadata.
- `DELETE /api/onboarding/templates/{template_id}` -> Archive template.
- `POST /api/onboarding/templates/{template_id}/tasks` -> Add tasks to template checklists.
- `PUT /api/onboarding/tasks/{task_id}` -> Update template checklist items.
- `DELETE /api/onboarding/tasks/{task_id}` -> Remove template tasks.
- `POST /api/onboarding/assign` -> Manually allocate an onboarding template to an employee.
- `GET /api/onboarding/employee/{employee_id}` -> Check employee onboarding checklist progress.
- `GET /api/onboarding/my` -> Fetch the onboarding checklist for the logged-in employee.
- `PUT /api/onboarding/plan/{plan_id}/task/{task_id}` -> Update onboarding plan checklist item progress.
- `GET /api/onboarding/summary` -> High-level onboarding progress statistics.
- `POST /api/onboarding/templates/{template_id}/required-documents` -> Add mandatory documents to template lists.
- `DELETE /api/onboarding/templates/{template_id}/required-documents/{document_type}` -> Remove document requirements.

---

## 9. Learning and Development (Training)

Enables employee upskilling through training programs and progress tracking.

### Workflows & Features
- **Training Programs**: HR defines course structures covering target skills, category, difficulty levels, and durations.
- **Assignments**: Assign courses to employee logs.
- **Progress Tracking**: Employees update progress percentage (0-100%) and complete courses.
- **L&D Analytics**: Visual summaries of course completion rates, active enrollments, and category distributions.

### Active Endpoints (`src/api/routes/training.py`)
- `GET /api/training/programs` -> View active training programs.
- `POST /api/training/programs` -> Create new programs.
- `PUT /api/training/programs/{program_id}` -> Edit program details.
- `DELETE /api/training/programs/{program_id}` -> Archive training programs.
- `POST /api/training/assign` -> Enroll employees in training programs.
- `GET /api/training/assignments/my` -> Employee fetches their course assignments.
- `GET /api/training/assignments` -> HR retrieves all enrollments.
- `PUT /api/training/assignments/{assignment_id}/progress` -> Update course completion status and progress percent.
- `GET /api/training/summary` -> Fetch L&D training enrollment analytics.

---

## 10. Document Vault and Verification

Secure file management portal for employee credentials and identification documents.

### Workflows & Features
- **Upload & Storage**: Secure file upload mechanisms that support PDF and image documentation.
- **Status Workflows**: Files are set to "Pending Review" upon upload. HR reviews uploads to mark them as "Approved" or "Rejected" (requiring verification notes and comments).
- **Document Categorization**: Identifies files based on types (e.g., ID Proof, Degree, Salary Slip, Relieving Letter).

### Active Endpoints (`src/api/routes/profile.py`)
- `POST /api/profile/documents` -> Upload files to storage (Candidate or Employee context).
- `GET /api/profile/documents` -> Retrieve personal uploaded document registries.
- `GET /api/profile/documents/{kind}/{document_id}/download` -> Download documents (Candidate/Employee paths).
- `GET /api/profile/documents/review` -> HR retrieves pending document review lists.
- `PUT /api/profile/documents/{kind}/{document_id}/decision` -> HR approves/rejects documents.

---

## 11. Core Employee Management & HR Operations

Governs day-to-day HR workflows, employee registries, directory searches, attendance check-ins, and leave management.

### Workflows & Features
- **Employee Registry**: Searchable database of all hires, allowing filtering by department, status, and designation.
- **Attendance Registry**: Daily Check-In and Check-Out timestamps. Tracks active shifts and calculates duration metrics.
- **Leave Operations**:
  - Employee Leave Requests: Submit leaves specifying dates, leave type, and justification notes.
  - Approval Workflow: Managers/HR review requests and mark status changes (Pending, Approved, Rejected) with feedback.
- **AI Skill Gap Analysis**:
  - Employees trigger AI analyses to evaluate current skills against role expectations.
  - Generates summaries, identifies growth areas, and suggests personalized learning modules.
- **AI HR Policy Assistant**: Policy-aware chat helper that resolves employee HR queries.

### Active Endpoints (`src/api/routes/employees.py`)
- `GET /api/employees` -> View employee directory.
- `GET /api/employees/me` -> Employee fetches their core profile.
- `GET /api/employees/dashboard` -> Employee dashboard context (announcements, metrics, summary stats).
- `POST /api/employees/attendance/check-in` -> Create Check-In attendance record.
- `POST /api/employees/attendance/check-out` -> Create Check-Out attendance record.
- `GET /api/employees/attendance` -> Retrieve employee attendance logs.
- `POST /api/employees/leave` -> Submit a leave request.
- `GET /api/employees/leave/me` -> Employee views their personal leave history.
- `GET /api/employees/leave` -> HR/Managers fetch pending employee leave requests.
- `POST /api/employees/leave/{leave_id}/decision` -> Approve or reject leave requests.
- `GET /api/employees/skill-gap/me` -> Retrieve current skill gap report.
- `POST /api/employees/skill-gap/me/analyze` -> Run AI analysis on employee skill gaps.
- `POST /api/employees/assistant` -> Chat with the AI HR assistant.
- `GET /api/employees/directory` -> Filtered registry lookup for staff directory.
- `GET /api/employees/{employee_id}` -> View details of an employee.
- `GET /api/employees/{employee_id}/profile` -> Fetch detailed employee profile.
- `PUT /api/employees/{employee_id}/profile` -> Edit employee profile details.

---

## 12. Organizational Structure

Maintains organizational hierarchies and department alignments.

### Workflows & Features
- **Departments**: Management of business divisions (e.g., Engineering, Marketing), assignment of department heads, and status updates (Active, Inactive).
- **Designations**: Job title hierarchies and designation levels within departments.

### Active Endpoints (`src/api/routes/departments.py` & `src/api/routes/designations.py`)
- `GET /api/departments` -> List business units.
- `POST /api/departments` -> Create departments.
- `PUT /api/departments/{dept_id}` -> Edit department details.
- `DELETE /api/departments/{dept_id}` -> Deactivate business units.
- `GET /api/designations` -> List job roles.
- `POST /api/designations` -> Create job roles.
- `PUT /api/designations/{desig_id}` -> Edit job roles.
- `DELETE /api/designations/{desig_id}` -> Archive designations.

---

## 13. Employee Compensation and Lifecycle tracking

Tracks designation changes and financial revisions.

### Workflows & Features
- **Compensation Revisions**: Record salary increment histories, percentage increases, and approval audit logs.
- **Promotion Tracks**: Tracks designatorial changes, upgrades, promotion dates, and rationale.
- **Employee Lifecycle Log**: Audited records of events during tenure (Joined, Onboarding Started, Promotion, Salary Revision).

### Active Endpoints (`src/api/routes/salary.py`, `src/api/routes/promotions.py`, & `src/api/routes/lifecycle.py`)
- `GET /api/salary/employee/{employee_id}` -> Fetch employee compensation histories.
- `POST /api/salary/employee/{employee_id}` -> Log a salary adjustment (HR/Admin only).
- `GET /api/promotions/recent` -> View recent promotion logs.
- `GET /api/promotions/employee/{employee_id}` -> View detailed promotion history of an employee.
- `POST /api/promotions/employee/{employee_id}` -> Log promotion updates.
- `GET /api/lifecycle/employee/{employee_id}` -> Retrieve lifecycle logs.
- `POST /api/lifecycle/employee/{employee_id}` -> Append events to employee lifecycle logs.

---

## 14. Helpdesk Support and Ticketing

Provides a workflow for staff members to submit grievances, requests, or IT support tickets.

### Workflows & Features
- **Ticket Submission**: Employees submit tickets categorizing requests (IT, HR, Payroll, Admin) and set priority levels (High, Medium, Low).
- **Ticket Resolution Workflows**: Managers and HR assign support tickets, track resolutions, and append troubleshooting notes.

### Active Endpoints (`src/api/routes/tickets.py`)
- `POST /api/tickets` -> Submit support tickets.
- `GET /api/tickets` -> View list of tickets.
- `GET /api/tickets/{ticket_id}` -> View support ticket details.
- `PUT /api/tickets/{ticket_id}/assign` -> Allocate tickets to support personnel.
- `PUT /api/tickets/{ticket_id}/status` -> Update status (Open, Pending, Resolved) and save resolution notes.

---

## 15. Dashboards, Metrics, and Notifications

Visual hubs and alert logs that synchronize operational flows across the application.

### Workflows & Features
- **In-App Notifications**: Real-time context alerts (Onboarding assigned, Leaves approved, Tickets assigned, Document decisions).
- **Executive Summaries**:
  - HR Dashboard: Unified overview displaying recruitment pipelines, vacancy rates, active candidate lists, pending approvals, and document audits.
  - Candidate Dashboard: Application pipelines, resume status reports, and active interview cards.

### Active Endpoints (`src/api/routes/dashboard.py` & `src/api/routes/notifications.py`)
- `GET /api/dashboard/hr` -> Multi-entity dashboard payload for HR operators.
- `GET /api/dashboard/candidate` -> Core details dashboard context for candidate logins.
- `GET /api/dashboard/hr/reviews` -> Action items widget queue for HR reviews.
- `GET /api/notifications` -> View notification alerts log.
- `PUT /api/notifications/read-all` -> Mark all notifications as read.
- `PUT /api/notifications/{notification_id}/read` -> Mark target notification as read.
