#!/usr/bin/env python3
"""Phase-rotation audit (Round 2 follow-up).

Discovery: same factor (range_pos_252) gives LS Sharpe 0.63 vs 0.23
depending on whether first rebalance is on day-200 vs day-201 of the
panel — i.e., the headline number is sensitive to which ~10 days/year
we rebalance on. This script averages over all 21 phase offsets to
produce a robust headline.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("/home/user/Factor_Zoo/logs/20260502_a_share_etf_anchor_high_v1")
SHARED = Path("/home/user/Factor_Zoo/logs/_shared_cache")
OUT = ROOT / "outputs"

DROP = {"512800.SS", "515170.SS"}
DELAY = 1
COST_BPS = 5.0
PRIMARY_K = 20
REBAL = 21


def annualize_sharpe(daily, k, min_obs=8):
    x = daily.dropna()
    if len(x) < min_obs or x.std() == 0:
        return float("nan")
    return float(x.mean() / x.std() * np.sqrt(252 / k))


def load():
    df = pd.read_parquet(SHARED / "etf_daily.parquet")
    df = df[~df.symbol.isin(DROP)].copy()
    df = df.sort_values(["date", "symbol"]).reset_index(drop=True)
    df["ret"] = df.groupby("symbol")["close"].pct_change()
    close = df.pivot(index="date", columns="symbol", values="close").sort_index()
    rets = df.pivot(index="date", columns="symbol", values="ret").sort_index()
    return close, rets


def range_pos(close, w):
    pmax = close.rolling(w, min_periods=200).max()
    pmin = close.rolling(w, min_periods=200).min()
    return (close - pmin) / (pmax - pmin).replace(0, np.nan)


def ls_with_phase(sig, fwd, phase, rebal=REBAL):
    """Sample at iloc[phase::rebal] for any phase in [0..rebal-1]."""
    valid = sig.dropna(how="all").index.intersection(fwd.dropna(how="all").index)
    sig_v = sig.loc[valid]
    fwd_v = fwd.loc[valid]
    sig_r = sig_v.iloc[phase::rebal]
    fwd_r = fwd_v.iloc[phase::rebal]
    rk = sig_r.rank(axis=1, pct=True)
    q_top = rk >= 0.8
    q_bot = rk < 0.2
    long_ret = fwd_r.where(q_top).sum(axis=1) / q_top.sum(axis=1).replace(0, np.nan)
    short_ret = fwd_r.where(q_bot).sum(axis=1) / q_bot.sum(axis=1).replace(0, np.nan)
    return long_ret - short_ret, q_top


def long_only_with_phase(sig, fwd, n, phase, rebal=REBAL):
    valid = sig.dropna(how="all").index.intersection(fwd.dropna(how="all").index)
    sig_v = sig.loc[valid]
    fwd_v = fwd.loc[valid]
    sig_r = sig_v.iloc[phase::rebal]
    fwd_r = fwd_v.iloc[phase::rebal]
    rk = sig_r.rank(axis=1, ascending=False, method="first")
    sel = rk <= n
    long_ret = fwd_r.where(sel).sum(axis=1) / sel.sum(axis=1).replace(0, np.nan)
    return long_ret - fwd_r.mean(axis=1), sel


def main():
    close, rets = load()
    fwd = rets.rolling(PRIMARY_K).sum().shift(-(DELAY + PRIMARY_K))

    sig = range_pos(close, 252)

    rows = []
    py_rows = []
    for phase in range(REBAL):
        ls, _ = ls_with_phase(sig, fwd, phase)
        ex5, _ = long_only_with_phase(sig, fwd, 5, phase)
        ex3, _ = long_only_with_phase(sig, fwd, 3, phase)
        rows.append({
            "phase": phase,
            "n_rebal": int(ls.notna().sum()),
            "sharpe_ls": annualize_sharpe(ls, PRIMARY_K),
            "sharpe_top3": annualize_sharpe(ex3, PRIMARY_K),
            "sharpe_top5": annualize_sharpe(ex5, PRIMARY_K),
            "worst_year_ls": float(ls.groupby(ls.index.year).apply(
                lambda x: annualize_sharpe(x, PRIMARY_K)).min()),
            "best_year_ls": float(ls.groupby(ls.index.year).apply(
                lambda x: annualize_sharpe(x, PRIMARY_K)).max()),
        })
        py = ls.groupby(ls.index.year).apply(
            lambda x: annualize_sharpe(x, PRIMARY_K))
        for yr, sh in py.items():
            py_rows.append({"phase": phase, "year": int(yr), "sharpe": sh})

    df_phase = pd.DataFrame(rows)
    df_phase.to_csv(OUT / "r2_phase_rotation_F1.csv", index=False)
    pd.DataFrame(py_rows).to_csv(OUT / "r2_phase_per_year_F1.csv", index=False)

    summary = {
        "factor": "range_pos_252 LS Q5 (k=20, rebal=21)",
        "n_phases": REBAL,
        "sharpe_ls_mean": float(df_phase["sharpe_ls"].mean()),
        "sharpe_ls_std": float(df_phase["sharpe_ls"].std()),
        "sharpe_ls_min": float(df_phase["sharpe_ls"].min()),
        "sharpe_ls_max": float(df_phase["sharpe_ls"].max()),
        "sharpe_ls_q25": float(df_phase["sharpe_ls"].quantile(0.25)),
        "sharpe_ls_q75": float(df_phase["sharpe_ls"].quantile(0.75)),
        "sharpe_top5_mean": float(df_phase["sharpe_top5"].mean()),
        "sharpe_top5_std": float(df_phase["sharpe_top5"].std()),
        "sharpe_top5_min": float(df_phase["sharpe_top5"].min()),
        "sharpe_top5_max": float(df_phase["sharpe_top5"].max()),
        "sharpe_top3_mean": float(df_phase["sharpe_top3"].mean()),
        "sharpe_top3_std": float(df_phase["sharpe_top3"].std()),
        "sharpe_top3_min": float(df_phase["sharpe_top3"].min()),
        "sharpe_top3_max": float(df_phase["sharpe_top3"].max()),
        "worst_year_min_across_phases": float(df_phase["worst_year_ls"].min()),
        "worst_year_median_across_phases": float(df_phase["worst_year_ls"].median()),
        "verdict": (
            "Phase sensitivity is severe; honest headline uses mean ± std "
            "across all 21 phases, not the best-phase headline."
        ),
    }
    with open(OUT / "r2_phase_rotation_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Also evaluate "averaged-over-phases" composite portfolio
    # by stacking all 21 phase LS series and treating as single returns series
    # (overlapping but non-redundant samples).
    all_ls = []
    all_ex5 = []
    for phase in range(REBAL):
        ls, _ = ls_with_phase(sig, fwd, phase)
        ex5, _ = long_only_with_phase(sig, fwd, 5, phase)
        all_ls.append(ls)
        all_ex5.append(ex5)
    avg_ls = pd.concat(all_ls).groupby(level=0).mean()
    avg_ex5 = pd.concat(all_ex5).groupby(level=0).mean()
    summary["sharpe_ls_phase_averaged_portfolio"] = annualize_sharpe(avg_ls, PRIMARY_K)
    summary["sharpe_top5_phase_averaged_portfolio"] = annualize_sharpe(avg_ex5, PRIMARY_K)
    py_avg = avg_ls.groupby(avg_ls.index.year).apply(
        lambda x: annualize_sharpe(x, PRIMARY_K))
    py_top5_avg = avg_ex5.groupby(avg_ex5.index.year).apply(
        lambda x: annualize_sharpe(x, PRIMARY_K))
    summary["py_ls_phase_averaged"] = {int(k): v for k, v in py_avg.to_dict().items()}
    summary["py_top5_phase_averaged"] = {int(k): v for k, v in py_top5_avg.to_dict().items()}
    with open(OUT / "r2_phase_rotation_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=lambda x: None if pd.isna(x) else x)

    print(df_phase.round(3).to_string(index=False))
    print("\nphase-averaged LS Sharpe:", summary["sharpe_ls_phase_averaged_portfolio"])
    print("phase-averaged top5 Sharpe:", summary["sharpe_top5_phase_averaged_portfolio"])
    print("phase-averaged per-year LS:", py_avg.round(2).to_dict())
    print("phase-averaged per-year top5:", py_top5_avg.round(2).to_dict())


if __name__ == "__main__":
    main()
