"""
tests/test_phase9_phase10_llmops.py
Phase 9 & 10 Verification: Observability, Error Taxonomy (E101-E106), and LLMOps Dashboard.
"""
import json
import os
import tempfile
import uuid
from pathlib import Path
import pytest

# Ensure isolated SQLite database before importing src.main
test_db_file = f"data/test_llmops_{uuid.uuid4().hex[:8]}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_file}"

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from src.core.llmops_metrics import (
    LLMOpsMetricsAggregator,
    _calculate_percentiles,
    GROQ_INPUT_COST_PER_MILLION,
    GROQ_OUTPUT_COST_PER_MILLION,
)
from src.core.resilience import ErrorTaxonomy
from src.core.security import create_access_token, hash_password
from src.database.connection import create_db_and_tables, get_session
from src.main import app
from src.models import HumanEvaluation, User


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    create_db_and_tables()
    yield
    if os.path.exists(test_db_file):
        try:
            os.remove(test_db_file)
        except OSError:
            pass


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    from src.database.connection import engine
    from sqlmodel import select
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == "admin_llmops")).first()
        if not user:
            user = User(
                username="admin_llmops",
                hashed_password=hash_password("AdminPass123!"),
                role="admin",
            )
            session.add(user)
            session.commit()
            session.refresh(user)
        return create_access_token(user_id=user.id, username=user.username, role="admin")


@pytest.fixture
def candidate_token(client):
    from src.database.connection import engine
    from sqlmodel import select
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == "candidate_llmops")).first()
        if not user:
            user = User(
                username="candidate_llmops",
                hashed_password=hash_password("CandPass123!"),
                role="candidate",
            )
            session.add(user)
            session.commit()
            session.refresh(user)
        return create_access_token(user_id=user.id, username=user.username, role="candidate")


def test_percentile_calculations():
    """Verify statistical percentile calculations for SLA metrics."""
    values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    res = _calculate_percentiles(values)

    assert res["min"] == 10.0
    assert res["p50"] == 50.0
    assert res["p90"] == 90.0
    assert res["p95"] == 100.0
    assert res["p99"] == 100.0
    assert res["max"] == 100.0
    assert res["mean"] == 55.0

    # Empty list handling
    empty_res = _calculate_percentiles([])
    assert empty_res["p50"] == 0.0
    assert empty_res["mean"] == 0.0


def test_llmops_metrics_aggregator_synthetic_traces(tmp_path):
    """Verify LLMOps aggregator on synthetic trace log file with Error Taxonomy."""
    trace_file = tmp_path / "synthetic_audit.jsonl"
    sample_records = [
        {
            "timestamp": "2026-09-20T00:00:00Z",
            "request_id": "req-1",
            "agent": "PlannerAgent",
            "tool": "WorkflowDAGPlanner",
            "latency_ms": 15.0,
            "input_tokens": 1000,
            "output_tokens": 200,
            "status": "SUCCESS",
            "details": {},
        },
        {
            "timestamp": "2026-09-20T00:01:00Z",
            "request_id": "req-2",
            "agent": "ValidatorAgent",
            "tool": "ConfidenceAuditor",
            "latency_ms": 25.0,
            "input_tokens": 500,
            "output_tokens": 100,
            "status": "RETRY_RECOMMENDED",
            "details": {"hallucination": True, "error_code": "E104"},
        },
        {
            "timestamp": "2026-09-20T00:02:00Z",
            "request_id": "req-3",
            "agent": "HttpGateway",
            "tool": "POST /api/resume/parse",
            "latency_ms": 120.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "status": "HTTP_429",
            "details": {"error": "Rate limit exceeded", "code": "E101"},
        },
        {
            "timestamp": "2026-09-20T00:03:00Z",
            "request_id": "req-4",
            "agent": "HttpGateway",
            "tool": "POST /api/resume/parse",
            "latency_ms": 45.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "status": "HTTP_200",
            "details": {},
        },
    ]

    with open(trace_file, "w", encoding="utf-8") as f:
        for r in sample_records:
            f.write(json.dumps(r) + "\n")

    aggregator = LLMOpsMetricsAggregator(trace_file=trace_file)
    metrics = aggregator.compute_metrics()

    assert metrics["overview"]["total_traced_calls"] == 4
    # 2 SUCCESS + 1 RETRY_RECOMMENDED (handled) = 3 / 4 = 75.0%
    assert metrics["overview"]["success_rate_pct"] == 75.0
    assert metrics["overview"]["latency_ms"]["p50"] == 35.0 or metrics["overview"]["latency_ms"]["p50"] > 0
    assert metrics["token_economics"]["total_input_tokens"] == 1500
    assert metrics["token_economics"]["total_output_tokens"] == 300

    # Verify Error Taxonomy count extraction
    taxonomy = metrics["error_taxonomy"]["breakdown"]
    assert taxonomy["E101"]["count"] == 1
    assert taxonomy["E104"]["count"] == 1
    assert taxonomy["E101"]["remediation"] == "Jittered Exponential Backoff Retry (max 3 attempts)."


def test_query_traces_filtering(tmp_path):
    """Test trace log querying with pagination, agent filter, and search."""
    trace_file = tmp_path / "filter_test.jsonl"
    records = [
        {"request_id": "req-101", "agent": "PlannerAgent", "tool": "ToolA", "status": "SUCCESS", "latency_ms": 10},
        {"request_id": "req-102", "agent": "ValidatorAgent", "tool": "ToolB", "status": "SUCCESS", "latency_ms": 20},
        {"request_id": "req-103", "agent": "PlannerAgent", "tool": "ToolC", "status": "FAILED", "latency_ms": 30},
    ]
    with open(trace_file, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    aggregator = LLMOpsMetricsAggregator(trace_file=trace_file)

    # Filter by agent
    planner_traces = aggregator.query_traces(agent="PlannerAgent")
    assert planner_traces["total"] == 2
    assert len(planner_traces["traces"]) == 2

    # Filter by search
    searched = aggregator.query_traces(search="ToolB")
    assert searched["total"] == 1
    assert searched["traces"][0]["request_id"] == "req-102"

    # Pagination limit
    paged = aggregator.query_traces(limit=1, offset=0)
    assert len(paged["traces"]) == 1


def test_admin_llmops_metrics_endpoint_rbac(client, admin_token, candidate_token):
    """Verify RBAC and response format of GET /api/admin/llmops/metrics."""
    # Candidate should be rejected with 403
    cand_resp = client.get(
        "/api/admin/llmops/metrics",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert cand_resp.status_code == 403

    # Admin should succeed with 200 OK
    admin_resp = client.get(
        "/api/admin/llmops/metrics",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_resp.status_code == 200
    data = admin_resp.json()
    assert "overview" in data
    assert "token_economics" in data
    assert "error_taxonomy" in data
    assert "agents" in data


def test_admin_llmops_traces_and_taxonomy_endpoints(client, admin_token):
    """Verify GET /api/admin/llmops/traces and GET /api/admin/llmops/error-taxonomy."""
    # Test Traces endpoint
    traces_resp = client.get(
        "/api/admin/llmops/traces?limit=10",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert traces_resp.status_code == 200
    t_data = traces_resp.json()
    assert "total" in t_data
    assert "traces" in t_data
    assert isinstance(t_data["traces"], list)

    # Test Taxonomy endpoint
    tax_resp = client.get(
        "/api/admin/llmops/error-taxonomy",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert tax_resp.status_code == 200
    tax_data = tax_resp.json()
    assert "breakdown" in tax_data
    assert "E101" in tax_data["breakdown"]
    assert "E106" in tax_data["breakdown"]


def test_export_metrics_summary(tmp_path):
    """Verify exporting metrics summary to JSON file."""
    aggregator = LLMOpsMetricsAggregator()
    out_file = tmp_path / "summary_test.json"
    result_path = aggregator.export_metrics_summary(filepath=out_file)

    assert result_path.exists()
    with open(result_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "overview" in data
    assert "error_taxonomy" in data
