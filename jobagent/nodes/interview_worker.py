"""A worker: runs once per angle in plan_interview's plan (invoked via Send, so
however many angles were planned, that many parallel invocations of this node run).
Each is independent - one angle failing doesn't take down the others. The category on
every question is the angle's own category, assigned by the orchestrator and never
re-decided here - that's what keeps categorization consistent across workers.

Exactly one question per angle, deliberately - letting a single worker write up to 3
meant angle count and questions-per-angle multiplied together, and in practice that
ceiling (up to 6 angles x 3 questions) was routinely hit with near-duplicate coverage
of the same gap rather than genuinely distinct angles. One question per angle keeps
the total question count equal to the (already input-driven, bounded) angle count."""

from jobagent.llm import extract
from jobagent.schemas import InterviewQuestion, InterviewQuestionDraft

SYSTEM = """Write the single sharpest likely interview question for this one specific \
angle, plus 1-4 concrete preparation steps for it. Stay focused on this angle only -
other angles are handled by other passes.

Each preparation step is one short, specific, actionable item (something to look up, \
rehearse, or build) - not a paragraph. Do not cram multiple tips into one item; split \
them into separate list entries instead."""


def interview_worker_node(state):
    angle = state["angle"]
    try:
        draft = extract(
            system=SYSTEM,
            user=f"Category: {angle.category}\nFocus: {angle.focus}",
            schema=InterviewQuestionDraft,
        )
        question = InterviewQuestion(question=draft.question, category=angle.category, how_to_prepare=draft.how_to_prepare)
    except Exception as e:
        question = InterviewQuestion(
            question=f"(unavailable for this angle: {angle.focus})",
            category=angle.category,
            how_to_prepare=[f"Unavailable: {e}"],
        )
    return {"interview_findings": [question]}
