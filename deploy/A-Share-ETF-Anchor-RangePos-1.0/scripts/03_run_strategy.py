"""
03_run_strategy.py — End-to-end backtest of the anchor / range-position
ETF strategy (long-only top-3, 21-phase ensemble, 10% vol-target).

Pipeline:
  1. Load signal from 02_build_signal.py
  2. 21-phase ensemble: each trading day deploy 1/21 NAV equally across
     the top-3 ETFs by signal; hold 21 days; sum across phases.
  3. Net of 5 bps/side cost (charged per phase rebal day).
  4. Compute excess vs equal-weight 20-ETF benchmark.
  5. Apply 10% vol-target overlay using yesterday's trailing 60d vol.
  6. Write metrics.json, peryear.csv, monthly.csv, pnl.csv, holdings.csv.
"""
from __future__ import annotations
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
CACHE = HERE / "data_cache"
OUT = HERE / "results"; OUT.mkdir(parents=True, exist_ok=True)

REBAL = 21
N_TOP = 3
COST_BPS = 5.0
TARGET_VOL = 0.10
VOL_LB = 60
LEVERAGE_CAP = 2.0
SKIP_WARMUP_YEAR = 2020

TRAIN_END = pd.Timestamp("2021-12-31")
VAL_END = pd.Timestamp("2022-12-30")


def say(s: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)


def annualize_sharpe(daily: pd.Series, k: int = 1, min_obs: int = 20) -> float:
    x = daily.dropna()
    if len(x) < min_obs or x.std() == 0:
        return float("nan")
    return float(x.mean() / x.std() * np.sqrt(252 / k))


def phase_ensemble_long_only(
    sig: pd.DataFrame, ret_d: pd.DataFrame,
    n: int, rebal: int, cost_bps: float,
    universe: list[str],
):
    sig = sig[universe]
    ret_d = ret_d[universe]
    dates = sig.index

    weights_total = pd.DataFrame(0.0, index=dates, columns=universe)
    cost_daily = pd.Series(0.0, index=dates)
    holdings_log = []  # (rebal_date, phase, top_n_list)

    for phase in range(rebal):
        rebal_dates = dates[phase::rebal]
        prev_w = pd.Series(0.0, index=universe)
        for i, rd in enumerate(rebal_dates):
            top = sig.loc[rd].dropna().nlargest(n).index.tolist()
            if len(top) < n:
                new_w = prev_w.copy()
            else:
                new_w = pd.Series(0.0, index=universe)
                for s in top:
                    new_w[s] = 1.0 / n
            holdings_log.append({
                "rebal_date": rd.strftime("%Y-%m-%d"),
                "phase": phase,
                "top_n": ";".join(top) if top else "",
            })

            turnover = (new_w - prev_w).abs().sum() / 2.0
            cost_daily.loc[rd] += turnover * (cost_bps / 1e4) / rebal

            end_idx = rebal_dates[i + 1] if i + 1 < len(rebal_dates) else dates[-1] + pd.Timedelta(days=1)
            mask = (dates >= rd) & (dates < end_idx)
            for s in universe:
                if new_w[s] != 0:
                    weights_total.loc[mask, s] += new_w[s] / rebal
            prev_w = new_w

    portfolio_gross = (weights_total * ret_d).sum(axis=1)
    portfolio_net = portfolio_gross - cost_daily
    bench = ret_d.mean(axis=1)
    return portfolio_gross, portfolio_net, bench, weights_total, cost_daily, holdings_log


def vol_target_overlay(excess: pd.Series) -> pd.Series:
    rv = excess.rolling(VOL_LB, min_periods=int(VOL_LB * 0.8)).std() * np.sqrt(252)
    scale = (TARGET_VOL / rv).clip(upper=LEVERAGE_CAP).shift(1)
    return excess * scale


def main() -> None:
    panel_path = CACHE / "etf_daily.parquet"
    sig_path = CACHE / "signal.parquet"
    uni_path = CACHE / "core_universe.json"
    for p in (panel_path, sig_path, uni_path):
        if not p.exists():
            raise FileNotFoundError(f"missing {p}; run 01 and 02 first.")

    say("Loading panel and signal ...")
    df = pd.read_parquet(panel_path)
    df = df.sort_values(["date", "symbol"]).reset_index(drop=True)
    df["ret"] = df.groupby("symbol")["close"].pct_change()
    rets = df.pivot(index="date", columns="symbol", values="ret").sort_index()
    sig = pd.read_parquet(sig_path).sort_index()

    with open(uni_path) as f:
        meta = json.load(f)
    universe = meta["symbols"]
    say(f"Universe: {len(universe)} symbols")

    say("Running 21-phase ensemble ...")
    gross, net, bench, weights, cost_d, holdings_log = phase_ensemble_long_only(
        sig, rets, n=N_TOP, rebal=REBAL, cost_bps=COST_BPS, universe=universe,
    )

    say("Applying 10% vol-target overlay on excess ...")
    excess_pre = net - bench
    excess = vol_target_overlay(excess_pre)
    portfolio = excess + bench

    valid = excess.dropna().index
    valid = valid[valid.year >= SKIP_WARMUP_YEAR]
    excess = excess.loc[valid]
    portfolio = portfolio.loc[valid]
    bench = bench.loc[valid]

    # ---------- metrics ----------
    say("Computing metrics ...")
    ann_factor = 252 / max((excess.index[-1] - excess.index[0]).days / 365.25, 1) * 1.0
    ann_ret_excess = float(excess.sum() / (len(excess) / 252))
    ann_ret_portfolio = float(portfolio.sum() / (len(portfolio) / 252))
    ann_ret_bench = float(bench.sum() / (len(bench) / 252))

    cum_excess = (1 + excess).cumprod()
    peak = cum_excess.cummax()
    dd = cum_excess / peak - 1
    max_dd = float(dd.min())
    max_dd_date = dd.idxmin().strftime("%Y-%m-%d")

    py = excess.groupby(excess.index.year).apply(lambda x: annualize_sharpe(x))
    n_pos = int((py > 0).sum())
    n_total = int(py.notna().sum())

    train = excess[excess.index <= TRAIN_END]
    val = excess[(excess.index > TRAIN_END) & (excess.index <= VAL_END)]
    test = excess[excess.index > VAL_END]

    metrics = {
        "factor_id": "anchor_range_pos_etf_v1",
        "deploy_version": "1.0",
        "panel_dates": [str(df.date.min().date()), str(df.date.max().date())],
        "evaluation_dates": [str(excess.index[0].date()), str(excess.index[-1].date())],
        "universe_size": len(universe),
        "config": {
            "rebal_days": REBAL, "n_top": N_TOP, "cost_bps_per_side": COST_BPS,
            "target_vol_ann": TARGET_VOL, "vol_lookback": VOL_LB,
            "leverage_cap": LEVERAGE_CAP, "delay": 1,
        },
        "headline": {
            "sharpe_excess_net5bps": annualize_sharpe(excess),
            "sharpe_portfolio_net5bps": annualize_sharpe(portfolio),
            "sharpe_bench": annualize_sharpe(bench),
            "ann_ret_excess_net5bps": ann_ret_excess,
            "ann_ret_portfolio_net5bps": ann_ret_portfolio,
            "ann_ret_bench": ann_ret_bench,
            "max_dd_excess": max_dd,
            "max_dd_date": max_dd_date,
            "n_pos_years": n_pos,
            "n_total_years": n_total,
            "frac_pos_years": n_pos / max(n_total, 1),
            "worst_year_sharpe": float(py.min()),
        },
        "tvt_split": {
            "train":    {"start": str(train.index[0].date()) if len(train) else None,
                         "end":   str(train.index[-1].date()) if len(train) else None,
                         "sharpe_excess": annualize_sharpe(train)},
            "validate": {"start": str(val.index[0].date())   if len(val)   else None,
                         "end":   str(val.index[-1].date())   if len(val)   else None,
                         "sharpe_excess": annualize_sharpe(val)},
            "test":     {"start": str(test.index[0].date())  if len(test)  else None,
                         "end":   str(test.index[-1].date())  if len(test)  else None,
                         "sharpe_excess": annualize_sharpe(test)},
        },
    }
    with open(OUT / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    say(f"  net excess Sharpe = {metrics['headline']['sharpe_excess_net5bps']:.3f}")
    say(f"  test       Sharpe = {metrics['tvt_split']['test']['sharpe_excess']:.3f}")
    say(f"  worst-year Sharpe = {metrics['headline']['worst_year_sharpe']:.3f}")
    say(f"  max DD            = {metrics['headline']['max_dd_excess']:.1%}")

    # ---------- peryear.csv ----------
    rows = []
    for yr, grp in excess.groupby(excess.index.year):
        rows.append({
            "year": int(yr),
            "n_days": len(grp),
            "sharpe_excess_net": annualize_sharpe(grp),
            "sharpe_portfolio_net": annualize_sharpe(portfolio.loc[grp.index]),
            "sharpe_bench": annualize_sharpe(bench.loc[grp.index]),
            "ann_ret_excess": float(grp.sum()),
            "ann_ret_portfolio": float(portfolio.loc[grp.index].sum()),
            "ann_ret_bench": float(bench.loc[grp.index].sum()),
        })
    pd.DataFrame(rows).to_csv(OUT / "peryear.csv", index=False)

    # ---------- monthly.csv ----------
    monthly_excess = excess.resample("ME").sum()
    monthly_port = portfolio.resample("ME").sum()
    monthly_bench = bench.resample("ME").sum()
    monthly = pd.DataFrame({
        "month": monthly_excess.index.strftime("%Y-%m"),
        "excess": monthly_excess.values,
        "portfolio": monthly_port.values,
        "bench": monthly_bench.values,
    })
    monthly.to_csv(OUT / "monthly.csv", index=False)

    # ---------- pnl.csv ----------
    pnl = pd.DataFrame({
        "date": excess.index.strftime("%Y-%m-%d"),
        "excess": excess.values,
        "portfolio": portfolio.values,
        "bench": bench.values,
        "cum_excess": (1 + excess).cumprod().values,
        "drawdown_excess": dd.values,
    })
    pnl.to_csv(OUT / "pnl.csv", index=False)

    # ---------- holdings.csv ----------
    pd.DataFrame(holdings_log).to_csv(OUT / "holdings.csv", index=False)

    say(f"Wrote results in {OUT}")


if __name__ == "__main__":
    main()
