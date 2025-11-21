import numpy as np
import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, callback, dash_table, dcc, html
from scipy import stats

from rel_freq_table import POPULATION_COLS, SAMPLE_CODE_COL, get_rel_freq_table
from utils.load_data import get_data

whole_df = get_data(sample_cols="*", metadata_cols="*")
print(whole_df.head())

rel_freq_df = get_rel_freq_table(whole_df)

rel_freq_df_subset = rel_freq_df[
    ["sample_code", "total_count", "population", "count", "percentage"]
]


def compute_welch_bh(
    df, group_col, value_col="percentage", response_col="response", responder_val="yes"
):
    """Compute Welch two-sample t-test (responder vs non-responder) per group and apply BH correction.

    Returns a DataFrame with columns: group, t_stat, p_value, p_adj
    """
    groups = []
    t_stats = []
    p_values = []

    # get unique groups in order
    unique_groups = list(df[group_col].dropna().unique())
    for g in unique_groups:
        sub = df[df[group_col] == g]
        grp1 = sub[sub[response_col] == responder_val][value_col].dropna().astype(float)
        grp2 = sub[sub[response_col] != responder_val][value_col].dropna().astype(float)

        if len(grp1) < 2 or len(grp2) < 2:
            groups.append(g)
            t_stats.append(np.nan)
            p_values.append(np.nan)
            continue

        try:
            tstat, pval = stats.ttest_ind(
                grp1, grp2, equal_var=False, nan_policy="omit"
            )
        except Exception:
            tstat, pval = np.nan, np.nan

        groups.append(g)
        t_stats.append(float(tstat) if not np.isnan(tstat) else np.nan)
        p_values.append(float(pval) if not np.isnan(pval) else np.nan)

    # Benjamini-Hochberg across the available p-values (ignore NaNs)
    p_arr = np.array(p_values, dtype=float)
    m = np.sum(~np.isnan(p_arr))
    p_adj = np.array([np.nan] * len(p_arr))
    if m > 0:
        # BH procedure
        idx = np.where(~np.isnan(p_arr))[0]
        p_nonan = p_arr[idx]
        order = np.argsort(p_nonan)
        ranks = np.empty_like(order)
        ranks[order] = np.arange(1, len(p_nonan) + 1)
        # compute adjusted p-values
        adj = p_nonan * len(p_nonan) / ranks
        # enforce monotonicity
        adj_sorted = np.minimum.accumulate(adj[::-1])[::-1]
        adj_sorted = np.clip(adj_sorted, 0, 1)
        p_adj_vals = adj_sorted
        p_adj[idx] = p_adj_vals

    res = pd.DataFrame(
        {
            group_col: groups,
            "t_stat": t_stats,
            "p_value": p_values,
            "p_adj": p_adj,
        }
    )
    return res


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
                        # --- Interactive features ---
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
    # Top filters (metadata filters) - affect both plots
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
    # Top plot: boxplot across all populations (x-axis = population)
    html.Div(
        [dcc.Graph(id="boxplot-allpop-graph")],
        style={"width": "80%", "margin": "1rem auto"},
    ),
    # Population selector (placed between the two plots)
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
    # Bottom plot: boxplot for the selected single population
    html.Div(
        [dcc.Graph(id="boxplot-for-timepoints")],
        style={"width": "80%", "margin": "1rem auto"},
    ),
]


@callback(
    Output("boxplot-allpop-graph", "figure"),
    Input("condition-dropdown", "value"),
    Input("treatment-dropdown", "value"),
    Input("sampletype-dropdown", "value"),
)
def update_allpop_plot(condition_value, treatment_value, sampletype_value):
    """Top plot: show percentage distributions across all populations (x = population)."""
    dff = rel_freq_df
    if condition_value:
        dff = dff[dff["condition"] == condition_value]
    if treatment_value:
        dff = dff[dff["treatment"] == treatment_value]
    if sampletype_value:
        dff = dff[dff["sample_type"] == sampletype_value]

    if dff.empty:
        return px.box(title="No data for selected filters")

    # ensure population order: prefer POPULATION_COLS if available
    pop_order = (
        POPULATION_COLS if POPULATION_COLS else sorted(dff["population"].unique())
    )

    fig = px.box(
        dff,
        x="population",
        y="percentage",
        color="response" if "response" in dff.columns else None,
        category_orders={"population": pop_order},
        hover_data=[],
        title="Percentage distribution across populations",
    )
    fig.update_layout(xaxis_title="Population", yaxis_title="Relative Freq (%)")

    # compute welch t-tests per population and BH-correct across populations
    stats_df = None
    try:
        stats_df = compute_welch_bh(
            dff,
            group_col="population",
            value_col="percentage",
            response_col="response",
            responder_val="yes",
        )
    except Exception:
        stats_df = None

    if stats_df is not None:
        tickvals = pop_order
        labels = []
        stats_map = stats_df.set_index("population")
        for tv in tickvals:
            if tv in stats_map.index:
                row = stats_map.loc[tv]
                pval = row.get("p_value", np.nan)
                p_adj = row.get("p_adj", np.nan)
                tval = row.get("t_stat", np.nan)
                if np.isnan(p_adj):
                    label = f"{tv}<br>n/a"
                else:
                    label = f"{tv}<br>p={pval:.3g}, adj_p={p_adj:.6g}, t={tval:.2f}"
            else:
                label = f"{tv}<br>n/a"
            labels.append(label)
        fig.update_xaxes(tickmode="array", tickvals=tickvals, ticktext=labels)
        # prevent hover showing the x tick text (which contains p/t); show only y
        fig.update_traces(hovertemplate="%{y}<extra></extra>")

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
    """Update the boxplot (with points) for the selected population.

    x-axis will be timepoints (or sample_code fallback). For each x-tick we run
    a Welch t-test (responder vs non-responder) and BH-correct across ticks.
    The adjusted p-value and t-statistic are appended under each x-tick label.
    """
    if population_value is None:
        return px.box(title="No population selected")

    # filter by population and metadata filters
    dff = rel_freq_df[rel_freq_df["population"] == population_value]
    if condition_value:
        dff = dff[dff["condition"] == condition_value]
    if treatment_value:
        dff = dff[dff["treatment"] == treatment_value]
    if sampletype_value:
        dff = dff[dff["sample_type"] == sampletype_value]
    if dff.empty:
        return px.box(title=f"No data for population: {population_value}")

    dff = dff.copy()
    if "time_from_treatment_start" in dff.columns:
        dff["timepoint"] = dff["time_from_treatment_start"].astype(str)
        x_col = "timepoint"
        # try to preserve numeric order for timepoints
        try:
            time_order = sorted(
                dff["time_from_treatment_start"].dropna().unique(),
                key=lambda v: float(v),
            )
            category_order = [str(t) for t in time_order]
        except Exception:
            category_order = sorted(dff["timepoint"].unique())
    else:
        x_col = "sample_code"
        category_order = None

    # create boxplot without individual points
    fig = px.box(
        dff,
        x=x_col,
        y="percentage",
        color="response" if "response" in dff.columns else None,
        points=False,
        hover_data=[],
        title=f"Percentage distribution for {population_value}",
        category_orders={x_col: category_order} if category_order is not None else None,
    )
    fig.update_layout(
        xaxis_title="Time from treatment start (in hours)",
        yaxis_title="Relative Freq (%)",
    )

    # compute tests per x-tick and annotate x-tick labels
    stats_df = None
    try:
        stats_df = compute_welch_bh(
            dff,
            group_col=x_col,
            value_col="percentage",
            response_col="response",
            responder_val="yes",
        )
    except Exception:
        stats_df = None

    if stats_df is not None and category_order is not None:
        tickvals = category_order
        labels = []
        stats_map = (
            stats_df.set_index(x_col)
            if x_col in stats_df.columns
            else stats_df.set_index(stats_df.columns[0])
        )
        for tv in tickvals:
            if tv in stats_map.index:
                row = stats_map.loc[tv]
                pval = row.get("p_value", np.nan)
                p_adj = row.get("p_adj", np.nan)
                tval = row.get("t_stat", np.nan)
                if np.isnan(p_adj):
                    label = f"{tv}<br>n/a"
                else:
                    label = f"{tv}<br>p={pval:.3g}, adj_pval={p_adj:.3g}, t={tval:.2f}"
            else:
                label = f"{tv}<br>n/a"
            labels.append(label)
        fig.update_xaxes(tickmode="array", tickvals=tickvals, ticktext=labels)
        # prevent hover showing the x tick text (which contains p/t); show only y
        fig.update_traces(hovertemplate="%{y}<extra></extra>")

    return fig


if __name__ == "__main__":
    app.run(debug=True)
