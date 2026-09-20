"""Position-value scoring + gap analysis, bundled into one call. Always runs
(no gating) - feeds resume_feedback and interview_prep, and its score/reasoning are
shown at the top of the final report."""

from jobagent.llm import extract
from jobagent.schemas import FitCheck

SYSTEM = """You evaluate how well a candidate's resume fits a job description.

Score fit 0-100, honestly and skeptically - do not inflate the score to be \
encouraging. Then list every specific gap between the resume and the job: for each, \
name the requirement, rate its severity (minor/moderate/major), and note what \
evidence (if any) exists in the resume that's relevant to it. Only leave the gaps \
list empty if the resume genuinely has no meaningful gap against this job.

Do not try to pre-judge whether a gap is fixable by rewriting - that's a separate, \
later step that does the actual work and can assess it properly. Just identify and \
rate the gaps here; explain your overall reasoning too, since a human will read it \
to decide whether the application is worth pursuing."""


def fit_check_node(state):
    jd = state["jd"]
    user = (
        f"Job description (structured):\n{jd.model_dump_json(indent=2)}\n\n"
        f"Resume (markdown):\n{state['resume_md']}"
    )
    # Low temperature: this is a classification/judgment call, and it's the single
    # highest-stakes field in the pipeline - determinism matters more here than the
    # diversity temperature would otherwise buy.
    fit = extract(system=SYSTEM, user=user, schema=FitCheck, temperature=0)
    return {"fit": fit}
