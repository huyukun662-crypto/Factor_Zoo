"""Macro matrix builder + IS-best category mapping discovery.

For multiple macro-axis combinations, find the IS-best CATEGORY per cell:

  Axis combinations explored:
    M1: PMI growth × CPI inflation (Merrill Lynch investment clock style)
    M2: cn_10y bucket × CPI inflation (interest rate × inflation)
    M3: us_real_rate sign × CPI inflation (US monetary cycle × inflation)
    M4: yield curve slope × CPI (10y-2y spread × inflation)
    M5: PMI × dxy_strong (growth × USD strength)

  Metric for selection: 'sharpe_min_vol' (excludes ann_vol < 2% to avoid cash auto-winning)
  Min observations per cell: 30

Outputs:
  report/outputs/macro_matrix_<axes>.csv : full table per axis combo
  report/outputs/macro_matrix_summary.csv: best mappings + cell counts

# [GUARDRAIL] All on IS (2013-2023).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from analysis.is_search import load_is_panels  # noqa: E402
from data.fetch_macro import fetch_all_macro  # noqa: E402
from strategy.categories import CATEGORIES, build_category_returns  # noqa: E402
from strategy.regime import build_regime_panel  # noqa: E402
from strategy.universe import BENCHMARK_SYMBOL  # noqa: E402

OUT = REPO_ROOT / "report" / "outputs"

ANN_FACTOR = np.sqrt(252)
MIN_OBS = 30
MIN_VOL = 0.02  # exclude annualized vol < 2% (cash filter)


def _bucket_cpi(s: pd.Series) -> pd.Series:
    return pd.cut(s, [-np.inf, 1.0, 3.0, np.inf],
                   labels=["low", "mid", "high"]).astype(str)


def _bucket_pmi(s: pd.Series) -> pd.Series:
    return pd.cut(s, [-np.inf, 49.0, 51.0, np.inf],
                   labels=["contract", "neutral", "expand"]).astype(str)


def _bucket_cn10y(s: pd.Series) -> pd.Series:
    return pd.cut(s, [-np.inf, 2.5, 3.5, np.inf],
                   labels=["low", "mid", "high"]).astype(str)


def _bucket_real_rate(s: pd.Series) -> pd.Series:
    return pd.Series(np.where(s.fillna(0) >= 0, "pos", "neg"), index=s.index)


def _bucket_spread(s: pd.Series) -> pd.Series:
    return pd.cut(s, [-np.inf, 0.0, 1.0, np.inf],
                   labels=["inverted", "flat", "steep"]).astype(str)


def _bucket_dxy_strong(s: pd.Series) -> pd.Series:
    return pd.Series(np.where(s.fillna(0).astype(int) == 1, "strong", "weak"),
                     index=s.index)


def per_cell_category_score(axis1: pd.Series, axis2: pd.Series,
                              category_returns: pd.DataFrame,
                              metric: str = "sharpe_min_vol",
                              ) -> pd.DataFrame:
    """For each (axis1 × axis2) cell × category, compute the metric.

    Returns long-form DataFrame with columns
      [a1, a2, category, n_days, ann_ret, ann_vol, sharpe, max_dd, score].
    """
    aligned = axis1.index.intersection(axis2.index).intersection(category_returns.index)
    a1 = axis1.loc[aligned]
    a2 = axis2.loc[aligned]
    cr = category_returns.loc[aligned]

    rows = []
    for v1 in sorted(a1.dropna().unique()):
        for v2 in sorted(a2.dropna().unique()):
            mask = (a1 == v1) & (a2 == v2)
            n = int(mask.sum())
            if n < MIN_OBS:
                continue
            sub = cr.loc[mask]
            for cat in sub.columns:
                s = sub[cat].dropna()
                if len(s) < MIN_OBS // 2:
                    continue
                mu = float(s.mean())
                sd = float(s.std())
                ann_ret = mu * 252
                ann_vol = sd * ANN_FACTOR
                sharpe = (ann_ret / ann_vol) if ann_vol > 0 else 0.0
                eq = (1 + s).cumprod()
                peak = eq.cummax()
                dd = (eq / peak - 1).min() if len(eq) else 0.0

                if metric == "sharpe":
                    score = sharpe
                elif metric == "sharpe_min_vol":
                    score = sharpe if ann_vol >= MIN_VOL else -np.inf
                elif metric == "annret":
                    score = ann_ret
                elif metric == "calmar":
                    score = ann_ret / abs(dd) if dd < 0 else 0.0
                elif metric == "sortino":
                    downside = float(s[s < 0].std()) if (s < 0).any() else 0.0
                    score = (ann_ret / (downside * ANN_FACTOR)) if downside > 0 else 0.0
                else:
                    raise ValueError(metric)
                rows.append({
                    "a1": str(v1), "a2": str(v2), "category": cat,
                    "n": int(len(s)), "ann_ret": ann_ret, "ann_vol": ann_vol,
                    "sharpe": sharpe, "max_dd": float(dd),
                    "score": float(score),
                })
    return pd.DataFrame(rows)


def best_category_per_cell(score_df: pd.DataFrame) -> dict[tuple, str]:
    """For each (a1, a2), return the category with max score."""
    out = {}
    for (a1, a2), sub in score_df.groupby(["a1", "a2"]):
        sub_valid = sub[sub["score"] > -np.inf]
        if sub_valid.empty:
            continue
        best = sub_valid.sort_values("score", ascending=False).iloc[0]
        out[(a1, a2)] = best["category"]
    return out


def main():
    panels = load_is_panels()
    macro = fetch_all_macro()
    bench = panels["close"][BENCHMARK_SYMBOL]
    regime_panel = build_regime_panel(bench, macro=macro, ma_window=200, vol_window=60)

    print("=== Setup ===")
    print(f"IS dates: {regime_panel.index.min().date()} .. {regime_panel.index.max().date()}, "
          f"{len(regime_panel)} days")
    print(f"Categories: {list(CATEGORIES.keys())}")

    # Category returns
    cat_ret = build_category_returns(panels["close"])
    print(f"Category returns shape: {cat_ret.shape}")
    print(f"Category daily-return availability (non-NaN days):")
    print(cat_ret.notna().sum().to_string())

    # Define axis variants
    cpi = regime_panel["cpi_yoy"]
    pmi = regime_panel["pmi"]
    cn10y = regime_panel.get("cn_10y")
    us_real = regime_panel.get("us_real_rate")
    spread = regime_panel.get("cn_10_2_spread")
    dxy_strong = regime_panel.get("dxy_strong")

    matrices = {
        "M1_PMI_x_CPI": ("PMI", _bucket_pmi(pmi), "CPI", _bucket_cpi(cpi)),
        "M2_cn10y_x_CPI": ("cn_10y", _bucket_cn10y(cn10y) if cn10y is not None else None,
                              "CPI", _bucket_cpi(cpi)),
        "M3_us_real_x_CPI": ("us_real_rate",
                                _bucket_real_rate(us_real) if us_real is not None else None,
                                "CPI", _bucket_cpi(cpi)),
        "M4_spread_x_CPI": ("cn_10_2_spread",
                              _bucket_spread(spread) if spread is not None else None,
                              "CPI", _bucket_cpi(cpi)),
        "M5_PMI_x_DXY": ("PMI", _bucket_pmi(pmi),
                            "DXY", _bucket_dxy_strong(dxy_strong) if dxy_strong is not None else None),
    }

    summary_rows = []

    for mname, (a1n, a1, a2n, a2) in matrices.items():
        print(f"\n=== {mname} ({a1n} × {a2n}) ===")
        if a1 is None or a2 is None:
            print("  axis missing, skipping")
            continue
        score_df = per_cell_category_score(a1, a2, cat_ret, metric="sharpe_min_vol")
        if score_df.empty:
            print("  no data, skipping")
            continue
        score_df["axis_pair"] = mname
        score_df.to_csv(OUT / f"macro_matrix_{mname}.csv", index=False)

        best_map = best_category_per_cell(score_df)
        # Pretty print mapping table
        print(f"  Cell -> Best category (by sharpe_min_vol):")
        # Pivot best map into a readable matrix
        rows = sorted(set(k[0] for k in best_map.keys()))
        cols = sorted(set(k[1] for k in best_map.keys()))
        print(f"    {a1n:<15s} | " + " | ".join(f"{c:^14s}" for c in cols))
        print(f"    {'-'*15} | " + " | ".join("-" * 14 for _ in cols))
        for r in rows:
            cells = []
            for c in cols:
                key = (r, c)
                if key in best_map:
                    sub = score_df[(score_df["a1"] == r) & (score_df["a2"] == c)]
                    n = int(sub["n"].iloc[0]) if not sub.empty else 0
                    cells.append(f"{best_map[key]:^10s}({n:3d})")
                else:
                    cells.append(f"{'(insuff)':^14s}")
            print(f"    {r:<15s} | " + " | ".join(f"{x:^14s}" for x in cells))

        # Show top 3 per cell for diagnostics
        print(f"\n  Top 3 categories per cell:")
        for (r, c), grp in score_df.groupby(["a1", "a2"]):
            top3 = grp.sort_values("score", ascending=False).head(3)
            top_str = ", ".join(f"{row['category']}({row['sharpe']:.2f})"
                                  for _, row in top3.iterrows())
            print(f"    {a1n}={r:<10s} {a2n}={c:<10s} n={int(grp['n'].iloc[0]):3d}  →  {top_str}")

        # Aggregate: how often each category is selected
        cat_counts = pd.Series([v for v in best_map.values()]).value_counts()
        for cat, cnt in cat_counts.items():
            summary_rows.append({"matrix": mname, "category": cat, "n_cells": cnt})

    pd.DataFrame(summary_rows).to_csv(OUT / "macro_matrix_summary.csv", index=False)
    print("\nDone. Per-matrix CSVs + summary saved.")


if __name__ == "__main__":
    main()
