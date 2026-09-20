"""Static (non-LLM) dedup check + storage for the generated report, so a duplicate
hit can re-show what was produced last time instead of just saying "skipped"."""

import re
import sqlite3
from pathlib import Path
from typing import Optional

from rapidfuzz import fuzz

from jobagent.config import DB_PATH, DEDUP_FUZZY_THRESHOLD, DISABLE_PERSISTENCE
from jobagent.schemas import DuplicateRecord


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _connect() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            company_norm TEXT NOT NULL,
            title_norm TEXT NOT NULL,
            report TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    # Migrate DBs created before the `report` column existed.
    existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(applications)")}
    if "report" not in existing_columns:
        conn.execute("ALTER TABLE applications ADD COLUMN report TEXT")
    return conn


def find_duplicate(company: str, title: str) -> Optional[DuplicateRecord]:
    """Read-only: return the existing record (with its saved report, if any) if this
    (company, title) is a near-duplicate of one already processed, else None."""
    if DISABLE_PERSISTENCE:
        return None

    company_norm = _normalize(company)
    title_norm = _normalize(title)

    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT company, title, report, created_at, company_norm, title_norm FROM applications"
        ).fetchall()
        for existing_company, existing_title, report, created_at, existing_company_norm, existing_title_norm in rows:
            if (
                fuzz.token_sort_ratio(company_norm, existing_company_norm) >= DEDUP_FUZZY_THRESHOLD
                and fuzz.token_sort_ratio(title_norm, existing_title_norm) >= DEDUP_FUZZY_THRESHOLD
            ):
                return DuplicateRecord(company=existing_company, title=existing_title, report=report, created_at=created_at)
        return None
    finally:
        conn.close()


def save_application(company: str, title: str, report: str) -> None:
    """Record a fully-processed application, including its report, for future dedup hits."""
    if DISABLE_PERSISTENCE:
        return

    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO applications (company, title, company_norm, title_norm, report) VALUES (?, ?, ?, ?, ?)",
            (company, title, _normalize(company), _normalize(title), report),
        )
        conn.commit()
    finally:
        conn.close()
