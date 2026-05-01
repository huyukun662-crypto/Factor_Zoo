#!/usr/bin/env python3
"""IVOL Round 2 evaluation — primary k=1, daily rebalance.
Same 8 expressions, re-evaluated to honor the revised metadata after G5 fail.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path("/home/user/Factor_Zoo/logs/20260501_a_share_etf_ivol_reversal_v1/scripts")))
import numpy as np
import pandas as pd

from importlib import import_module
m = import_module("02_backtest_ivol")

ROOT = Path("/home/user/Factor_Zoo/logs/20260501_a_share_etf_ivol_reversal_v1")
OUT = ROOT / "outputs"
WORK = ROOT / "working"

PRIMARY_K = 1            # REVISED
COST_BPS = 5.0
WORST_YEAR_FLOOR = 0.5
TRAIN_END = pd.Timestamp("2021-12-31")
VAL_END = pd.Timestamp("2022-12-31")
DELAY = 1


def main():
    panel = m.load_panel()
    rets = m.to_wide(panel, "ret")
    bench = rets[m.BENCH]
    rebalance_days = 1

    signals = {
        "f1_ivol_resid_20d":    m.signal_ivol(rets, bench, m.BETA_W, 20, "std"),
        "f2_total_vol_20d":     m.signal_total_vol(rets, 20),
        "f3_ivol_resid_10d":    m.signal_ivol(rets, bench, m.BETA_W, 10, "std"),
        "f4_ivol_resid_40d":    m.signal_ivol(rets, bench, m.BETA_W, 40, "std"),
        "f5_ivol_resid_amp_20d": m.signal_ivol(rets, bench, m.BETA_W, 20, "mean_abs"),
        "f6_ivol_lag5_20d":     m.signal_lagged(m.signal_ivol(rets, bench, m.BETA_W, 20, "std"), 5),
        "f7_vol_of_vol_20m40":  m.signal_vol_of_vol(rets, bench, m.BETA_W, 20, 40),
        "f8_kitchen_sink_rank": m.signal_kitchen_sink(rets, bench),
    }

    # Override fwd_ret for k=1 with delay=1
    def fwd1(rets):
        cum = rets.rolling(1).sum()
        return cum.shift(-(DELAY + 1))

    f = fwd1(rets)

    rows = []
    yr_rows = []
    for fid, sig in signals.items():
        res = m.quintile_long_short(sig, f)
        rk = res["rank"]
        ls = res["ls"]; lo = res["longonly"]; ex = res["excess"]
        sharpe = m.annualize_sharpe(ls, PRIMARY_K)
        sharpe_lo = m.annualize_sharpe(lo, PRIMARY_K)
        sharpe_ex = m.annualize_sharpe(ex, PRIMARY_K)
        net = m.net_sharpe_at_cost(rk, ls, PRIMARY_K, COST_BPS, rebalance_days)
        to_yr = m.turnover_annualized(rk, rebalance_days)
        def slc(s, lo_, hi_):
            return s[(s.index > lo_) & (s.index <= hi_)]
        ls_train = slc(ls, pd.Timestamp("1900-01-01"), TRAIN_END)
        ls_val   = slc(ls, TRAIN_END, VAL_END)
        ls_test  = slc(ls, VAL_END, pd.Timestamp("2030-01-01"))
        rows.append({
            "expr": fid,
            "sharpe_ls_gross": sharpe,
            "sharpe_ls_train": m.annualize_sharpe(ls_train, PRIMARY_K),
            "sharpe_ls_val":   m.annualize_sharpe(ls_val,   PRIMARY_K),
            "sharpe_ls_test":  m.annualize_sharpe(ls_test,  PRIMARY_K),
            "sharpe_ls_net5bps": net,
            "sharpe_longonly_gross": sharpe_lo,
            "sharpe_excess_gross": sharpe_ex,
            "ann_turnover_pct": to_yr * 100,
        })
        ys = m.per_year_sharpe(ls, PRIMARY_K)
        for y, sh in ys.items():
            yr_rows.append({"expr": fid, "year": int(y), "sharpe": sh})

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "round2_k1_summary.csv", index=False)
    yr_df = pd.DataFrame(yr_rows)
    yr_df.to_csv(OUT / "round2_k1_per_year.csv", index=False)

    # Add floors
    floors = {}
    for fid in signals:
        years = yr_df[yr_df.expr == fid].sort_values("year")
        wy = float(years.sharpe.min()) if len(years) else float("nan")
        if len(years) >= 2:
            best_y = years.sharpe.idxmax()
            byo = years.drop(best_y)
            byo_sharpe = float(byo.sharpe.mean())
        else:
            byo_sharpe = float("nan")
        sh_full = next((r for r in rows if r["expr"] == fid), {}).get("sharpe_ls_gross", float("nan"))
        floors[fid] = {
            "worst_year_sharpe": wy,
            "best_year_out_avg_sharpe": byo_sharpe,
            "headline_sharpe_full": sh_full,
            "wy_pass": (wy >= WORST_YEAR_FLOOR) if np.isfinite(wy) else False,
            "byo_pass": (byo_sharpe >= 0.5 * sh_full) if np.isfinite(byo_sharpe) and np.isfinite(sh_full) and sh_full > 0 else False,
        }
    with (OUT / "round2_k1_floors.json").open("w") as f:
        json.dump(floors, f, indent=2)

    # Markdown
    lines = ["# Round 2 — IVOL evaluated at k=1 (revised primary horizon)", ""]
    lines.append("## Round-2 LS / long-only at k=1, daily rebalance, 5 bps/side")
    lines.append("")
    lines.append("| expr | LS gross | LS net@5bps | LS train | LS val | LS test | longonly | excess | turnover% |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        lines.append(f"| {r['expr']} | {r['sharpe_ls_gross']:.2f} | {r['sharpe_ls_net5bps']:.2f} | "
                     f"{r['sharpe_ls_train']:.2f} | {r['sharpe_ls_val']:.2f} | {r['sharpe_ls_test']:.2f} | "
                     f"{r['sharpe_longonly_gross']:.2f} | {r['sharpe_excess_gross']:.2f} | {r['ann_turnover_pct']:.0f} |")
    lines.append("")
    lines.append("## Per-year LS Sharpe")
    lines.append("")
    lines.append(yr_df.pivot(index='expr', columns='year', values='sharpe').round(2).to_markdown())
    lines.append("")
    lines.append("## Floors")
    lines.append("")
    lines.append("| expr | wy_sharpe | wy_pass | byo_avg | byo_pass |")
    lines.append("|---|---:|---|---:|---|")
    for fid in signals:
        fl = floors[fid]
        lines.append(f"| {fid} | {fl['worst_year_sharpe']:.2f} | {fl['wy_pass']} | {fl['best_year_out_avg_sharpe']:.2f} | {fl['byo_pass']} |")
    (OUT / "backtest_results_batch_0001_round2.md").write_text("\n".join(lines))
    print("OK round 2 (k=1)")


if __name__ == "__main__":
    main()
