"""
tests/test_phase3_tools.py
Phase 3: Practical Tool Integration Comprehensive Test Suite.
Tests SQLQueryTool (Read-Only & Security Guardrails), PDFExtractionTool (Native & OCR Fallback),
WhisperTranscriptionTool, HRCalculatorTool (Deterministic Math), and EmailDraftTool (HITL Dispatch).
"""
import os
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

os.environ["AUTO_CREATE_DB_SCHEMA"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-talentforge"

from src.database.connection import create_db_and_tables, engine
from src.main import app
from src.models import User
from src.tools.calculator_tool import hr_calculator_tool
from src.tools.email_tool import email_draft_tool
from src.tools.ocr_tool import pdf_extraction_tool
from src.tools.sql_tool import sql_query_tool
from src.tools.whisper_tool import whisper_transcription_tool

create_db_and_tables()
client = TestClient(app)


def _register(username: str, role: str) -> str:
    client.post("/api/auth/register", json={"username": username, "password": "Pass123!"})
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if user:
            user.role = role
            session.add(user)
            session.commit()
    login = client.post("/api/auth/login", json={"username": username, "password": "Pass123!"})
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_sql_query_tool_read_only_and_security_blocks():
    """Task 3.1: Verify SQLQueryTool executes SELECT queries and strictly blocks mutations."""
    # 1. Valid read-only query
    out = sql_query_tool.run(query="SELECT 1 as test_val, 'active' as status")
    assert out.row_count == 1
    assert "test_val" in out.columns or len(out.columns) >= 1
    assert len(out.rows) == 1

    # 2. Security violation: DROP TABLE
    with pytest.raises(PermissionError):
        sql_query_tool.run(query="DROP TABLE users")

    # 3. Security violation: DELETE FROM
    with pytest.raises(PermissionError):
        sql_query_tool.run(query="DELETE FROM candidate_applications WHERE id = 1")

    # 4. Security violation: INSERT INTO
    with pytest.raises(PermissionError):
        sql_query_tool.run(query="INSERT INTO users (username) VALUES ('hacker')")


def test_pdf_and_ocr_extraction_tool(tmp_path):
    """Tasks 3.2 & 3.3: Verify PDF text extraction and fallback handling."""
    # 1. Text resume extraction
    sample_text_resume = tmp_path / "sample_resume.txt"
    sample_text_resume.write_text(
        "Alice Vance is a Senior Python Developer with over 6 years of experience building scalable backend microservices, "
        "REST APIs with FastAPI, containerized deployments with Docker, and relational databases in PostgreSQL. "
        "Education: Bachelor of Science in Computer Engineering from Stanford University."
    )

    out = pdf_extraction_tool.run(file_path=str(sample_text_resume))
    assert out.character_count > 0
    assert "Alice Vance" in out.text
    assert out.page_count >= 1
    assert out.is_scanned is False

    # 2. Test OCR fallback on simulated image file
    sample_img = tmp_path / "scanned_resume.png"
    sample_img.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")  # Minimal dummy PNG header

    img_out = pdf_extraction_tool.run(file_path=str(sample_img))
    assert img_out.is_scanned is True
    assert img_out.extraction_method == "ocr_image_reader"
    assert len(img_out.text) > 0


def test_whisper_transcription_tool(tmp_path):
    """Task 3.4: Verify WhisperTranscriptionTool returns validated transcript and confidence."""
    dummy_audio = tmp_path / "interview_answer.wav"
    dummy_audio.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00")

    out = whisper_transcription_tool.run(audio_path=str(dummy_audio), language="en")
    assert len(out.transcript) > 10
    assert 0.0 <= out.confidence <= 1.0
    assert out.duration_seconds > 0.0
    assert out.language == "en"


def test_hr_calculator_tool_deterministic_math():
    """Task 3.5: Verify HRCalculatorTool computes exact weighted averages and GPA normalizations."""
    # 1. Weighted Average: (80*0.4 + 90*0.6) = 32 + 54 = 86.0
    weighted_out = hr_calculator_tool.run(
        operation="weighted_average",
        values=[80.0, 90.0],
        weights=[0.4, 0.6],
    )
    assert weighted_out.result == 86.0

    # 2. GPA Normalization: (3.8 / 4.0) * 100 = 95.0%
    gpa_out = hr_calculator_tool.run(
        operation="gpa_normalization",
        values=[3.8],
        scale_max=4.0,
    )
    assert gpa_out.result == 95.0

    # 3. Percentile Rank: 85 among [60, 70, 80, 85, 90, 95] -> 3 below out of 6 -> 50.0%
    pct_out = hr_calculator_tool.run(
        operation="percentile_rank",
        values=[85.0, 60.0, 70.0, 80.0, 85.0, 90.0, 95.0],
    )
    assert pct_out.result == 50.0


def test_email_draft_and_dispatch_workflow():
    """Task 3.6: Verify EmailDraftTool and Human-in-the-Loop dispatch endpoint."""
    suffix = uuid.uuid4().hex[:6]
    hr_token = _register(f"hr_email_{suffix}", "hr")

    # 1. Generate Email Draft
    draft_resp = client.post(
        "/api/notifications/email/draft",
        json={
            "candidate_id": 101,
            "candidate_name": "Alice Vance",
            "candidate_email": "alice@example.com",
            "job_title": "AI Architect",
            "email_type": "interview_invitation",
            "interview_link": "https://talentforge.ai/interview/sess-123",
        },
        headers=_headers(hr_token),
    )
    assert draft_resp.status_code == 200, draft_resp.text
    draft_data = draft_resp.json()
    assert draft_data["status"] == "draft"
    assert draft_data["requires_hr_approval"] is True
    assert "AI Architect" in draft_data["subject"]

    # 2. Rejection if not approved
    bad_send = client.post(
        "/api/notifications/email/dispatch",
        json={
            "draft_id": draft_data["draft_id"],
            "approved": False,
            "recipient_email": draft_data["recipient_email"],
            "subject": draft_data["subject"],
            "body": draft_data["body"],
        },
        headers=_headers(hr_token),
    )
    assert bad_send.status_code == 400

    # 3. Successful dispatch with HR approval
    good_send = client.post(
        "/api/notifications/email/dispatch",
        json={
            "draft_id": draft_data["draft_id"],
            "approved": True,
            "recipient_email": draft_data["recipient_email"],
            "subject": draft_data["subject"],
            "body": draft_data["body"],
        },
        headers=_headers(hr_token),
    )
    assert good_send.status_code == 200
    assert good_send.json()["status"] == "dispatched"
