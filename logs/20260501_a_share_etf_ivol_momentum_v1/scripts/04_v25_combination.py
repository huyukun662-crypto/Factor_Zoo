#!/usr/bin/env python3
"""Test inverted-IVOL m1 + V25 weekly ensemble (multiple weights).

V25 NAV from /tmp/v25_repo/results/nav_v25_vs_benchmark.csv.
Inverted-IVOL m1 reproduced from the parent backtest module.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path("/home/user/Factor_Zoo/logs/20260501_a_share_etf_ivol_momentum_v1/scripts")))
m = __import__("02_backtest_ivol_momentum")

ROOT = Path("/home/user/Factor_Zoo/logs/20260501_a_share_etf_ivol_momentum_v1")
V25_NAV = Path("/tmp/v25_repo/results/nav_v25_vs_benchmark.csv")
V7_PATH = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs/round8_equity_curves.csv")
OUT = ROOT / "outputs"

# Reproduce m1 (LS no gate, IVOL_resid_20d, monthly)
panel = m.load_panel()
rets = m.to_wide(panel, "ret")
bench = rets[m.BENCH]
fwd = m.fwd_ret(rets, m.PRIMARY_K)
sig = m.signal_ivol(rets, bench, m.BETA_W, m.IVOL_W, residualize=True, lag=0)
res = m.quintile_LS(sig, fwd)
ivol_ret = res["ls"].dropna()

# IVOL k=20 portfolio: convert to per-day equity, resample weekly Friday
ivol_eq = (1 + ivol_ret.fillna(0) / m.PRIMARY_K).cumprod()
ivol_wk = ivol_eq.resample("W-FRI").last().pct_change()

# Read V25 NAV
v25 = pd.read_csv(V25_NAV)
v25.columns = [c.lstrip("﻿") for c in v25.columns]
v25["date"] = pd.to_datetime(v25["date"])
v25 = v25.set_index("date").sort_index()
v25_wk_ret = v25["v25_nav"].pct_change()
csi_wk_ret = v25["csi_nav"].pct_change()

# V7_gold for comparison
v7 = pd.read_csv(V7_PATH).rename(columns={"trade_week": "date"})
v7["date"] = pd.to_datetime(v7["date"])
v7 = v7.set_index("date").sort_index()
v7_wk_ret = v7["V7_gold"].pct_change()

# Align all on V25's weekly index
all_df = pd.concat({
    "ivol": ivol_wk, "v25": v25_wk_ret, "v7": v7_wk_ret, "csi": csi_wk_ret
}, axis=1, sort=True).dropna()
print(f"weeks aligned: {len(all_df)} | range: {all_df.index.min().date()} -> {all_df.index.max().date()}")
print()


def wk_sharpe(s):
    s = s.dropna()
    if len(s) < 10 or s.std() == 0:
        return float("nan")
    return float(s.mean() / s.std() * np.sqrt(52))


def per_year_wk(s):
    return s.groupby(s.index.year).apply(wk_sharpe)


def stats(s, label):
    s = s.dropna()
    ar = s.mean() * 52
    vol = s.std() * np.sqrt(52)
    sh = ar / vol if vol > 0 else float("nan")
    eq = (1 + s).cumprod()
    dd = ((eq / eq.cummax()) - 1).min()
    return {"label": label, "ann_ret": ar, "vol": vol, "sharpe": sh, "max_dd": dd}


print("=== full-window correlation matrix (weekly returns) ===")
print(all_df.corr().round(3).to_string())
print()

# Ensembles with V25
weights_grid = [(0.5, 0.5), (0.3, 0.7), (0.7, 0.3), (0.2, 0.8), (0.4, 0.6)]
print(f"=== Inverted-IVOL m1 + V25 ensembles (full window {all_df.index.min().date()} - {all_df.index.max().date()}) ===")
print(f"V25 alone:      sharpe={wk_sharpe(all_df['v25']):.2f}  ann={all_df['v25'].mean()*52:+.1%}")
print(f"V7_gold alone:  sharpe={wk_sharpe(all_df['v7']):.2f}  ann={all_df['v7'].mean()*52:+.1%}")
print(f"Inv-IVOL alone: sharpe={wk_sharpe(all_df['ivol']):.2f}  ann={all_df['ivol'].mean()*52:+.1%}")
print(f"CSI all-share:  sharpe={wk_sharpe(all_df['csi']):.2f}  ann={all_df['csi'].mean()*52:+.1%}")
print()

result = {
    "n_weeks_aligned": len(all_df),
    "date_range": [str(all_df.index.min().date()), str(all_df.index.max().date())],
    "weekly_corr_matrix": all_df.corr().round(4).to_dict(),
    "standalone": {
        "v25":  {"sharpe_weekly": wk_sharpe(all_df["v25"])},
        "v7":   {"sharpe_weekly": wk_sharpe(all_df["v7"])},
        "ivol": {"sharpe_weekly": wk_sharpe(all_df["ivol"])},
        "csi":  {"sharpe_weekly": wk_sharpe(all_df["csi"])},
    },
    "ensembles": {},
}

print("=== weight grid: w_ivol × Inv-IVOL + (1-w) × V25 ===")
print("| w_ivol | sharpe | ann_ret | vol  | max_dd | worst_yr |")
print("|---:|---:|---:|---:|---:|---:|")
for w_ivol, w_v25 in weights_grid:
    combo = w_ivol * all_df["ivol"] + w_v25 * all_df["v25"]
    s = stats(combo, f"ivol{w_ivol}_v25{w_v25}")
    yr = per_year_wk(combo)
    result["ensembles"][f"ivol{w_ivol}_v25{w_v25}"] = {
        "sharpe": s["sharpe"], "ann_ret": s["ann_ret"], "vol": s["vol"],
        "max_dd": s["max_dd"], "per_year": yr.round(3).to_dict(),
        "worst_year": float(yr.min()) if not yr.empty else None,
    }
    print(f"| {w_ivol:.1f}    | {s['sharpe']:.2f} | {s['ann_ret']:+.1%} | {s['vol']:.1%} | {s['max_dd']:+.2%} | {yr.min():+.2f} |")

print()
print("=== per-year ===")
yr_table = pd.DataFrame({
    "v25": per_year_wk(all_df["v25"]),
    "v7": per_year_wk(all_df["v7"]),
    "ivol": per_year_wk(all_df["ivol"]),
    "5050_ivol_v25": per_year_wk(0.5 * all_df["ivol"] + 0.5 * all_df["v25"]),
    "3070_ivol_v25": per_year_wk(0.3 * all_df["ivol"] + 0.7 * all_df["v25"]),
    "5050_ivol_v7":  per_year_wk(0.5 * all_df["ivol"] + 0.5 * all_df["v7"]),
    "csi":  per_year_wk(all_df["csi"]),
}).round(2)
print(yr_table.to_string())

# Save
yr_table.to_csv(OUT / "v25_combo_per_year.csv")
with (OUT / "v25_combo_summary.json").open("w") as f:
    json.dump(result, f, indent=2, default=str)
print()
print(f"Saved: {OUT / 'v25_combo_summary.json'} and {OUT / 'v25_combo_per_year.csv'}")
