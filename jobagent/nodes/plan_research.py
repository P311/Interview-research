"""The orchestrator. Given the company/role, plans a variable number (1-4) of
specific research angles - the count and content depend on the input, which is what
distinguishes this from a fixed-template search (that was the earlier design's gap:
it always ran the same query regardless of company)."""

from jobagent.llm import extract
from jobagent.schemas import ResearchAngle, ResearchPlan

SYSTEM = """Plan the company research needed for a candidate deciding whether to \
apply to this job and how to prepare for an interview. Decide which specific angles \
are actually worth investigating for THIS company and role - a well-known public \
company needs different angles (recent earnings, layoffs, why this specific team is \
hiring) than an obscure startup (what the company even does, founders' background, \
whether it's funded). Don't pad the list to hit a round number; 1-4 angles, only the \
ones that matter here. Each angle needs a concrete search query, not a vague topic."""

def plan_research_node(state):
    jd = state["jd"]
    user = f"Company: {jd.company}\nRole: {jd.title}\nLocation: {jd.location or 'unknown'}"
    try:
        plan = extract(system=SYSTEM, user=user, schema=ResearchPlan)
    except Exception:
        plan = ResearchPlan(
            angles=[ResearchAngle(angle="company overview", query=f"{jd.company} company overview news")]
        )
    return {"research_plan": plan}
