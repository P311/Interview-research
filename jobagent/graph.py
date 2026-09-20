from langgraph.graph import END, StateGraph

from jobagent.nodes.compile_report import compile_report_node
from jobagent.nodes.dedup import dedup_node
from jobagent.nodes.fit_check import fit_check_node
from jobagent.nodes.interview_worker import interview_worker_node
from jobagent.nodes.parse import parse_node
from jobagent.nodes.plan_interview import plan_interview_node
from jobagent.nodes.plan_research import plan_research_node
from jobagent.nodes.record import record_node
from jobagent.nodes.research_worker import research_worker_node
from jobagent.nodes.resume_feedback import resume_feedback_node
from jobagent.nodes.synthesize_interview_prep import synthesize_interview_prep_node
from jobagent.nodes.synthesize_research import synthesize_research_node
from jobagent.routing import route_after_dedup, route_interview_to_workers, route_research_to_workers
from jobagent.state import GraphState


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("parse", parse_node)
    graph.add_node("dedup", dedup_node)
    graph.add_node("fit_check", fit_check_node)
    graph.add_node("resume_feedback", resume_feedback_node)
    graph.add_node("plan_research", plan_research_node)
    graph.add_node("research_worker", research_worker_node)
    graph.add_node("synthesize_research", synthesize_research_node)
    graph.add_node("plan_interview", plan_interview_node)
    graph.add_node("interview_worker", interview_worker_node)
    graph.add_node("synthesize_interview_prep", synthesize_interview_prep_node)
    graph.add_node("compile_report", compile_report_node)
    graph.add_node("record", record_node)

    graph.set_entry_point("parse")
    graph.add_edge("parse", "dedup")
    graph.add_conditional_edges("dedup", route_after_dedup)

    # fit_check chain
    graph.add_edge("fit_check", "resume_feedback")

    # research chain (the orchestrator-workers pattern)
    graph.add_conditional_edges("plan_research", route_research_to_workers)
    graph.add_edge("research_worker", "synthesize_research")

    # interview-prep chain (a second, independent orchestrator-workers pattern):
    # plan_interview waits on both fit_check (gap context) and synthesize_research
    # (company context) via the same list-form barrier used below, then fans out to
    # one interview_worker per planned angle.
    graph.add_edge(["fit_check", "synthesize_research"], "plan_interview")
    graph.add_conditional_edges("plan_interview", route_interview_to_workers)
    graph.add_edge("interview_worker", "synthesize_interview_prep")

    # fan-in: passing a LIST of sources to one add_edge call creates a barrier that
    # waits for every listed source, regardless of how many hops each branch took to
    # get there. Two separate add_edge() calls into the same node do NOT do this -
    # each would fire the node independently as soon as its own source completes.
    graph.add_edge(["resume_feedback", "synthesize_interview_prep"], "compile_report")

    graph.add_edge("compile_report", "record")
    graph.add_edge("record", END)

    return graph.compile()
