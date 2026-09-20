"""
src/tools/recruitment_tools.py
Concrete typed tool implementations inheriting from BaseHRMSTool.
Includes ResumeParserTool, SkillGapAnalyzerTool, and ATSScorerTool.
"""
import re
from typing import Type
from pydantic import BaseModel, Field

from src.resume_lab import parse_resume
from src.tools.base_tool import BaseHRMSTool


# ── 1. Resume Parser Tool ────────────────────────────────────────────────────
class ResumeParserInput(BaseModel):
    resume_text: str = Field(description="Raw text content of the candidate's resume")


class ResumeParserOutput(BaseModel):
    skills: list[str] = Field(default_factory=list, description="Extracted skills")
    experience: list[str] = Field(default_factory=list, description="Extracted work experience entries")
    education: list[str] = Field(default_factory=list, description="Extracted education details")
    projects: list[str] = Field(default_factory=list, description="Extracted project summaries")
    summary: str = Field(default="", description="Candidate executive summary")


class ResumeParserTool(BaseHRMSTool):
    name: str = "ResumeParserTool"
    description: str = "Extracts structured sections (skills, work history, education, projects) from resume text."
    args_schema: Type[BaseModel] = ResumeParserInput
    return_schema: Type[BaseModel] = ResumeParserOutput

    def _run(self, resume_text: str) -> ResumeParserOutput:
        parsed = parse_resume(resume_text)
        skills = parsed.get("skills", [])
        experience = parsed.get("experience", [])
        education = parsed.get("education", [])
        projects = parsed.get("projects", [])
        summary = parsed.get("summary", "")

        # Fallback detection for unstructured or flat text resumes
        resume_lower = resume_text.lower()
        if not education:
            edu_matches = re.findall(r"(?:b\.?s\.?|bachelor|m\.?s\.?|master|ph\.?d|b\.?tech|degree|university|college)[^\n\.\,]+", resume_text, re.IGNORECASE)
            if edu_matches:
                education = [m.strip() for m in edu_matches[:3]]

        if not experience:
            exp_matches = re.findall(r"(?:\d+\+?\s+years?(?:\s+of)?\s+experience|engineer|developer|architect|lead)[^\n\.\,]+", resume_text, re.IGNORECASE)
            if exp_matches:
                experience = [m.strip() for m in exp_matches[:3]]

        return ResumeParserOutput(
            skills=skills,
            experience=experience,
            education=education,
            projects=projects,
            summary=summary,
        )


# ── 2. Skill Gap Analyzer Tool ────────────────────────────────────────────────
class SkillGapInput(BaseModel):
    required_skills: str = Field(description="Comma-separated or listed required skills from job posting")
    detected_skills: list[str] = Field(default_factory=list, description="List of detected skills from resume")
    resume_text: str = Field(default="", description="Full resume text for fallback lexical search")


class SkillGapOutput(BaseModel):
    matched_skills: list[str] = Field(default_factory=list, description="Required skills confirmed in candidate resume")
    missing_skills: list[str] = Field(default_factory=list, description="Required skills not detected in resume")
    match_percentage: float = Field(ge=0.0, le=100.0, description="Percentage of required skills fulfilled")


class SkillGapAnalyzerTool(BaseHRMSTool):
    name: str = "SkillGapAnalyzerTool"
    description: str = "Calculates exact skill match overlap, missing competencies, and fulfillment percentage."
    args_schema: Type[BaseModel] = SkillGapInput
    return_schema: Type[BaseModel] = SkillGapOutput

    def _run(self, required_skills: str, detected_skills: list[str], resume_text: str = "") -> SkillGapOutput:
        # Normalize required skills
        req_list = [s.strip().lower() for s in re.split(r"[,;\n]+", required_skills) if s.strip()]
        if not req_list:
            return SkillGapOutput(matched_skills=[], missing_skills=[], match_percentage=100.0)

        # Build candidate term set
        candidate_terms = {s.lower() for s in detected_skills}
        resume_lower = resume_text.lower()

        matched = []
        missing = []
        for req in req_list:
            if req in candidate_terms or (resume_lower and req in resume_lower):
                matched.append(req.title())
            else:
                missing.append(req.title())

        percentage = round((len(matched) / len(req_list)) * 100.0, 1)
        return SkillGapOutput(
            matched_skills=matched,
            missing_skills=missing,
            match_percentage=percentage,
        )


# ── 3. ATS Scorer Tool ────────────────────────────────────────────────────────
class ATSScorerInput(BaseModel):
    job_title: str = Field(description="Job title")
    required_skills: str = Field(description="Job required skills")
    experience_required: str = Field(default="", description="Target years or experience level")
    resume_text: str = Field(description="Candidate resume text")
    detected_skills: list[str] = Field(default_factory=list, description="Detected skills list")
    experience_items_count: int = Field(default=0, description="Number of detected work/project items")
    has_education: bool = Field(default=False, description="True if education is detected")


class ATSScorerOutput(BaseModel):
    fit_score: int = Field(ge=0, le=100, description="Overall ATS composite score")
    skill_score: int = Field(ge=0, le=45, description="Skills alignment component (max 45)")
    experience_score: int = Field(ge=0, le=25, description="Experience depth component (max 25)")
    education_score: int = Field(ge=0, le=10, description="Education component (max 10)")
    relevance_score: int = Field(ge=0, le=20, description="Title & domain relevance component (max 20)")
    recommendation: str = Field(description="Strongly Recommended | Recommended | Consider | Reject")


class ATSScorerTool(BaseHRMSTool):
    name: str = "ATSScorerTool"
    description: str = "Performs deterministic, rubric-weighted ATS scoring across skills, experience, education, and domain relevance."
    args_schema: Type[BaseModel] = ATSScorerInput
    return_schema: Type[BaseModel] = ATSScorerOutput

    def _run(
        self,
        job_title: str,
        required_skills: str,
        experience_required: str,
        resume_text: str,
        detected_skills: list[str],
        experience_items_count: int = 0,
        has_education: bool = False,
    ) -> ATSScorerOutput:
        req_list = [s.strip().lower() for s in re.split(r"[,;\n]+", required_skills) if s.strip()]
        resume_lower = resume_text.lower()
        candidate_terms = {s.lower() for s in detected_skills}

        matched_count = sum(1 for req in req_list if req in candidate_terms or req in resume_lower)
        skill_score = round((matched_count / len(req_list)) * 45) if req_list else 24
        
        has_exp_evidence = "year" in resume_lower or "experience" in resume_lower or experience_items_count > 0
        experience_score = min(25, max(15 if has_exp_evidence and experience_items_count == 0 else 0, experience_items_count * 5))
        education_score = 10 if (has_education or any(k in resume_lower for k in ["b.s.", "bachelor", "master", "degree", "university", "college"])) else 4

        # Title relevance
        title_terms = {w.lower() for w in re.findall(r"\b[a-zA-Z]{3,}\b", job_title)}
        title_overlap = sum(1 for w in title_terms if w in resume_lower)
        relevance_score = min(20, max(10 if title_overlap > 0 else 0, title_overlap * 5 + (5 if matched_count > 0 else 0)))

        composite = max(0, min(100, skill_score + experience_score + education_score + relevance_score))

        if composite >= 85:
            rec = "Strongly Recommended"
        elif composite >= 70:
            rec = "Recommended"
        elif composite >= 50:
            rec = "Consider"
        else:
            rec = "Reject"

        return ATSScorerOutput(
            fit_score=composite,
            skill_score=skill_score,
            experience_score=experience_score,
            education_score=education_score,
            relevance_score=relevance_score,
            recommendation=rec,
        )


# Export singleton tool instances
resume_parser_tool = ResumeParserTool()
skill_gap_tool = SkillGapAnalyzerTool()
ats_scorer_tool = ATSScorerTool()
