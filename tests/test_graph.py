"""End-to-end graph wiring tests: every LLM call and the search call are mocked out,
so these check the *structure* of the pipeline (fan-out from dedup, the dynamic
Send-based orchestrator fan-out in the research chain, and the two fan-ins) - not
judgment quality or planning quality. Those belong in eval/, not here."""

from contextlib import ExitStack
from unittest.mock import patch

from jobagent.schemas import (
    CompanyResearch,
    DuplicateRecord,
    FitCheck,
    InterviewAngle,
    InterviewPlan,
    InterviewPrepNotes,
    InterviewQuestionDraft,
    JobDescription,
    ResearchAngle,
    ResearchFinding,
    ResearchPlan,
    ResumeFeedback,
)

FAKE_JD = JobDescription(company="Acme", title="Backend Engineer", summary="s")


def make_fake_extract(num_angles=2, num_interview_angles=1):
    def fake_extract(*, system, user, schema, max_tokens=8000, temperature=None):
        name = schema.__name__
        if name == "JobDescription":
            return FAKE_JD
        if name == "FitCheck":
            return FitCheck(fit_score=80, gaps=[], reasoning="r")
        if name == "ResumeFeedback":
            return ResumeFeedback(overall_recommendation="looks solid")
        if name == "ResearchPlan":
            angles = [ResearchAngle(angle=f"angle{i}", query=f"query{i}") for i in range(num_angles)]
            return ResearchPlan(angles=angles)
        if name == "ResearchFinding":
            return ResearchFinding(angle="a", finding="some finding")
        if name == "CompanyResearch":
            return CompanyResearch(key_points=["Acme is a widget company."])
        if name == "InterviewPlan":
            angles = [
                InterviewAngle(category="technical_depth", focus=f"focus{i}") for i in range(num_interview_angles)
            ]
            return InterviewPlan(angles=angles)
        if name == "InterviewQuestionDraft":
            return InterviewQuestionDraft(question="Q?", how_to_prepare=["prep"])
        if name == "InterviewPrepNotes":
            return InterviewPrepNotes(general_prep_notes="notes")
        raise AssertionError(f"unexpected schema in this test: {schema}")

    return fake_extract


def fake_search(query, max_results=5):
    return "some research notes"


EXISTING_DUPLICATE = DuplicateRecord(
    company="Acme", title="Backend Engineer", report="the old report", created_at="2026-01-01 00:00:00"
)


def run_pipeline(num_angles=2, num_interview_angles=1, is_new=True):
    fake_extract = make_fake_extract(num_angles, num_interview_angles)
    node_modules = [
        "jobagent.nodes.parse",
        "jobagent.nodes.fit_check",
        "jobagent.nodes.resume_feedback",
        "jobagent.nodes.plan_research",
        "jobagent.nodes.research_worker",
        "jobagent.nodes.synthesize_research",
        "jobagent.nodes.plan_interview",
        "jobagent.nodes.interview_worker",
        "jobagent.nodes.synthesize_interview_prep",
    ]
    with ExitStack() as stack:
        for module in node_modules:
            stack.enter_context(patch(f"{module}.extract", side_effect=fake_extract))
        stack.enter_context(patch("jobagent.nodes.research_worker.search", side_effect=fake_search))
        duplicate = None if is_new else EXISTING_DUPLICATE
        stack.enter_context(patch("jobagent.nodes.dedup.find_duplicate", return_value=duplicate))
        save_mock = stack.enter_context(patch("jobagent.nodes.record.save_application"))

        from jobagent.graph import build_graph

        result = build_graph().invoke({"jd_text": "jd", "resume_md": "resume"})
        return result, save_mock


def test_duplicate_stops_after_dedup_and_returns_the_old_report():
    result, save_mock = run_pipeline(is_new=False)
    assert result["is_new"] is False
    assert result["duplicate"].report == "the old report"
    assert "fit" not in result
    save_mock.assert_not_called()


def test_everything_runs_and_the_report_gets_recorded():
    result, save_mock = run_pipeline()
    assert result["resume_feedback"] is not None
    assert result["company_research"] is not None
    assert result["interview_prep"] is not None
    assert result["report"]
    save_mock.assert_called_once_with("Acme", "Backend Engineer", result["report"])


def test_research_fan_out_scales_with_the_plan_not_a_fixed_count():
    """The number of research_worker invocations should track the orchestrator's
    plan (dynamic), not a hardcoded fan-out width - this is the property that makes
    it orchestrator-workers rather than a fixed parallel split."""
    result_two, _ = run_pipeline(num_angles=2)
    result_four, _ = run_pipeline(num_angles=4)
    assert len(result_two["research_findings"]) == 2
    assert len(result_four["research_findings"]) == 4


def test_single_angle_plan_still_produces_a_report():
    result, _ = run_pipeline(num_angles=1)
    assert len(result["research_findings"]) == 1
    assert result["company_research"] is not None
    assert result["report"]


def test_interview_fan_out_scales_with_the_plan_not_a_fixed_count():
    """Same property as the research fan-out, for the interview-prep orchestrator:
    the number of interview_worker invocations tracks plan_interview's plan."""
    result_one, _ = run_pipeline(num_interview_angles=1)
    result_three, _ = run_pipeline(num_interview_angles=3)
    assert len(result_one["interview_findings"]) == 1
    assert len(result_three["interview_findings"]) == 3
    assert result_one["interview_prep"] is not None
    assert result_three["interview_prep"] is not None
    assert len(result_three["interview_prep"].likely_questions) == 3
