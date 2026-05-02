#!/usr/bin/env python3
"""Round 4 — combine the best R3 engineering choices.

R3 winners:
  H7 = phase-avg + portfolio vol-target  (Sharpe 0.71, worst -0.20)
  H6 = phase-avg + top-3                 (Sharpe 0.63, worst -0.04)
  H5 = phase-avg + core universe         (Sharpe 0.52, worst +0.09 — only positive worst-year)
  H1 = phase-avg baseline                (Sharpe 0.55, worst -0.13)

R4 combines them.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("/home/user/Factor_Zoo/logs/20260502_a_share_etf_anchor_high_v1")
SHARED = Path("/home/user/Factor_Zoo/logs/_shared_cache")
OUT = ROOT / "outputs"

# Reuse R3 functions by import-via-exec
import sys
sys.path.insert(0, str(ROOT / "scripts"))
import importlib.util
spec = importlib.util.spec_from_file_location("r3", ROOT / "scripts" / "05_backtest_r3.py")
r3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r3)

DROP_FULL = r3.DROP_FULL
BENCH = r3.BENCH
COST_BPS = r3.COST_BPS
REBAL = r3.REBAL
TARGET_VOL = r3.TARGET_VOL
TRAIN_END = r3.TRAIN_END
VAL_END = r3.VAL_END


def main():
    df = r3.load_panel()
    close = r3.to_wide(df, "close")
    rets = r3.to_wide(df, "ret")

    bench = close[BENCH]
    ma200 = bench.rolling(200, min_periods=180).mean()
    regime_on = (bench > ma200).astype(int)

    rp_60 = r3.range_pos(close, 60)
    rp_120 = r3.range_pos(close, 120)
    rp_252 = r3.range_pos(close, 252)
    multi_rank = (
        rp_60.rank(axis=1, pct=True)
        + rp_120.rank(axis=1, pct=True)
        + rp_252.rank(axis=1, pct=True)
    ) / 3.0

    # also a longer-window version
    rp_500 = r3.range_pos(close, 500)
    multi_rank_extended = (
        rp_60.rank(axis=1, pct=True)
        + rp_120.rank(axis=1, pct=True)
        + rp_252.rank(axis=1, pct=True)
        + rp_500.rank(axis=1, pct=True)
    ) / 4.0

    core = r3.core_universe(close)
    print(f"Core universe size: {len(core)} (full: {close.shape[1]})")

    bench_full = rets.mean(axis=1)
    bench_core_d = rets[core].mean(axis=1)

    variants = {}

    # K1: top-3 + core universe
    pd1, pn1, _, _, _ = r3.phase_ensemble_long_only(multi_rank, rets, n=3, universe_filter=core)
    variants["K1"] = {"port_net": pn1, "bench": bench_core_d, "vol_target": False}

    # K2: vol-target + core universe (top-5)
    pd2, pn2, _, _, _ = r3.phase_ensemble_long_only(multi_rank, rets, n=5, universe_filter=core)
    variants["K2"] = {"port_net": pn2, "bench": bench_core_d, "vol_target": True}

    # K3: vol-target + top-3 (full universe)
    pd3, pn3, _, _, _ = r3.phase_ensemble_long_only(multi_rank, rets, n=3)
    variants["K3"] = {"port_net": pn3, "bench": bench_full, "vol_target": True}

    # K4: full stack — vol-target + top-3 + core universe
    pd4, pn4, _, _, _ = r3.phase_ensemble_long_only(multi_rank, rets, n=3, universe_filter=core)
    variants["K4"] = {"port_net": pn4, "bench": bench_core_d, "vol_target": True}

    # K5: extended-window multi_rank (60/120/252/500), top-3, core universe, vol-target
    pd5, pn5, _, _, _ = r3.phase_ensemble_long_only(
        multi_rank_extended, rets, n=3, universe_filter=core)
    variants["K5"] = {"port_net": pn5, "bench": bench_core_d, "vol_target": True}

    # K6: K4 + bench overlay regime (off-regime hold bench instead of EW)
    pd6_pre, pn6_pre, _, _, _ = r3.phase_ensemble_long_only(
        multi_rank, rets, n=3, universe_filter=core, regime=regime_on)
    variants["K6"] = {"port_net": pn6_pre, "bench": bench_core_d, "vol_target": True}

    # K7: K4 with target vol = 15%
    variants["K7"] = {"port_net": pn4, "bench": bench_core_d, "vol_target": True, "target_vol": 0.15}

    # K8: K4 with target vol = 8%
    variants["K8"] = {"port_net": pn4, "bench": bench_core_d, "vol_target": True, "target_vol": 0.08}

    rows = []
    py_rows = []
    py_excess_rows = []
    for vid, v in variants.items():
        port = v["port_net"].copy()
        bench_local = v["bench"]
        excess = port - bench_local
        if v.get("vol_target"):
            tv = v.get("target_vol", TARGET_VOL)
            excess = r3.vol_target_overlay(excess, target=tv)
            port = excess + bench_local

        excess = excess.dropna()
        valid = excess.index[excess.index.year >= 2020]
        excess = excess.loc[valid]
        port_v = port.reindex(valid)

        sharpe_excess = r3.annualize_sharpe(excess, 1)
        sharpe_port = r3.annualize_sharpe(port_v, 1)

        py_excess = r3.per_year_sharpe(excess, 1)
        py_excess_pct = r3.per_year_excess_pct(excess)
        py_port_pct = r3.per_year_excess_pct(port_v)
        py_bench_pct = r3.per_year_excess_pct(bench_local.reindex(valid))

        train_mask = excess.index <= TRAIN_END
        val_mask = (excess.index > TRAIN_END) & (excess.index <= VAL_END)
        test_mask = excess.index > VAL_END
        sharpe_train = r3.annualize_sharpe(excess[train_mask], 1)
        sharpe_val = r3.annualize_sharpe(excess[val_mask], 1)
        sharpe_test = r3.annualize_sharpe(excess[test_mask], 1)

        worst_year_sharpe = float(py_excess.min())
        n_pos_years = int((py_excess > 0).sum())
        n_total_years = int(py_excess.notna().sum())

        # max drawdown of cum excess
        cum_excess = (1 + excess).cumprod()
        peak = cum_excess.cummax()
        dd = (cum_excess / peak - 1).min()

        rows.append({
            "id": vid,
            "sharpe_excess_net": sharpe_excess,
            "sharpe_port_net": sharpe_port,
            "sharpe_train_excess": sharpe_train,
            "sharpe_val_excess": sharpe_val,
            "sharpe_test_excess": sharpe_test,
            "worst_year_sharpe_excess": worst_year_sharpe,
            "max_dd_excess": float(dd),
            "n_pos_years": n_pos_years,
            "n_total_years": n_total_years,
            "frac_pos_years": n_pos_years / max(n_total_years, 1),
        })
        for yr, sh in py_excess.items():
            py_rows.append({"id": vid, "year": int(yr), "sharpe": sh})
        for yr, ex in py_excess_pct.items():
            py_excess_rows.append({
                "id": vid, "year": int(yr),
                "excess_return_ann": float(ex),
                "port_return_ann": float(py_port_pct.get(yr, np.nan)),
                "bench_return_ann": float(py_bench_pct.get(yr, np.nan)),
            })

    pd.DataFrame(rows).to_csv(OUT / "r4_summary_batch_0004.csv", index=False)
    pd.DataFrame(py_rows).to_csv(OUT / "r4_per_year_sharpe_batch_0004.csv", index=False)
    pd.DataFrame(py_excess_rows).to_csv(OUT / "r4_per_year_excess_batch_0004.csv", index=False)

    floors = {}
    for r in rows:
        vid = r["id"]
        floors[vid] = {
            "sharpe_excess_net": r["sharpe_excess_net"],
            "promote_sharpe_geq_1.0": r["sharpe_excess_net"] >= 1.0,
            "candidate_sharpe_geq_0.5": r["sharpe_excess_net"] >= 0.5,
            "worst_year_geq_0": r["worst_year_sharpe_excess"] >= 0,
            "max_dd_excess": r["max_dd_excess"],
            "test_geq_50pct_full": (
                r["sharpe_test_excess"] >= 0.5 * r["sharpe_excess_net"]
                if r["sharpe_excess_net"] > 0 else False
            ),
            "frac_pos_years_geq_70pct": r["frac_pos_years"] >= 0.70,
            "verdict": (
                "PROMOTE" if (r["sharpe_excess_net"] >= 1.0 and r["worst_year_sharpe_excess"] >= 0)
                else "ADMITTED_CANDIDATE" if (r["sharpe_excess_net"] >= 1.0)
                else "RESEARCH_ONLY" if (r["sharpe_excess_net"] >= 0.5)
                else "REJECT"
            ),
        }
    with open(OUT / "r4_floors_batch_0004.json", "w") as f:
        json.dump(floors, f, indent=2)

    df_summary = pd.DataFrame(rows).round(3)
    print("\n=== R4 Summary ===")
    print(df_summary.to_string(index=False))
    print("\n=== Floors ===")
    print(pd.DataFrame(floors).T.round(3).to_string())

    md = ["# Backtest Results — batch_0004 (R4 best-of-best combinations)\n"]
    md.append("\nAll variants 21-phase ensemble. K2..K8 use vol-target overlay (target=10% unless specified).\n")
    md.append("\n## Summary table\n")
    md.append(df_summary.to_markdown(index=False))
    md.append("\n\n## Per-year excess Sharpe\n")
    py_df = pd.DataFrame(py_rows)
    py_pivot = py_df.pivot(index="id", columns="year", values="sharpe").round(2)
    md.append(py_pivot.to_markdown())
    md.append("\n\n## Per-year excess return (cumulative, fractional)\n")
    py_ret_df = pd.DataFrame(py_excess_rows)
    py_ret_pivot = py_ret_df.pivot(index="id", columns="year", values="excess_return_ann").round(3)
    md.append(py_ret_pivot.to_markdown())
    md.append("\n\n## PROMOTE floor decisions\n")
    md.append(pd.DataFrame(floors).T.round(3).to_markdown())

    with open(OUT / "r4_backtest_results_batch_0004.md", "w") as f:
        f.write("\n".join(str(x) for x in md))

    return floors


if __name__ == "__main__":
    main()
