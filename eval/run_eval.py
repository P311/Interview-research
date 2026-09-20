"""Evaluate fit_check's judgment against a small hand-labeled set of (JD, resume) pairs.

This is intentionally NOT a full-pipeline run. fit_check's fit_score is the number a
human actually reads to decide whether an application is worth pursuing, so a wrong
call there is invisible unless you check it against cases where you already know the
right answer. Everything downstream is comparatively low-stakes and much harder to
grade automatically, so it's out of scope here.

Usage:
    cp eval/cases.example.jsonl eval/cases.jsonl
    # edit cases.jsonl with real (JD, resume) pairs whose outcome you already know -
    # jobs you applied to and got/didn't get an interview, jobs you correctly skipped, etc.
    python eval/run_eval.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobagent.nodes.fit_check import fit_check_node
from jobagent.nodes.parse import parse_node

CASES_PATH = Path(__file__).parent / "cases.jsonl"
EXAMPLE_PATH = Path(__file__).parent / "cases.example.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"


def load_cases():
    if not CASES_PATH.exists():
        return []
    with open(CASES_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


def run():
    cases = load_cases()
    if not cases:
        print(f"No cases in {CASES_PATH}.")
        print(f"Copy {EXAMPLE_PATH} to {CASES_PATH} and fill in real (JD, resume, outcome) cases you already know the answer for.")
        return

    results = []
    correct = 0
    for case in cases:
        state = {"jd_text": case["jd_text"], "resume_md": case["resume_md"]}
        state.update(parse_node(state))
        state.update(fit_check_node(state))
        fit = state["fit"]

        expected = case["expected"]
        passed = expected["fit_score_min"] <= fit.fit_score <= expected["fit_score_max"]
        correct += passed

        results.append(
            {
                "id": case["id"],
                "predicted_fit_score": fit.fit_score,
                "predicted_gaps": [g.requirement for g in fit.gaps],
                "expected": expected,
                "passed": passed,
                "reasoning": fit.reasoning,
            }
        )
        status = "PASS" if passed else "FAIL"
        print(
            f"[{status}] {case['id']}: predicted score={fit.fit_score} "
            f"(expected {expected['fit_score_min']}-{expected['fit_score_max']}), "
            f"{len(fit.gaps)} gap(s) identified"
        )

    print(f"\n{correct}/{len(cases)} passed")

    RESULTS_DIR.mkdir(exist_ok=True)
    out_path = RESULTS_DIR / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"Results saved to {out_path}")


if __name__ == "__main__":
    run()
