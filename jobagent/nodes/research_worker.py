"""A worker: runs once per angle in the orchestrator's plan (invoked via Send, so
however many angles were planned, that many parallel invocations of this node run).
Each is independent - one angle failing doesn't take down the others."""

from jobagent.llm import extract
from jobagent.schemas import ResearchFinding
from jobagent.search import search

SYSTEM = """Answer this one specific research question about a company, using ONLY \
the search results provided - do not add facts from prior knowledge you can't \
verify. If the results don't answer it, say so plainly rather than guessing."""


def research_worker_node(state):
    angle = state["angle"]
    try:
        results_text = search(angle.query)
        finding = extract(
            system=SYSTEM,
            user=f"Question: {angle.angle}\n\nSearch results:\n{results_text}",
            schema=ResearchFinding,
        )
    except Exception as e:
        finding = ResearchFinding(angle=angle.angle, finding=f"Unavailable: {e}", sources=[])
    return {"research_findings": [finding]}
