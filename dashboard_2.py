from typing import List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, callback, dash_table, dcc, html
from scipy import stats

from rel_freq_table import POPULATION_COLS, SAMPLE_CODE_COL, get_rel_freq_table
from utils.load_data import get_data
from utils.plotting import PlotController

# Load data (same approach as original)
whole_df = get_data(sample_cols="*", metadata_cols="*")
rel_freq_df = get_rel_freq_table(whole_df)

rel_freq_df_subset = rel_freq_df[
    ["sample_code", "total_count", "population", "count", "percentage"]
]

# Instantiate controller with shared dataframe
controller = PlotController(rel_freq_df, population_cols=POPULATION_COLS)


app = Dash()


app.layout = [
    html.H2(children="Loblaw's Dashboard", style={"textAlign": "center"}),
    html.Div(
        [
            html.Div(
                [
                    html.H3(
                        "Summary of Relative Frequencies", style={"textAlign": "left"}
                    ),
                    dash_table.DataTable(
                        data=rel_freq_df_subset.to_dict("records"),
                        columns=[
                            {"name": i, "id": i} for i in rel_freq_df_subset.columns
                        ],
                        filter_action="native",
                        sort_action="native",
                        sort_mode="multi",
                        column_selectable="single",
                        row_selectable="multi",
                        page_action="native",
                        page_size=10,
                        style_table={"overflowX": "auto"},
                        style_cell={"textAlign": "left"},
                    ),
                ]
            ),
        ],
        style={"width": "80%", "margin": "auto"},
    ),
    html.Div(
        [
            html.Div(
                [
                    html.Label("Condition:"),
                    dcc.Dropdown(
                        id="condition-dropdown",
                        options=[
                            {"label": c, "value": c}
                            for c in sorted(rel_freq_df["condition"].dropna().unique())
                        ],
                        value=(
                            "melanoma"
                            if "melanoma" in rel_freq_df["condition"].dropna().unique()
                            else (
                                sorted(rel_freq_df["condition"].dropna().unique())[0]
                                if len(rel_freq_df["condition"].dropna().unique()) > 0
                                else None
                            )
                        ),
                        clearable=False,
                        style={"width": "14rem"},
                    ),
                ],
                style={"display": "inline-block", "marginRight": "1rem"},
            ),
            html.Div(
                [
                    html.Label("Treatment:"),
                    dcc.Dropdown(
                        id="treatment-dropdown",
                        options=[
                            {"label": t, "value": t}
                            for t in sorted(rel_freq_df["treatment"].dropna().unique())
                        ],
                        value=(
                            "miraclib"
                            if "miraclib" in rel_freq_df["treatment"].dropna().unique()
                            else (
                                sorted(rel_freq_df["treatment"].dropna().unique())[0]
                                if len(rel_freq_df["treatment"].dropna().unique()) > 0
                                else None
                            )
                        ),
                        clearable=False,
                        style={"width": "14rem"},
                    ),
                ],
                style={"display": "inline-block", "marginRight": "1rem"},
            ),
            html.Div(
                [
                    html.Label("Sample type:"),
                    dcc.Dropdown(
                        id="sampletype-dropdown",
                        options=[
                            {"label": s, "value": s}
                            for s in sorted(
                                rel_freq_df["sample_type"].dropna().unique()
                            )
                        ],
                        value=(
                            "PBMC"
                            if "PBMC" in rel_freq_df["sample_type"].dropna().unique()
                            else (
                                sorted(rel_freq_df["sample_type"].dropna().unique())[0]
                                if len(rel_freq_df["sample_type"].dropna().unique()) > 0
                                else None
                            )
                        ),
                        clearable=False,
                        style={"width": "14rem"},
                    ),
                ],
                style={"display": "inline-block"},
            ),
        ],
        style={"width": "80%", "margin": "1rem auto"},
    ),
    html.Div(
        [dcc.Graph(id="boxplot-allpop-graph")],
        style={"width": "80%", "margin": "1rem auto"},
    ),
    html.Div(
        [
            html.Label("Select population:"),
            dcc.Dropdown(
                id="population-dropdown",
                options=[
                    {"label": p, "value": p}
                    for p in (
                        POPULATION_COLS or sorted(rel_freq_df["population"].unique())
                    )
                ],
                value=(
                    "b_cell"
                    if "b_cell"
                    in (POPULATION_COLS or sorted(rel_freq_df["population"].unique()))
                    else (
                        POPULATION_COLS[0]
                        if POPULATION_COLS
                        else (
                            sorted(rel_freq_df["population"].unique())[0]
                            if len(rel_freq_df["population"].unique()) > 0
                            else None
                        )
                    )
                ),
                clearable=False,
                style={"width": "20rem"},
            ),
        ],
        style={"width": "80%", "margin": "1rem auto", "textAlign": "left"},
    ),
    html.Div(
        [dcc.Graph(id="boxplot-for-timepoints")],
        style={"width": "80%", "margin": "1rem auto"},
    ),
    html.Div(
        [
            # FIXME: Admittedly the time point doesn't change the stats this is probably a bug
            html.Label("Select timepoint :"),
            dcc.Dropdown(
                id="timepoint-dropdown",
                options=[
                    {"label": str(p), "value": p}  # value is numeric
                    for p in sorted(
                        rel_freq_df["time_from_treatment_start"].dropna().unique()
                    )
                ],
                value=0,  # default numeric value
                clearable=False,
                style={"width": "20rem"},
            ),
            html.Div(id="subset-analysis-note"),
        ],
        style={"width": "80%", "margin": "1rem auto", "textAlign": "left"},
    ),
]


@callback(
    Output("boxplot-allpop-graph", "figure"),
    Input("condition-dropdown", "value"),
    Input("treatment-dropdown", "value"),
    Input("sampletype-dropdown", "value"),
)
def update_allpop_plot(condition_value, treatment_value, sampletype_value):
    dff = controller.filter_df(None, condition_value, treatment_value, sampletype_value)
    if dff.empty:
        return px.box(title="No data for selected filters")

    pop_order = (
        controller.population_cols
        if controller.population_cols
        else [str(p) for p in sorted(dff["population"].unique())]
    )

    fig = controller.build_box_figure(
        dff,
        x_col="population",
        y_col="percentage",
        color_col="response" if "response" in dff.columns else None,
        title="",
        category_order=pop_order,
        show_points=False,
    )
    fig.update_layout(
        xaxis_title="Cell Population Type", yaxis_title="Relative Freq (%)"
    )
    fig.update_layout(
        title=(
            "<b>Relative Cell Frequencies in Responders vs Non-Responders</b><br>"
            "('t' value is from Welch's t-test, and 'd' value is Cohen's d for responders vs non-responders)"
        )
    )

    stats_df = controller.compute_stats(dff, group_col="population")
    if stats_df is not None:
        controller.annotate_ticks(
            fig, pop_order, stats_df, stats_group_col="population"
        )

    return fig


@callback(
    Output("boxplot-for-timepoints", "figure"),
    Input("population-dropdown", "value"),
    Input("condition-dropdown", "value"),
    Input("treatment-dropdown", "value"),
    Input("sampletype-dropdown", "value"),
)
def update_timepoint_box(
    population_value, condition_value, treatment_value, sampletype_value
):
    if population_value is None:
        return px.box(title="No population selected")

    dff = controller.filter_df(
        population_value, condition_value, treatment_value, sampletype_value
    )
    if dff.empty:
        return px.box(title=f"No data for population: {population_value}")

    dff = dff.copy()
    if "time_from_treatment_start" in dff.columns:
        dff["timepoint"] = dff["time_from_treatment_start"].astype(str)
        x_col = "timepoint"
        category_order = controller.determine_category_order(
            dff, x_col="timepoint", prefer_numeric=True
        )
    else:
        x_col = SAMPLE_CODE_COL if SAMPLE_CODE_COL else "sample_code"
        category_order = None

    fig = controller.build_box_figure(
        dff,
        x_col=x_col,
        y_col="percentage",
        color_col="response" if "response" in dff.columns else None,
        title="",
        category_order=category_order,
        show_points=False,
    )
    fig.update_layout(
        xaxis_title="Time from treatment start (in hours)",
        yaxis_title="Relative Freq (%)",
    )
    fig.update_layout(
        title=(
            f"<b>Relative {population_value} Frequencies in Responders vs Non-Responders Across Timepoints</b><br>"
            "('t' value is from Welch's t-test, and 'd' value is Cohen's d for responders vs non-responders)"
        )
    )

    stats_df = controller.compute_stats(dff, group_col=x_col)
    if stats_df is not None and category_order is not None:
        controller.annotate_ticks(fig, category_order, stats_df, stats_group_col=x_col)

    return fig


@callback(
    Output("subset-analysis-note", "children"),
    Input("timepoint-dropdown", "value"),
    Input("population-dropdown", "value"),
    Input("condition-dropdown", "value"),
    Input("treatment-dropdown", "value"),
    Input("sampletype-dropdown", "value"),
)
def update_subset_analysis_note(
    timepoint_value,
    population_value,
    condition_value,
    treatment_value,
    sampletype_value,
):
    dff = controller.filter_df(
        population_value, condition_value, treatment_value, sampletype_value
    ).copy()
    if dff.empty:
        return html.H5("No data for selected filters.")

    print(len(dff))
    print(
        dff["time_from_treatment_start"].value_counts(),
        dff["time_from_treatment_start"].dtypes,
    )

    dff_tp = dff[dff["time_from_treatment_start"] == timepoint_value].copy()
    print(timepoint_value, type(timepoint_value))
    print(
        dff_tp["time_from_treatment_start"].unique(),
        dff_tp["time_from_treatment_start"].dtypes,
    )
    print(len(dff_tp))

    # Build structured output: only the leading label is bold
    header = html.H1(
        [
            html.B("Subset Analysis: "),
            f"{population_value} — condition: {condition_value} | treatment: {treatment_value} | sample type: {sampletype_value} | timepoint: {timepoint_value}",
        ],
        style={"color": "#2C3E50"},
    )
    stats_lines = html.Div(
        [
            html.Span(
                [
                    html.B("Number of samples per project: "),
                    f"{dff_tp['project'].nunique()}",
                ]
            ),
            html.Br(),
            html.Span(
                [
                    html.B("Number of responder subjects: "),
                    f"{dff_tp[dff_tp['response'] == 'yes']['subject'].nunique()}",
                ]
            ),
            html.Br(),
            html.Span(
                [
                    html.B("Number of non-responder subjects: "),
                    f"{dff_tp[dff_tp['response'] == 'no']['subject'].nunique()}",
                ]
            ),
            html.Br(),
            html.Span(
                [
                    html.B("Number of male subjects: "),
                    f"{dff_tp[dff_tp['sex'] == 'M']['subject'].nunique()}",
                ]
            ),
            html.Br(),
            html.Span(
                [
                    html.B("Number of female subjects: "),
                    f"{dff_tp[dff_tp['sex'] == 'F']['subject'].nunique()}",
                ]
            ),
        ],
        style={"fontSize": "1.5rem", "color": "#34495E"},
    )

    return html.Div([header, stats_lines], style={"paddingTop": "0.25rem"})


if __name__ == "__main__":
    app.run(debug=True)
