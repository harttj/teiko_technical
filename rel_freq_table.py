"""
Script to calculate relative frequencies of cell populations.

This module contains functions to process raw cell count data and
compute the percentage of each cell type relative to the total count
per sample.
"""

import os
import sqlite3

import pandas as pd

from utils.load_data import get_data
from utils.path_constants import OUTPUT_DIR

SAMPLE_CODE_COL = "sample_code"
POPULATION_COLS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]


def get_rel_freq_table(
    df: pd.DataFrame,
    population_cols: list[str] = POPULATION_COLS,
    sample_code_col: str = SAMPLE_CODE_COL,
) -> pd.DataFrame:
    """
    Get the relative frequency table of cell counts.

    :param df: The input dataframe containing cell counts.
    :param population_cols: List of column names representing cell populations.
    :param sample_code_col: The column name for sample codes.
    :return: A DataFrame with relative frequencies.
    """
    # determine id columns (metadata + sample_code)
    id_cols = list(set([col for col in df.columns if col not in population_cols]))

    # make sure the sample_code_col is included in id_cols (needed for grouping later)
    if sample_code_col in df.columns and sample_code_col not in id_cols:
        id_cols.insert(0, sample_code_col)

    # Filter population_cols to those actually present in the dataframe
    population_cols = [c for c in population_cols if c in df.columns]

    # drop duplicate columns if any (keep first occurrence) to avoid key collisions
    temp_df = df.copy()
    # temp_df = temp_df.loc[:, ~temp_df.columns.duplicated()]

    df_long = pd.melt(
        temp_df,
        id_vars=[c for c in id_cols if c in temp_df.columns] or None,
        value_vars=population_cols,
        var_name="population",
        value_name="count",
    )

    # find the total count per sample and give it to total_counts
    total_counts = df_long.groupby(sample_code_col)["count"].sum()
    df_long = df_long.merge(total_counts, on=sample_code_col, suffixes=("", "_total"))
    df_long.rename(columns={"count_total": "total_count"}, inplace=True)
    df_long["percentage"] = df_long["count"] / df_long["total_count"] * 100

    # sort df_long by sample_code and then by population
    df_long = df_long.sort_values(by=[sample_code_col, "population"])

    return df_long


if __name__ == "__main__":
    save_path = os.path.join(OUTPUT_DIR, "relative_frequency_table.csv")

    sample_cols = ",".join([SAMPLE_CODE_COL] + POPULATION_COLS)
    df = get_data(sample_cols=sample_cols, metadata_cols="")
    rel_freq_table = get_rel_freq_table(df)
    rel_freq_table.to_csv(save_path, index=False)
    print(f"Relative frequency table saved to {save_path}")
