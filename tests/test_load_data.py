import sqlite3
import sys
import types
from pathlib import Path

import pandas as pd
import pytest

# Ensure `utils.load_data` can import even if `narwhals` isn't installed in the env
fake = types.ModuleType("narwhals")
fake.col = lambda *a, **k: None
sys.modules["narwhals"] = fake

from utils import database, load_data

# Helper to resolve the repo DB path
DB_PATH = database.DEFAULT_DB_PATH


def _skip_if_no_repo_db():
    if not DB_PATH.exists():
        pytest.skip(
            f"Repository DB not found at {DB_PATH}; skipping tests that require it."
        )

    # Ensure required tables exist
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('samples','metadata')"
    )
    found = {r[0] for r in cur.fetchall()}
    conn.close()
    if not ({"samples", "metadata"} <= found):
        pytest.skip(
            f"Repository DB at {DB_PATH} missing required tables; skipping tests."
        )


def test_repo_db_exists_or_skip():
    """Sanity check: either the DB exists or tests skip."""
    if not DB_PATH.exists():
        pytest.skip(f"Repository DB not found at {DB_PATH}")


def test_get_data_query_reads_repo_db():
    _skip_if_no_repo_db()
    df = load_data.get_data(
        query="SELECT COUNT(*) as cnt FROM samples", db_path=DB_PATH
    )
    assert isinstance(df, pd.DataFrame)
    assert "cnt" in df.columns
    # count should be a non-negative integer
    assert int(df.loc[0, "cnt"]) >= 0


def test_get_data_returns_expected_columns_from_repo_db():
    _skip_if_no_repo_db()
    # Request a small set of columns from both tables; this will perform a join
    df = load_data.get_data(
        sample_cols="sample_code, b_cell", metadata_cols="project", db_path=DB_PATH
    )
    for col in ("sample_code", "b_cell", "project"):
        assert col in df.columns


def test_get_data_raises_on_no_columns():
    _skip_if_no_repo_db()
    with pytest.raises(ValueError):
        load_data.get_data(sample_cols="", metadata_cols="", db_path=DB_PATH)
