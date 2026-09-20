import operator
from typing import Annotated, Optional, TypedDict

from jobagent.schemas import (
    CompanyResearch,
    DuplicateRecord,
    FitCheck,
    InterviewPlan,
    InterviewPrep,
    InterviewQuestion,
    JobDescription,
    ResearchFinding,
    ResearchPlan,
    ResumeFeedback,
)


class GraphState(TypedDict, total=False):
    jd_text: str
    resume_md: str

    jd: JobDescription
    is_new: bool
    duplicate: Optional[DuplicateRecord]

    fit: FitCheck
    resume_feedback: Optional[ResumeFeedback]

    research_plan: ResearchPlan
    # Each research_worker Send() contributes one finding - accumulate rather than overwrite.
    research_findings: Annotated[list[ResearchFinding], operator.add]
    company_research: Optional[CompanyResearch]
    company_research_status: str

    interview_plan: InterviewPlan
    # Each interview_worker Send() contributes 1-3 questions for its angle - accumulate.
    interview_findings: Annotated[list[InterviewQuestion], operator.add]
    interview_prep: Optional[InterviewPrep]

    report: Optional[str]
