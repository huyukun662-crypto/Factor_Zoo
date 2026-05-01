#!/usr/bin/env python3
"""Test 50/50 weekly ensemble of inverted IVOL (m1) with V7_gold."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path("/home/user/Factor_Zoo/logs/20260501_a_share_etf_ivol_momentum_v1/scripts")))
m = __import__("02_backtest_ivol_momentum")

ROOT = Path("/home/user/Factor_Zoo/logs/20260501_a_share_etf_ivol_momentum_v1")
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

# IVOL k=20 monthly: convert to daily-equivalent equity curve, resample weekly
ivol_eq = (1 + ivol_ret.fillna(0) / m.PRIMARY_K).cumprod()
ivol_wk = ivol_eq.resample("W-FRI").last().pct_change()

v7 = pd.read_csv(V7_PATH).rename(columns={"trade_week": "date"})
v7["date"] = pd.to_datetime(v7["date"])
v7 = v7.set_index("date").sort_index()
v7_wk_ret = v7["V7_gold"].pct_change()

joined = pd.concat([ivol_wk.rename("ivol"), v7_wk_ret.rename("v7")], axis=1, sort=True).dropna()
print(f"weeks aligned: {len(joined)}, range: {joined.index.min().date()} -> {joined.index.max().date()}")
print(f"corr ivol vs v7_gold: {joined['ivol'].corr(joined['v7']):.4f}")
print()

def wk_sharpe(s):
    s = s.dropna()
    if len(s) < 10 or s.std() == 0: return float("nan")
    return float(s.mean() / s.std() * np.sqrt(52))

def per_year_wk(s):
    return s.groupby(s.index.year).apply(wk_sharpe)

# 50/50 combo
combo = 0.5 * joined["ivol"] + 0.5 * joined["v7"]

print(f"=== weekly Sharpe (full window {joined.index.min().date()} - {joined.index.max().date()}) ===")
print(f"V7_gold alone:     {wk_sharpe(joined['v7']):.2f}")
print(f"Inv-IVOL alone:    {wk_sharpe(joined['ivol']):.2f}")
print(f"50/50 ensemble:    {wk_sharpe(combo):.2f}")
print()

print("=== per-year ===")
yr = pd.DataFrame({
    "v7": per_year_wk(joined["v7"]),
    "ivol": per_year_wk(joined["ivol"]),
    "combo_5050": per_year_wk(combo),
}).round(2)
print(yr.to_string())

# Save
yr.to_csv(OUT / "v7_combo_per_year.csv")
result = {
    "n_weeks_aligned": len(joined),
    "weekly_corr_ivol_v7": float(joined["ivol"].corr(joined["v7"])),
    "v7_alone_sharpe_weekly": wk_sharpe(joined["v7"]),
    "ivol_alone_sharpe_weekly": wk_sharpe(joined["ivol"]),
    "combo_5050_sharpe_weekly": wk_sharpe(combo),
    "v7_alone_per_year": per_year_wk(joined["v7"]).round(3).to_dict(),
    "ivol_alone_per_year": per_year_wk(joined["ivol"]).round(3).to_dict(),
    "combo_5050_per_year": per_year_wk(combo).round(3).to_dict(),
}
with (OUT / "v7_combo_summary.json").open("w") as f:
    json.dump(result, f, indent=2, default=str)
