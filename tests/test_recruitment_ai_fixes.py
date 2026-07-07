import pytest
from src.services.recruitment_ai import _skill_matches, _term_set, _normalize_ai_payload
from src.models import JobPosting

def test_skill_matches_filler_words():
    # Candidates possessing 'python' should match 'Experience with Python'
    resume_terms = _term_set("I have hands-on Python experience.")
    assert "python" in resume_terms
    assert _skill_matches("Experience with Python", resume_terms) is True
    assert _skill_matches("Strong understanding of Python", resume_terms) is True

def test_skill_matches_singular_plural():
    # Singular/plural mismatches (REST APIs vs REST API) should be matched
    resume_terms = _term_set("Worked with REST API design.")
    assert "api" in resume_terms
    assert _skill_matches("REST APIs", resume_terms) is True

def test_normalize_ai_payload_preserves_empty_lists():
    # If the AI successfully analyzed the candidate and found NO missing skills,
    # it should return an empty list [] instead of overriding it with the fallback matching.
    job = JobPosting(
        title="Software Engineer",
        description="Write Python code.",
        required_skills="Python, Django, SQL",
        department="Engineering",
        salary_range="100k-120k",
        experience_required="2 years"
    )
    
    # Payload has empty missing_skills
    payload = {
        "fit_score": 85,
        "recommendation": "Recommended",
        "summary": "Great match.",
        "strengths": ["Python expertise"],
        "weaknesses": ["None"],
        "missing_skills": [],  # Empty list: AI says 0 missing skills!
        "observations": ["Candidate has all skills"],
        "interview_prep": {
            "technical_questions": ["Q1"],
            "behavioral_questions": ["Q2"],
            "probing_areas": ["P1"]
        }
    }
    
    normalized = _normalize_ai_payload(payload, "Resume with Python and Django.", job, source="ai")
    
    # It must preserve the AI's empty list instead of falling back to the fallback's missing skills!
    assert normalized["missing_skills"] == []
    assert normalized["strengths"] == ["Python expertise"]
