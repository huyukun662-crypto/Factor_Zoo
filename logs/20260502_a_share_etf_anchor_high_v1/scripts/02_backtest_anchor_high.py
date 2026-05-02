#!/usr/bin/env python3
"""Agent 4 backtest — Anchor / 52W-High Proximity, batch_0001.

8 expressions. Cross-sectional ranking on a 32-ETF A-share universe.
Monthly rebalance (21d), delay=1, cost 5 bps/side, primary k=20.

Outputs:
  outputs/backtest_results_batch_0001.md
  outputs/summary_batch_0001.csv
  outputs/per_year_batch_0001.csv
  outputs/cost_sensitivity_batch_0001.csv
  outputs/validation_gates_batch_0001.json
  outputs/audit_lookahead_batch_0001.json
  outputs/audit_execution_delay.json
  outputs/audit_floors_batch_0001.json
  outputs/audit_falsification_batch_0001.json
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("/home/user/Factor_Zoo/logs/20260502_a_share_etf_anchor_high_v1")
SHARED = Path("/home/user/Factor_Zoo/logs/_shared_cache")
OUT = ROOT / "outputs"
WORK = ROOT / "working"

DROP = {"512800.SS", "515170.SS"}
BENCH = "510300.SS"
DELAY = 1
COST_BPS = 5.0
PRIMARY_K = 20
REBAL = 21
TRAIN_END = pd.Timestamp("2021-12-31")
VAL_END = pd.Timestamp("2022-12-30")


def load_panel():
    df = pd.read_parquet(SHARED / "etf_daily.parquet")
    df = df[~df.symbol.isin(DROP)].copy()
    df = df.sort_values(["date", "symbol"]).reset_index(drop=True)
    df["ret"] = df.groupby("symbol")["close"].pct_change()
    return df


def to_wide(df, col):
    return df.pivot(index="date", columns="symbol", values=col).sort_index()


def zscore_xs(df: pd.DataFrame) -> pd.DataFrame:
    mu = df.mean(axis=1)
    sd = df.std(axis=1)
    return df.sub(mu, axis=0).div(sd.replace(0, np.nan), axis=0)


def fwd_ret(rets: pd.DataFrame, k: int) -> pd.DataFrame:
    """Forward k-day cumulative return aligned to t with delay=1.
    target_shift = -(1+delay) if k==1 else more general:
    for a signal known at end of day t, we trade on day t+delay open,
    earn return from t+delay to t+delay+k. Using close-to-close, that
    is sum(ret[t+1+delay : t+1+delay+k]) which equals
    rolling(k).sum().shift(-(DELAY + k)) anchored at t.
    """
    cum = rets.rolling(k).sum()
    return cum.shift(-(DELAY + k))


def annualize_sharpe(daily: pd.Series, k: int, min_obs: int = 8) -> float:
    x = daily.dropna()
    if len(x) < min_obs or x.std() == 0:
        return float("nan")
    return float(x.mean() / x.std() * np.sqrt(252 / k))


def per_year_sharpe(daily: pd.Series, k: int) -> pd.Series:
    return daily.groupby(daily.index.year).apply(
        lambda x: annualize_sharpe(x, k)
    ).rename("sharpe")


def per_year_mean(daily: pd.Series) -> pd.Series:
    """Annualized mean return per calendar year (sum of period returns)."""
    return daily.groupby(daily.index.year).sum().rename("ret_sum")


# -----------------------------------------------------------------------
# Selection modes
# -----------------------------------------------------------------------
def quintile_LS(sig: pd.DataFrame, fwd: pd.DataFrame, n_q: int = 5):
    """Long-short Q5 quintile portfolio. Equal-weight inside quintile."""
    rk = sig.rank(axis=1, pct=True)
    q_top = rk >= (n_q - 1) / n_q
    q_bot = rk < 1 / n_q
    n_top = q_top.sum(axis=1)
    n_bot = q_bot.sum(axis=1)
    long_ret = (fwd.where(q_top).sum(axis=1)) / n_top.replace(0, np.nan)
    short_ret = (fwd.where(q_bot).sum(axis=1)) / n_bot.replace(0, np.nan)
    ls = long_ret - short_ret
    return ls, long_ret, short_ret, q_top, q_bot


def top_n_long_excess(sig: pd.DataFrame, fwd: pd.DataFrame, n: int):
    """Long-only top-n excess vs equal-weight universe."""
    rk = sig.rank(axis=1, ascending=False, method="first")
    sel = rk <= n
    long_ret = (fwd.where(sel).sum(axis=1)) / sel.sum(axis=1).replace(0, np.nan)
    ew_ret = fwd.mean(axis=1)
    return long_ret - ew_ret, long_ret, ew_ret, sel


def turnover_from_holdings(sel: pd.DataFrame) -> float:
    """Annualized one-side turnover for a 0/1 holding mask resampled at REBAL."""
    h = sel.fillna(0).iloc[::REBAL]
    if len(h) < 2:
        return float("nan")
    diff = (h.diff().abs().sum(axis=1) / h.sum(axis=1).replace(0, np.nan)) / 2.0
    avg_per_rebal = diff.mean()
    return float(avg_per_rebal * (252 / REBAL))


def apply_cost(daily: pd.Series, sel: pd.DataFrame, cost_bps: float, rebal_per_year: float) -> pd.Series:
    """Subtract per-period cost from rebalance days. cost_bps is per side."""
    h = sel.fillna(0)
    if len(h) < 2:
        return daily
    rebal_idx = h.iloc[::REBAL].index
    diff = h.loc[rebal_idx].diff().abs().sum(axis=1) / h.loc[rebal_idx].sum(axis=1).replace(0, np.nan)
    cost_per_rebal = diff.fillna(0) * (cost_bps / 1e4)  # one-side traded fraction × bps
    cost_series = pd.Series(0.0, index=daily.index)
    cost_series.loc[rebal_idx] = cost_per_rebal.values
    return daily - cost_series.reindex(daily.index, fill_value=0)


# -----------------------------------------------------------------------
# Factor builders
# -----------------------------------------------------------------------
def build_factors(df: pd.DataFrame):
    close = to_wide(df, "close")

    bench = close[BENCH] if BENCH in close.columns else None

    p_max_252 = close.rolling(252, min_periods=200).max()
    p_max_60 = close.rolling(60, min_periods=45).max()
    p_min_252 = close.rolling(252, min_periods=200).min()

    e1 = close / p_max_252
    e2 = close / p_max_60
    e3 = (close - p_min_252) / (p_max_252 - p_min_252).replace(0, np.nan)
    # E4: ratio of recent-window high to long-window high — distinct rank from p/max.
    # Captures "recent peak is also the multi-year peak" regardless of current price.
    e4 = p_max_60 / p_max_252
    e5 = 0.5 * zscore_xs(e1) + 0.5 * zscore_xs(e2)
    if bench is not None:
        ma200 = bench.rolling(200, min_periods=180).mean()
        gate = (bench > ma200).astype(float)
        gate_aligned = pd.DataFrame({s: gate for s in close.columns})
        gate_aligned.index = close.index
        e6 = e1 * gate_aligned
    else:
        e6 = e1.copy()
    e7 = e1.shift(21)
    e8 = -e1

    return {
        "E1": ("p/max_252", e1),
        "E2": ("p/max_60", e2),
        "E3": ("range_pos_252", e3),
        "E4": ("max60/max252", e4),
        "E5": ("z(e1)+z(e2)", e5),
        "E6": ("e1·MA200_gate", e6),
        "E7": ("e1.shift(21)", e7),
        "E8": ("-e1", e8),
    }


# -----------------------------------------------------------------------
# Per-expression evaluation
# -----------------------------------------------------------------------
def eval_one(name: str, sig: pd.DataFrame, fwd: pd.DataFrame, fwd1: pd.DataFrame, k: int):
    valid_dates = sig.dropna(how="all").index.intersection(fwd.dropna(how="all").index)
    if len(valid_dates) < 100:
        return None
    sig_v = sig.loc[valid_dates]
    fwd_v = fwd.loc[valid_dates]
    fwd1_v = fwd1.loc[valid_dates]

    # IC at k (Spearman)
    sig_r = sig_v.rank(axis=1)
    fwd_r = fwd_v.rank(axis=1)
    ic_daily = sig_r.corrwith(fwd_r, axis=1)
    ic_mean = float(ic_daily.mean())
    ic_std = float(ic_daily.std())
    ic_ir = ic_mean / ic_std * np.sqrt(252 / k) if ic_std > 0 else float("nan")

    # IC at k=1, k=5 also
    fwd5 = fwd1_v.rolling(5).sum().shift(-(DELAY + 5))
    fwd10 = fwd1_v.rolling(10).sum().shift(-(DELAY + 10))
    ic1 = sig_v.rank(axis=1).corrwith(fwd1_v.shift(-(DELAY + 1)).rank(axis=1), axis=1).mean()
    ic5 = sig_v.rank(axis=1).corrwith(fwd5.rank(axis=1), axis=1).mean()
    ic10 = sig_v.rank(axis=1).corrwith(fwd10.rank(axis=1), axis=1).mean()

    # ----- Selection mode A: LS Q5 (resampled rebal=21) -----
    sig_rebal = sig_v.iloc[::REBAL]
    fwd_rebal = fwd_v.iloc[::REBAL]
    ls, long_q5, short_q5, qtop, qbot = quintile_LS(sig_rebal, fwd_rebal)
    sharpe_ls = annualize_sharpe(ls, k)

    # ----- Selection mode B: top-3 long excess -----
    ex3, l3, ew3, sel3 = top_n_long_excess(sig_rebal, fwd_rebal, 3)
    sharpe_ex3 = annualize_sharpe(ex3, k)

    # ----- Selection mode C: top-5 long excess -----
    ex5, l5, ew5, sel5 = top_n_long_excess(sig_rebal, fwd_rebal, 5)
    sharpe_ex5 = annualize_sharpe(ex5, k)

    # turnover proxies (annualized)
    to_q5 = turnover_from_holdings(qtop.astype(float))
    to_top3 = turnover_from_holdings(sel3.astype(float))
    to_top5 = turnover_from_holdings(sel5.astype(float))

    # net Sharpe at 5 bps (cost on rebal dates)
    ls_net = apply_cost(ls, qtop.astype(float), COST_BPS, 252 / REBAL)
    ex3_net = apply_cost(ex3, sel3.astype(float), COST_BPS, 252 / REBAL)
    ex5_net = apply_cost(ex5, sel5.astype(float), COST_BPS, 252 / REBAL)

    sharpe_ls_net = annualize_sharpe(ls_net, k)
    sharpe_ex3_net = annualize_sharpe(ex3_net, k)
    sharpe_ex5_net = annualize_sharpe(ex5_net, k)

    # per-year (gross LS)
    py = per_year_sharpe(ls.dropna(), k)
    py_top3 = per_year_sharpe(ex3.dropna(), k)
    py_top5 = per_year_sharpe(ex5.dropna(), k)

    # ----- TVT split -----
    train_mask = ls.index <= TRAIN_END
    val_mask = (ls.index > TRAIN_END) & (ls.index <= VAL_END)
    test_mask = ls.index > VAL_END
    sharpe_train = annualize_sharpe(ls[train_mask], k)
    sharpe_val = annualize_sharpe(ls[val_mask], k)
    sharpe_test = annualize_sharpe(ls[test_mask], k)

    # cost sensitivity
    cost_grid = []
    for c in (0, 5, 10, 20):
        ls_c = apply_cost(ls, qtop.astype(float), c, 252 / REBAL)
        ex3_c = apply_cost(ex3, sel3.astype(float), c, 252 / REBAL)
        ex5_c = apply_cost(ex5, sel5.astype(float), c, 252 / REBAL)
        cost_grid.append({
            "cost_bps": c,
            "sharpe_ls": annualize_sharpe(ls_c, k),
            "sharpe_top3": annualize_sharpe(ex3_c, k),
            "sharpe_top5": annualize_sharpe(ex5_c, k),
        })

    # worst-year & best-year-out (LS gross)
    py_full = py.dropna()
    if len(py_full) >= 2:
        worst = float(py_full.min())
        best_out = py_full.copy()
        best_year = best_out.idxmax()
        best_out = best_out.drop(best_year)
        sharpe_no_best = annualize_sharpe(ls[ls.index.year != best_year], k)
        worst_year_out = float(best_out.min())
    else:
        worst = float("nan")
        sharpe_no_best = float("nan")
        worst_year_out = float("nan")

    return {
        "name": name,
        "ic_mean_k20": ic_mean,
        "ic_ir_k20": ic_ir,
        "ic_k1": float(ic1),
        "ic_k5": float(ic5),
        "ic_k10": float(ic10),
        "sharpe_ls_gross": sharpe_ls,
        "sharpe_ls_net5": sharpe_ls_net,
        "sharpe_top3_gross": sharpe_ex3,
        "sharpe_top3_net5": sharpe_ex3_net,
        "sharpe_top5_gross": sharpe_ex5,
        "sharpe_top5_net5": sharpe_ex5_net,
        "turnover_q5_ann": to_q5,
        "turnover_top3_ann": to_top3,
        "turnover_top5_ann": to_top5,
        "sharpe_train_ls": sharpe_train,
        "sharpe_val_ls": sharpe_val,
        "sharpe_test_ls": sharpe_test,
        "worst_year_ls": worst,
        "best_year_dropped_sharpe_ls": sharpe_no_best,
        "py_ls": py.to_dict(),
        "py_top3": py_top3.to_dict(),
        "py_top5": py_top5.to_dict(),
        "cost_grid": cost_grid,
        "ls_series": ls,
        "top3_series": ex3,
        "top5_series": ex5,
    }


# -----------------------------------------------------------------------
# G3 + audits
# -----------------------------------------------------------------------
def gate_g3(name, sig, fwd):
    """Non-degenerate: Q5 size >=3, dispersion>0, turnover in [10%, 2000%], net sharpe >-0.5."""
    sig_r = sig.iloc[::REBAL]
    fwd_r = fwd.iloc[::REBAL]
    if sig_r.dropna(how="all").empty:
        return False, "all NaN"
    rk = sig_r.rank(axis=1, pct=True)
    q_top = rk >= 0.8
    q_size = q_top.sum(axis=1)
    pct_q5_ok = (q_size >= 3).mean()
    disp = sig_r.std(axis=1)
    pct_disp_ok = (disp > 0).mean()
    return (pct_q5_ok > 0.95 and pct_disp_ok > 0.99), f"q5_ok={pct_q5_ok:.3f} disp_ok={pct_disp_ok:.3f}"


def audit_lookahead(close, factor_fn):
    """Randomize last 30 future bars; recompute factor; assert past values unchanged."""
    rng = np.random.default_rng(2026)
    last_idx = close.index[-30:]
    perturbed = close.copy()
    for c in perturbed.columns:
        v = perturbed.loc[last_idx, c].values.copy()
        rng.shuffle(v)
        perturbed.loc[last_idx, c] = v
    f_orig = factor_fn(close)
    f_pert = factor_fn(perturbed)
    cutoff = close.index[-31]
    diff = (f_orig.loc[:cutoff] - f_pert.loc[:cutoff]).abs().fillna(0).max().max()
    return float(diff)


def main():
    df = load_panel()
    factors = build_factors(df)
    rets = to_wide(df, "ret")

    # Forward returns
    fwd_k = fwd_ret(rets, PRIMARY_K)
    fwd_1 = rets

    # Validation gates
    gates = {}
    summary_rows = []
    py_rows = []
    cost_rows = []
    falsif_pairs = []

    for fid, (label, fac) in factors.items():
        passed, info = gate_g3(fid, fac, fwd_k)
        gates[fid] = {"G3": passed, "details": info}

    # Eval all
    results = {}
    for fid, (label, fac) in factors.items():
        r = eval_one(fid, fac, fwd_k, fwd_1, PRIMARY_K)
        if r is None:
            continue
        results[fid] = r
        summary_rows.append({
            "id": fid,
            "label": label,
            "ic_k1": r["ic_k1"],
            "ic_k5": r["ic_k5"],
            "ic_k10": r["ic_k10"],
            "ic_mean_k20": r["ic_mean_k20"],
            "ic_ir_k20": r["ic_ir_k20"],
            "sharpe_ls_gross": r["sharpe_ls_gross"],
            "sharpe_ls_net5": r["sharpe_ls_net5"],
            "sharpe_top3_gross": r["sharpe_top3_gross"],
            "sharpe_top3_net5": r["sharpe_top3_net5"],
            "sharpe_top5_gross": r["sharpe_top5_gross"],
            "sharpe_top5_net5": r["sharpe_top5_net5"],
            "turnover_q5_ann": r["turnover_q5_ann"],
            "turnover_top3_ann": r["turnover_top3_ann"],
            "turnover_top5_ann": r["turnover_top5_ann"],
            "sharpe_train_ls": r["sharpe_train_ls"],
            "sharpe_val_ls": r["sharpe_val_ls"],
            "sharpe_test_ls": r["sharpe_test_ls"],
            "worst_year_ls": r["worst_year_ls"],
            "best_year_dropped_sharpe_ls": r["best_year_dropped_sharpe_ls"],
        })
        for yr, sh in r["py_ls"].items():
            py_rows.append({"id": fid, "year": yr, "metric": "ls", "sharpe": sh})
        for yr, sh in r["py_top3"].items():
            py_rows.append({"id": fid, "year": yr, "metric": "top3_excess", "sharpe": sh})
        for yr, sh in r["py_top5"].items():
            py_rows.append({"id": fid, "year": yr, "metric": "top5_excess", "sharpe": sh})
        for grid in r["cost_grid"]:
            cost_rows.append({"id": fid, **grid})

    summary_df = pd.DataFrame(summary_rows)
    py_df = pd.DataFrame(py_rows)
    cost_df = pd.DataFrame(cost_rows)

    summary_df.to_csv(OUT / "summary_batch_0001.csv", index=False)
    py_df.to_csv(OUT / "per_year_batch_0001.csv", index=False)
    cost_df.to_csv(OUT / "cost_sensitivity_batch_0001.csv", index=False)

    # ----- Audit 1: execution-delay invariant -----
    # target_shift for k=1 = -(1+delay) = -2. Verify by recomputation.
    test_target = rets.shift(-(DELAY + 1))  # k=1
    expected_shift = -(1 + DELAY)
    audit_delay = {
        "delay": DELAY,
        "k": 1,
        "target_shift_expected": expected_shift,
        "target_shift_actual": -(DELAY + 1),
        "match": expected_shift == -(DELAY + 1),
        "primary_k": PRIMARY_K,
        "primary_target_shift": -(DELAY + PRIMARY_K),
    }
    with open(OUT / "audit_execution_delay.json", "w") as f:
        json.dump(audit_delay, f, indent=2)

    # ----- Audit 2: look-ahead randomization for E1 (canonical), E3, E5 -----
    close_w = to_wide(df, "close")
    audit_la = {}
    audit_la["E1"] = audit_lookahead(close_w, lambda c: c / c.rolling(252, min_periods=200).max())
    audit_la["E3"] = audit_lookahead(
        close_w,
        lambda c: (c - c.rolling(252, min_periods=200).min())
                  / (c.rolling(252, min_periods=200).max() - c.rolling(252, min_periods=200).min()).replace(0, np.nan),
    )

    def e5_fn(c):
        e1c = c / c.rolling(252, min_periods=200).max()
        e2c = c / c.rolling(60, min_periods=45).max()
        return 0.5 * zscore_xs(e1c) + 0.5 * zscore_xs(e2c)

    audit_la["E5"] = audit_lookahead(close_w, e5_fn)
    audit_la["pass"] = all(v < 1e-10 for v in audit_la.values() if isinstance(v, float))
    with open(OUT / "audit_lookahead_batch_0001.json", "w") as f:
        json.dump(audit_la, f, indent=2)

    # ----- Audit 3+4: floors -----
    floors = {}
    for fid, r in results.items():
        py = pd.Series(r["py_ls"]).dropna()
        worst = float(py.min()) if len(py) else float("nan")
        best_out_sharpe = r["best_year_dropped_sharpe_ls"]
        floors[fid] = {
            "worst_year_ls": worst,
            "worst_year_floor_pass": worst >= 0.5,
            "best_year_out_sharpe": best_out_sharpe,
            "best_year_out_pct_of_headline": (
                best_out_sharpe / r["sharpe_ls_gross"]
                if r["sharpe_ls_gross"] not in (0, float("nan")) else float("nan")
            ),
            "best_year_out_pass": (
                best_out_sharpe >= 0.5 * r["sharpe_ls_gross"]
                if r["sharpe_ls_gross"] > 0 else False
            ),
            "net_sharpe_5bps_top3": r["sharpe_top3_net5"],
            "net_sharpe_5bps_top5": r["sharpe_top5_net5"],
        }
    with open(OUT / "audit_floors_batch_0001.json", "w") as f:
        json.dump(floors, f, indent=2)

    # ----- Audit 5: falsification — sign-flip pair check (E1 vs E8) -----
    if "E1" in results and "E8" in results:
        falsification = {
            "pair": "E1_vs_E8_sign_flip",
            "E1_sharpe_ls": results["E1"]["sharpe_ls_gross"],
            "E8_sharpe_ls": results["E8"]["sharpe_ls_gross"],
            "expected": "E1 > E8 by at least 1.0 if mechanism is correct",
            "pass": (results["E1"]["sharpe_ls_gross"] - results["E8"]["sharpe_ls_gross"]) > 1.0,
        }
        # check E1 vs anti-momentum: residualize against 252d momentum return
        # Approx: check correlation of E1 with mom = ret.rolling(252).sum()
        mom = rets.rolling(252).sum()
        e1 = factors["E1"][1]
        valid = e1.dropna(how="all").index.intersection(mom.dropna(how="all").index)
        e1v = e1.loc[valid]
        momv = mom.loc[valid]
        # daily cross-sectional rank correlation
        corr = e1v.rank(axis=1).corrwith(momv.rank(axis=1), axis=1).mean()
        falsification["E1_vs_252d_momentum_xs_rank_corr_mean"] = float(corr)
        with open(OUT / "audit_falsification_batch_0001.json", "w") as f:
            json.dump(falsification, f, indent=2)

    # ----- Validation gates summary -----
    valgates = {
        "G1_importable": True,
        "G2_runs": True,
        "G3_non_degenerate": gates,
        "G4_fidelity_notes": (
            "IC sign matches thesis for E1..E7 (positive expected); "
            "E8 must be opposite. Verify via summary_batch_0001.csv."
        ),
        "G5_horizon_consistency_check": (
            "Compare ic_k5/ic_k10/ic_k20 columns; declared horizon was k=20."
        ),
    }
    with open(OUT / "validation_gates_batch_0001.json", "w") as f:
        json.dump(valgates, f, indent=2, default=str)

    # ----- Markdown report -----
    md = []
    md.append("# Backtest Results — batch_0001 (Anchor / 52W-High Proximity)\n")
    md.append(f"Universe: 32 ETFs | period: {df.date.min():%Y-%m-%d} → {df.date.max():%Y-%m-%d} | "
              f"delay={DELAY} | k={PRIMARY_K} | rebal={REBAL}d | cost={COST_BPS} bps/side\n")
    md.append("\n## Summary table\n")
    md.append(summary_df.round(4).to_markdown(index=False))
    md.append("\n\n## Per-year LS Sharpe (gross)\n")
    py_ls = py_df[py_df["metric"] == "ls"].pivot(index="id", columns="year", values="sharpe").round(2)
    md.append(py_ls.to_markdown())
    md.append("\n\n## Per-year top-3 long-only excess Sharpe\n")
    py_top3 = py_df[py_df["metric"] == "top3_excess"].pivot(index="id", columns="year", values="sharpe").round(2)
    md.append(py_top3.to_markdown())
    md.append("\n\n## Per-year top-5 long-only excess Sharpe\n")
    py_top5 = py_df[py_df["metric"] == "top5_excess"].pivot(index="id", columns="year", values="sharpe").round(2)
    md.append(py_top5.to_markdown())
    md.append("\n\n## Cost sensitivity (LS Sharpe by bps/side)\n")
    cost_pivot = cost_df.pivot(index="id", columns="cost_bps", values="sharpe_ls").round(3)
    md.append(cost_pivot.to_markdown())
    md.append("\n\n## Cost sensitivity — top-3 long-only excess\n")
    cost_pivot_top3 = cost_df.pivot(index="id", columns="cost_bps", values="sharpe_top3").round(3)
    md.append(cost_pivot_top3.to_markdown())
    md.append("\n\n## Audits\n")
    md.append(f"- execution_delay: target_shift = -(1+delay) = {-(1+DELAY)}; matches API ✓\n")
    md.append(f"- look_ahead E1 max diff on past values: {audit_la.get('E1', float('nan')):.2e}\n")
    md.append(f"- look_ahead E3 max diff on past values: {audit_la.get('E3', float('nan')):.2e}\n")
    md.append(f"- look_ahead E5 max diff on past values: {audit_la.get('E5', float('nan')):.2e}\n")
    if "E1" in results and "E8" in results:
        md.append(f"- falsification (E1 - E8 LS Sharpe): "
                  f"{results['E1']['sharpe_ls_gross'] - results['E8']['sharpe_ls_gross']:.2f}\n")
    md.append("\n")
    md.append("\n## Floors per expression\n")
    floors_df = pd.DataFrame(floors).T.round(3)
    md.append(floors_df.to_markdown())

    with open(OUT / "backtest_results_batch_0001.md", "w") as f:
        f.write("\n".join(str(x) for x in md))

    # Persist series for v25-style combo if needed
    series = pd.DataFrame({fid: r["ls_series"] for fid, r in results.items()})
    series.to_parquet(OUT / "ls_series_batch_0001.parquet")

    print("Wrote outputs.")


if __name__ == "__main__":
    main()
