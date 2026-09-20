from typing import Literal, Optional

from pydantic import BaseModel, Field


class JobDescription(BaseModel):
    company: str
    title: str
    seniority: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    salary_range: Optional[str] = None
    requirements: list[str] = Field(default_factory=list)
    nice_to_haves: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    summary: str


class DuplicateRecord(BaseModel):
    company: str
    title: str
    report: Optional[str] = None
    created_at: str


class Gap(BaseModel):
    requirement: str
    severity: Literal["minor", "moderate", "major"]
    evidence_in_resume: Optional[str] = None


class FitCheck(BaseModel):
    fit_score: int = Field(ge=0, le=100)
    # No blanket "structural vs resume_fixable" verdict: that field turned out to be
    # both the least reliable thing in the schema (measured: 50-88% agreement across
    # repeated identical calls) and redundant with the per-gap closes_gap judgment
    # resume_feedback makes after actually attempting a reframe - a real, evidenced
    # answer beats a premature holistic guess. fit_score + itemized gaps + reasoning
    # carry the same information without forcing a premature binary call.
    gaps: list[Gap] = Field(default_factory=list)
    reasoning: str


class ResumeTweak(BaseModel):
    section: str
    current: str
    suggested: str
    reason: str


class GapRewriteItem(BaseModel):
    gap: str
    existing_evidence: Optional[str] = None
    suggested_reframe: str
    closes_gap: bool
    confidence: Literal["low", "medium", "high"]
    reasoning: str


class ResumeFeedback(BaseModel):
    polish_tweaks: list[ResumeTweak] = Field(default_factory=list)
    gap_reframes: list[GapRewriteItem] = Field(default_factory=list)
    overall_recommendation: str


class ResearchAngle(BaseModel):
    angle: str
    query: str


class ResearchPlan(BaseModel):
    angles: list[ResearchAngle] = Field(min_length=1, max_length=4)


class ResearchFinding(BaseModel):
    angle: str
    finding: str
    sources: list[str] = Field(default_factory=list)


class CompanyResearch(BaseModel):
    summary: str
    why_posted: Optional[str] = None
    recent_news: list[str] = Field(default_factory=list)
    culture_notes: Optional[str] = None
    sources: list[str] = Field(default_factory=list)


# A fixed enum, not free text: the category label used to be invented fresh per
# question and came out differently worded every run even on identical input.
# Constraining it, and assigning it once per angle in plan_interview rather than
# per-question, is what keeps it stable.
InterviewCategory = Literal["gap_probe", "company_fit", "behavioral", "technical_depth", "closing"]


class InterviewAngle(BaseModel):
    category: InterviewCategory
    focus: str


class InterviewPlan(BaseModel):
    angles: list[InterviewAngle] = Field(min_length=1, max_length=6)


class InterviewQuestionDraft(BaseModel):
    question: str
    how_to_prepare: str


class InterviewQuestion(BaseModel):
    question: str
    category: InterviewCategory
    how_to_prepare: str


class InterviewPrepNotes(BaseModel):
    general_prep_notes: str


class InterviewPrep(BaseModel):
    likely_questions: list[InterviewQuestion]
    general_prep_notes: str
