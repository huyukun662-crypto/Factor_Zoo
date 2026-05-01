#!/usr/bin/env python3
"""inv_ivol_ls_voltarget_etf_v1 — production reference implementation.

Inverted IVOL on A-share thematic ETFs, long-short Q5/Q1, monthly rebalance,
dynamically sized to 10% annualized vol target.

Sign convention: high IVOL → long. Direction inverted from classical
Ang-Hodrick-Xing-Zhang because A-share thematic ETFs are narrative buckets;
high-IVOL ETFs are the marginally-bid lottery tickets, not the over-priced
stocks of the AHXZ stock-level finding.

Inputs:
  panel: DataFrame with columns [date, symbol, close, ret] (ret = pct_change of close)

Universe (30 A-share ETFs after dropping 4 truncated tickers in 2025):
  broad-index 8 + thematic 21 + commodity 1.

Reproducibility: pure pandas, no external state. Look-ahead-clean (rolling
windows backward, vol-target uses shift(1) on exposure).

Deployable as RESEARCH-ONLY standalone (worst-year 2022 = +0.16 misses
the 0.5 floor); deploys best as a 0.5/0.5 weekly overlay on V7_gold or V25
(see logs/20260501_a_share_etf_ivol_momentum_v1/outputs/v25_addendum.md).
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

# ---- defaults ----
DROPPED_TICKERS = {"512100.SS", "515050.SS", "515170.SS", "512800.SS"}
BENCH = "510300.SS"
BETA_WINDOW_DAYS = 60
IVOL_WINDOW_DAYS = 20
PRIMARY_K = 20            # monthly rebalance horizon
DELAY = 1                 # signal at close(t) → trade at close(t+1)
COST_BPS_PER_SIDE = 5.0
VOL_TARGET_ANN = 0.10
VOL_TARGET_WINDOW_DAYS = 60
MAX_LEVERAGE = 2.0
N_QUINTILES = 5


# ---- helpers ----

def _wide(panel: pd.DataFrame, col: str) -> pd.DataFrame:
    return panel.pivot(index="date", columns="symbol", values=col).sort_index()


def _rolling_beta(rets: pd.DataFrame, bench: pd.Series, w: int) -> pd.DataFrame:
    cov = rets.rolling(w).cov(bench)
    var = bench.rolling(w).var()
    return cov.div(var, axis=0)


def compute_signal(panel: pd.DataFrame,
                   bench: str = BENCH,
                   beta_w: int = BETA_WINDOW_DAYS,
                   ivol_w: int = IVOL_WINDOW_DAYS,
                   dropped: set[str] = DROPPED_TICKERS) -> pd.DataFrame:
    """Compute the inverted-IVOL signal (high signal = long)."""
    panel = panel[~panel.symbol.isin(dropped)].copy()
    rets = _wide(panel, "ret")
    if bench not in rets.columns:
        raise KeyError(f"Benchmark {bench} not in panel")
    b = rets[bench]
    beta = _rolling_beta(rets, b, beta_w)
    eps = rets.sub(beta.mul(b, axis=0))
    ivol = eps.rolling(ivol_w).std() * np.sqrt(252)
    return ivol  # positive: high IVOL = long


def quintile_LS_returns(signal: pd.DataFrame,
                         rets: pd.DataFrame,
                         k: int = PRIMARY_K,
                         delay: int = DELAY,
                         n_q: int = N_QUINTILES) -> dict[str, pd.Series]:
    """Long top-quintile, short bottom-quintile, equal-weighted within leg.
    Returns dict with 'ls' (long-short), 'longonly', 'rank' (cross-sectional rank)."""
    fwd = rets.rolling(k).sum().shift(-(delay + k))
    rk = signal.rank(axis=1, pct=True)
    q_top = rk >= (n_q - 1) / n_q
    q_bot = rk < 1 / n_q
    n_top = q_top.sum(axis=1).replace(0, np.nan)
    n_bot = q_bot.sum(axis=1).replace(0, np.nan)
    long_ret = (q_top.astype(float).where(q_top) * fwd).sum(axis=1) / n_top
    short_ret = (q_bot.astype(float).where(q_bot) * fwd).sum(axis=1) / n_bot
    ls = long_ret - short_ret
    return {"ls": ls, "longonly": long_ret, "shortleg": short_ret, "rank": rk,
            "q5": q_top, "q1": q_bot}


def vol_target_overlay(ret_series: pd.Series,
                       k: int = PRIMARY_K,
                       target_ann_vol: float = VOL_TARGET_ANN,
                       vol_window_days: int = VOL_TARGET_WINDOW_DAYS,
                       max_lev: float = MAX_LEVERAGE) -> tuple[pd.Series, pd.Series]:
    """Scale return series to target annualized vol. Exposure is shifted by 1
    so the next period's exposure is decided from past data only."""
    daily_vol = ret_series.rolling(vol_window_days).std() * np.sqrt(252 / k)
    exposure = (target_ann_vol / daily_vol).clip(upper=max_lev).shift(1)
    return ret_series * exposure, exposure


def cost_drag_LS(rk: pd.DataFrame,
                 cost_bps_side: float = COST_BPS_PER_SIDE,
                 rebalance_days: int = 21,
                 n_q: int = N_QUINTILES) -> pd.Series:
    """Estimate per-period cost drag from quintile membership churn."""
    cost = cost_bps_side / 10000.0
    q_top = (rk >= (n_q - 1) / n_q).astype(int)
    q_bot = (rk < 1 / n_q).astype(int)
    if rebalance_days > 1:
        idx = q_top.index[::rebalance_days]
        q_top = q_top.loc[idx]
        q_bot = q_bot.loc[idx]
    long_to = q_top.diff().abs().sum(axis=1) / 2 / q_top.sum(axis=1).replace(0, np.nan)
    short_to = q_bot.diff().abs().sum(axis=1) / 2 / q_bot.sum(axis=1).replace(0, np.nan)
    return ((long_to.fillna(0) + short_to.fillna(0)) * cost * 2).reindex(rk.index, method="ffill").fillna(0)


@dataclass
class FactorResult:
    raw_LS_ret: pd.Series
    voltarget_LS_ret: pd.Series
    voltarget_LS_ret_net5bps: pd.Series
    exposure: pd.Series
    rank: pd.DataFrame
    signal: pd.DataFrame


def run(panel: pd.DataFrame) -> FactorResult:
    """Full pipeline: panel → vol-target-scaled long-short return."""
    panel = panel[~panel.symbol.isin(DROPPED_TICKERS)].copy()
    rets = _wide(panel, "ret")
    sig = compute_signal(panel)
    qres = quintile_LS_returns(sig, rets)
    raw = qres["ls"]
    vt_ret, exposure = vol_target_overlay(raw)
    drag = cost_drag_LS(qres["rank"]) * exposure
    vt_net = vt_ret.sub(drag.reindex(vt_ret.index).fillna(0))
    return FactorResult(raw_LS_ret=raw, voltarget_LS_ret=vt_ret,
                        voltarget_LS_ret_net5bps=vt_net, exposure=exposure,
                        rank=qres["rank"], signal=sig)


# ---- self-test / reproducibility ----
if __name__ == "__main__":
    from pathlib import Path
    PANEL = Path("/home/user/Factor_Zoo/logs/_shared_cache/etf_daily.parquet")
    panel = pd.read_parquet(PANEL)
    panel["ret"] = panel.groupby("symbol")["close"].pct_change()
    res = run(panel)
    s = res.voltarget_LS_ret_net5bps.dropna()

    def ann_sharpe(s, k=PRIMARY_K):
        return float(s.mean() / s.std() * np.sqrt(252 / k))

    print(f"vol-target LS net@5bps Sharpe: {ann_sharpe(s):.2f}")
    print(f"avg exposure: {res.exposure.mean():.2f}")
    print()
    print("per-year Sharpe:")
    yr = s.groupby(s.index.year).apply(lambda x: ann_sharpe(x))
    print(yr.round(2).to_string())
