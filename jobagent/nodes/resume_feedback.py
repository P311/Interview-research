"""Always runs (no fit-based gating). Merges what used to be two mutually-exclusive
nodes (resume_polish / gap_closing_rewrite) into one, since without branching there's
no clean way to pick between them - the model gives whatever mix of advice the
situation calls for, conditioned on fit_check's gap analysis already in state."""

from jobagent.llm import extract
from jobagent.schemas import ResumeFeedback

SYSTEM = """Give the candidate feedback on their resume for this specific job.

Always include light polish: ATS keyword alignment with the job description's exact \
terminology, phrasing/emphasis tweaks, reordering bullets to foreground the most \
relevant experience first.

You will be given a fixed, numbered list of gaps from a prior analysis. Address \
EXACTLY those gaps in gap_reframes - one entry per listed gap. Do not invent \
additional gaps beyond that list, and do not skip any of them, even if you'd have \
framed a gap differently yourself. For each: find what evidence already exists in \
the resume that's under-emphasized or mis-framed relative to that gap, propose a \
concrete reframe, and honestly assess whether it actually closes the gap \
(closes_gap) - don't force a fix that isn't real. If the gap list is empty, leave \
gap_reframes empty."""


def resume_feedback_node(state):
    jd = state["jd"]
    fit = state["fit"]
    gaps_list = (
        "\n".join(f"{i + 1}. {g.requirement} (severity: {g.severity})" for i, g in enumerate(fit.gaps))
        if fit.gaps
        else "(none)"
    )
    user = (
        f"Job description:\n{jd.model_dump_json(indent=2)}\n\n"
        f"Resume:\n{state['resume_md']}\n\n"
        f"Gaps to address (exactly these, one gap_reframes entry each):\n{gaps_list}\n\n"
        f"Full gap analysis for context:\n{fit.model_dump_json(indent=2)}"
    )
    result = extract(system=SYSTEM, user=user, schema=ResumeFeedback)
    return {"resume_feedback": result}
