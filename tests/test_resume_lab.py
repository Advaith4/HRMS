from src.resume_lab import apply_fix, parse_resume, repair_resume_text_spacing, validate_resume_analysis


def test_parse_resume_extracts_core_sections():
    text = """
Summary
Flutter developer building mobile apps.
Skills
Flutter, Dart, Firebase
Projects
- Worked on chatbot project
Experience
- Responsible for app UI
"""

    parsed = parse_resume(text)

    assert "Flutter" in parsed["skills"]
    assert parsed["projects"] == ["Worked on chatbot project"]
    assert parsed["experience"] == ["Responsible for app UI"]


def test_repair_resume_text_spacing_unstucks_common_pdf_word_runs():
    broken = "Third-yearComputerScienceEngineeringstudentwithstrongfoundationsinprogramming,datastructures,andsoftwaredevelopment."

    repaired = repair_resume_text_spacing(broken)

    assert "Third-year Computer Science Engineering student" in repaired
    assert "strong foundations in programming" in repaired
    assert "data structures" in repaired
    assert "software development" in repaired


def test_parse_resume_repairs_glued_summary_words():
    text = """
Summary
Third-yearComputerScienceEngineeringstudentwithstrongfoundationsinprogramming,datastructures,andsoftwaredevelopment.
Skills
Python, FastAPI, SQL
"""

    parsed = parse_resume(text)

    assert "Computer Science Engineering student" in parsed["summary"]
    assert "data structures" in parsed["summary"]


def test_repair_resume_text_spacing_handles_multi_sentence_resume_summary():
    broken = (
        "Third-yearComputerScienceEngineeringstudentwithstrongfoundationsinprogramming,datastructures,"
        "andsoftwaredevelopment.Skilledinbuildingefficient,maintainableapplicationswithafocusoncleancode"
        "andproblem-solving.PossessesworkingknowledgeofGenerativeAI,largelanguagemodels,andmulti-agentsystems,"
        "withtheabilitytointegrateintelligentfunctionalities"
    )

    repaired = repair_resume_text_spacing(broken)

    assert "Skilled in building efficient, maintainable applications" in repaired
    assert "clean code and problem-solving" in repaired
    assert "Generative AI, large language models, and multi-agent systems" in repaired
    assert "with the ability to integrate intelligent functionalities" in repaired


def test_repair_resume_text_spacing_collapses_character_spaced_pdf_text():
    broken = (
        "T h i r d - y e a r C o m p u t e r S c i e n c e E n g i n e e r i n g "
        "s t u d e n t w i t h s t r o n g f o u n d a t i o n s i n p r o g r a m m i n g , "
        "d a t a s t r u c t u r e s , a n d s o f t w a r e d e v e l o p m e n t ."
    )

    repaired = repair_resume_text_spacing(broken)

    assert "Third-year Computer Science Engineering student" in repaired
    assert "strong foundations in programming" in repaired
    assert "data structures" in repaired
    assert "software development" in repaired


def test_parse_resume_repairs_character_spaced_section_content():
    text = """
S U M M A R Y
T h i r d - y e a r C o m p u t e r S c i e n c e E n g i n e e r i n g s t u d e n t w i t h s t r o n g f o u n d a t i o n s i n p r o g r a m m i n g .
S K I L L S
P y t h o n , F a s t A P I , S Q L
"""

    parsed = parse_resume(text)

    assert "Computer Science Engineering student" in parsed["summary"]
    assert parsed["skills"] == ["Python", "FastAPI", "SQL"]


def test_invalid_analysis_falls_back_to_grounded_issue():
    text = """
Summary
Flutter developer building mobile apps.
Projects
Worked on chatbot project
"""
    parsed = parse_resume(text)

    analysis = validate_resume_analysis({}, text, parsed)
    issues = [issue for section in analysis["sections"] for issue in section["issues"]]

    assert analysis["score"] > 0
    assert issues
    assert all(issue["original"] in text for issue in issues)
    assert all(issue["improved"] for issue in issues)
    assert any(issue["action_type"] == "manual" for issue in issues)


def test_apply_fix_replaces_exact_text_once():
    current = "Projects\nWorked on chatbot project\nSkills\nFlutter"
    issue = {
        "id": "abc123",
        "section": "projects",
        "original": "Worked on chatbot project",
        "improved": "Contributed to chatbot project.",
    }

    result = apply_fix(current, issue, [])

    assert result["applied"] is True
    assert "Worked on chatbot project" not in result["current_resume"]
    assert "Contributed to chatbot project" in result["current_resume"]
    assert result["applied_fixes"][0]["issue_id"] == "abc123"


def test_validate_analysis_converts_invented_metrics_to_manual_guidance():
    text = """
Projects
Worked on chatbot project
Skills
Python
"""
    payload = {
        "score": 70,
        "breakdown": {"impact": 50, "clarity": 70, "structure": 70, "ats": 70},
        "sections": [
            {
                "section": "projects",
                "issues": [
                    {
                        "original": "Worked on chatbot project",
                        "problem": "Missing impact.",
                        "improved": "Developed a chatbot that reduced support tickets by 35%.",
                        "action_type": "replace",
                        "severity": "high",
                        "category": "impact",
                    }
                ],
            }
        ],
        "summary_feedback": {"strengths": [], "weaknesses": [], "priority_fixes": []},
    }

    analysis = validate_resume_analysis(payload, text, parse_resume(text))
    issue = analysis["sections"][0]["issues"][0]

    assert issue["action_type"] == "manual"
    assert "35" not in issue["improved"]
    assert issue["evidence_needed"]


def test_apply_fix_refuses_manual_guidance():
    current = "Projects\nWorked on chatbot project"
    issue = {
        "id": "manual123",
        "section": "projects",
        "original": "Worked on chatbot project",
        "improved": "Manual edit needed: add verified scope and outcome.",
        "action_type": "manual",
    }

    result = apply_fix(current, issue, [])

    assert result["applied"] is False
    assert result["current_resume"] == current
    assert "verified details" in result["message"]
