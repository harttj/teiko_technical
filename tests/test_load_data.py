import importlib
import sqlite3
import sys
import types
from pathlib import Path

import pandas as pd

# Provide a lightweight fake `narwhals` module so importing utils.load_data won't fail
fake = types.ModuleType("narwhals")
fake.col = lambda *a, **k: None
sys.modules["narwhals"] = fake

from utils import database, load_data


def _make_db_with_data(db_path: Path):
    database.init_db(db_path)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # insert one metadata and one sample
    cur.execute(
        "INSERT INTO metadata (project, subject, condition, age, sex, treatment, response) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("P1", "S1", "C", 10, "F", "T", "Y"),
    )
    meta_id = cur.lastrowid
    cur.execute(
        "INSERT INTO samples (sample_code, metadata_id, sample_type, time_from_treatment_start, b_cell) VALUES (?, ?, ?, ?, ?)",
        ("sample1", meta_id, "typeA", 0, 42),
    )
    conn.commit()
    conn.close()


def test_get_data_with_query_override(tmp_path):
    db_file = tmp_path / "d.db"
    _make_db_with_data(db_file)

    df = load_data.get_data(query="SELECT sample_code FROM samples", db_path=db_file)
    assert isinstance(df, pd.DataFrame)
    assert "sample_code" in df.columns
    assert df.loc[0, "sample_code"] == "sample1"


def test_get_data_resolves_columns(tmp_path):
    db_file = tmp_path / "d2.db"
    _make_db_with_data(db_file)

    df = load_data.get_data(
        sample_cols="sample_code, b_cell", metadata_cols="project, age", db_path=db_file
    )
    # columns might be returned in either order depending on PRAGMA output; assert presence
    for col in ("sample_code", "b_cell", "project", "age"):
        assert col in df.columns


def test_get_data_raises_on_empty_params(tmp_path):
    db_file = tmp_path / "d3.db"
    _make_db_with_data(db_file)

    try:
        load_data.get_data(sample_cols="", metadata_cols="", db_path=db_file)
        raised = False
    except ValueError:
        raised = True
    assert raised
