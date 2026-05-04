"""Cross-category portfolio construction: risk parity / mean-variance / HRP.

Layered architecture:
  Layer 1 (matrix → top-N categories per day):
      For each (axis1, axis2) cell, rank 6 categories by sharpe_min_vol;
      keep top-N.
  Layer 2 (cross-category weighting):
      Allocate among the top-N selected categories using:
        - equal weight (control)
        - risk parity (1/vol)
        - softmax of matrix score
        - mean-variance with shrinkage
  Layer 3 (intra-category):
      Within each chosen category, equal-weight / top-K / vol-parity.

Final defensive weight panel = Layer3_panels weighted by Layer2 alloc.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategy.categories import CATEGORIES


def top_n_categories_per_cell(score_df: pd.DataFrame, n: int = 2
                                 ) -> dict[tuple, list[str]]:
    """For each cell, return list of top-N categories by `score_df.score`.
    score_df has columns [a1, a2, category, score, ...].
    """
    out: dict[tuple, list[str]] = {}
    for (a1, a2), grp in score_df.groupby(["a1", "a2"]):
        valid = grp[grp["score"] > -np.inf]
        if valid.empty:
            continue
        top = valid.sort_values("score", ascending=False).head(n)
        out[(str(a1), str(a2))] = top["category"].tolist()
    return out


def daily_top_n_categories(a1: pd.Series, a2: pd.Series,
                              top_n_map: dict[tuple, list[str]],
                              default: list[str] | None = None,
                              ) -> pd.DataFrame:
    """For each day, lookup top-N categories from cell map.

    Returns DataFrame indexed by date with bool columns for each category.
    """
    cat_names = list(CATEGORIES.keys())
    out = pd.DataFrame(False, index=a1.index, columns=cat_names)
    if default is None:
        default = ["红利低波"]
    for dt in a1.index:
        v1 = a1.get(dt); v2 = a2.get(dt)
        if pd.isna(v1) or pd.isna(v2):
            top = default
        else:
            top = top_n_map.get((str(v1), str(v2)), default)
        for c in top:
            if c in out.columns:
                out.at[dt, c] = True
    return out


def cross_category_weights(category_returns: pd.DataFrame,
                              selected: pd.DataFrame,
                              method: str = "risk_parity",
                              vol_lookback: int = 60,
                              score_panel: pd.DataFrame | None = None,
                              shrink: float = 0.5,
                              ) -> pd.DataFrame:
    """Compute daily category-level weights given the per-day selection mask.

    Parameters
    ----------
    category_returns : DataFrame (date × cat) of category daily returns
    selected         : DataFrame (date × cat) of bool, True if category selected
    method           : 'equal' | 'risk_parity' | 'softmax' | 'mvo_shrunk'
    vol_lookback     : window for vol estimation
    score_panel      : DataFrame (date × cat) of matrix score per day (used for
                       softmax / mvo)
    shrink           : MVO covariance shrinkage parameter
    """
    if method == "equal":
        sel_int = selected.astype(float)
        s = sel_int.sum(axis=1).replace(0, np.nan)
        return sel_int.div(s, axis=0).fillna(0)

    if method == "risk_parity":
        cat_vol = category_returns.rolling(vol_lookback, min_periods=20).std()
        inv_vol = (1.0 / cat_vol.replace(0, np.nan)).fillna(0)
        inv_vol = inv_vol.where(selected, 0.0)
        s = inv_vol.sum(axis=1).replace(0, np.nan)
        return inv_vol.div(s, axis=0).fillna(0)

    if method == "softmax":
        if score_panel is None:
            raise ValueError("softmax requires score_panel")
        scores = score_panel.where(selected, -np.inf)
        # softmax with stability
        max_s = scores.max(axis=1)
        e = np.exp(scores.sub(max_s, axis=0))
        e = e.where(np.isfinite(e), 0)
        s = e.sum(axis=1).replace(0, np.nan)
        return e.div(s, axis=0).fillna(0)

    if method == "mvo_shrunk":
        # rolling MVO with shrinkage
        # w_t ∝ ((1-shrink) * diag(Σ) + shrink * Σ)^(-1) * μ
        # where Σ = trailing cov of selected categories, μ = score
        if score_panel is None:
            raise ValueError("mvo_shrunk requires score_panel")
        out = pd.DataFrame(0.0, index=selected.index, columns=selected.columns)
        cat_names = list(category_returns.columns)
        for i, dt in enumerate(selected.index):
            if i < vol_lookback:
                continue
            sel = selected.iloc[i].astype(bool)
            sel_cats = [c for c in cat_names if sel.get(c, False)]
            if len(sel_cats) <= 1:
                # single category: w=1
                for c in sel_cats:
                    out.at[dt, c] = 1.0
                continue
            window = category_returns.iloc[max(0, i - vol_lookback): i][sel_cats]
            window = window.dropna(how="all")
            if len(window) < 30:
                # fallback equal-weight
                for c in sel_cats:
                    out.at[dt, c] = 1.0 / len(sel_cats)
                continue
            cov = window.cov().values
            diag = np.diag(np.diag(cov))
            cov_shrunk = (1 - shrink) * diag + shrink * cov
            mu = np.array([float(score_panel.iloc[i].get(c, 0.0)) for c in sel_cats])
            try:
                w = np.linalg.solve(cov_shrunk, mu)
            except np.linalg.LinAlgError:
                w = np.ones(len(sel_cats)) / len(sel_cats)
            w = np.clip(w, 0.0, None)
            tot = w.sum()
            if tot <= 1e-12:
                w = np.ones(len(sel_cats)) / len(sel_cats)
            else:
                w = w / tot
            for j, c in enumerate(sel_cats):
                out.at[dt, c] = float(w[j])
        return out

    raise ValueError(method)


def expand_category_to_symbol_weights(cat_weights: pd.DataFrame,
                                          intra_panels: dict[str, pd.DataFrame],
                                          all_symbols: list[str],
                                          ) -> pd.DataFrame:
    """Multiply category weights by intra-category symbol panels.

    Returns DataFrame (date × symbol) of final defensive weights.
    """
    out = pd.DataFrame(0.0, index=cat_weights.index, columns=all_symbols)
    for cat in cat_weights.columns:
        if cat not in intra_panels:
            continue
        cat_w = cat_weights[cat]
        cat_panel = intra_panels[cat].reindex(index=cat_weights.index, columns=all_symbols, fill_value=0)
        out = out.add(cat_panel.mul(cat_w, axis=0), fill_value=0)
    return out


def build_score_panel(a1: pd.Series, a2: pd.Series,
                       score_df: pd.DataFrame) -> pd.DataFrame:
    """Build per-day per-category score panel from cell × category score table.

    Returns DataFrame (date × cat) with score for each category at each day's cell.
    """
    cat_names = sorted(score_df["category"].unique())
    out = pd.DataFrame(0.0, index=a1.index, columns=cat_names)
    cell_scores: dict[tuple, dict[str, float]] = {}
    for (v1, v2), grp in score_df.groupby(["a1", "a2"]):
        cell_scores[(str(v1), str(v2))] = dict(zip(grp["category"], grp["score"]))
    for dt in a1.index:
        v1 = a1.get(dt); v2 = a2.get(dt)
        if pd.isna(v1) or pd.isna(v2):
            continue
        sc = cell_scores.get((str(v1), str(v2)), {})
        for c, s in sc.items():
            if c in out.columns:
                out.at[dt, c] = s if np.isfinite(s) else 0.0
    return out
