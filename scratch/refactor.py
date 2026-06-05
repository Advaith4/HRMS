import re

with open('src/api/routes/interview.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Remove helper functions. They start around line 30 with INTERVIEW_PHASES, up to @router.post('/start')
# Let's find the router initialization
router_idx = content.find('router = APIRouter')
# Find the start of @router.post('/start-for-application')
app_start_idx = content.find('@router.post("/start-for-application")')

if router_idx != -1 and app_start_idx != -1:
    # Keep up to router definition
    router_end = content.find('\n', router_idx) + 1
    head = content[:router_end]
    
    # We also need some imports from interview_core
    core_imports = '''
from src.services.interview_core import (
    _sessions,
    _normalize_training_mode,
    _normalize_persona,
    _get_or_create_memory,
    _latest_candidate_resume_text,
    _build_personalization_context,
    _memory_snapshot,
    _phase_meta,
    _ensure_intro_question,
    _normalize_focus_type,
    _update_coach_memory,
    INTERVIEWER_PERSONAS,
    TRAINING_MODES,
    _save_session_state,
    _state_from_record,
    _should_end_interview_early,
    _pick_next_phase,
    _format_feedback_message,
    _generate_daily_plan,
    _unique_strings,
    _recurring_area_label,
    _upsert_weak_area_counts,
    _derive_section_scores,
    _derive_weak_areas,
    _build_resume_context,
    _choose_focus_mode,
    _normalize_and_repair_evaluation,
    _safe_json_load,
    INTERVIEW_PHASES,
    PHASE_SEQUENCE
)
'''
    
    # The rest of the file starts from app_start_idx
    tail = content[app_start_idx:]
    
    # Rename start-for-application to start
    tail = tail.replace('@router.post("/start-for-application")', '@router.post("/start")')
    tail = tail.replace('def start_interview_for_application(', 'def start_interview(')
    
    # Write back
    with open('src/api/routes/interview.py', 'w', encoding='utf-8') as f:
        f.write(head + core_imports + '\n' + tail)
        print('Successfully refactored interview.py')
else:
    print('Failed to find indices')
