import argparse
from pathlib import Path

from jobagent.graph import build_graph


def main():
    parser = argparse.ArgumentParser(description="Analyze a job description against a resume.")
    parser.add_argument("--jd", required=True, type=Path, help="Path to a job description text file")
    parser.add_argument("--resume", required=True, type=Path, help="Path to a resume markdown file")
    parser.add_argument("--out", type=Path, default=None, help="Write the report to this file instead of stdout")
    args = parser.parse_args()

    jd_text = args.jd.read_text()
    resume_md = args.resume.read_text()

    app = build_graph()
    result = app.invoke({"jd_text": jd_text, "resume_md": resume_md})

    if not result.get("is_new", True):
        dup = result["duplicate"]
        print(f"Already processed {dup.company} - {dup.title} on {dup.created_at}. Re-showing that report:\n")
        print(dup.report or "(no report was saved for that run)")
        return

    report = result.get("report", "")
    if args.out:
        args.out.write_text(report)
        print(f"Report written to {args.out}")
    else:
        print(report)


if __name__ == "__main__":
    main()
