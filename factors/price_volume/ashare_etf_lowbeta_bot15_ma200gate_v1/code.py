#!/usr/bin/env python3
"""Reproducer for ashare_etf_lowbeta_bot15_ma200gate_v1.

Loads the Tushare cache and rebuilds the factor + daily P&L. All values
should match `factor_signals.parquet` and the per-year Sharpe in
`annual.csv` modulo float rounding.

Usage (from repo root):
    python3 factors/price_volume/ashare_etf_lowbeta_bot15_ma200gate_v1/code.py
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / "logs/_shared_cache/etf_daily_tushare.parquet"
HERE  = Path(__file__).parent

DELAY = 1
HOLD_DAYS = 21
COST_BPS = 5e-4
TOPN = 15
BETA_K = 60
MA_GATE = 200
BENCH = "510300.SH"
MIN_BARS = 1500
MIN_AVG_AMOUNT = 5e4   # CNY 1000-units → 50M CNY/day


def load_panel():
    df = pd.read_parquet(CACHE)
    counts = df.groupby("symbol").size()
    keep = set(counts[counts >= MIN_BARS].index)
    avg_amt = df.groupby("symbol").amount.mean()
    keep &= set(avg_amt[avg_amt >= MIN_AVG_AMOUNT].index)
    df = df[df.symbol.isin(keep)]
    P = df.pivot(index="date", columns="symbol", values="close").sort_index()
    return P


def build_factor(P):
    log_ret = np.log(P).diff()
    rb = log_ret[BENCH]
    cov = log_ret.rolling(BETA_K).cov(rb)
    var = rb.rolling(BETA_K).var()
    beta = cov.div(var.replace(0, np.nan), axis=0)
    abs_beta = beta.abs()

    px = P[BENCH]
    ma = px.rolling(MA_GATE).mean()
    regime = (px > ma).astype(float)

    idx = P.index
    me = pd.DatetimeIndex(sorted(
        pd.Series(idx, index=idx).groupby([idx.year, idx.month]).max().values))

    W_me = pd.DataFrame(0.0, index=me, columns=P.columns)
    for t in me:
        if t not in abs_beta.index:
            continue
        s = abs_beta.loc[t].dropna()
        active = P.loc[t].dropna().index
        s = s.loc[s.index.intersection(active)]
        if len(s) < TOPN:
            continue
        sel = s.nsmallest(TOPN).index
        w = pd.Series(0.0, index=P.columns)
        w.loc[sel] = 1.0 / TOPN
        if t in regime.index:
            w *= float(regime.loc[t])
        W_me.loc[t] = w.values

    # broadcast to daily (weight effective from close[t_me+1] onward)
    W_d = pd.DataFrame(0.0, index=idx, columns=P.columns)
    me_pos = idx.get_indexer(me)
    for k, pos in enumerate(me_pos):
        if pos < 0 or pos + 1 >= len(idx):
            continue
        start = pos + 1
        end_pos = me_pos[k+1] + 1 if k + 1 < len(me_pos) else len(idx)
        end_pos = min(end_pos, len(idx))
        W_d.loc[idx[start]:idx[end_pos-1], :] = W_me.loc[me[k]].values
    return W_me, W_d, abs_beta, regime


def backtest(W_d, P):
    log_ret = np.log(P).diff()
    gross = (W_d * log_ret).sum(axis=1)
    dW = W_d.diff().abs().sum(axis=1) / 2.0
    net = gross - dW * COST_BPS
    return gross, net


def annualised_sharpe(s):
    s = s.dropna()
    if s.std() == 0 or len(s) < 50:
        return 0.0
    return float(np.sqrt(252) * s.mean() / s.std())


if __name__ == "__main__":
    P = load_panel()
    print(f"[load] {P.shape[1]} ETFs, {P.shape[0]} dates")
    W_me, W_d, abs_beta, regime = build_factor(P)
    gross, net = backtest(W_d, P)
    ew = np.log(P).diff().mean(axis=1)
    print(f"[winner ] gross Sharpe = {annualised_sharpe(gross):.3f}, "
          f"net = {annualised_sharpe(net):.3f}, "
          f"MDD = {(np.exp(net.cumsum()) / np.exp(net.cumsum()).cummax() - 1).min():.3f}")
    print(f"[ew     ] Sharpe = {annualised_sharpe(ew):.3f}")
    py = net.dropna().groupby(net.index.year).apply(annualised_sharpe)
    print("[per-year net Sharpe]")
    print(py.round(3).to_string())
