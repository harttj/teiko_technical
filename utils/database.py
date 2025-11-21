"""Small utilities to initialize an SQLite database and load the
`data/cell-count.csv` file into it.

Schema design (simple, normalized):
- `metadata`: one row per subject (project+subject)
- `samples`: one row per sample with time and cell counts, FK -> metadata_id

Only `sample` is a globally unique identifier for measurements; the
`metadata` table keeps subject-level fields. By default we keep a
UNIQUE(project, subject) constraint to avoid accidental duplicated metadata
rows.
"""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Optional

METADATA_ID_COL = "metadata_id"
SCHEMA_SQL = f"""

BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS metadata (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	project TEXT NOT NULL,
	subject TEXT NOT NULL,
	condition TEXT,
	age INTEGER,
	sex TEXT,
	treatment TEXT,
	response TEXT,
	UNIQUE(project, subject)
);

CREATE TABLE IF NOT EXISTS samples (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	sample_code TEXT NOT NULL UNIQUE,
	{METADATA_ID_COL} INTEGER NOT NULL REFERENCES metadata(id),
	sample_type TEXT,
	time_from_treatment_start INTEGER,
	b_cell INTEGER,
	cd8_t_cell INTEGER,
	cd4_t_cell INTEGER,
	nk_cell INTEGER,
	monocyte INTEGER
);
COMMIT;
"""

DEFAULT_DB_PATH = Path("data/cell_counts.db")


def init_db(db_path: str | Path) -> None:
    """
    Create the database file and tables if they don't exist.

    :param db_path: Path to the SQLite database file.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


def _get_metadata_id(
    cursor: sqlite3.Cursor, project: str, subject: str, row: dict
) -> int:
    """
    Insert or lookup a metadata row and return its id.

    :param cursor: SQLite cursor object.
    :param project: The project name.
    :param subject: The subject identifier.
    :param row: A dictionary containing row data.
    :return: The metadata ID.
    """
    cursor.execute(
        "SELECT id FROM metadata WHERE project = ? AND subject = ?",
        (project, subject),
    )
    found = cursor.fetchone()
    if found:
        return found[0]

    # Insert new metadata using available fields from the CSV row
    def _safe_int(value: Optional[str]) -> Optional[int]:
        if value in (None, "", "na"):
            return None
        try:
            return int(value)
        except Exception:
            return None

    cursor.execute(
        """
		INSERT INTO metadata (project, subject, condition, age, sex, treatment, response)
		VALUES (?, ?, ?, ?, ?, ?, ?)
		""",
        (
            project,
            subject,
            row.get("condition") or None,
            _safe_int(row.get("age")),
            row.get("sex") or None,
            row.get("treatment") or None,
            row.get("response") or None,
        ),
    )
    last = cursor.lastrowid
    if last is None:
        raise RuntimeError("Failed to insert metadata row")
    return int(last)


def load_csv_to_sqlite(
    csv_path: str | Path,
    db_path: str | Path = DEFAULT_DB_PATH,
    replace_db: bool = False,
) -> None:
    """Load the CSV file into the SQLite database.

    :param csv_path: path to `cell-count.csv`.
    :param db_path: path to sqlite db file to create/use.
    :param replace_db: if True, remove existing DB and create fresh.
    """
    csv_path = Path(csv_path)
    db_path = Path(db_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    if replace_db and db_path.exists():
        db_path.unlink()

    init_db(db_path)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)

    # Insert within a single transaction for speed
    try:
        for row in rows:
            project = row.get("project")
            subject = row.get("subject")
            if not project or not subject:
                # skip malformed rows
                continue

            metadata_id = _get_metadata_id(cursor, project, subject, row)

            def _to_int_or_none(key: str) -> Optional[int]:
                v = row.get(key)
                if v in (None, ""):
                    return None
                try:
                    return int(v)
                except Exception:
                    return None

            cursor.execute(
                """
				INSERT OR IGNORE INTO samples
				(sample_code, metadata_id, sample_type, time_from_treatment_start, b_cell, cd8_t_cell, cd4_t_cell, nk_cell, monocyte)
				VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
				""",
                (
                    row.get("sample"),
                    metadata_id,
                    row.get("sample_type") or None,
                    _to_int_or_none("time_from_treatment_start"),
                    _to_int_or_none("b_cell"),
                    _to_int_or_none("cd8_t_cell"),
                    _to_int_or_none("cd4_t_cell"),
                    _to_int_or_none("nk_cell"),
                    _to_int_or_none("monocyte"),
                ),
            )

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load cell-count CSV into SQLite DB")
    parser.add_argument(
        "csv",
        nargs="?",
        help="path to cell-count.csv",
        default="data/cell-count.csv",
    )
    parser.add_argument(
        "db",
        nargs="?",
        help="path to sqlite db file to create",
        default=str(DEFAULT_DB_PATH),
    )
    parser.add_argument(
        "--replace", action="store_true", help="replace existing db", default=False
    )
    args = parser.parse_args()
    load_csv_to_sqlite(args.csv, args.db, replace_db=args.replace)
