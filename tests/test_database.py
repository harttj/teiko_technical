"""
Tests for database initialization and CSV loading utilities.

This module contains tests for the database module, verifying that
the SQLite database can be initialized and populated from CSV files.
"""


def test_placeholder():
    """Placeholder test to ensure pytest can find and run tests."""
    assert True


import csv
import sqlite3
from pathlib import Path

from utils import database


def test_init_db_creates_file_and_tables(tmp_path):
    db_file = tmp_path / "test_cell_counts.db"
    # Ensure parent dir exists
    database.init_db(db_file)
    assert db_file.exists()

    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cur.fetchall()}
    assert "metadata" in tables
    assert "samples" in tables
    conn.close()


def test__get_metadata_id_inserts_and_finds(tmp_path):
    # Use an in-memory DB to exercise _get_metadata_id directly
    conn = sqlite3.connect(":memory:")
    conn.executescript(database.SCHEMA_SQL)
    cur = conn.cursor()

    row = {"condition": "A", "age": "42", "sex": "M", "treatment": "T", "response": "R"}
    id1 = database._get_metadata_id(cur, "proj", "subj", row)
    assert isinstance(id1, int)

    # Calling again with same project/subject returns same id
    id2 = database._get_metadata_id(cur, "proj", "subj", row)
    assert id1 == id2

    # A different subject creates a new id
    id3 = database._get_metadata_id(cur, "proj", "subj2", row)
    assert id3 != id1

    conn.close()


def test_load_csv_to_sqlite_roundtrip(tmp_path):
    csv_file = tmp_path / "cells.csv"
    db_file = tmp_path / "out.db"

    headers = [
        "project",
        "subject",
        "condition",
        "age",
        "sex",
        "treatment",
        "response",
        "sample",
        "sample_type",
        "time_from_treatment_start",
        "b_cell",
        "cd8_t_cell",
        "cd4_t_cell",
        "nk_cell",
        "monocyte",
    ]

    rows = [
        [
            "P1",
            "S1",
            "C",
            "30",
            "F",
            "Tx",
            "Yes",
            "sample1",
            "typeA",
            "0",
            "10",
            "5",
            "3",
            "2",
            "1",
        ],
        [
            "P1",
            "S1",
            "C",
            "30",
            "F",
            "Tx",
            "Yes",
            "sample1",
            "typeA",
            "0",
            "10",
            "5",
            "3",
            "2",
            "1",
        ],  # duplicate sample -> ignored
        [
            "P2",
            "S2",
            "",
            "",
            "",
            "",
            "",
            "sample2",
            "typeB",
            "12",
            "7",
            "2",
            "1",
            "0",
            "4",
        ],
        [
            "",
            "",
            "bad",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ],  # malformed row skipped
    ]

    with csv_file.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)

    # Should not raise
    database.load_csv_to_sqlite(csv_file, db_file, replace_db=True)

    conn = sqlite3.connect(str(db_file))
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM metadata")
    (meta_count,) = cur.fetchone()
    assert meta_count == 2

    cur.execute("SELECT COUNT(*) FROM samples")
    (sample_count,) = cur.fetchone()
    # duplicate sample should be ignored, so two inserted
    assert sample_count == 2
    conn.close()


def test_load_csv_to_sqlite_missing_file(tmp_path):
    missing = tmp_path / "nope.csv"
    db_file = tmp_path / "out.db"
    try:
        database.load_csv_to_sqlite(missing, db_file)
        raised = False
    except FileNotFoundError:
        raised = True
    assert raised
