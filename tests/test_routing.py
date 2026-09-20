"""Pure routing-logic tests."""

from langgraph.graph import END
from langgraph.types import Send

from jobagent.routing import route_after_dedup, route_interview_to_workers, route_research_to_workers
from jobagent.schemas import InterviewAngle, InterviewPlan, ResearchAngle, ResearchPlan


def test_dedup_new_fans_out_to_fit_check_and_plan_research():
    assert route_after_dedup({"is_new": True}) == ["fit_check", "plan_research"]


def test_dedup_duplicate_ends_run():
    assert route_after_dedup({"is_new": False}) == END


def test_route_research_sends_one_worker_per_angle():
    plan = ResearchPlan(
        angles=[
            ResearchAngle(angle="funding", query="Acme funding"),
            ResearchAngle(angle="culture", query="Acme culture"),
        ]
    )
    sends = route_research_to_workers({"research_plan": plan})
    assert len(sends) == 2
    assert all(isinstance(s, Send) for s in sends)
    assert all(s.node == "research_worker" for s in sends)
    assert {s.arg["angle"].angle for s in sends} == {"funding", "culture"}


def test_route_research_handles_single_angle_plan():
    plan = ResearchPlan(angles=[ResearchAngle(angle="overview", query="Acme overview")])
    sends = route_research_to_workers({"research_plan": plan})
    assert len(sends) == 1


def test_route_interview_sends_one_worker_per_angle():
    plan = InterviewPlan(
        angles=[
            InterviewAngle(category="gap_probe", focus="Kubernetes gap"),
            InterviewAngle(category="company_fit", focus="recent funding round"),
        ]
    )
    sends = route_interview_to_workers({"interview_plan": plan})
    assert len(sends) == 2
    assert all(isinstance(s, Send) for s in sends)
    assert all(s.node == "interview_worker" for s in sends)
    assert {s.arg["angle"].category for s in sends} == {"gap_probe", "company_fit"}


def test_route_interview_handles_single_angle_plan():
    plan = InterviewPlan(angles=[InterviewAngle(category="technical_depth", focus="general fit")])
    sends = route_interview_to_workers({"interview_plan": plan})
    assert len(sends) == 1
