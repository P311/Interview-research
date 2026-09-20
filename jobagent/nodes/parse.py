"""Worker 1: turn raw job description text into structured JSON."""

from jobagent.llm import extract
from jobagent.schemas import JobDescription

SYSTEM = (
    "You extract structured data from job descriptions. Be faithful to the source "
    "text; don't invent requirements, a seniority level, or a location that isn't "
    "stated or clearly implied."
)


def parse_node(state):
    jd = extract(
        system=SYSTEM,
        user=f"Extract the job description below into structured fields.\n\n{state['jd_text']}",
        schema=JobDescription,
    )
    return {"jd": jd}
