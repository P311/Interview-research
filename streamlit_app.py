"""Public demo entrypoint (Streamlit Community Cloud). Not used by the CLI - see
jobagent/cli.py for that. Two things this file does that the CLI doesn't need to:
persistence is force-disabled (a shared public host must not accumulate strangers'
pasted resumes in a file on disk), and runs are rate-limited per session (a public
URL means anyone can trigger real paid LLM + search calls on every click)."""

import os
import time

import streamlit as st

# Must happen before any jobagent import - jobagent.config reads these at import time.
for key in ("JOBAGENT_LLM_API_KEY", "TAVILY_API_KEY"):
    if key in st.secrets:
        os.environ[key] = st.secrets[key]
os.environ["DISABLE_PERSISTENCE"] = "true"

from jobagent.graph import build_graph  # noqa: E402

st.set_page_config(page_title="Job Application Agent", page_icon="\U0001f9ed")

COOLDOWN_SECONDS = 120

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
                result = build_graph().invoke({"jd_text": jd_text, "resume_md": resume_md})
                st.session_state["report"] = result.get("report", "No report was generated.")
            except Exception as e:
                st.session_state["report"] = None
                st.error(f"Something went wrong: {e}")

if st.session_state.get("report"):
    # st.markdown treats a $...$ pair as inline LaTeX - escape literal dollar signs
    # (dollar amounts show up constantly in the company-research section) so they
    # render as currency, not get parsed as math delimiters.
    st.markdown(st.session_state["report"].replace("$", r"\$"))
