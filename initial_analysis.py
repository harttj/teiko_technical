import os
import sqlite3

import pandas as pd

from utils.load_data import get_data
from utils.path_constants import OUTPUT_DIR

SAMPLE_CODE_COL = "sample_code"


def get_rel_freq_table(save_path="", return_df=True) -> pd.DataFrame:
    """Get the relative frequency table of cell counts."""

    population_cols = ["b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte"]

    df = get_data(sample_cols=",".join([SAMPLE_CODE_COL] + population_cols))

    id_cols = [col for col in df.columns if col not in population_cols]

    df_long = df.reset_index().melt(
        id_vars=SAMPLE_CODE_COL,
        value_vars=population_cols,
        var_name="population",
        value_name="count",
    )

    # find the total count per sample and give it to total_counts
    total_counts = df_long.groupby(SAMPLE_CODE_COL)["count"].sum()
    df_long = df_long.merge(total_counts, on=SAMPLE_CODE_COL, suffixes=("", "_total"))
    df_long.rename(columns={"count_total": "total_count"}, inplace=True)
    df_long["percentage"] = df_long["count"] / df_long["total_count"] * 100

    # sort df_long by sample_code and then by population
    df_long = df_long.sort_values(by=[SAMPLE_CODE_COL, "population"])

    # sort columns according to the google form instructions
    df_long = df_long[
        [SAMPLE_CODE_COL, "total_count", "population", "count", "percentage"]
    ]

    if save_path:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        df_long.to_csv(save_path, index=False)

    if return_df:
        return df_long


if __name__ == "__main__":
    get_rel_freq_table(os.path.join(OUTPUT_DIR, "relative_frequency_table.csv"))
