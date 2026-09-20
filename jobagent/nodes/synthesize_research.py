"""Fan-in: gathers whatever the workers found (accumulated in research_findings via
the operator.add reducer on GraphState) and merges it into the final CompanyResearch
shape the rest of the pipeline expects."""

from jobagent.llm import extract
from jobagent.schemas import CompanyResearch

SYSTEM = """Distill these separate research findings about a company into short, \
scannable key points for a job candidate deciding whether to apply and how to \
prepare - not a narrative summary. Each point is one short factual sentence (roughly \
25 words or fewer), not a paragraph cramming several facts together. Only include \
points that would actually change how a candidate thinks about the company or the \
interview - skip filler. Do not add facts beyond what the findings say; if a finding \
says information is unavailable, say so plainly rather than padding around it."""


def synthesize_research_node(state):
    findings = state.get("research_findings", [])
    if not findings:
        return {"company_research": None, "company_research_status": "failed: no findings"}

    findings_text = "\n\n".join(f"[{f.angle}]\n{f.finding}" for f in findings)
    try:
        research = extract(system=SYSTEM, user=findings_text, schema=CompanyResearch)
        return {"company_research": research, "company_research_status": "ok"}
    except Exception as e:
        return {"company_research": None, "company_research_status": f"failed: {e}"}
