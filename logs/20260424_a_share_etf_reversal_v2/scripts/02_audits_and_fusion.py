#!/usr/bin/env python3
"""
Agent 4 audits + Agent 5 fusion comparison.

Runs:
  1. Execution-delay audit (double-path verification of target[t])
  2. Look-ahead randomization (shuffle future bars → IC should collapse)
  3. Best-year-out Sharpe (headline Sharpe after removing best calendar year)
  4. Falsification adversarial (probe_mom_20d_plus already computed; cross-check)
  5. V7 fusion comparison: long-only top-3 top-k blended as weighted overlay

Outputs:
  outputs/audit_report.json
  outputs/audit_report.md
  outputs/v7_fusion_results.csv
  outputs/v7_fusion_pnl_<variant>.csv
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

SESSION = Path("/home/user/Factor_Zoo/logs/20260424_a_share_etf_reversal_v2")
OUT = SESSION / "outputs"
V7_PNL = Path(
    "/home/user/Factor_Zoo/logs/20260423_a_share_etf_weekly_tqpb_v1/outputs/round2/d2_v7_pnl_series.csv"
)
DATA_SRC = Path(
    "/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs/etf_daily.parquet"
)

TOP_CANDIDATES = ["r1_rev_40d", "r1_rev_80d", "r1_rev_60d"]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def annualize(pnl: pd.Series) -> dict:
    p = pnl.dropna()
    if len(p) < 30:
        return {"sharpe": np.nan, "ret_ann": np.nan, "vol_ann": np.nan, "maxdd": np.nan, "n_days": len(p)}
    mu = p.mean() * 252
    sigma = p.std() * np.sqrt(252)
    sharpe = float(mu / sigma) if sigma > 0 else np.nan
    eq = (1 + p).cumprod()
    dd = float((eq / eq.cummax() - 1).min())
    return {"sharpe": sharpe, "ret_ann": float(mu), "vol_ann": float(sigma), "maxdd": dd, "n_days": int(len(p))}


def per_year_sharpe(pnl: pd.Series) -> dict:
    p = pnl.dropna()
    out = {}
    for y in sorted(set(p.index.year)):
        yp = p[p.index.year == y]
        if len(yp) < 30:
            out[int(y)] = {"sharpe": np.nan, "n": int(len(yp))}
            continue
        mu, sigma = yp.mean() * 252, yp.std() * np.sqrt(252)
        out[int(y)] = {"sharpe": float(mu / sigma) if sigma > 0 else np.nan, "n": int(len(yp))}
    return out


def best_year_out(pnl: pd.Series) -> dict:
    """Return Sharpe after removing the calendar year that most inflates headline."""
    p = pnl.dropna()
    all_s = annualize(p)["sharpe"]
    years = sorted(set(p.index.year))
    per_year_removed = {}
    for y in years:
        rest = p[p.index.year != y]
        if len(rest) < 60:
            continue
        per_year_removed[y] = annualize(rest)["sharpe"]
    if not per_year_removed:
        return {"headline": all_s, "best_year": None, "out_sharpe": np.nan, "ratio": np.nan}
    # The "best year" is the one whose removal lowers headline the most
    best_year = min(per_year_removed, key=lambda y: per_year_removed[y])
    out_sh = per_year_removed[best_year]
    return {
        "headline": float(all_s),
        "best_year": int(best_year),
        "out_sharpe": float(out_sh),
        "ratio": float(out_sh / all_s) if all_s and abs(all_s) > 1e-9 else np.nan,
        "per_year_removed": {int(y): float(v) for y, v in per_year_removed.items()},
    }


# --------------------------------------------------------------------------- #
# 1. Execution-delay audit
# --------------------------------------------------------------------------- #
def audit_execution_delay() -> dict:
    """
    Verify target[t] = log(close_adj[t+1+k]) - log(close_adj[t+1]) via two paths:
      path A: shift(-(1+k)) and shift(-1) then log ratio
      path B: rolling log returns from [t+2..t+1+k] summed
    They should match up to machine precision.
    """
    df = pd.read_parquet(DATA_SRC)
    df = df.rename(columns={"trade_date": "date", "ts_code": "symbol"}).sort_values(["symbol", "date"])
    k = 60
    # Path A (canonical)
    fwd_end = df.groupby("symbol")["close_adj"].shift(-(1 + k))
    fwd_start = df.groupby("symbol")["close_adj"].shift(-1)
    targetA = np.log(fwd_end / fwd_start)
    # Path B: sum of 1-bar log returns from t+2 to t+1+k (i.e. 60 step returns starting at t+2)
    ret1 = df.groupby("symbol")["close_adj"].transform(lambda s: np.log(s / s.shift(1)))
    # target for date t is sum of ret1[t+2..t+1+k]; using cumulative sum with shift
    cs = ret1.groupby(df["symbol"]).cumsum()
    # target B[t] = cs[t+1+k] - cs[t+1]
    csA = cs.groupby(df["symbol"]).shift(-(1 + k))
    csB = cs.groupby(df["symbol"]).shift(-1)
    targetB = csA - csB
    diff = (targetA - targetB).abs()
    return {
        "path_A_spec": "log(close_adj[t+1+60] / close_adj[t+1])",
        "path_B_spec": "sum of 1-bar logrets[t+2 .. t+1+60]",
        "max_abs_diff": float(diff.max(skipna=True)) if diff.notna().any() else None,
        "median_abs_diff": float(diff.median(skipna=True)) if diff.notna().any() else None,
        "n_compared": int(diff.notna().sum()),
        "pass": bool(diff.max(skipna=True) < 1e-10),
    }


# --------------------------------------------------------------------------- #
# 2. Look-ahead randomization audit
# --------------------------------------------------------------------------- #
def audit_lookahead_randomization(seed: int = 42) -> dict:
    """
    Shuffle symbol labels on the target within each date (preserves per-date
    target distribution, destroys signal→target mapping). A clean pipeline
    should see IC collapse to ~zero.

    We test at the signal's NATIVE horizon: r1_rev_40d at k=40.
    """
    from scipy.stats import spearmanr

    df = pd.read_parquet(DATA_SRC).rename(columns={"trade_date": "date", "ts_code": "symbol"})
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    k_sig, k_tgt = 40, 40

    df["logret_k"] = df.groupby("symbol")["close_adj"].transform(
        lambda s: np.log(s / s.shift(k_sig))
    )
    df["bar_age"] = df.groupby("symbol").cumcount()
    df["is_live"] = df["bar_age"] >= 60
    sig = -df["logret_k"]

    fwd_end = df.groupby("symbol")["close_adj"].shift(-(1 + k_tgt))
    fwd_start = df.groupby("symbol")["close_adj"].shift(-1)
    target_real = np.log(fwd_end / fwd_start)

    # Filter to common sample window after feature computation
    COMMON_START = pd.Timestamp("2019-01-04")
    keep = df["date"] >= COMMON_START
    df = df.loc[keep].reset_index(drop=True)
    sig = sig.loc[keep].reset_index(drop=True)
    target_real = target_real.loc[keep].reset_index(drop=True)

    per_date_mean = sig.where(df["is_live"]).groupby(df["date"]).transform("mean")
    sig_dem = sig.where(df["is_live"]) - per_date_mean

    # Within-date shuffle of target (permute symbol labels for each date)
    rng = np.random.default_rng(seed)
    df["_target_real"] = target_real.values
    shuffled = df.groupby("date")["_target_real"].transform(
        lambda s: rng.permutation(s.values)
    )

    def ic_spearman(a, b, d):
        dfx = pd.DataFrame({"a": a, "b": b, "d": d}).dropna()
        if dfx.empty:
            return np.nan, np.nan
        per = dfx.groupby("d").apply(
            lambda g: spearmanr(g["a"], g["b"])[0] if len(g) >= 5 else np.nan,
            include_groups=False,
        ).dropna()
        if per.empty:
            return np.nan, np.nan
        mu, sd, n = per.mean(), per.std(), len(per)
        return float(mu), float(mu / (sd / np.sqrt(n))) if sd > 0 else np.nan

    ic_real, t_real = ic_spearman(sig_dem, target_real, df["date"])
    ic_shuf, t_shuf = ic_spearman(sig_dem, shuffled, df["date"])
    return {
        "signal": "r1_rev_40d (demeaned)",
        "horizon_k_signal": k_sig,
        "horizon_k_target": k_tgt,
        "shuffle_scheme": "within-date symbol-label permutation",
        "ic_real": ic_real,
        "ic_tstat_real": t_real,
        "ic_shuffled": ic_shuf,
        "ic_tstat_shuffled": t_shuf,
        "pass": bool(abs(ic_shuf) < 0.005 and abs(t_shuf or 0) < 2.0),
    }


# --------------------------------------------------------------------------- #
# 3. Best-year-out audit for top candidates
# --------------------------------------------------------------------------- #
def audit_best_year_out() -> dict:
    result = {}
    for cid in TOP_CANDIDATES:
        for strat in ["longonly_top3_monthly", "longonly_top3_weekly"]:
            fp = OUT / f"pnl_{cid}_{strat}.csv"
            if not fp.exists():
                # run script only saves the best strat per expression; re-run the per-strat pnl here
                continue
            s = pd.read_csv(fp, index_col=0, parse_dates=True).squeeze("columns")
            ann = annualize(s)
            py = per_year_sharpe(s)
            byo = best_year_out(s)
            worst_year = min(py, key=lambda y: py[y]["sharpe"] if not np.isnan(py[y]["sharpe"]) else 99)
            result[f"{cid}__{strat}"] = {
                "headline_sharpe": ann["sharpe"],
                "worst_year": int(worst_year),
                "worst_year_sharpe": float(py[worst_year]["sharpe"]),
                "best_year_out": byo,
                "per_year": {int(k): float(v["sharpe"]) for k, v in py.items()},
            }
    return result


# --------------------------------------------------------------------------- #
# 4. Falsification summary (already computed; load from IC table)
# --------------------------------------------------------------------------- #
def audit_falsification() -> dict:
    ic = pd.read_csv(OUT / "ic_table_batch_0001.csv")
    probe = ic[(ic["id"] == "probe_mom_20d_plus") & (ic["horizon_k"] == 60)].iloc[0]
    return {
        "probe_id": "probe_mom_20d_plus (+logret_20d)",
        "target_horizon": 60,
        "ic": float(probe["ic"]),
        "ic_tstat": float(probe["ic_t"]),
        "expected": "near zero if no momentum leakage",
        "pass": bool(abs(probe["ic"]) < 0.005 and abs(probe["ic_t"]) < 1.0),
    }


# --------------------------------------------------------------------------- #
# 5. V7 fusion comparison
# --------------------------------------------------------------------------- #
def run_v7_fusion() -> pd.DataFrame:
    v7 = pd.read_csv(V7_PNL, index_col=0, parse_dates=True)["pnl_v7_orig"].rename("v7")
    # Resample V7 weekly pnl back to daily by spreading pnl over the week (constant slice)
    # Actually V7 is weekly; we'll work at weekly frequency — the reversal daily pnls must be
    # resampled to weekly sum to align with V7.
    rows = []
    pnl_series_written = {}
    for cid in TOP_CANDIDATES:
        for strat in ["longonly_top3_monthly", "longonly_top3_weekly"]:
            fp = OUT / f"pnl_{cid}_{strat}.csv"
            if not fp.exists():
                continue
            daily = pd.read_csv(fp, index_col=0, parse_dates=True).squeeze("columns")
            # Weekly sum on Friday-ending week
            weekly = daily.resample("W-FRI").sum()
            weekly.name = f"pnl_{cid}_{strat}"
            joined = pd.concat([v7, weekly], axis=1).dropna()
            if len(joined) < 30:
                continue
            v7_sub = joined["v7"]
            rev_sub = joined[weekly.name]
            ann_v7 = annualize(v7_sub)
            ann_rev = annualize(rev_sub)
            corr = float(v7_sub.corr(rev_sub))
            for w in [0.10, 0.15, 0.20, 0.30, 0.50]:
                combo = (1 - w) * v7_sub + w * rev_sub
                ann_c = annualize(combo)
                rows.append({
                    "reversal_id": cid, "reversal_strategy": strat,
                    "blend_weight": w, "v7_sharpe": ann_v7["sharpe"],
                    "reversal_sharpe": ann_rev["sharpe"],
                    "combined_sharpe": ann_c["sharpe"],
                    "delta_vs_v7": ann_c["sharpe"] - ann_v7["sharpe"],
                    "corr_weekly": corr,
                    "n_weeks": int(len(joined)),
                })
            pnl_series_written[(cid, strat)] = (v7_sub, rev_sub)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "v7_fusion_results.csv", index=False)
    # save one example pnl series
    if ("r1_rev_40d", "longonly_top3_monthly") in pnl_series_written:
        v7_sub, rev_sub = pnl_series_written[("r1_rev_40d", "longonly_top3_monthly")]
        pd.DataFrame({"v7": v7_sub, "rev_40d_mo": rev_sub}).to_csv(OUT / "v7_fusion_pnl_r1_rev_40d_monthly.csv")
    return df


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    print("=== Audit 1: Execution-delay ===")
    a1 = audit_execution_delay()
    print(f"  max abs diff (A vs B paths) = {a1['max_abs_diff']:.2e}")
    print(f"  pass = {a1['pass']}\n")

    print("=== Audit 2: Look-ahead randomization ===")
    a2 = audit_lookahead_randomization()
    print(f"  real  IC = {a2['ic_real']:+.4f}  t = {a2['ic_tstat_real']:+.2f}")
    print(f"  shuf  IC = {a2['ic_shuffled']:+.4f}  t = {a2['ic_tstat_shuffled']:+.2f}  ({a2['shuffle_scheme']})")
    print(f"  pass = {a2['pass']}\n")

    print("=== Audit 3: Best-year-out ===")
    a3 = audit_best_year_out()
    for k, v in a3.items():
        byo = v["best_year_out"]
        print(
            f"  {k:40s}  headline={v['headline_sharpe']:+.3f}  worst_year={v['worst_year']} "
            f"({v['worst_year_sharpe']:+.3f})  best_year={byo['best_year']}  out_Sh={byo['out_sharpe']:+.3f}  "
            f"ratio={byo['ratio']:+.2f}"
        )
    print()

    print("=== Audit 4: Falsification probe ===")
    a4 = audit_falsification()
    print(f"  probe IC = {a4['ic']:+.4f}  t = {a4['ic_tstat']:+.2f}  pass = {a4['pass']}\n")

    print("=== V7 fusion sweep ===")
    fus = run_v7_fusion()
    if len(fus):
        # Pivot for readability
        piv = fus.pivot_table(
            index=["reversal_id", "reversal_strategy"],
            columns="blend_weight",
            values="combined_sharpe",
        )
        print(piv.round(3).to_string())
        # Baseline
        print(f"\nV7 baseline Sh = {fus.iloc[0]['v7_sharpe']:.3f}  n_weeks = {fus.iloc[0]['n_weeks']}")
    else:
        print("  no fusion rows generated")

    report = {
        "audit_1_execution_delay": a1,
        "audit_2_lookahead_randomization": a2,
        "audit_3_best_year_out": a3,
        "audit_4_falsification_probe": a4,
        "audit_5_worst_year_floor": {
            "threshold_promote": 0.5,
            "threshold_research_floor": 0.0,
            "results": {
                k: {"worst_year": v["worst_year"], "worst_year_sharpe": v["worst_year_sharpe"],
                    "pass_research_floor_0": v["worst_year_sharpe"] >= 0.0,
                    "pass_promote_floor_0.5": v["worst_year_sharpe"] >= 0.5}
                for k, v in a3.items()
            },
        },
    }
    with open(OUT / "audit_report.json", "w") as f:
        json.dump(report, f, indent=2, default=float)
    print("\n✅ Audit report written: outputs/audit_report.json")
    return 0


if __name__ == "__main__":
    main()
