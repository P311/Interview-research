"""Public demo entrypoint (Streamlit Community Cloud). Not used by the CLI - see
jobagent/cli.py for that. Three things this file does that the CLI doesn't need to:
persistence is force-disabled (a shared public host must not accumulate strangers'
pasted resumes in a file on disk), runs are rate-limited per session (a public URL
means anyone can trigger real paid LLM + search calls on every click), and the result
is rendered with native widgets (tabs, metrics, expanders) instead of one long
markdown dump - it has the structured Pydantic state to work with, not just the
CLI's flattened report string, so it should look like it."""

import os
import time
from collections import Counter

import streamlit as st

# Must happen before any jobagent import - jobagent.config reads these at import time.
# st.secrets raises outright (not just an empty lookup) when no secrets.toml exists
# at all, which is the normal case for local runs that rely on .env instead - only
# Streamlit Cloud always has a (possibly empty) secrets store.
try:
    for key in ("JOBAGENT_LLM_API_KEY", "TAVILY_API_KEY"):
        if key in st.secrets:
            os.environ[key] = st.secrets[key]
except Exception:
    pass
os.environ["DISABLE_PERSISTENCE"] = "true"

from jobagent.graph import build_graph  # noqa: E402
from jobagent.nodes.compile_report import INTERVIEW_CATEGORY_LABELS  # noqa: E402

st.set_page_config(page_title="Job Application Agent", page_icon="\U0001f9ed")

COOLDOWN_SECONDS = 120


def render_gap_table(gaps):
    if not gaps:
        st.write("No gaps identified.")
        return
    st.dataframe(
        [
            {"Requirement": g.requirement, "Severity": g.severity, "Evidence in resume": g.evidence_in_resume or "—"}
            for g in gaps
        ],
        hide_index=True,
        width="stretch",
    )


def render_gap_reframes(items):
    if not items:
        st.write("No gaps to close.")
        return
    st.dataframe(
        [{"Gap": i.gap, "Closes it?": "Yes" if i.closes_gap else "No", "Confidence": i.confidence} for i in items],
        hide_index=True,
        width="stretch",
    )
    for item in items:
        with st.expander(item.gap):
            st.write(item.suggested_reframe)
            st.caption(f"Closes gap: {item.closes_gap} · Confidence: {item.confidence}")
            if item.existing_evidence:
                st.caption(f"Existing evidence: {item.existing_evidence}")


def render_company_research(research, status):
    if not research:
        st.info(f"Unavailable ({status}).")
        return
    for p in research.key_points:
        st.markdown(f"- {p}")
    if research.why_posted:
        st.write(f"**Why this role was posted:** {research.why_posted}")
    if research.recent_news:
        st.write("**Recent news:**")
        for n in research.recent_news:
            st.markdown(f"- {n}")
    if research.culture_notes:
        st.write(f"**Culture notes:** {research.culture_notes}")
    if research.sources:
        with st.expander("Sources"):
            for s in research.sources:
                st.markdown(f"- {s}")


def render_interview_prep(prep):
    if not prep:
        st.info("Unavailable.")
        return
    by_category = {}
    for q in prep.likely_questions:
        by_category.setdefault(q.category, []).append(q)
    for category, label in INTERVIEW_CATEGORY_LABELS.items():
        questions = by_category.get(category)
        if not questions:
            continue
        st.subheader(label)
        for q in questions:
            with st.expander(q.question):
                for tip in q.how_to_prepare:
                    st.markdown(f"- {tip}")
    if prep.general_prep_notes:
        st.divider()
        st.write(prep.general_prep_notes)


def render_result(result):
    jd = result["jd"]
    fit = result["fit"]

    st.header(f"{jd.title} at {jd.company}")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Fit score", f"{fit.fit_score}/100")
    with col2:
        if fit.gaps:
            counts = Counter(g.severity for g in fit.gaps)
            severity_summary = ", ".join(f"{counts[s]} {s}" for s in ("major", "moderate", "minor") if counts[s])
            st.metric("Gaps identified", len(fit.gaps), help=severity_summary)
        else:
            st.metric("Gaps identified", 0)
    st.write(fit.reasoning)

    tab_gaps, tab_resume, tab_research, tab_interview = st.tabs(
        ["Gaps", "Resume feedback", "Company research", "Interview prep"]
    )
    with tab_gaps:
        render_gap_table(fit.gaps)
    with tab_resume:
        feedback = result.get("resume_feedback")
        if feedback:
            render_gap_reframes(feedback.gap_reframes)
            st.divider()
            st.write(feedback.overall_recommendation)
        else:
            st.info("Unavailable.")
    with tab_research:
        render_company_research(result.get("company_research"), result.get("company_research_status", "unknown"))
    with tab_interview:
        render_interview_prep(result.get("interview_prep"))

    with st.expander("Raw markdown report"):
        # st.markdown treats a $...$ pair as inline LaTeX - escape literal dollar
        # signs (dollar amounts show up constantly in company research) so they
        # render as currency, not get parsed as math delimiters.
        st.markdown(result.get("report", "").replace("$", r"\$"))


st.title("Job Application Agent")
st.write(
    "Paste a job description and a resume. This runs a LangGraph "
    "orchestrator-workers pipeline - fit check, resume feedback, company research, "
    "and interview prep - and returns one report. Takes roughly 30-90 seconds "
    "(several LLM calls plus live web search)."
)

with st.expander("How this works"):
    st.write(
        "Two independent orchestrator-workers subgraphs, not a fixed pipeline: "
        "`plan_research` decides which company-research angles are worth "
        "investigating for this specific company (1-4, varying with the input) and "
        "fans them out to parallel workers; `plan_interview` does the same for "
        "interview-prep angles (1-6) based on the gaps found and the company "
        "research. See the README in this repository for the full architecture."
    )
    st.caption(
        "This demo runs with persistence disabled - nothing you paste here is "
        "stored - and is rate-limited to one run per session every "
        f"{COOLDOWN_SECONDS} seconds."
    )

col1, col2 = st.columns(2)
with col1:
    jd_text = st.text_area("Job description", height=320, placeholder="Paste the job description here...")
with col2:
    resume_md = st.text_area("Resume (markdown or plain text)", height=320, placeholder="Paste your resume here...")

run_clicked = st.button("Run", type="primary")

if run_clicked:
    last_run = st.session_state.get("last_run", 0.0)
    elapsed = time.time() - last_run
    if elapsed < COOLDOWN_SECONDS:
        st.warning(f"Rate-limited: try again in {int(COOLDOWN_SECONDS - elapsed)}s.")
    elif not jd_text.strip() or not resume_md.strip():
        st.warning("Paste both a job description and a resume first.")
    else:
        st.session_state["last_run"] = time.time()
        with st.spinner("Running the pipeline (fit check, research, interview prep)..."):
            try:
                st.session_state["result"] = build_graph().invoke({"jd_text": jd_text, "resume_md": resume_md})
            except Exception as e:
                st.session_state["result"] = None
                st.error(f"Something went wrong: {e}")

if st.session_state.get("result"):
    render_result(st.session_state["result"])
