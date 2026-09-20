"""Fan-in node: waits for both resume_feedback and interview_prep (which itself
waits on synthesize_research) and merges everything into one report."""

from collections import Counter

INTERVIEW_CATEGORY_LABELS = {
    "gap_probe": "Gap probes",
    "company_fit": "Company fit",
    "behavioral": "Behavioral",
    "technical_depth": "Technical depth",
    "closing": "Closing",
}


def compile_report_node(state):
    jd = state["jd"]
    fit = state["fit"]

    if fit.gaps:
        counts = Counter(g.severity for g in fit.gaps)
        severity_summary = ", ".join(f"{counts[s]} {s}" for s in ("major", "moderate", "minor") if counts[s])
        gap_line = f"**Gaps identified:** {len(fit.gaps)} ({severity_summary})"
    else:
        gap_line = "**Gaps identified:** none"

    lines = [
        f"# {jd.title} at {jd.company}",
        "",
        f"**Fit score:** {fit.fit_score}/100  ",
        gap_line,
        "",
        fit.reasoning,
        "",
    ]

    feedback = state.get("resume_feedback")
    if feedback:
        if feedback.gap_reframes:
            lines.append("## Closing the gap")
            lines.append("| Gap | Closes it? | Confidence |")
            lines.append("|---|---|---|")
            for item in feedback.gap_reframes:
                lines.append(f"| {item.gap} | {'Yes' if item.closes_gap else 'No'} | {item.confidence} |")
            lines.append("")
            for item in feedback.gap_reframes:
                lines.append(
                    f"- **{item.gap}**: {item.suggested_reframe}  "
                    f"_(closes gap: {item.closes_gap}, confidence: {item.confidence})_"
                )
            lines.append(f"\n{feedback.overall_recommendation}")
            lines.append("")

    research = state.get("company_research")
    if research:
        lines.append("## Company research")
        lines.extend(f"- {p}" for p in research.key_points)
        if research.why_posted:
            lines.append(f"\n**Why this role was posted:** {research.why_posted}")
        if research.recent_news:
            lines.append("\n**Recent news:**")
            lines.extend(f"- {n}" for n in research.recent_news)
        if research.culture_notes:
            lines.append(f"\n**Culture notes:** {research.culture_notes}")
        if research.sources:
            lines.append("\n**Sources:**")
            lines.extend(f"- {s}" for s in research.sources)
        lines.append("")
    else:
        status = state.get("company_research_status", "unknown")
        lines.append(f"## Company research\nUnavailable ({status}).\n")

    prep = state.get("interview_prep")
    if prep:
        lines.append("## Interview preparation")
        by_category = {}
        for q in prep.likely_questions:
            by_category.setdefault(q.category, []).append(q)
        for category, label in INTERVIEW_CATEGORY_LABELS.items():
            questions = by_category.get(category)
            if not questions:
                continue
            lines.append(f"### {label}")
            for q in questions:
                lines.append(f"- {q.question}")
                lines.extend(f"  - {tip}" for tip in q.how_to_prepare)
            lines.append("")
        lines.append(prep.general_prep_notes)

    return {"report": "\n".join(lines)}
