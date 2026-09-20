"""Tiny node whose only job is the DB write - keeps compile_report_node a pure
function of state, and mirrors dedup.py's pattern of being the one place that
touches the DB for its concern. Only reached on the "new application" path, once a
report has actually been produced."""

from jobagent.db import save_application


def record_node(state):
    jd = state["jd"]
    save_application(jd.company, jd.title, state["report"])
    return {}
