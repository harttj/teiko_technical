import numpy as np
import pandas as pd
from scipy import stats


def compute_welch_bh(
    df: pd.DataFrame,
    group_col: str,
    value_col: str = "percentage",
    response_col: str = "response",
    responder_val: str = "yes",
) -> pd.DataFrame:
    """Compute Welch two-sample t-test (responder vs non-responder) per group and apply BH correction.

    Returns a DataFrame with columns: group, t_stat, p_value, p_adj, d
    """
    groups = []
    t_stats = []
    p_values = []
    ds = []

    unique_groups = list(df[group_col].dropna().unique())
    for g in unique_groups:
        sub = df[df[group_col] == g]
        grp1 = sub[sub[response_col] == "yes"][value_col].dropna().astype(float)
        grp2 = sub[sub[response_col] == "no"][value_col].dropna().astype(float)

        if len(grp1) < 2 or len(grp2) < 2:
            groups.append(g)
            t_stats.append(np.nan)
            p_values.append(np.nan)
            ds.append(np.nan)
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
        # Cohen's d for independent samples (use average of sample variances)
        try:
            n1 = len(grp1)
            n2 = len(grp2)
            m1 = float(np.mean(grp1))
            m2 = float(np.mean(grp2))
            s1 = float(np.std(grp1, ddof=1))
            s2 = float(np.std(grp2, ddof=1))
            denom = np.sqrt((s1**2 + s2**2) / 2.0)
            dval = (m1 - m2) / denom if denom > 0 else np.nan
        except Exception:
            dval = np.nan
        ds.append(float(dval) if not np.isnan(dval) else np.nan)

    # Benjamini-Hochberg across the available p-values (ignore NaNs)
    p_arr = np.array(p_values, dtype=float)
    m = np.sum(~np.isnan(p_arr))
    p_adj = np.array([np.nan] * len(p_arr))
    if m > 0:
        idx = np.where(~np.isnan(p_arr))[0]
        p_nonan = p_arr[idx]
        order = np.argsort(p_nonan)
        ranks = np.empty_like(order)
        ranks[order] = np.arange(1, len(p_nonan) + 1)
        adj = p_nonan * len(p_nonan) / ranks
        adj_sorted = np.minimum.accumulate(adj[::-1])[::-1]
        adj_sorted = np.clip(adj_sorted, 0, 1)
        p_adj_vals = adj_sorted
        p_adj[idx] = p_adj_vals

    res = pd.DataFrame(
        {
            group_col: unique_groups,
            "t_stat": t_stats,
            "p_value": p_values,
            "p_adj": p_adj,
            "d": ds,
        }
    )
    return res
