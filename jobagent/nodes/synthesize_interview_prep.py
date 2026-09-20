"""Fan-in: gathers whatever interview_worker instances produced (accumulated in
interview_findings via the operator.add reducer on GraphState) and adds one overall
prep-notes summary on top."""

from jobagent.llm import extract
from jobagent.schemas import InterviewPrep, InterviewPrepNotes

SYSTEM = """Given this list of likely interview questions (already decided), write \
brief overall preparation notes: the 2-3 themes the candidate should be ready to \
speak to across all of them, and any general framing advice. Don't repeat the \
per-question preparation advice - synthesize across it instead."""


def synthesize_interview_prep_node(state):
    findings = state.get("interview_findings", [])
    if not findings:
        return {"interview_prep": None}

    findings_text = "\n\n".join(f"[{q.category}] {q.question}\n{q.how_to_prepare}" for q in findings)
    try:
        notes = extract(system=SYSTEM, user=findings_text, schema=InterviewPrepNotes)
        general_prep_notes = notes.general_prep_notes
    except Exception:
        general_prep_notes = "See the per-question preparation advice above."

    return {"interview_prep": InterviewPrep(likely_questions=findings, general_prep_notes=general_prep_notes)}
