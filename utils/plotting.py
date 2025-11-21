"""
Controller and helpers for generating dashboard visualizations.

This module contains the PlotController class, which encapsulates
logic for filtering data, determining sort orders, building Plotly
figures, and annotating plots with statistical results.
"""

from typing import List, Optional

import numpy as np
import pandas as pd
import plotly.express as px

from utils.stats import compute_welch_bh


class PlotController:
    """Encapsulates filtering, ordering, figure creation and stats annotation for the dashboard plots."""

    def __init__(
        self, df: pd.DataFrame, population_cols: Optional[List[str]] = None
    ) -> None:
        """
        Initialize the PlotController.

        :param df: The dataframe containing the data.
        :param population_cols: Optional list of population columns.
        """
        self._df = df.copy()
        self.population_cols = list(population_cols) if population_cols else None

    def filter_df(
        self,
        population: Optional[str],
        condition: Optional[str],
        treatment: Optional[str],
        sample_type: Optional[str],
    ) -> pd.DataFrame:
        """
        Filter the dataframe based on the provided criteria.

        :param population: The population to filter by.
        :param condition: The condition to filter by.
        :param treatment: The treatment to filter by.
        :param sample_type: The sample type to filter by.
        :return: A filtered DataFrame.
        """
        dff = self._df
        if population is not None:
            dff = dff[dff["population"] == population]
        if condition:
            dff = dff[dff["condition"] == condition]
        if treatment:
            dff = dff[dff["treatment"] == treatment]
        if sample_type:
            dff = dff[dff["sample_type"] == sample_type]
        return dff

    def determine_category_order(
        self, df: pd.DataFrame, x_col: str, prefer_numeric: bool = False
    ) -> Optional[List[str]]:
        """
        Determine the order of categories for the x-axis.

        :param df: The dataframe to determine order from.
        :param x_col: The column name for the x-axis.
        :param prefer_numeric: Whether to prefer numeric ordering.
        :return: A list of strings representing the category order, or None.
        """
        # If a numeric time column exists and numeric ordering is requested, attempt numeric sort
        if x_col == "timepoint" and "time_from_treatment_start" in df.columns:
            try:
                order = sorted(
                    df["time_from_treatment_start"].dropna().unique(),
                    key=lambda v: float(v),
                )
                return [str(t) for t in order]
            except Exception:
                pass

        if x_col in df.columns:
            unique_vals = df[x_col].dropna().unique()
            return [str(v) for v in sorted(unique_vals, key=lambda x: str(x))]

        return None

    def build_box_figure(
        self,
        df: pd.DataFrame,
        x_col: str,
        y_col: str = "percentage",
        color_col: Optional[str] = None,
        title: Optional[str] = None,
        category_order: Optional[List[str]] = None,
        show_points: bool = True,
    ):
        """
        Build a box plot figure.

        :param df: The dataframe containing the data.
        :param x_col: The column name for the x-axis.
        :param y_col: The column name for the y-axis.
        :param color_col: The column name for color grouping.
        :param title: The title of the plot.
        :param category_order: The order of categories.
        :param show_points: Whether to show individual data points.
        :return: A Plotly figure object.
        """
        color_arg = color_col if (color_col and color_col in df.columns) else None
        points_arg = "all" if show_points else False
        cat_orders = {x_col: category_order} if category_order is not None else None
        fig = px.box(
            df,
            x=x_col,
            y=y_col,
            color=color_arg,
            points=points_arg,
            hover_data=[],
            title=title,
            category_orders=cat_orders,
        )
        return fig

    def compute_stats(
        self,
        df: pd.DataFrame,
        group_col: str,
        value_col: str = "percentage",
        response_col: str = "response",
        responder_val: str = "yes",
    ) -> Optional[pd.DataFrame]:
        """
        Compute statistics for the data.

        :param df: The dataframe containing the data.
        :param group_col: The column to group by.
        :param value_col: The column containing values to analyze.
        :param response_col: The column containing response labels.
        :param responder_val: The value indicating a responder.
        :return: A DataFrame containing statistics, or None if computation fails.
        """
        if response_col not in df.columns:
            return None
        try:
            return compute_welch_bh(
                df,
                group_col=group_col,
                value_col=value_col,
                response_col=response_col,
                responder_val=responder_val,
            )
        except Exception:
            return None

    def annotate_ticks(
        self, fig, tickvals: List[str], stats_df: pd.DataFrame, stats_group_col: str
    ) -> None:
        """
        Annotate the x-axis ticks with statistics.

        :param fig: The Plotly figure to annotate.
        :param tickvals: The values for the x-axis ticks.
        :param stats_df: The dataframe containing statistics.
        :param stats_group_col: The column in stats_df matching the tick values.
        """
        if stats_df is None:
            return
        try:
            stats_map = stats_df.set_index(stats_group_col)
        except Exception:
            stats_map = stats_df.set_index(stats_df.columns[0])

        labels = []
        for tv in tickvals:
            if tv in stats_map.index:
                row = stats_map.loc[tv]
                pval = row.get("p_value", np.nan)
                p_adj = row.get("p_adj", np.nan)
                tval = row.get("t_stat", np.nan)
                dval = row.get("d", np.nan)
                if np.isnan(p_adj):
                    label = f"{tv}<br>n/a"
                else:
                    # include Cohen's d in the label alongside p, adjusted p, and t
                    label = f"{tv}<br>p={pval:.3g}, adj_p={p_adj:.3g}, t={tval:.2f}, d={dval:.2f}"
            else:
                label = f"{tv}<br>n/a"
            labels.append(label)

        fig.update_xaxes(tickmode="array", tickvals=tickvals, ticktext=labels)
        fig.update_traces(hovertemplate="%{y}<extra></extra>")
