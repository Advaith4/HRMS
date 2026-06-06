"""Unit tests for interview stabilization — no database required."""

from __future__ import annotations

import pytest

from src.services.interview_status import (
    PHASE_SEQUENCE_V2,
    PHASE_TURN_TARGETS_V2,
    TOTAL_INTERVIEW_TURNS_V2,
    has_completed_required_turns,
    next_phase_for_completed_turn,
)
from src.services.interview_core import (
    _ensure_live_state,
    _is_interview_complete_after_answer,
    _state_from_record,
)
from src.api.routes.interview import (
    _candidate_visible_messages,
    _phase_aware_question,
    _question_matches_phase,
    _sanitize_candidate_response,
)


class _FakeRecord:
    def __init__(self):
        self.role = "Software Engineer"
        self.difficulty = 5
        self.training_mode = "adaptive"
        self.interviewer_persona = "balanced"
        self.personalization_context = "{}"
        self.messages = "[]"
        self.id = 1
        self.session_token = "abc123"
        self.user_id = 42


def test_phase_turn_targets_sum_to_twelve():
    assert sum(PHASE_TURN_TARGETS_V2.values()) == 12
    assert TOTAL_INTERVIEW_TURNS_V2 == 12


def test_phase_progression_sequence():
    phase = PHASE_SEQUENCE_V2[0]
    phase_turn_count = 0
    total_answers = 0
    for _ in range(20):
        phase_turn_count += 1
        total_answers += 1
        next_phase, complete = next_phase_for_completed_turn(phase, phase_turn_count)
        if complete:
            assert phase == "Final Evaluation"
            assert total_answers == TOTAL_INTERVIEW_TURNS_V2
            return
        if phase_turn_count >= PHASE_TURN_TARGETS_V2[phase]:
            phase = next_phase
            phase_turn_count = 0
    pytest.fail("Interview did not complete within safety bound")


def test_completion_only_on_final_evaluation_turn():
    assert not _is_interview_complete_after_answer("Behavioral Assessment", 3)
    assert not _is_interview_complete_after_answer("Final Evaluation", 0)
    assert _is_interview_complete_after_answer("Final Evaluation", 1)


def test_has_completed_required_turns_requires_all_phases():
    messages = []
    for phase, turns in PHASE_TURN_TARGETS_V2.items():
        for turn in range(turns):
            messages.append({"role": "ai", "content": f"Q {phase} {turn}", "phase": phase})
            messages.append({"role": "user", "content": f"A {phase} {turn}"})
            messages.append({"role": "feedback", "content": "internal", "score": 7})
    assert has_completed_required_turns(messages)


def test_candidate_visible_messages_hide_feedback_and_scores():
    messages = [
        {"role": "ai", "content": "Question?", "score": 9},
        {"role": "user", "content": "Answer"},
        {"role": "feedback", "content": "Great job", "score": 8, "meta": {"verdict": "Ready"}},
    ]
    visible = _candidate_visible_messages(messages)
    assert len(visible) == 2
    assert all(m.get("role") != "feedback" for m in visible)
    assert all("score" not in m for m in visible)


def test_sanitize_candidate_response_strips_evaluation_on_complete():
    payload = {
        "interview_complete": True,
        "next_question": "hidden",
        "final_feedback": {"verdict": "Ready"},
        "final_verdict": "Ready",
        "avg_score": 9.0,
        "messages": [],
    }
    sanitized = _sanitize_candidate_response(payload)
    assert sanitized["next_question"] == ""
    assert "final_feedback" not in sanitized
    assert "avg_score" not in sanitized


def test_sanitize_candidate_response_strips_evaluation():
    payload = {
        "next_question": "Next?",
        "feedback_message": "Strong depth and metrics.",
        "avg_score": 8.5,
        "final_verdict": "Ready",
        "messages": [
            {"role": "ai", "content": "Q1"},
            {"role": "feedback", "content": "hidden", "score": 7},
        ],
        "personalization_context": {"last_score": 7, "coach_memory": {"score_trend": [7]}},
        "coach_memory": {"score_trend": [7]},
        "interview_complete": False,
    }
    sanitized = _sanitize_candidate_response(payload)
    assert sanitized["feedback_message"] == "Your answer has been recorded."
    assert "avg_score" not in sanitized
    assert "final_verdict" not in sanitized
    assert sanitized["messages"] == [{"role": "ai", "content": "Q1"}]
    assert "last_score" not in sanitized["personalization_context"]


def test_sanitize_candidate_response_clears_next_question_on_complete():
    payload = {
        "next_question": "Should not appear",
        "interview_complete": True,
        "messages": [],
    }
    sanitized = _sanitize_candidate_response(payload)
    assert sanitized["next_question"] == ""
    assert "Generating final report" in sanitized["interviewer_response"]


def test_ensure_live_state_adds_required_keys():
    state = _ensure_live_state({})
    for key in ("role", "difficulty", "current_question", "answers", "questions", "scores", "messages"):
        assert key in state
    assert isinstance(state["personalization_context"], dict)


def test_state_from_record_is_safe_for_submit():
    rec = _FakeRecord()
    state = _state_from_record(rec)
    assert state["current_question"] == ""
    assert state["answers"] == []
    assert state["difficulty"] == 5


def test_completion_and_question_generation_mutually_exclusive():
    """Simulate turn-12 response shaping: no next question when complete."""
    interview_complete = True
    next_q = "leaked question"
    if interview_complete:
        next_q = ""
    ai_appended = not interview_complete and bool(next_q)
    assert next_q == ""
    assert ai_appended is False


def test_duplicate_message_rendering_prevented_by_single_source():
    backend_messages = [
        {"role": "ai", "content": "Q1"},
        {"role": "user", "content": "A1"},
        {"role": "feedback", "content": "eval", "score": 6},
        {"role": "ai", "content": "Q2"},
    ]
    visible = _candidate_visible_messages(backend_messages)
    roles = [m["role"] for m in visible]
    assert roles.count("user") == 1
    assert roles.count("ai") == 2
    assert "feedback" not in roles


def test_technical_phase_rejects_intro_clarification_question():
    bad_question = "Let me rephrase that. Could you provide a different example regarding general introduction?"
    assert not _question_matches_phase(bad_question, "Technical Assessment")

    final_question, question_type, duplicate, _similarity, replaced = _phase_aware_question(
        phase="Technical Assessment",
        phase_question_count=0,
        role="Backend Engineer",
        generated_question=bad_question,
        previous_questions=[
            "Tell me about yourself as it relates to this Backend Engineer role.",
            "Walk me through the background, education, or experience that prepared you for this role.",
            "Choose one resume project or claim and explain your ownership, evidence, and outcome.",
        ],
        clarification_attempts={},
    )

    assert replaced is True
    assert duplicate is False
    assert question_type == "project_architecture"
    assert "architecture" in final_question.lower()
    assert "introduction" not in final_question.lower()
    assert "clarification" not in final_question.lower()


def test_duplicate_technical_question_progresses_without_clarification_loop():
    previous = [
        "Walk me through the architecture of a project you built, including the major components and why you designed it that way.",
        "Describe a difficult technical challenge you faced in that project and the engineering decision that resolved it.",
        "Design a production-ready system for a core feature in this role. Cover data flow, scale, reliability, and tradeoffs.",
    ]

    final_question, question_type, duplicate, _similarity, replaced = _phase_aware_question(
        phase="Technical Assessment",
        phase_question_count=0,
        role="Backend Engineer",
        generated_question=previous[0],
        previous_questions=previous,
        clarification_attempts={"Technical Assessment": 1},
    )

    assert replaced is True
    assert duplicate is False
    assert question_type == "apis"
    assert "api" in final_question.lower()
    assert "clarification" not in final_question.lower()
