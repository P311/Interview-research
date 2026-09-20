"""Worker 2 (dedup) is a static, deterministic script - test it as one, no LLM involved."""

import sqlite3

import jobagent.db as db


def _use_tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "apps.db"))


def test_no_duplicate_when_db_empty(tmp_path, monkeypatch):
    _use_tmp_db(tmp_path, monkeypatch)
    assert db.find_duplicate("Acme", "Backend Engineer") is None


def test_saved_application_is_found_with_its_report(tmp_path, monkeypatch):
    _use_tmp_db(tmp_path, monkeypatch)
    db.save_application("Acme", "Backend Engineer", "the report text")

    dup = db.find_duplicate("Acme", "Backend Engineer")
    assert dup is not None
    assert dup.company == "Acme"
    assert dup.title == "Backend Engineer"
    assert dup.report == "the report text"


def test_minor_title_wording_is_still_caught(tmp_path, monkeypatch):
    """'Sr' vs 'Senior' scores ~90.5 with rapidfuzz.token_sort_ratio - just above
    DEDUP_FUZZY_THRESHOLD (90), so this one is caught."""
    _use_tmp_db(tmp_path, monkeypatch)
    db.save_application("Acme", "Sr Backend Engineer", "report v1")
    dup = db.find_duplicate("Acme", "Senior Backend Engineer")
    assert dup is not None
    assert dup.report == "report v1"


def test_different_seniority_is_a_different_role(tmp_path, monkeypatch):
    """Adding 'Senior' to a bare title is a real seniority change, not a wording
    variant (~82.1 similarity) - correctly not treated as a duplicate."""
    _use_tmp_db(tmp_path, monkeypatch)
    db.save_application("Acme", "Backend Engineer", "report")
    assert db.find_duplicate("Acme", "Senior Backend Engineer") is None


def test_different_company_is_not_a_duplicate(tmp_path, monkeypatch):
    _use_tmp_db(tmp_path, monkeypatch)
    db.save_application("Acme", "Backend Engineer", "report")
    assert db.find_duplicate("Globex", "Backend Engineer") is None


def test_known_limitation_company_suffix_not_caught(tmp_path, monkeypatch):
    """KNOWN GAP: 'Acme Robotics' vs 'Acme Robotics Inc' scores ~86.7 - just under
    the 90 threshold - so this currently comes back as *not* a duplicate. Documenting
    the actual behavior rather than asserting the (currently false) ideal."""
    _use_tmp_db(tmp_path, monkeypatch)
    db.save_application("Acme Robotics", "Backend Engineer", "report")
    assert db.find_duplicate("Acme Robotics Inc", "Backend Engineer") is None


def test_migrates_a_db_created_before_the_report_column_existed(tmp_path, monkeypatch):
    """The DB already on disk from earlier runs predates the `report` column -
    _connect() must add it in place without losing existing rows."""
    db_path = str(tmp_path / "old.db")
    monkeypatch.setattr(db, "DB_PATH", db_path)

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            company_norm TEXT NOT NULL,
            title_norm TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        "INSERT INTO applications (company, title, company_norm, title_norm) VALUES (?, ?, ?, ?)",
        ("Docebo", "Founding Forward Deployed Engineer", "docebo", "founding forward deployed engineer"),
    )
    conn.commit()
    conn.close()

    dup = db.find_duplicate("Docebo", "Founding Forward Deployed Engineer")
    assert dup is not None
    assert dup.report is None

    # and writes still work post-migration
    db.save_application("New Co", "New Role", "fresh report")
    assert db.find_duplicate("New Co", "New Role").report == "fresh report"
