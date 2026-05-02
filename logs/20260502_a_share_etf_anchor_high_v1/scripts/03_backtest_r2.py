#!/usr/bin/env python3
"""Agent 4 backtest — Round 2, batch_0002.

Eight E3-centric variants to attempt to rescue worst-year:
  F1 range_pos_252 baseline
  F2 range_pos_120
  F3 range_pos_60
  F4 multi-window equal-rank composite (60/120/252)
  F5 range_pos_252 / vol_60 (vol-targeted selection)
  F6 range_pos_252 with bench>MA200 regime gate
  F7 range_pos_252 minus beta*momentum (residualized)
  F8 range_pos_252 with rebal=42d
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
BENCH = "510300.SS"
DELAY = 1
COST_BPS = 5.0
PRIMARY_K = 20
REBAL_DEFAULT = 21
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


def range_pos(close: pd.DataFrame, w: int) -> pd.DataFrame:
    pmax = close.rolling(w, min_periods=int(w * 0.8)).max()
    pmin = close.rolling(w, min_periods=int(w * 0.8)).min()
    return (close - pmin) / (pmax - pmin).replace(0, np.nan)


def annualize_sharpe(daily: pd.Series, k: int, min_obs: int = 8) -> float:
    x = daily.dropna()
    if len(x) < min_obs or x.std() == 0:
        return float("nan")
    return float(x.mean() / x.std() * np.sqrt(252 / k))


def per_year_sharpe(daily: pd.Series, k: int) -> pd.Series:
    return daily.groupby(daily.index.year).apply(
        lambda x: annualize_sharpe(x, k)
    ).rename("sharpe")


def quintile_LS(sig: pd.DataFrame, fwd: pd.DataFrame, n_q: int = 5):
    rk = sig.rank(axis=1, pct=True)
    q_top = rk >= (n_q - 1) / n_q
    q_bot = rk < 1 / n_q
    long_ret = fwd.where(q_top).sum(axis=1) / q_top.sum(axis=1).replace(0, np.nan)
    short_ret = fwd.where(q_bot).sum(axis=1) / q_bot.sum(axis=1).replace(0, np.nan)
    return long_ret - short_ret, long_ret, short_ret, q_top, q_bot


def top_n_long_excess(sig: pd.DataFrame, fwd: pd.DataFrame, n: int):
    rk = sig.rank(axis=1, ascending=False, method="first")
    sel = rk <= n
    long_ret = fwd.where(sel).sum(axis=1) / sel.sum(axis=1).replace(0, np.nan)
    return long_ret - fwd.mean(axis=1), long_ret, sel


def turnover_ann(sel: pd.DataFrame, rebal: int) -> float:
    h = sel.fillna(0).iloc[::rebal]
    if len(h) < 2:
        return float("nan")
    diff = (h.diff().abs().sum(axis=1) / h.sum(axis=1).replace(0, np.nan)) / 2.0
    return float(diff.mean() * (252 / rebal))


def apply_cost(daily: pd.Series, sel: pd.DataFrame, cost_bps: float, rebal: int) -> pd.Series:
    h = sel.fillna(0)
    rebal_idx = h.iloc[::rebal].index
    diff = h.loc[rebal_idx].diff().abs().sum(axis=1) / h.loc[rebal_idx].sum(axis=1).replace(0, np.nan)
    cost_per_rebal = diff.fillna(0) * (cost_bps / 1e4)
    cost_series = pd.Series(0.0, index=daily.index)
    cost_series.loc[rebal_idx] = cost_per_rebal.values
    return daily - cost_series.reindex(daily.index, fill_value=0)


def fwd_ret(rets: pd.DataFrame, k: int) -> pd.DataFrame:
    return rets.rolling(k).sum().shift(-(DELAY + k))


def zscore_xs(df: pd.DataFrame) -> pd.DataFrame:
    mu = df.mean(axis=1)
    sd = df.std(axis=1)
    return df.sub(mu, axis=0).div(sd.replace(0, np.nan), axis=0)


def residualize_xs_daily(target: pd.DataFrame, control: pd.DataFrame) -> pd.DataFrame:
    """For each date, OLS residual of target on control across symbols."""
    out = target.copy() * np.nan
    for d in target.index:
        y = target.loc[d].dropna()
        x = control.loc[d].reindex(y.index).dropna()
        common = y.index.intersection(x.index)
        if len(common) < 8:
            continue
        y_c = y.loc[common].values
        x_c = x.loc[common].values
        x_c = (x_c - x_c.mean())
        denom = (x_c * x_c).sum()
        if denom == 0:
            continue
        b = (x_c * (y_c - y_c.mean())).sum() / denom
        resid = (y_c - y_c.mean()) - b * x_c
        out.loc[d, common] = resid
    return out


def build_factors(df):
    close = to_wide(df, "close")
    rets = to_wide(df, "ret")

    f1 = range_pos(close, 252)
    f2 = range_pos(close, 120)
    f3 = range_pos(close, 60)

    # F4: equal-rank average across windows
    r1 = f1.rank(axis=1, pct=True)
    r2 = f2.rank(axis=1, pct=True)
    r3 = f3.rank(axis=1, pct=True)
    f4 = (r1 + r2 + r3) / 3.0

    # F5: divided by vol_60 (annualized)
    vol_60 = rets.rolling(60, min_periods=45).std() * np.sqrt(252)
    f5 = f1 / vol_60.replace(0, np.nan)

    # F6: regime gate on bench
    bench = close[BENCH] if BENCH in close.columns else None
    if bench is not None:
        ma200 = bench.rolling(200, min_periods=180).mean()
        gate = (bench > ma200).astype(float)
        gate_aligned = pd.DataFrame(
            {s: gate.values for s in close.columns}, index=close.index
        )
        f6 = f1 * gate_aligned
    else:
        f6 = f1.copy()

    # F7: residualize F1 against 252d momentum
    mom_252 = rets.rolling(252, min_periods=200).sum()
    f7 = residualize_xs_daily(f1, mom_252)

    # F8 = F1 (different rebal applied at eval time)
    f8 = f1.copy()

    return {
        "F1": ("range_pos_252", f1, REBAL_DEFAULT),
        "F2": ("range_pos_120", f2, REBAL_DEFAULT),
        "F3": ("range_pos_60", f3, REBAL_DEFAULT),
        "F4": ("multi_window_rank", f4, REBAL_DEFAULT),
        "F5": ("range_pos_252_div_vol60", f5, REBAL_DEFAULT),
        "F6": ("range_pos_252_MA200_gate", f6, REBAL_DEFAULT),
        "F7": ("range_pos_252_resid_mom", f7, REBAL_DEFAULT),
        "F8": ("range_pos_252_rebal42", f8, 42),
    }


def eval_one(name: str, sig: pd.DataFrame, fwd_k: pd.DataFrame, fwd_1: pd.DataFrame,
             k: int, rebal: int):
    valid = sig.dropna(how="all").index.intersection(fwd_k.dropna(how="all").index)
    if len(valid) < 100:
        return None
    sig_v = sig.loc[valid]
    fwd_v = fwd_k.loc[valid]
    fwd1_v = fwd_1.loc[valid]

    # IC at multiple horizons
    sig_r = sig_v.rank(axis=1)
    fwd_r = fwd_v.rank(axis=1)
    ic_daily = sig_r.corrwith(fwd_r, axis=1)
    ic_mean = float(ic_daily.mean())
    ic_std = float(ic_daily.std())
    ic_ir = ic_mean / ic_std * np.sqrt(252 / k) if ic_std > 0 else float("nan")

    fwd5 = fwd1_v.rolling(5).sum().shift(-(DELAY + 5))
    fwd10 = fwd1_v.rolling(10).sum().shift(-(DELAY + 10))
    ic1 = sig_v.rank(axis=1).corrwith(fwd1_v.shift(-(DELAY + 1)).rank(axis=1), axis=1).mean()
    ic5 = sig_v.rank(axis=1).corrwith(fwd5.rank(axis=1), axis=1).mean()
    ic10 = sig_v.rank(axis=1).corrwith(fwd10.rank(axis=1), axis=1).mean()

    sig_rebal = sig_v.iloc[::rebal]
    fwd_rebal = fwd_v.iloc[::rebal]

    ls, _, _, qtop, _ = quintile_LS(sig_rebal, fwd_rebal)
    ex3, _, sel3 = top_n_long_excess(sig_rebal, fwd_rebal, 3)
    ex5, _, sel5 = top_n_long_excess(sig_rebal, fwd_rebal, 5)

    sharpe_ls = annualize_sharpe(ls, k)
    sharpe_ex3 = annualize_sharpe(ex3, k)
    sharpe_ex5 = annualize_sharpe(ex5, k)

    ls_net = apply_cost(ls, qtop.astype(float), COST_BPS, rebal)
    ex3_net = apply_cost(ex3, sel3.astype(float), COST_BPS, rebal)
    ex5_net = apply_cost(ex5, sel5.astype(float), COST_BPS, rebal)

    sharpe_ls_net = annualize_sharpe(ls_net, k)
    sharpe_ex3_net = annualize_sharpe(ex3_net, k)
    sharpe_ex5_net = annualize_sharpe(ex5_net, k)

    py_ls = per_year_sharpe(ls.dropna(), k)
    py_ex3 = per_year_sharpe(ex3.dropna(), k)
    py_ex5 = per_year_sharpe(ex5.dropna(), k)

    train_mask = ls.index <= TRAIN_END
    val_mask = (ls.index > TRAIN_END) & (ls.index <= VAL_END)
    test_mask = ls.index > VAL_END
    sharpe_train = annualize_sharpe(ls[train_mask], k)
    sharpe_val = annualize_sharpe(ls[val_mask], k)
    sharpe_test = annualize_sharpe(ls[test_mask], k)

    cost_grid = []
    for c in (0, 5, 10, 20):
        ls_c = apply_cost(ls, qtop.astype(float), c, rebal)
        ex3_c = apply_cost(ex3, sel3.astype(float), c, rebal)
        ex5_c = apply_cost(ex5, sel5.astype(float), c, rebal)
        cost_grid.append({
            "cost_bps": c,
            "sharpe_ls": annualize_sharpe(ls_c, k),
            "sharpe_top3": annualize_sharpe(ex3_c, k),
            "sharpe_top5": annualize_sharpe(ex5_c, k),
        })

    py_full = py_ls.dropna()
    if len(py_full) >= 2:
        worst = float(py_full.min())
        best_year = py_full.idxmax()
        sharpe_no_best = annualize_sharpe(ls[ls.index.year != best_year], k)
    else:
        worst = float("nan")
        sharpe_no_best = float("nan")

    return {
        "name": name,
        "ic_k1": float(ic1), "ic_k5": float(ic5), "ic_k10": float(ic10),
        "ic_mean_k20": ic_mean, "ic_ir_k20": ic_ir,
        "sharpe_ls_gross": sharpe_ls, "sharpe_ls_net5": sharpe_ls_net,
        "sharpe_top3_gross": sharpe_ex3, "sharpe_top3_net5": sharpe_ex3_net,
        "sharpe_top5_gross": sharpe_ex5, "sharpe_top5_net5": sharpe_ex5_net,
        "turnover_q5_ann": turnover_ann(qtop.astype(float), rebal),
        "turnover_top3_ann": turnover_ann(sel3.astype(float), rebal),
        "turnover_top5_ann": turnover_ann(sel5.astype(float), rebal),
        "sharpe_train_ls": sharpe_train,
        "sharpe_val_ls": sharpe_val,
        "sharpe_test_ls": sharpe_test,
        "worst_year_ls": worst,
        "best_year_dropped_sharpe_ls": sharpe_no_best,
        "py_ls": py_ls.to_dict(),
        "py_top3": py_ex3.to_dict(),
        "py_top5": py_ex5.to_dict(),
        "cost_grid": cost_grid,
        "rebal": rebal,
    }


def main():
    df = load_panel()
    factors = build_factors(df)
    rets = to_wide(df, "ret")
    fwd_k = fwd_ret(rets, PRIMARY_K)

    summary_rows, py_rows, cost_rows = [], [], []
    floors = {}
    results = {}
    for fid, (label, fac, rebal) in factors.items():
        r = eval_one(fid, fac, fwd_k, rets, PRIMARY_K, rebal)
        if r is None:
            continue
        results[fid] = r
        summary_rows.append({
            "id": fid, "label": label, "rebal": rebal,
            "ic_k1": r["ic_k1"], "ic_k5": r["ic_k5"], "ic_k10": r["ic_k10"],
            "ic_mean_k20": r["ic_mean_k20"], "ic_ir_k20": r["ic_ir_k20"],
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
        floors[fid] = {
            "ls_net5_sharpe": r["sharpe_ls_net5"],
            "ls_net5_pass": r["sharpe_ls_net5"] >= 0.5,
            "worst_year": r["worst_year_ls"],
            "worst_year_pass": (
                r["worst_year_ls"] >= 0.5 if not pd.isna(r["worst_year_ls"]) else False
            ),
            "best_year_out": r["best_year_dropped_sharpe_ls"],
            "best_year_out_pct": (
                r["best_year_dropped_sharpe_ls"] / r["sharpe_ls_gross"]
                if r["sharpe_ls_gross"] not in (0,) else float("nan")
            ),
            "best_year_out_pass": (
                r["best_year_dropped_sharpe_ls"] >= 0.5 * r["sharpe_ls_gross"]
                if r["sharpe_ls_gross"] > 0 else False
            ),
            "train_pass": r["sharpe_train_ls"] >= 0.4 if not pd.isna(r["sharpe_train_ls"]) else False,
            "test_pass": r["sharpe_test_ls"] >= 0.4 if not pd.isna(r["sharpe_test_ls"]) else False,
        }
        floors[fid]["all_promote_floors_pass"] = all([
            floors[fid]["ls_net5_pass"],
            floors[fid]["worst_year_pass"],
            floors[fid]["best_year_out_pass"],
            floors[fid]["train_pass"],
            floors[fid]["test_pass"],
        ])

    pd.DataFrame(summary_rows).to_csv(OUT / "r2_summary_batch_0002.csv", index=False)
    pd.DataFrame(py_rows).to_csv(OUT / "r2_per_year_batch_0002.csv", index=False)
    pd.DataFrame(cost_rows).to_csv(OUT / "r2_cost_sensitivity_batch_0002.csv", index=False)
    with open(OUT / "r2_floors_batch_0002.json", "w") as f:
        json.dump(floors, f, indent=2, default=lambda x: None if pd.isna(x) else x)

    md = ["# Backtest Results — batch_0002 (R2 E3-centric variants)\n"]
    md.append(f"\nUniverse: 32 ETFs | period: {df.date.min():%Y-%m-%d} → {df.date.max():%Y-%m-%d}\n")
    md.append(f"\ndelay={DELAY} | k={PRIMARY_K} | cost={COST_BPS} bps/side\n")
    md.append("\n## Summary table\n")
    md.append(pd.DataFrame(summary_rows).round(4).to_markdown(index=False))
    md.append("\n\n## Floors check (PROMOTE)\n")
    md.append(pd.DataFrame(floors).T.round(3).to_markdown())
    md.append("\n\n## Per-year LS Sharpe (gross)\n")
    py_df = pd.DataFrame(py_rows)
    py_ls = py_df[py_df["metric"] == "ls"].pivot(index="id", columns="year", values="sharpe").round(2)
    md.append(py_ls.to_markdown())
    md.append("\n\n## Per-year top-5 long-only excess Sharpe\n")
    py_top5 = py_df[py_df["metric"] == "top5_excess"].pivot(index="id", columns="year", values="sharpe").round(2)
    md.append(py_top5.to_markdown())

    with open(OUT / "r2_backtest_results_batch_0002.md", "w") as f:
        f.write("\n".join(str(x) for x in md))

    print("Wrote R2 outputs.")
    return floors


if __name__ == "__main__":
    main()
