"""
scripts/seed_star_candidate.py

Inserts one "star" candidate with realistic high scores into every table
that the Interview Intelligence leaderboard & report reads from:
  - users
  - resumes
  - job_postings  (reuses existing OPEN job or creates one)
  - candidate_applications
  - application_ai_analyses
  - interview_sessions       (status=analyzed, avg_score=9.1)
  - candidate_credibility_reports
  - interview_intelligence_reports

Run from the project root:
    python -m scripts.seed_star_candidate
"""

import json
import os
import sys
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select

from src.database.connection import engine
from src.core.security import hash_password
from src.models import (
    User,
    Resume,
    JobPosting,
    CandidateApplication,
    ApplicationAIAnalysis,
    InterviewSession,
    CandidateCredibilityReport,
    InterviewIntelligenceReport,
)

# ── Candidate data ────────────────────────────────────────────────────────────

CANDIDATE_USERNAME = "arjun_sharma_star"
CANDIDATE_PASSWORD = "TalentForge@2025"

RESUME_TEXT = """
Arjun Sharma — Senior Full-Stack Engineer
Contact: arjun.sharma@email.com | LinkedIn: linkedin.com/in/arjunsharma | GitHub: github.com/arjunsharma

SUMMARY
Results-driven Senior Full-Stack Engineer with 6+ years building scalable SaaS products.
Deep expertise in Python, FastAPI, React, PostgreSQL, and AWS. Led teams of 5–8 engineers
and shipped products serving 500k+ users. Passionate about system design, clean code, and
mentoring junior developers.

SKILLS
Languages: Python, TypeScript, JavaScript, Go, SQL
Frontend: React, Next.js, Redux, TailwindCSS, WebSocket
Backend: FastAPI, Django, Node.js, Express, gRPC, REST
Databases: PostgreSQL, MongoDB, Redis, Elasticsearch, DynamoDB
DevOps: AWS, Docker, Kubernetes, Terraform, GitHub Actions, CI/CD
Other: Microservices, Agile, Scrum, TDD, System Design, OpenAI, LangChain

EXPERIENCE
Senior Software Engineer — TechNova Pvt. Ltd. (2021–Present)
- Designed and shipped a real-time analytics platform handling 10M+ events/day using Kafka, Redis, and FastAPI
- Led migration of monolith to Kubernetes-based microservices, reducing deployment time by 70%
- Mentored 4 junior engineers and conducted weekly code reviews
- Built multi-tenant SaaS auth system with JWT, OAuth2 and role-based access control

Software Engineer — CloudBase Systems (2019–2021)
- Developed React dashboards with real-time WebSocket updates for IoT monitoring
- Implemented PostgreSQL query optimisation reducing average API response from 800ms to 120ms
- Contributed to open-source FastAPI plugins (500+ GitHub stars)

EDUCATION
B.Tech Computer Science — IIT Bombay (2015–2019) | CGPA: 9.2/10

CERTIFICATIONS
AWS Certified Solutions Architect — Associate
Google Cloud Professional Data Engineer
"""

MESSAGES = [
    # === Resume Validation Phase ===
    {"role": "ai", "content": "Tell me about a recent project where you demonstrated ownership from design to deployment.", "difficulty": 7, "phase": "Resume Validation", "timestamp": "2025-01-15T09:00:00"},
    {"role": "user", "content": "At TechNova I single-handedly designed and shipped a real-time analytics platform. I chose Kafka for event streaming, Redis for caching hot aggregations, and FastAPI for the REST layer. I wrote the system design doc, ran architecture reviews, handled DB migrations, and personally deployed it on Kubernetes. It now processes over 10 million events per day with sub-50ms P99 latency.", "timestamp": "2025-01-15T09:01:30"},
    {"role": "feedback", "content": "Excellent response! Clear ownership, specific metrics, and end-to-end accountability.", "score": 9, "focus_area": "ownership", "timestamp": "2025-01-15T09:01:31"},
    {"role": "ai", "content": "How did you handle the monolith-to-microservices migration? Walk me through your decision-making.", "difficulty": 8, "phase": "Resume Validation", "timestamp": "2025-01-15T09:03:00"},
    {"role": "user", "content": "We started with a strangler-fig pattern. First I identified bounded contexts using domain analysis — auth, billing, analytics, and notifications were clear seams. I containerised each service with Docker, wrote Helm charts for Kubernetes deployment, and set up GitHub Actions CI/CD pipelines. We used feature flags to roll out gradually — zero downtime migrations. Deployment cycle dropped from 45 minutes to under 8 minutes.", "timestamp": "2025-01-15T09:04:30"},
    {"role": "feedback", "content": "Strong technical depth! Strangler-fig pattern, Helm charts, feature flags — all correct and well-explained.", "score": 9, "focus_area": "system design", "timestamp": "2025-01-15T09:04:31"},
    {"role": "ai", "content": "Explain a performance bottleneck you identified and resolved in a PostgreSQL-heavy system.", "difficulty": 8, "phase": "Resume Validation", "timestamp": "2025-01-15T09:06:00"},
    {"role": "user", "content": "We had a dashboard query that JOINed five tables and ran EXPLAIN ANALYZE — it showed a Seq Scan on the events table with 2M rows. I added a composite index on (user_id, created_at), rewrote the query to avoid a correlated subquery, and used a materialised view for the aggregation. Response time went from 800ms to under 120ms. I also introduced pg_stat_statements monitoring to catch future regressions.", "timestamp": "2025-01-15T09:07:30"},
    {"role": "feedback", "content": "Perfect answer — EXPLAIN ANALYZE, composite index, materialised view, and monitoring. That's senior-level database thinking.", "score": 10, "focus_area": "databases", "timestamp": "2025-01-15T09:07:31"},
    # === Technical Assessment Phase ===
    {"role": "ai", "content": "Design a rate-limiting system for a public API serving 50,000 RPS.", "difficulty": 9, "phase": "Technical Assessment", "timestamp": "2025-01-15T09:10:00"},
    {"role": "user", "content": "I'd use a token-bucket algorithm implemented in Redis with Lua scripts for atomic operations. Each API key gets a Redis key with a sliding window counter. For 50k RPS across multiple nodes, I'd use Redis Cluster with consistent hashing. I'd expose rate-limit headers (X-RateLimit-Remaining, X-RateLimit-Reset) and return 429 with Retry-After. For burst tolerance, the token bucket refills at a fixed rate but allows short bursts up to 2x the limit.", "timestamp": "2025-01-15T09:11:30"},
    {"role": "feedback", "content": "Excellent. Token bucket, Redis Cluster, Lua atomicity, proper headers — comprehensive and production-ready design.", "score": 9, "focus_area": "system design", "timestamp": "2025-01-15T09:11:31"},
    {"role": "ai", "content": "How would you implement real-time notifications for 1M concurrent users?", "difficulty": 9, "phase": "Technical Assessment", "timestamp": "2025-01-15T09:13:00"},
    {"role": "user", "content": "I'd use WebSockets with a pub/sub backbone. Each app server maintains WebSocket connections; events are published to Kafka topics partitioned by user_id. A notification consumer group reads from Kafka and fans out to the appropriate WebSocket server via Redis pub/sub. For mobile, I'd add APNs/FCM as a fallback. Connection state is stored in Redis with TTL. For 1M concurrent, horizontal scaling of WebSocket servers behind a load balancer with sticky sessions or a connection registry.", "timestamp": "2025-01-15T09:14:30"},
    {"role": "feedback", "content": "Solid architecture — Kafka partitioning, Redis pub/sub bridge, push notification fallback, horizontal scaling. Well-rounded answer.", "score": 9, "focus_area": "distributed systems", "timestamp": "2025-01-15T09:14:31"},
    {"role": "ai", "content": "Explain how you'd secure a multi-tenant SaaS application at the API and database level.", "difficulty": 8, "phase": "Technical Assessment", "timestamp": "2025-01-15T09:16:00"},
    {"role": "user", "content": "At the API level: JWT with tenant_id claim, validated on every request through a middleware that injects tenant context. Role-based access control with per-tenant role definitions. At the database level: Row-Level Security in PostgreSQL — each query automatically filtered by tenant_id via SET app.current_tenant. I also use separate DB schemas per high-value tenant for isolation. Secrets stored in AWS Secrets Manager, rotated quarterly. All data encrypted at rest (AES-256) and in transit (TLS 1.3).", "timestamp": "2025-01-15T09:17:30"},
    {"role": "feedback", "content": "Excellent multi-layered security thinking. RLS, JWT claims, schema isolation, secrets rotation — this is production-grade.", "score": 10, "focus_area": "security", "timestamp": "2025-01-15T09:17:31"},
    {"role": "ai", "content": "What's your approach to writing maintainable, testable code in a large Python codebase?", "difficulty": 7, "phase": "Technical Assessment", "timestamp": "2025-01-15T09:19:00"},
    {"role": "user", "content": "I follow Clean Architecture principles — separate domain logic from infrastructure. Use dependency injection for testability. Write unit tests with pytest and mock external dependencies. Integration tests use TestContainers for real DB interactions. I enforce type hints with mypy, linting with ruff, and pre-commit hooks. For large codebases, I organise by feature, not by layer — keeps related code co-located. Code review is non-negotiable — minimum 2 approvals for anything touching core business logic.", "timestamp": "2025-01-15T09:20:30"},
    {"role": "feedback", "content": "Great engineering culture mindset. Clean Architecture, dependency injection, TestContainers, feature-based organisation — all best practices.", "score": 9, "focus_area": "software engineering", "timestamp": "2025-01-15T09:20:31"},
    {"role": "ai", "content": "Walk me through implementing a distributed transaction across two microservices.", "difficulty": 9, "phase": "Technical Assessment", "timestamp": "2025-01-15T09:22:00"},
    {"role": "user", "content": "I'd use the Saga pattern — either choreography or orchestration. For complex flows, orchestration with a saga orchestrator is cleaner. Each service exposes compensating transactions. For example, an order service publishes an 'OrderCreated' event; the payment service consumes it and either publishes 'PaymentSucceeded' or 'PaymentFailed'. On failure, the orchestrator triggers compensating actions. I use an outbox pattern — write the event to a local DB table in the same transaction as the business operation, then a background publisher reads and publishes to Kafka. This ensures exactly-once semantics.", "timestamp": "2025-01-15T09:23:30"},
    {"role": "feedback", "content": "Advanced answer — Saga pattern, outbox pattern, compensating transactions, exactly-once semantics. This is expert-level distributed systems knowledge.", "score": 10, "focus_area": "distributed systems", "timestamp": "2025-01-15T09:23:31"},
    # === Behavioral Assessment Phase ===
    {"role": "ai", "content": "Tell me about a time you had a major technical disagreement with a teammate. How did you resolve it?", "difficulty": 7, "phase": "Behavioral Assessment", "timestamp": "2025-01-15T09:26:00"},
    {"role": "user", "content": "We disagreed on whether to use GraphQL or REST for our new API. I preferred REST for simplicity; my colleague wanted GraphQL for flexibility. Instead of debating endlessly, I proposed we run a spike — two days each building a proof of concept. We defined evaluation criteria: DX, performance, caching complexity, and client flexibility. After presenting both, the team chose GraphQL for the client-facing API and REST for internal services. It was a win because the decision was data-driven, not ego-driven.", "timestamp": "2025-01-15T09:27:30"},
    {"role": "feedback", "content": "Mature conflict resolution. Data-driven decision making, structured evaluation — excellent soft skills.", "score": 9, "focus_area": "collaboration", "timestamp": "2025-01-15T09:27:31"},
    {"role": "ai", "content": "Describe a situation where you had to deliver under extreme time pressure. What was your approach?", "difficulty": 7, "phase": "Behavioral Assessment", "timestamp": "2025-01-15T09:29:00"},
    {"role": "user", "content": "Our largest enterprise client had a go-live deadline in 3 days and a critical integration was broken. I immediately set up a war room, triaged the issue to a race condition in our async job processor, and assigned owners for each sub-problem. I communicated hourly status to the CTO and the client. We worked in shifts, tested on staging continuously, and shipped a hotfix 6 hours before go-live. Post-mortem revealed we needed better integration test coverage — I led the initiative to add it.", "timestamp": "2025-01-15T09:30:30"},
    {"role": "feedback", "content": "Strong STAR answer — clear situation, structured response, ownership, and learning. Shows leadership under pressure.", "score": 9, "focus_area": "leadership", "timestamp": "2025-01-15T09:30:31"},
    {"role": "ai", "content": "How do you approach mentoring junior developers?", "difficulty": 6, "phase": "Behavioral Assessment", "timestamp": "2025-01-15T09:32:00"},
    {"role": "user", "content": "I pair mentoring with structured feedback. I start by understanding their goals and current gaps. Then I assign them progressively harder tasks with clear success criteria. I do weekly 1:1s focused on unblocking and growth, not status updates. During code reviews I explain the 'why' behind feedback rather than just correcting. I also encourage juniors to present their solutions in team meetings — builds confidence and communication skills. Three of my mentees were promoted to mid-level within 18 months.", "timestamp": "2025-01-15T09:33:30"},
    {"role": "feedback", "content": "Excellent mentoring philosophy. Structured, empathetic, outcome-focused. The promotion metric shows real impact.", "score": 9, "focus_area": "leadership", "timestamp": "2025-01-15T09:33:31"},
    # === Final Evaluation ===
    {"role": "ai", "content": "Why do you want to join our company, and where do you see yourself in 3 years?", "difficulty": 6, "phase": "Final Evaluation", "timestamp": "2025-01-15T09:36:00"},
    {"role": "user", "content": "I've followed your company's engineering blog and the work on distributed systems is genuinely impressive — the post on your event-sourcing migration was insightful. In 3 years I see myself leading a platform engineering team, owning the developer experience and infrastructure reliability. I want to build systems that are boring in the best way — so reliable that developers don't have to think about them. I believe the scale of challenges here is exactly where I can make the most impact.", "timestamp": "2025-01-15T09:37:30"},
    {"role": "feedback", "content": "Thoughtful and specific. Genuine research into the company, clear 3-year vision, humble confidence.", "score": 9, "focus_area": "motivation", "timestamp": "2025-01-15T09:37:31"},
]

SUPPORTED_CLAIMS = [
    {"claim": "Python", "evidence": "strong", "explanation": "Demonstrated Python in system design answers with specific examples (FastAPI, async workers, microservices)."},
    {"claim": "FastAPI", "evidence": "strong", "explanation": "Mentioned FastAPI multiple times with concrete use cases — REST layer for 10M events/day platform."},
    {"claim": "PostgreSQL", "evidence": "strong", "explanation": "Scored 10/10 on DB question — explained EXPLAIN ANALYZE, composite indexes, materialised views."},
    {"claim": "React", "evidence": "strong", "explanation": "Referenced React dashboards with WebSocket real-time updates in experience walkthrough."},
    {"claim": "Kubernetes", "evidence": "strong", "explanation": "Described full Kubernetes migration with Helm charts and zero-downtime deployment."},
    {"claim": "Redis", "evidence": "strong", "explanation": "Used Redis in rate-limiting design (token bucket) and notification architecture (pub/sub)."},
    {"claim": "Kafka", "evidence": "strong", "explanation": "Described Kafka partitioning by user_id for notification fan-out and outbox pattern for distributed transactions."},
    {"claim": "AWS", "evidence": "strong", "explanation": "Mentioned AWS Secrets Manager, RDS-level encryption, and AWS as production deployment target."},
]

WEAK_CLAIMS = [
    {"claim": "TensorFlow", "evidence": "weak", "explanation": "Listed on resume but no interview evidence provided for ML framework usage."},
]

MISSING_EVIDENCE = [
    {"claim": "Go", "evidence": "none", "explanation": "Go listed on resume but never referenced during interview answers."},
]

FOLLOWUP_TOPICS = ["Go language experience", "ML/AI project work", "TensorFlow in production"]


def _avg(scores):
    return round(sum(scores) / len(scores), 2) if scores else 0.0


def seed():
    scores = [msg["score"] for msg in MESSAGES if msg.get("role") == "feedback" and "score" in msg]
    avg_score = _avg(scores)
    print(f"Computed avg_score from {len(scores)} Q&A rounds: {avg_score}/10")

    with Session(engine) as db:
        # ── 1. User ──────────────────────────────────────────────────────────
        existing_user = db.exec(select(User).where(User.username == CANDIDATE_USERNAME)).first()
        if existing_user:
            print(f"User '{CANDIDATE_USERNAME}' already exists (id={existing_user.id}). Skipping creation.")
            user = existing_user
        else:
            user = User(
                username=CANDIDATE_USERNAME,
                hashed_password=hash_password(CANDIDATE_PASSWORD),
                role="candidate",
                target_role="Senior Full-Stack Engineer",
                location="Bengaluru, India",
                experience="Senior (6+ years)",
                is_active=True,
            )
            db.add(user)
            db.flush()
            print(f"Created user id={user.id}")

        # ── 2. Resume ────────────────────────────────────────────────────────
        existing_resume = db.exec(select(Resume).where(Resume.user_id == user.id)).first()
        if not existing_resume:
            resume = Resume(
                user_id=user.id,
                raw_text=RESUME_TEXT.strip(),
                original_text=RESUME_TEXT.strip(),
                current_text=RESUME_TEXT.strip(),
            )
            db.add(resume)
            db.flush()
            print(f"Created resume id={resume.id}")
        else:
            print(f"Resume already exists (id={existing_resume.id})")

        # ── 3. Job Posting ───────────────────────────────────────────────────
        job = db.exec(select(JobPosting).where(JobPosting.status == "OPEN")).first()
        if not job:
            # Need an HR/admin user to set as created_by
            admin = db.exec(select(User).where(User.role == "admin")).first()
            hr = db.exec(select(User).where(User.role == "hr")).first()
            creator = admin or hr or user  # fallback to self
            job = JobPosting(
                title="Senior Full-Stack Engineer",
                description="We are looking for an exceptional senior engineer to join our platform team. You will design and build scalable, reliable distributed systems that power our core product.",
                required_skills="Python, FastAPI, React, PostgreSQL, Kubernetes, Docker, AWS, Redis, Kafka, Microservices, CI/CD",
                department="Engineering",
                salary_range="₹30–50 LPA",
                experience_required="5–8 years",
                status="OPEN",
                created_by=creator.id,
            )
            db.add(job)
            db.flush()
            print(f"Created job posting id={job.id}")
        else:
            print(f"Reusing existing job posting id={job.id} ('{job.title}')")

        # ── 4. CandidateApplication ──────────────────────────────────────────
        existing_app = db.exec(
            select(CandidateApplication)
            .where(CandidateApplication.candidate_user_id == user.id)
            .where(CandidateApplication.job_id == job.id)
        ).first()
        if existing_app:
            print(f"Application already exists (id={existing_app.id})")
            application = existing_app
        else:
            application = CandidateApplication(
                candidate_user_id=user.id,
                job_id=job.id,
                resume_text=RESUME_TEXT.strip(),
                status="Shortlisted",
            )
            db.add(application)
            db.flush()
            print(f"Created application id={application.id}")

        # ── 5. ApplicationAIAnalysis ─────────────────────────────────────────
        existing_analysis = db.exec(
            select(ApplicationAIAnalysis).where(ApplicationAIAnalysis.application_id == application.id)
        ).first()
        if not existing_analysis:
            analysis = ApplicationAIAnalysis(
                application_id=application.id,
                fit_score=93,
                recommendation="Strongly Recommended",
                summary=(
                    "Arjun Sharma is an exceptional senior engineer with deep expertise spanning "
                    "the full stack. His 6 years of experience includes leading complex migrations, "
                    "building high-throughput distributed systems, and mentoring junior engineers. "
                    "His resume claims are comprehensive and well-supported by quantifiable outcomes. "
                    "Strongly recommend for the Senior Full-Stack Engineer role."
                ),
                strengths=json.dumps([
                    "Expert-level Python, FastAPI, and PostgreSQL",
                    "Proven distributed systems design (Kafka, Redis, Kubernetes)",
                    "Strong leadership — led team of 8 engineers",
                    "Quantifiable impact (10M events/day, 70% deployment speedup)",
                    "Excellent mentoring track record (3 promotions in 18 months)",
                ]),
                weaknesses=json.dumps([
                    "Limited public ML/AI project visibility",
                    "Go experience not demonstrated in depth",
                ]),
                missing_skills=json.dumps([]),
                observations=json.dumps([
                    "IIT Bombay graduate with 9.2 CGPA — strong academic foundation",
                    "Open-source contributor (500+ GitHub stars on FastAPI plugin)",
                    "AWS and GCP certified — multi-cloud exposure",
                    "Monolith-to-microservices migration experience is highly relevant",
                ]),
                technical_questions=json.dumps([
                    "Design a globally distributed rate-limiter at 100k RPS.",
                    "How would you debug a memory leak in a Python FastAPI service?",
                    "Explain your approach to blue-green deployments on Kubernetes.",
                ]),
                behavioral_questions=json.dumps([
                    "Describe a time you influenced engineering culture positively.",
                    "Tell me about a product decision you pushed back on and why.",
                ]),
                probing_areas=json.dumps(["Go proficiency", "ML/AI project depth", "Cost optimisation at scale"]),
                status="completed",
                source="seed_script",
            )
            db.add(analysis)
            db.flush()
            print(f"Created AI analysis id={analysis.id}")
        else:
            print(f"AI analysis already exists (id={existing_analysis.id})")

        # ── 6. InterviewSession ──────────────────────────────────────────────
        existing_session = db.exec(
            select(InterviewSession).where(InterviewSession.user_id == user.id)
        ).first()
        if existing_session:
            print(f"Interview session already exists (id={existing_session.id})")
            session_rec = existing_session
        else:
            session_rec = InterviewSession(
                user_id=user.id,
                session_token=uuid.uuid4().hex,
                role="Senior Full-Stack Engineer",
                difficulty=9,
                training_mode="adaptive",
                interviewer_persona="technical",
                messages=json.dumps(MESSAGES),
                personalization_context=json.dumps({
                    "source": "resume_lab",
                    "weak_areas": [],
                    "focus_counts": {"weak_area": 0, "general": 3, "domain": 7, "behavioral": 3},
                    "current_focus_area": "system design",
                    "current_phase": "Final Evaluation",
                    "phase_history": ["Resume Validation", "Technical Assessment", "Behavioral Assessment", "Final Evaluation"],
                    "training_mode": "adaptive",
                    "interviewer_persona": "technical",
                    "difficulty": 9,
                }),
                avg_score=avg_score,
                application_id=application.id,
                violations_count=0,
                violations=json.dumps([]),
                status="analyzed",
                job_fit_report=json.dumps({
                    "jobFit": 95,
                    "strengths": ["distributed systems", "PostgreSQL optimisation", "security architecture"],
                    "weaknesses": ["Go proficiency", "ML/AI depth"],
                }),
                competency_scores=json.dumps({
                    "system_design": 9.5,
                    "coding": 9.0,
                    "databases": 9.7,
                    "behavioral": 9.0,
                    "communication": 9.2,
                }),
                communication_metrics=json.dumps({
                    "clarity": 9.5,
                    "conciseness": 9.0,
                    "technical_vocabulary": 9.8,
                }),
                behavioral_report=json.dumps({
                    "leadership": "Strong",
                    "collaboration": "Excellent",
                    "problem_solving": "Expert",
                }),
            )
            db.add(session_rec)
            db.flush()
            print(f"Created interview session id={session_rec.id}")

        # ── 7. CandidateCredibilityReport ────────────────────────────────────
        existing_cred = db.exec(
            select(CandidateCredibilityReport).where(CandidateCredibilityReport.session_id == session_rec.id)
        ).first()
        if not existing_cred:
            cred = CandidateCredibilityReport(
                candidate_id=user.id,
                session_id=session_rec.id,
                credibility_score=91,
                supported_claims=json.dumps(SUPPORTED_CLAIMS),
                weak_claims=json.dumps(WEAK_CLAIMS),
                missing_evidence=json.dumps(MISSING_EVIDENCE),
                followup_topics=json.dumps(FOLLOWUP_TOPICS),
                resume_score=93,
                interview_avg_score=avg_score,
                recommendation="Strongly Supported",
                status="completed",
                source="seed_script",
            )
            db.add(cred)
            db.flush()
            print(f"Created credibility report id={cred.id}")
        else:
            print(f"Credibility report already exists (id={existing_cred.id})")

        # ── 8. InterviewIntelligenceReport ───────────────────────────────────
        existing_intel = db.exec(
            select(InterviewIntelligenceReport).where(InterviewIntelligenceReport.application_id == application.id)
        ).first()
        if not existing_intel:
            # hiring_score = 0.35*resume + 0.40*interview*10 + 0.25*credibility
            hiring_score = round(0.35 * 93 + 0.40 * avg_score * 10 + 0.25 * 91, 1)
            intel = InterviewIntelligenceReport(
                application_id=application.id,
                candidate_id=user.id,
                session_id=session_rec.id,
                resume_score=93.0,
                technical_score=round((9.5 + 9.0 + 9.7 + 9.0) / 4 * 10, 1),
                behavioral_score=round((9.0 + 9.0 + 9.0) / 3 * 10, 1),
                credibility_score=91.0,
                overall_score=hiring_score,
                recommendation="Strongly Recommended",
                executive_summary=(
                    "Arjun Sharma delivered an outstanding interview performance demonstrating deep "
                    "expertise across distributed systems, database optimisation, security architecture, "
                    "and engineering leadership. His answers were consistently specific, metrics-driven, "
                    "and production-aware. Resume claims are 8/10 strongly supported by interview evidence. "
                    "He is an immediate hire recommendation for the Senior Full-Stack Engineer role. "
                    "Hiring score: {:.1f}/100.".format(hiring_score)
                ),
                strengths=json.dumps([
                    "Expert distributed systems design (Kafka, Redis, Kubernetes)",
                    "Deep PostgreSQL optimisation skills",
                    "Security-first mindset (RLS, JWT, secrets rotation)",
                    "Proven engineering leadership and mentoring impact",
                    "Strong communication — articulate, concise, and technical",
                ]),
                weaknesses=json.dumps([
                    "Go language not demonstrated in interview",
                    "ML/AI project work shallow compared to resume claims",
                ]),
                technical_assessment=(
                    "Demonstrated expert-level proficiency in system design, databases, security, "
                    "and software engineering practices. All 5 technical questions answered with "
                    "production-grade depth and specific examples."
                ),
                behavioral_assessment=(
                    "Showed mature collaboration, strong leadership under pressure, and a structured "
                    "mentoring approach with measurable outcomes."
                ),
                resume_validation=(
                    "8 of 10 technical claims strongly supported by interview evidence. "
                    "Go and TensorFlow experience not demonstrated."
                ),
                source="seed_script",
                status="analyzed",
            )
            db.add(intel)
            db.flush()
            print(f"Created intelligence report id={intel.id}, hiring_score={hiring_score}")
        else:
            print(f"Intelligence report already exists (id={existing_intel.id})")

        db.commit()

    print("\n✅  Star candidate seeded successfully!")
    print(f"   Username : {CANDIDATE_USERNAME}")
    print(f"   Password : {CANDIDATE_PASSWORD}")
    print(f"   Avg Score: {avg_score}/10  |  Credibility: 91  |  Resume Fit: 93")


if __name__ == "__main__":
    seed()
