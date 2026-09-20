"""Measure a node's run-to-run consistency on one fixed input.

fit_check used to also emit a "structural vs resume_fixable" gap_type label, which
turned out to flip categorically across identical runs even at temperature=0 - it
was removed from the schema entirely rather than patched further (see git history /
chat log: it no longer drove any control flow, and duplicated the more reliable
per-gap closes_gap judgment resume_feedback makes after actually attempting a
reframe). This script now measures fit_score's own spread instead, and generalizes
the same held-fixed-input methodology to resume_feedback, the other free-form
judgment node.

Upstream nodes are called ONCE and held fixed so the measurement isolates the node(s)
under test's own variance:
  - fit_check: parse held fixed.
  - resume_feedback: parse AND fit_check held fixed (fit_check's own variance is a
    separate, already-measured question - don't let it leak into this one).
  - interview_prep: parse, fit_check, and one research pass held fixed. This one
    re-runs a 3-node subgraph per trial (plan_interview -> interview_worker x N ->
    synthesize_interview_prep), not a single node - see check_interview_prep.

Usage:
    python eval/consistency_check.py --jd jd.txt --resume resume.md --node fit_check --n 8
    python eval/consistency_check.py --jd jd.txt --resume resume.md --node resume_feedback --n 5
    python eval/consistency_check.py --jd jd.txt --resume resume.md --node interview_prep --n 5
"""

import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobagent.nodes.fit_check import fit_check_node
from jobagent.nodes.interview_worker import interview_worker_node
from jobagent.nodes.parse import parse_node
from jobagent.nodes.plan_interview import plan_interview_node
from jobagent.nodes.plan_research import plan_research_node
from jobagent.nodes.research_worker import research_worker_node
from jobagent.nodes.resume_feedback import resume_feedback_node
from jobagent.nodes.synthesize_interview_prep import synthesize_interview_prep_node
from jobagent.nodes.synthesize_research import synthesize_research_node


def check_fit_check(state, n):
    scores, gap_counts = [], []
    for i in range(n):
        fit = fit_check_node(state)["fit"]
        scores.append(fit.fit_score)
        gap_counts.append(len(fit.gaps))
        print(f"  trial {i + 1:2d}: score={fit.fit_score:3d}  gaps={len(fit.gaps)}")

    print(f"\nfit_score: min={min(scores)} max={max(scores)} mean={statistics.mean(scores):.1f} stdev={statistics.pstdev(scores):.1f}")
    print(f"gap count: min={min(gap_counts)} max={max(gap_counts)} mean={statistics.mean(gap_counts):.1f}")


def check_resume_feedback(state, n):
    state.update(fit_check_node(state))
    fit = state["fit"]
    print(f"fit_check held fixed: score={fit.fit_score}, {len(fit.gaps)} gap(s)\n")

    for i in range(n):
        feedback = resume_feedback_node(state)["resume_feedback"]
        print(f"--- trial {i + 1} ---")
        print(f"  gap_reframes: {len(feedback.gap_reframes)}")
        for item in feedback.gap_reframes:
            print(f"    - closes_gap={item.closes_gap!s:5}  confidence={item.confidence:6}  gap={item.gap[:70]!r}")
        print(f"  overall_recommendation: {feedback.overall_recommendation[:150]!r}")
        print()


def check_interview_prep(state, n):
    state.update(fit_check_node(state))
    fit = state["fit"]

    # One real research pass, held fixed - company research is intentionally
    # variable by design (the orchestrator plans differently per company), so this
    # isolates interview prep's own variance rather than re-measuring that.
    state.update(plan_research_node(state))
    findings = []
    for angle in state["research_plan"].angles:
        findings.extend(research_worker_node({"angle": angle})["research_findings"])
    state["research_findings"] = findings
    state.update(synthesize_research_node(state))
    print(
        f"fit_check held fixed: score={fit.fit_score}, {len(fit.gaps)} gap(s)\n"
        f"company_research held fixed: {len(state['research_plan'].angles)} angle(s), "
        f"status={state.get('company_research_status')}\n"
    )

    # interview prep is now a 3-node orchestrator-workers subgraph (plan_interview ->
    # interview_worker x N -> synthesize_interview_prep) rather than one call, so each
    # trial re-runs all three, mirroring the graph's own control flow exactly.
    for i in range(n):
        trial_state = dict(state)
        trial_state.update(plan_interview_node(trial_state))
        plan = trial_state["interview_plan"]

        interview_findings = []
        for angle in plan.angles:
            interview_findings.extend(interview_worker_node({"angle": angle})["interview_findings"])
        trial_state["interview_findings"] = interview_findings
        trial_state.update(synthesize_interview_prep_node(trial_state))
        prep = trial_state["interview_prep"]

        angle_categories = [a.category for a in plan.angles]
        question_categories = [q.category for q in prep.likely_questions] if prep else []
        print(f"--- trial {i + 1} ---")
        print(f"  angles planned: {len(plan.angles)}  categories: {angle_categories}")
        print(f"  likely_questions: {len(prep.likely_questions) if prep else 0}  categories: {question_categories}")
        notes = prep.general_prep_notes[:150] if prep else "(none)"
        print(f"  general_prep_notes: {notes!r}")
        print()


NODE_CHECKS = {
    "fit_check": check_fit_check,
    "resume_feedback": check_resume_feedback,
    "interview_prep": check_interview_prep,
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Measure a node's consistency across repeated calls on one fixed input.")
    parser.add_argument("--jd", required=True, type=Path)
    parser.add_argument("--resume", required=True, type=Path)
    parser.add_argument("--node", choices=NODE_CHECKS.keys(), default="fit_check")
    parser.add_argument("--n", type=int, default=8)
    args = parser.parse_args()

    state = {"jd_text": args.jd.read_text(), "resume_md": args.resume.read_text()}
    state.update(parse_node(state))
    jd = state["jd"]
    print(f"Parsed once: {jd.company} - {jd.title} (held fixed across all {args.n} trials)\n")

    NODE_CHECKS[args.node](state, args.n)
