"""Worker 2: static dedup gate, no LLM involved. Read-only - the write (saving this
application's own report) happens later, in record.py, only once a report actually
exists."""

from jobagent.db import find_duplicate


def dedup_node(state):
    jd = state["jd"]
    duplicate = find_duplicate(jd.company, jd.title)
    return {"is_new": duplicate is None, "duplicate": duplicate}
