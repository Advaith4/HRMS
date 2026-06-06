import sys

content = open('d:/GitHub/HRMS/src/api/routes/interview.py', 'r').read()

target = '''        "coach_memory": context["coach_memory"],
        "avg_score": avg,
        "phase": next_phase,
        "phase_goal": _phase_meta(next_phase)["goal"],
        "phase_focus": _phase_meta(next_phase)["focus"],
        "phase_history": context.get("phase_history", [next_phase]),
        "interview_complete": next_phase == "Final Evaluation",
        "final_feedback": final_feedback,
        "final_verdict": final_verdict,
        "verdict_explanation": verdict_explanation,
        "personalization_context": context,
    }'''

replacement = '''    final_feedback = None
    if next_phase == "Final Evaluation":
        final_feedback = {
            "overall_score": round(avg, 2) if avg is not None else score,
            "strengths": normalized_eval.get("what_went_well", [])[:3],
            "weaknesses": normalized_eval.get("what_was_missing", [])[:3],
            "improvement_plan": normalized_eval.get("how_to_improve", [])[:3],
            "verdict": final_verdict,
            "verdict_explanation": verdict_explanation,
        }

    return {
        **result,
        "evaluation": normalized_eval,
        "next_question": next_q,
        "difficulty": state["difficulty"],
        "focus_area": context["current_focus_area"],
        "focus_type": focus_type,
        "weak_areas": context.get("weak_areas", []),
        "question_mix": context.get("question_mix") or _question_mix_for_mode(context.get("training_mode", state.get("training_mode", "adaptive"))),
        "training_mode": context.get("training_mode", state.get("training_mode", "adaptive")),
        "interviewer_persona": context.get("interviewer_persona", state.get("interviewer_persona", "balanced")),
        "persona": INTERVIEWER_PERSONAS.get(context.get("interviewer_persona", "balanced"), INTERVIEWER_PERSONAS["balanced"]),
        "feedback_message": feedback_text,
        "feedback": feedback,
        "answer_expectation": result.get("answer_expectation", ""),
        "session_turn": len(state["answers"]),
        "coach_memory": context["coach_memory"],
        "avg_score": avg,
        "phase": next_phase,
        "phase_goal": _phase_meta(next_phase)["goal"],
        "phase_focus": _phase_meta(next_phase)["focus"],
        "phase_history": context.get("phase_history", [next_phase]),
        "interview_complete": next_phase == "Final Evaluation",
        "final_feedback": final_feedback,
        "final_verdict": final_verdict,
        "verdict_explanation": verdict_explanation,
        "personalization_context": context,
    }'''

if target in content:
    content = content.replace(target, replacement)
    open('d:/GitHub/HRMS/src/api/routes/interview.py', 'w').write(content)
    print("Replaced successfully")
else:
    print("Target not found in file")
