import os
import sqlite3

import pandas as pd

from utils.load_data import get_data
from utils.path_constants import OUTPUT_DIR

SAMPLE_CODE_COL = "sample_code"
POPULATION_COLS = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]


def get_rel_freq_table(
    population_cols: list[str] = POPULATION_COLS, sample_code_col: str = SAMPLE_CODE_COL
) -> pd.DataFrame:
    """Get the relative frequency table of cell counts."""

    id_cols = [col for col in df.columns if col not in population_cols]
    df_long = df.reset_index().melt(
        id_vars=id_cols,
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
    rel_freq_table = get_rel_freq_table()
    rel_freq_table.to_csv(save_path, index=False)
    print(f"Relative frequency table saved to {save_path}")
