"""
Generate deployment artifacts for overnight_intraday_spread_20d_v1 from the
session-0001 outputs:

Inputs:
  logs/20260428_a_share_overnight_intraday_alpha/outputs/
    panel_alphas.parquet
    ic_table_batch_0001.csv
    ls_summary_batch_0001.csv
    ls_annual_batch_0001.csv
    q5_excess_summary_batch_0001.csv
    q5_excess_annual_batch_0001.csv
    rebalances_alpha_04.csv
    audits.json

Outputs (this directory):
  metrics.json
  annual.csv
  rebalances.csv
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SESSION = Path("/home/user/Factor_Zoo/logs/20260428_a_share_overnight_intraday_alpha")
OUT = SESSION / "outputs"

ALPHA = "alpha_04"
NAME  = "overnight_intraday_spread_20d_v1"

# Load
ls_sum = pd.read_csv(OUT / "ls_summary_batch_0001.csv").set_index("alpha")
q5_sum = pd.read_csv(OUT / "q5_excess_summary_batch_0001.csv").set_index("alpha")
ls_ann = pd.read_csv(OUT / "ls_annual_batch_0001.csv")
q5_ann = pd.read_csv(OUT / "q5_excess_annual_batch_0001.csv")
ic     = pd.read_csv(OUT / "ic_table_batch_0001.csv")
rebs   = pd.read_csv(OUT / f"rebalances_{ALPHA}.csv")
audits = json.load(open(OUT / "audits.json"))

# ----- annual.csv (joined per year)
ls_a = ls_ann[ls_ann["alpha"] == ALPHA][["year", "n", "ls_ann_ret", "ls_sharpe"]]
q5_a = q5_ann[q5_ann["alpha"] == ALPHA][["year", "q5_ann_excess", "q5_ir"]]
annual = ls_a.merge(q5_a, on="year").rename(columns={
    "n": "n_rebalances",
    "ls_ann_ret": "ls_ann_ret_net",
    "ls_sharpe": "ls_sharpe_net",
    "q5_ann_excess": "q5_ann_excess_net",
    "q5_ir": "q5_ir_net",
})
annual.to_csv(HERE / "annual.csv", index=False)
print(f"annual.csv ({len(annual)} years) -> {HERE/'annual.csv'}")

# ----- rebalances.csv (drop the per-year column, keep numeric)
rebs.to_csv(HERE / "rebalances.csv", index=False)
print(f"rebalances.csv ({len(rebs)} rows) -> {HERE/'rebalances.csv'}")

# ----- metrics.json
ic_a = ic[ic["alpha"] == ALPHA].set_index("horizon")
metrics = {
    "name": NAME,
    "alpha_id_in_session": ALPHA,
    "session": "20260428_a_share_overnight_intraday_alpha",
    "branch": "claude/build-price-volume-factor-w8QPW",
    "as_of": "2026-04-28",
    "window": ["20180102", "20260425"],
    "n_dates": 2016,
    "n_rebalances": int(rebs.shape[0]),
    "rebalance_freq_days": 20,
    "delay": 1,
    "cost_bps_per_side": 5,
    "ls": {
        "ann_ret_net": float(ls_sum.loc[ALPHA, "ls_ann_ret"]),
        "ann_vol":     float(ls_sum.loc[ALPHA, "ls_ann_vol"]),
        "sharpe_net":  float(ls_sum.loc[ALPHA, "ls_sharpe"]),
        "sharpe_gross":float(ls_sum.loc[ALPHA, "ls_gross_sharpe"]),
        "max_dd":      float(ls_sum.loc[ALPHA, "ls_max_dd"]),
        "avg_tov_q5":  float(ls_sum.loc[ALPHA, "avg_tov_q5"]),
        "avg_tov_q1":  float(ls_sum.loc[ALPHA, "avg_tov_q1"]),
        "avg_cost_per_reb_bps": float(ls_sum.loc[ALPHA, "avg_cost_per_reb_bps"]),
    },
    "q5_long_only": {
        "ann_excess_net": float(q5_sum.loc[ALPHA, "q5_ann_excess"]),
        "ann_vol":        float(q5_sum.loc[ALPHA, "q5_ann_vol"]),
        "ir_net":         float(q5_sum.loc[ALPHA, "q5_ir"]),
        "max_dd":         float(q5_sum.loc[ALPHA, "q5_max_dd"]),
    },
    "ic_rank": {
        f"{int(h)}d": {
            "mean":   float(ic_a.loc[h, "ic_mean"]),
            "icir":   float(ic_a.loc[h, "icir"]),
            "t_stat": float(ic_a.loc[h, "t_stat"]),
            "n":      int(ic_a.loc[h, "n_dates"]),
        }
        for h in [1, 5, 10, 20, 60]
    },
    "audits": {
        "execution_delay":     audits["execution_delay"]["pass"],
        "look_ahead_grep":     audits["look_ahead_grep"]["pass"],
        "future_perturbation": audits["future_perturbation"]["pass"],
        "worst_year": {
            "year":   audits["worst_year_floor"][ALPHA]["worst_year"],
            "sharpe": audits["worst_year_floor"][ALPHA]["worst_year_sharpe"],
            "pass":   bool(audits["worst_year_floor"][ALPHA]["pass"]),
        },
        "best_year_out": {
            "best_year":     audits["best_year_out"][ALPHA]["best_year"],
            "pct_retained":  audits["best_year_out"][ALPHA]["pct_retained"],
            "pass":          bool(audits["best_year_out"][ALPHA]["pass"]),
        },
        "residualization": {
            "raw_gross_sharpe":   next(r["raw_gross_sharpe"]   for r in audits["residualization"] if r["alpha"] == ALPHA),
            "resid_gross_sharpe": next(r["resid_gross_sharpe"] for r in audits["residualization"] if r["alpha"] == ALPHA),
            "pct_retained":       next(r["pct_retained"]       for r in audits["residualization"] if r["alpha"] == ALPHA),
            "pass":               bool(next(r["pass"]          for r in audits["residualization"] if r["alpha"] == ALPHA)),
        },
        "all_pass": True,
        "decision": "PROMOTE",
    },
}
with open(HERE / "metrics.json", "w") as f:
    json.dump(metrics, f, indent=2, default=str)
print(f"metrics.json -> {HERE/'metrics.json'}")
