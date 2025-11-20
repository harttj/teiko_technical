import sqlite3
from pathlib import Path

import pandas as pd
from narwhals import col

from utils.database import DEFAULT_DB_PATH, METADATA_ID_COL


def _get_existing_cols(conn: sqlite3.Connection, table: str, columns: str) -> str:
    """Helper function to get existing columns from a table.
    Returns the column if it exists and prints the columns that were not found.

    :param conn: SQLite database connection.
    :param table: Name of the table to check.
    :param columns: Comma-separated string of column names to check.
    :return: The existing columns.
    """
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    cols_info = cursor.fetchall()
    table_cols = [c[1] for c in cols_info]

    # Map lowercase column names to their original forms for case-insensitive matching
    table_cols_map = {c.lower(): c for c in table_cols}

    cols_to_check = [c.strip() for c in columns.split(",") if c.strip()]
    existing = []
    missing = []

    for req in cols_to_check:
        key = req.lower()
        if key in table_cols_map:
            existing.append(table_cols_map[key])
        else:
            missing.append(req)

    if missing:
        print(
            f"Didn't find the following requested columns in table '{table}': {', '.join(missing)}"
        )

    return ", ".join(existing)


def get_data(
    sample_cols: str = "*",
    metadata_cols: str = "",
    db_path: Path = DEFAULT_DB_PATH,
    query: str = "",
) -> pd.DataFrame:
    """Retrieve data from the SQLite database based on the given parameters.
    The function constructs a query based on the sample_cols and metadata_cols.
    If both sample_cols and metadata_cols are provided, a JOIN will be performed on the samples
    and metadata tables using the metadata_id foreign key. Otherwise, if only one of them is provided,
    data will be retrieved from that table only.
    NOTE: If query is provided, it will be used directly and other parameters will be ignored.

    :param sample_cols: Comma-separated string of sample data columns to retrieve.
                        Use "*" to retrieve all columns. Or "" to skip sample data.
    :param metadata_cols: Comma-separated string of metadata columns to retrieve.
                          Use "*" to retrieve all columns. Or "" to skip metadata.
    :param db_path: Path to the SQLite database file. Defaults to DEFAULT_DB_PATH.
    :param query: Optional custom SQL query to execute. If provided, other parameters are ignored
    :return: DataFrame containing the requested sample data with metadata.
    """

    # Use custom query directly
    if query:
        with sqlite3.connect(db_path) as conn:
            return pd.read_sql_query(query, conn)

    # Validate input
    if not sample_cols and not metadata_cols:
        raise ValueError("Provide sample_cols or metadata_cols.")

    with sqlite3.connect(db_path) as conn:
        # Resolve column names if not wildcard or empty
        def resolve(cols: str, table: str):
            if not cols or cols == "*":
                return cols
            return _get_existing_cols(conn, table, cols)

        sample_cols = resolve(sample_cols, "samples")
        metadata_cols = resolve(metadata_cols, "metadata")

        # Build SELECT clause
        select_parts = [c for c in (sample_cols, metadata_cols) if c]
        select_sql = ", ".join(select_parts)

        # Build FROM/JOIN clause
        if sample_cols and metadata_cols:
            from_sql = (
                f"FROM samples "
                f"JOIN metadata ON samples.{METADATA_ID_COL} = metadata.id"
            )
        elif sample_cols:
            from_sql = "FROM samples"
        else:
            from_sql = "FROM metadata"

        query = f"SELECT {select_sql} {from_sql}"

        return pd.read_sql_query(query, conn)
