from langgraph.graph import END
from langgraph.types import Send


def route_after_dedup(state):
    if not state["is_new"]:
        return END
    return ["fit_check", "plan_research"]


def route_research_to_workers(state):
    """Fan out to one research_worker invocation per angle in the orchestrator's
    plan - the number of Send() calls varies per input, which is the mechanism that
    actually makes this orchestrator-workers rather than a fixed fan-out."""
    return [Send("research_worker", {"angle": angle}) for angle in state["research_plan"].angles]


def route_interview_to_workers(state):
    """Same mechanism as route_research_to_workers, for the interview-prep
    orchestrator: fan out to one interview_worker per angle plan_interview planned."""
    return [Send("interview_worker", {"angle": angle}) for angle in state["interview_plan"].angles]
