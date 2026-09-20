"""Fan-in: gathers whatever the workers found (accumulated in research_findings via
the operator.add reducer on GraphState) and merges it into the final CompanyResearch
shape the rest of the pipeline expects."""

from jobagent.llm import extract
from jobagent.schemas import CompanyResearch

SYSTEM = """Merge these separate research findings about a company into one coherent \
summary for a job candidate. Do not add facts beyond what the findings say. If a \
finding says information is unavailable, don't paper over it."""


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
