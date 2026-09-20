"""The orchestrator for interview prep. Given the gap analysis and company research,
plans a variable number (1-6) of specific angles worth a dedicated question round -
more substantive gaps or richer company research means more angles, not a fixed
template. Each angle is assigned one of a fixed set of categories up front, so
categorization stays consistent across workers instead of being invented per-question
downstream (measured: free-text categories were a source of real inconsistency across
identical repeated runs)."""

from jobagent.llm import extract
from jobagent.schemas import InterviewAngle, InterviewPlan

SYSTEM = """Plan the interview-prep angles worth a dedicated question round for this \
candidate applying to this role.

Use the gap analysis and company research provided. Prioritize angles for the \
major/moderate gaps - each substantive gap usually deserves its own probing angle so \
the candidate can rehearse addressing it. Add a company_fit or behavioral angle only \
if the company research gives you something concrete to probe (a specific mission, \
recent news, stated values) - don't invent generic ones. Add a closing angle only if \
there's something specific worth asking the candidate to close with.

Don't pad the list to hit a round number; 1-6 angles, only the ones that matter for \
this candidate and this company. Each angle needs a category from the fixed set and a \
concrete focus (what specifically this angle should probe), not a vague topic."""


def plan_interview_node(state):
    fit = state["fit"]
    research = state.get("company_research")
    research_text = research.model_dump_json(indent=2) if research else "Not available."

    user = f"Gap analysis:\n{fit.model_dump_json(indent=2)}\n\nCompany research:\n{research_text}"
    try:
        plan = extract(system=SYSTEM, user=user, schema=InterviewPlan)
    except Exception:
        plan = InterviewPlan(angles=[InterviewAngle(category="technical_depth", focus="general fit for the role")])
    return {"interview_plan": plan}
