"""
src/core/llmops_metrics.py
Centralized LLMOps Observability, Error Taxonomy, and Telemetry Engine for TalentForge AI.
"""
import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlmodel import Session, select

from src.core.resilience import ErrorTaxonomy
from src.models import HumanEvaluation

logger = logging.getLogger(__name__)

EVIDENCE_LOGS_DIR = Path("evidence/logs")
EVIDENCE_METRICS_DIR = Path("evidence/metrics")
DEFAULT_TRACE_FILE = EVIDENCE_LOGS_DIR / "audit_trace.jsonl"
DEFAULT_METRICS_SUMMARY_FILE = EVIDENCE_METRICS_DIR / "llmops_dashboard_metrics.json"

# Pricing model (USD per 1,000,000 tokens) for Llama-3.1-8B-Instant (Groq)
GROQ_INPUT_COST_PER_MILLION = 0.05
GROQ_OUTPUT_COST_PER_MILLION = 0.08


def _calculate_percentiles(values: List[float]) -> Dict[str, float]:
    """Calculate standard latency percentiles."""
    if not values:
        return {"min": 0.0, "p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0, "mean": 0.0}
    
    sorted_vals = sorted(values)
    n = len(sorted_vals)

    def _get_p(p: float) -> float:
        idx = int(math.ceil((p / 100.0) * n)) - 1
        return round(sorted_vals[max(0, min(n - 1, idx))], 2)

    return {
        "min": round(sorted_vals[0], 2),
        "p50": _get_p(50),
        "p90": _get_p(90),
        "p95": _get_p(95),
        "p99": _get_p(99),
        "max": round(sorted_vals[-1], 2),
        "mean": round(sum(sorted_vals) / n, 2),
    }


class LLMOpsMetricsAggregator:
    """
    Parses and aggregates operational telemetry from audit logs and human evaluation metrics.
    """

    def __init__(self, trace_file: Path | str = DEFAULT_TRACE_FILE):
        self.trace_file = Path(trace_file)

    def load_traces(self) -> List[Dict[str, Any]]:
        """Load all trace entries from the audit JSONL file."""
        if not self.trace_file.exists():
            return []
        
        traces = []
        try:
            with open(self.trace_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        traces.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except Exception as exc:
            logger.warning("Error reading audit trace file %s: %s", self.trace_file, exc)
            return []
        
        return traces

    def query_traces(
        self,
        agent: Optional[str] = None,
        tool: Optional[str] = None,
        status: Optional[str] = None,
        error_code: Optional[str] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
        order_desc: bool = True,
    ) -> Dict[str, Any]:
        """
        Query and filter traces with pagination and text search.
        """
        all_traces = self.load_traces()
        filtered = []

        for t in all_traces:
            # Agent filter
            if agent and t.get("agent", "").lower() != agent.lower():
                continue
            
            # Tool filter
            t_tool = t.get("tool")
            if tool:
                tool_str = str(t_tool).lower() if t_tool else ""
                if tool.lower() not in tool_str:
                    continue

            # Status filter
            t_status = t.get("status", "")
            if status and status.upper() not in t_status.upper():
                continue

            # Error code filter
            if error_code:
                details_str = json.dumps(t.get("details", {}))
                status_str = t.get("status", "")
                if error_code.upper() not in details_str.upper() and error_code.upper() not in status_str.upper():
                    continue

            # Text search filter
            if search:
                search_lower = search.lower()
                blob = f"{t.get('request_id', '')} {t.get('agent', '')} {t.get('tool', '')} {t.get('status', '')} {json.dumps(t.get('details', {}))}".lower()
                if search_lower not in blob:
                    continue

            filtered.append(t)

        total = len(filtered)
        if order_desc:
            filtered.reverse()

        paginated = filtered[offset : offset + limit]

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "traces": paginated,
        }

    def compute_metrics(self, session: Optional[Session] = None) -> Dict[str, Any]:
        """
        Computes complete LLMOps metrics suite: latencies, throughput, error taxonomy,
        token economics, and human feedback.
        """
        traces = self.load_traces()
        total_traces = len(traces)

        if total_traces == 0:
            return self._empty_metrics()

        latencies = []
        input_tokens_total = 0
        output_tokens_total = 0
        agent_stats: Dict[str, Dict[str, Any]] = {}
        tool_stats: Dict[str, Dict[str, Any]] = {}
        error_taxonomy_counts = {
            "E101": 0,  # Rate limit
            "E102": 0,  # Schema validation failure
            "E103": 0,  # LLM timeout
            "E104": 0,  # Hallucination detected
            "E105": 0,  # Missing/corrupt resume file
            "E106": 0,  # Database/SQL error
            "OTHER_ERRORS": 0,
        }

        success_count = 0
        failed_count = 0
        retry_count = 0

        for t in traces:
            latency = float(t.get("latency_ms", 0.0) or 0.0)
            latencies.append(latency)

            in_tok = int(t.get("input_tokens", 0) or 0)
            out_tok = int(t.get("output_tokens", 0) or 0)
            input_tokens_total += in_tok
            output_tokens_total += out_tok

            agent = t.get("agent", "UnknownAgent")
            tool = t.get("tool")
            status = str(t.get("status", "SUCCESS")).upper()
            details = t.get("details", {})

            # Classify status
            is_success = (
                status == "SUCCESS"
                or status == "COMPLETED"
                or (status.startswith("HTTP_") and status[5:6] == "2")
            )
            is_retry = (
                status == "RETRY_RECOMMENDED"
                or bool(details.get("retry_recommended"))
            )
            is_error = (
                status == "FAILED"
                or status == "ERROR"
                or (status.startswith("HTTP_") and status[5:6] in ("4", "5"))
                or bool(details.get("error"))
                or "error" in details
            )

            if is_success and not is_retry:
                success_count += 1
            elif is_retry:
                retry_count += 1
                success_count += 1  # retry handled successfully
            elif is_error:
                failed_count += 1
            else:
                success_count += 1

            # Check for error taxonomy codes in status or details
            details_blob = json.dumps(details).upper()
            has_explicit_tax = False
            for code in ["E101", "E102", "E103", "E104", "E105", "E106"]:
                if code in details_blob or code in status:
                    error_taxonomy_counts[code] += 1
                    has_explicit_tax = True

            # Semantic error classification if no explicit code
            if not has_explicit_tax:
                if "429" in status or "RATE" in details_blob:
                    error_taxonomy_counts["E101"] += 1
                elif "VALIDATION" in details_blob or "SCHEMA" in details_blob:
                    error_taxonomy_counts["E102"] += 1
                elif "TIMEOUT" in details_blob:
                    error_taxonomy_counts["E103"] += 1
                elif details.get("hallucination") is True or "HALLUCINATION" in details_blob:
                    error_taxonomy_counts["E104"] += 1
                elif "CORRUPT" in details_blob or "MISSING_FILE" in details_blob:
                    error_taxonomy_counts["E105"] += 1
                elif "DATABASE" in details_blob or "SQL" in details_blob:
                    error_taxonomy_counts["E106"] += 1
                elif is_error:
                    error_taxonomy_counts["OTHER_ERRORS"] += 1

            # Per-agent telemetry
            if agent not in agent_stats:
                agent_stats[agent] = {
                    "total_calls": 0,
                    "latencies": [],
                    "success_count": 0,
                    "retry_count": 0,
                    "error_count": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                }
            agent_stats[agent]["total_calls"] += 1
            agent_stats[agent]["latencies"].append(latency)
            agent_stats[agent]["input_tokens"] += in_tok
            agent_stats[agent]["output_tokens"] += out_tok
            if is_error:
                agent_stats[agent]["error_count"] += 1
            elif is_retry:
                agent_stats[agent]["retry_count"] += 1
                agent_stats[agent]["success_count"] += 1
            else:
                agent_stats[agent]["success_count"] += 1

            # Per-tool telemetry
            tool_name = str(tool) if tool else "UnassignedTool"
            if tool_name not in tool_stats:
                tool_stats[tool_name] = {
                    "total_calls": 0,
                    "latencies": [],
                    "error_count": 0,
                }
            tool_stats[tool_name]["total_calls"] += 1
            tool_stats[tool_name]["latencies"].append(latency)
            if is_error:
                tool_stats[tool_name]["error_count"] += 1

        # Calculate Percentiles
        latency_dist = _calculate_percentiles(latencies)

        # Agent breakdown formatting
        agents_summary = {}
        for ag, st in agent_stats.items():
            ag_dist = _calculate_percentiles(st["latencies"])
            ag_success_rate = (
                round((st["success_count"] / st["total_calls"]) * 100.0, 2)
                if st["total_calls"] > 0
                else 100.0
            )
            agents_summary[ag] = {
                "total_calls": st["total_calls"],
                "success_rate_pct": ag_success_rate,
                "error_count": st["error_count"],
                "retry_count": st["retry_count"],
                "mean_latency_ms": ag_dist["mean"],
                "p50_latency_ms": ag_dist["p50"],
                "p95_latency_ms": ag_dist["p95"],
                "p99_latency_ms": ag_dist["p99"],
                "input_tokens": st["input_tokens"],
                "output_tokens": st["output_tokens"],
            }

        # Tool breakdown formatting
        tools_summary = {}
        for tl, st in tool_stats.items():
            tl_dist = _calculate_percentiles(st["latencies"])
            tools_summary[tl] = {
                "total_calls": st["total_calls"],
                "mean_latency_ms": tl_dist["mean"],
                "p95_latency_ms": tl_dist["p95"],
                "error_count": st["error_count"],
            }

        # Token Economics
        total_tokens = input_tokens_total + output_tokens_total
        input_cost_usd = (input_tokens_total / 1_000_000.0) * GROQ_INPUT_COST_PER_MILLION
        output_cost_usd = (output_tokens_total / 1_000_000.0) * GROQ_OUTPUT_COST_PER_MILLION
        total_cost_usd = round(input_cost_usd + output_cost_usd, 6)

        # Success rate
        success_rate_pct = round((success_count / total_traces) * 100.0, 2)
        error_rate_pct = round((failed_count / total_traces) * 100.0, 2)
        retry_rate_pct = round((retry_count / total_traces) * 100.0, 2)

        # Error Taxonomy Schema details
        error_taxonomy_report = self._build_taxonomy_details(error_taxonomy_counts)

        # Human Alignment
        human_eval_summary = self._get_human_eval_metrics(session)

        metrics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overview": {
                "total_traced_calls": total_traces,
                "success_count": success_count,
                "failed_count": failed_count,
                "retry_count": retry_count,
                "success_rate_pct": success_rate_pct,
                "error_rate_pct": error_rate_pct,
                "retry_rate_pct": retry_rate_pct,
                "latency_ms": latency_dist,
            },
            "token_economics": {
                "total_input_tokens": input_tokens_total,
                "total_output_tokens": output_tokens_total,
                "total_tokens": total_tokens,
                "input_cost_usd": round(input_cost_usd, 6),
                "output_cost_usd": round(output_cost_usd, 6),
                "total_cost_usd": total_cost_usd,
                "model": "llama-3.1-8b-instant (Groq)",
            },
            "error_taxonomy": error_taxonomy_report,
            "agents": agents_summary,
            "tools": tools_summary,
            "human_alignment": human_eval_summary,
        }

        return metrics

    def _build_taxonomy_details(self, counts: Dict[str, int]) -> Dict[str, Any]:
        """Builds structured taxonomy descriptors and counts."""
        definitions = {
            "E101": {
                "name": "RATE_LIMIT_EXCEEDED",
                "description": "Provider rate limit (HTTP 429).",
                "remediation": "Jittered Exponential Backoff Retry (max 3 attempts).",
                "severity": "MEDIUM",
                "count": counts.get("E101", 0),
            },
            "E102": {
                "name": "VALIDATION_FAILURE",
                "description": "Structured Pydantic validation failed on LLM response.",
                "remediation": "Self-correction reflection loop with schema feedback.",
                "severity": "HIGH",
                "count": counts.get("E102", 0),
            },
            "E103": {
                "name": "LLM_TIMEOUT",
                "description": "LLM inference exceeded execution deadline (15s).",
                "remediation": "Deterministic Fallback Scorer substitution.",
                "severity": "HIGH",
                "count": counts.get("E103", 0),
            },
            "E104": {
                "name": "HALLUCINATION_DETECTED",
                "description": "Validator Agent detected ungrounded or fabricated claims.",
                "remediation": "Confidence gate check with prompt reframing & retry.",
                "severity": "CRITICAL",
                "count": counts.get("E104", 0),
            },
            "E105": {
                "name": "CORRUPT_OR_MISSING_FILE",
                "description": "Resume PDF is empty, scanned without text, or missing.",
                "remediation": "Tesseract OCR / PDFTextRepair fallback.",
                "severity": "MEDIUM",
                "count": counts.get("E105", 0),
            },
            "E106": {
                "name": "DATABASE_ERROR",
                "description": "Database query, migration, or transaction failed.",
                "remediation": "Idempotent table creation and AST SQL validation.",
                "severity": "CRITICAL",
                "count": counts.get("E106", 0),
            },
            "OTHER_ERRORS": {
                "name": "UNCLASSIFIED_RUNTIME_ERROR",
                "description": "Unhandled application exception or 5xx response.",
                "remediation": "Global Exception Handler & trace capture.",
                "severity": "HIGH",
                "count": counts.get("OTHER_ERRORS", 0),
            },
        }

        total_errors = sum(counts.values())
        return {
            "total_errors": total_errors,
            "breakdown": definitions,
        }

    def _get_human_eval_metrics(self, session: Optional[Session] = None) -> Dict[str, Any]:
        """Aggregate Human Evaluation feedback ratings from the database."""
        if not session:
            return {
                "total_ratings": 0,
                "mean_overall": 5.0,
                "mean_correctness": 5.0,
                "mean_helpfulness": 5.0,
                "mean_completeness": 5.0,
                "mean_safety_groundedness": 5.0,
                "alignment_rate_pct": 100.0,
            }

        try:
            evals = session.exec(select(HumanEvaluation)).all()
            if not evals:
                return {
                    "total_ratings": 0,
                    "mean_overall": 5.0,
                    "mean_correctness": 5.0,
                    "mean_helpfulness": 5.0,
                    "mean_completeness": 5.0,
                    "mean_safety_groundedness": 5.0,
                    "alignment_rate_pct": 100.0,
                }

            n = len(evals)
            c = sum(e.correctness for e in evals) / n
            h = sum(e.helpfulness for e in evals) / n
            comp = sum(e.completeness for e in evals) / n
            s = sum(e.safety_groundedness for e in evals) / n
            overall = (c + h + comp + s) / 4.0
            
            # Count evaluations with overall score >= 4.0 as aligned
            aligned = sum(1 for e in evals if (e.correctness + e.helpfulness + e.completeness + e.safety_groundedness) / 4.0 >= 4.0)
            alignment_rate = round((aligned / n) * 100.0, 2)

            return {
                "total_ratings": n,
                "mean_overall": round(overall, 2),
                "mean_correctness": round(c, 2),
                "mean_helpfulness": round(h, 2),
                "mean_completeness": round(comp, 2),
                "mean_safety_groundedness": round(s, 2),
                "alignment_rate_pct": alignment_rate,
            }
        except Exception as exc:
            logger.warning("Error fetching human evaluations for LLMOps: %s", exc)
            return {
                "total_ratings": 0,
                "mean_overall": 0.0,
                "alignment_rate_pct": 0.0,
            }

    def _empty_metrics(self) -> Dict[str, Any]:
        """Returns zero-state metrics schema."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overview": {
                "total_traced_calls": 0,
                "success_count": 0,
                "failed_count": 0,
                "retry_count": 0,
                "success_rate_pct": 100.0,
                "error_rate_pct": 0.0,
                "retry_rate_pct": 0.0,
                "latency_ms": _calculate_percentiles([]),
            },
            "token_economics": {
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_tokens": 0,
                "input_cost_usd": 0.0,
                "output_cost_usd": 0.0,
                "total_cost_usd": 0.0,
                "model": "llama-3.1-8b-instant (Groq)",
            },
            "error_taxonomy": self._build_taxonomy_details({}),
            "agents": {},
            "tools": {},
            "human_alignment": self._get_human_eval_metrics(None),
        }

    def export_metrics_summary(self, filepath: Path | str = DEFAULT_METRICS_SUMMARY_FILE, session: Optional[Session] = None) -> Path:
        """Exports computed metrics to JSON for evidence and auditing."""
        metrics = self.compute_metrics(session=session)
        out_path = Path(filepath)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
        logger.info("Exported LLMOps metrics to %s", out_path)
        return out_path

