#!/usr/bin/env python3
"""R7 feasibility: anchor_inv_ivol_ensemble_50_50_v1 x V25 ETF rotation.

Lightweight analysis (per user, plan partitioned-booping-hartmanis):
- Load existing ensemble daily PnL + V25 daily PnL (from cloned repo).
- Resample both to weekly Friday returns to match V25's weekly rebal cadence.
- Compute correlation matrix among legs.
- Weight-grid scan (ensemble vs V25 + three-way + vol-parity).
- Per-year Sharpe / max DD / worst-year-Sharpe.
- Emit r7_v25_feasibility.md + r7_v25_weight_grid.csv.
"""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path("/home/user/Factor_Zoo/logs/20260502_a_share_etf_anchor_high_v1")
OUT = ROOT / "outputs"
ENSEMBLE_PNL = Path(
    "/home/user/Factor_Zoo/factors/price_volume/"
    "anchor_inv_ivol_ensemble_50_50_v1/ensemble_pnl.csv"
)
V25_PNL = Path("/tmp/v25_repo/results/v25_daily_pnl.csv")
V25_NAV = Path("/tmp/v25_repo/results/nav_v25_vs_benchmark.csv")

ANN = 52  # annualization factor for weekly Sharpe


def load_ensemble_daily() -> pd.DataFrame:
    df = pd.read_csv(ENSEMBLE_PNL)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()
    return df[["anchor_excess", "ivol_excess_scaled", "blend_excess"]]


def load_v25_weekly() -> pd.Series:
    """V25 weekly NAV (published, matches Sharpe 1.85 full-sample 2019-2026).

    Note: v25_daily_pnl.csv has a different timing/scale and does not
    reconstruct the published Sharpe via simple daily->weekly summation.
    We therefore read the NAV file directly.
    """
    n = pd.read_csv(V25_NAV)
    n.columns = [c.lstrip("﻿") for c in n.columns]
    n["date"] = pd.to_datetime(n["date"])
    n = n.set_index("date").sort_index()
    return n["v25_nav"].pct_change().rename("v25")


def load_csi_weekly() -> pd.Series:
    n = pd.read_csv(V25_NAV)
    n.columns = [c.lstrip("﻿") for c in n.columns]
    n["date"] = pd.to_datetime(n["date"])
    return n.set_index("date").sort_index()["csi_nav"].pct_change().rename("csi")


def to_weekly(s_daily: pd.Series) -> pd.Series:
    """Weekly Friday return = sum of daily returns (small-return additive ok)."""
    return s_daily.resample("W-FRI").sum()


def sharpe(x: pd.Series) -> float:
    x = x.dropna()
    if len(x) < 4 or x.std() == 0:
        return float("nan")
    return float(x.mean() / x.std() * np.sqrt(ANN))


def max_dd(x: pd.Series) -> float:
    eq = (1 + x.fillna(0)).cumprod()
    peak = eq.cummax()
    return float((eq / peak - 1).min())


def per_year_sharpe(x: pd.Series) -> dict[int, float]:
    out = {}
    for y, g in x.dropna().groupby(x.index.year):
        out[int(y)] = sharpe(g)
    return out


def per_year_cum(x: pd.Series) -> dict[int, float]:
    out = {}
    for y, g in x.dropna().groupby(x.index.year):
        out[int(y)] = float((1 + g).prod() - 1)
    return out


def stats(x: pd.Series, label: str) -> dict:
    yrly = per_year_sharpe(x)
    complete = {y: s for y, s in yrly.items() if y < 2026}
    return {
        "label": label,
        "n_weeks": int(x.dropna().shape[0]),
        "ann_ret": float(x.mean() * ANN),
        "ann_vol": float(x.std() * np.sqrt(ANN)),
        "sharpe": sharpe(x),
        "max_dd": max_dd(x),
        "per_year_sharpe": yrly,
        "per_year_cum": per_year_cum(x),
        "worst_complete_year": min(complete.values()) if complete else float("nan"),
        "worst_complete_year_label": min(complete, key=complete.get) if complete else None,
    }


def main():
    print("loading...")
    ens = load_ensemble_daily()
    v25_w = load_v25_weekly()
    csi_w = load_csi_weekly()

    # --- weekly bars (Friday close == V25's native weekly grid)
    anchor_w = to_weekly(ens["anchor_excess"]).rename("anchor")
    ivol_w = to_weekly(ens["ivol_excess_scaled"]).rename("ivol_v2")
    blend_w = to_weekly(ens["blend_excess"]).rename("ensemble")

    df = pd.concat([anchor_w, ivol_w, blend_w, v25_w, csi_w], axis=1).dropna()
    # Restrict to 2020-onwards (ensemble starts 2020-01)
    df = df[df.index.year >= 2020]
    print(f"aligned weekly bars: {len(df)}  ({df.index.min().date()} -> {df.index.max().date()})")

    # --- correlation matrix
    corr = df.corr()
    print("\n=== weekly Pearson correlation ===")
    print(corr.round(3))

    # --- standalone stats
    rows = []
    for col in ["anchor", "ivol_v2", "ensemble", "v25", "csi"]:
        rows.append(stats(df[col], col))

    # --- two-way grid: ensemble x v25
    grid = []
    for w in np.round(np.arange(0.0, 1.01, 0.1), 2):
        blend = w * df["ensemble"] + (1 - w) * df["v25"]
        s = stats(blend, f"ens{w:.1f}_v25{1-w:.1f}")
        s["w_ensemble"] = float(w)
        s["w_v25"] = float(1 - w)
        s["mode"] = "two-way"
        grid.append(s)

    # --- three-way: anchor + ivol_v2 + v25, equal-weight + vol-parity
    three_way_eq = (df["anchor"] + df["ivol_v2"] + df["v25"]) / 3
    s = stats(three_way_eq, "three_way_equal")
    s.update({"mode": "three-way-equal", "w_ensemble": None, "w_v25": None})
    grid.append(s)

    # vol parity: weights inversely proportional to standalone vol
    vols = {c: df[c].std() for c in ["anchor", "ivol_v2", "v25"]}
    inv = {k: 1 / v for k, v in vols.items()}
    Z = sum(inv.values())
    w_vp = {k: v / Z for k, v in inv.items()}
    print(f"\nvol-parity weights: {w_vp}")
    vp = (
        w_vp["anchor"] * df["anchor"]
        + w_vp["ivol_v2"] * df["ivol_v2"]
        + w_vp["v25"] * df["v25"]
    )
    s = stats(vp, "three_way_volparity")
    s.update({
        "mode": "three-way-volparity",
        "w_anchor": w_vp["anchor"], "w_ivol_v2": w_vp["ivol_v2"], "w_v25": w_vp["v25"],
    })
    grid.append(s)

    # --- emit weight-grid CSV
    rows_csv = []
    for s in rows + grid:
        flat = {
            "label": s["label"],
            "mode": s.get("mode", "standalone"),
            "n_weeks": s["n_weeks"],
            "ann_ret": round(s["ann_ret"], 4),
            "ann_vol": round(s["ann_vol"], 4),
            "sharpe": round(s["sharpe"], 3),
            "max_dd": round(s["max_dd"], 4),
            "worst_year": round(s["worst_complete_year"], 3) if not np.isnan(s["worst_complete_year"]) else None,
            "worst_year_label": s["worst_complete_year_label"],
        }
        for y in [2020, 2021, 2022, 2023, 2024, 2025, 2026]:
            flat[f"sh_{y}"] = round(s["per_year_sharpe"].get(y, float("nan")), 3) if y in s["per_year_sharpe"] else None
            flat[f"cum_{y}"] = round(s["per_year_cum"].get(y, float("nan")), 4) if y in s["per_year_cum"] else None
        rows_csv.append(flat)

    grid_df = pd.DataFrame(rows_csv)
    grid_path = OUT / "r7_v25_weight_grid.csv"
    grid_df.to_csv(grid_path, index=False)
    print(f"\nwrote {grid_path}")

    # --- summary JSON for the report
    summary = {
        "n_weeks_aligned": len(df),
        "date_range": [str(df.index.min().date()), str(df.index.max().date())],
        "weekly_corr": corr.round(4).to_dict(),
        "vol_parity_weights": w_vp,
        "all_rows": rows_csv,
    }
    json_path = OUT / "r7_v25_summary.json"
    json_path.write_text(json.dumps(summary, indent=2, default=str))
    print(f"wrote {json_path}")

    # Print top-5 by Sharpe and by worst-year for quick eyeball
    df_grid = pd.DataFrame(rows_csv)
    print("\n=== top 5 by Sharpe ===")
    print(df_grid.sort_values("sharpe", ascending=False).head(5)[
        ["label", "sharpe", "max_dd", "worst_year", "ann_ret", "ann_vol"]
    ])
    print("\n=== top 5 by worst-year ===")
    print(df_grid.sort_values("worst_year", ascending=False).head(5)[
        ["label", "sharpe", "max_dd", "worst_year", "ann_ret", "ann_vol"]
    ])


if __name__ == "__main__":
    main()
