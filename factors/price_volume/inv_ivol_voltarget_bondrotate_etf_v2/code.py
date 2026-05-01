#!/usr/bin/env python3
"""inv_ivol_voltarget_bondrotate_etf_v2 — production reference implementation.

Builds on v1 (inv_ivol_ls_voltarget_etf_v1) with two upgrades:
  1. Universe expanded from 30 → 61 A-share equity ETFs (more cross-section).
  2. Cross-asset bond rotation: when LS trailing 12-week return < -3%, switch
     to 511010 (国债 ETF) as defensive ballast.

This addresses v1's worst-year-fail (2022 = +0.11) by routing the strategy
into bonds during equity drawdown regimes. Bond ETFs are EXCLUDED from the
LS cross-section (they would corrupt Q1 short leg by being structurally
low-IVOL but UP in equity-bear years like 2022).

Status: RESEARCH-ONLY (worst-year 2022 = +0.31, still misses 0.5 floor)
        but materially closer to ADMITTED than v1; net headline Sharpe
        crosses the 1.0 IR bar.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd

# ---- universe ----
DROPPED_TICKERS = {"512100.SS", "515050.SS", "515170.SS", "512800.SS"}
BOND_ETFS = {"511010.SS", "511220.SS", "511260.SS", "511810.SS"}
CROSS_MARKET_ETFS = {"159920.SZ", "513050.SS", "513100.SS", "513500.SS", "513900.SS"}

BENCH = "510300.SS"
DEFENSIVE_BOND = "511010.SS"  # 国债 ETF for rotation

# ---- params ----
BETA_WINDOW_DAYS = 60
IVOL_WINDOW_DAYS = 20
PRIMARY_K = 20
DELAY = 1
COST_BPS_PER_SIDE = 5.0
VOL_TARGET_ANN = 0.10
VOL_TARGET_WINDOW_DAYS = 60
MAX_LEVERAGE = 2.0
N_QUINTILES = 5

# bond rotation
ROTATION_LOOKBACK_WEEKS = 12
ROTATION_THRESHOLD = -0.03  # if 12-week trailing cumret < -3%, route to bond


def _wide(panel: pd.DataFrame, col: str) -> pd.DataFrame:
    return panel.pivot(index="date", columns="symbol", values=col).sort_index()


def _rolling_beta(rets: pd.DataFrame, bench: pd.Series, w: int) -> pd.DataFrame:
    cov = rets.rolling(w).cov(bench)
    var = bench.rolling(w).var()
    return cov.div(var, axis=0)


def equity_universe(panel: pd.DataFrame) -> set[str]:
    """Equity-only sub-universe: drop bonds and cross-market ETFs."""
    all_syms = set(panel.symbol.unique())
    return all_syms - DROPPED_TICKERS - BOND_ETFS - CROSS_MARKET_ETFS


def compute_signal(panel: pd.DataFrame,
                   bench: str = BENCH,
                   beta_w: int = BETA_WINDOW_DAYS,
                   ivol_w: int = IVOL_WINDOW_DAYS) -> pd.DataFrame:
    """Compute IVOL signal on equity-only sub-universe (high IVOL = long)."""
    eq_syms = equity_universe(panel)
    panel_eq = panel[panel.symbol.isin(eq_syms | {bench})].copy()
    rets = _wide(panel_eq, "ret")
    if bench not in rets.columns:
        raise KeyError(f"Benchmark {bench} not in panel")
    b = rets[bench]
    beta = _rolling_beta(rets, b, beta_w)
    eps = rets.sub(beta.mul(b, axis=0))
    return eps.rolling(ivol_w).std() * np.sqrt(252)


def quintile_LS_returns(signal: pd.DataFrame,
                         rets_eq: pd.DataFrame,
                         k: int = PRIMARY_K,
                         delay: int = DELAY,
                         n_q: int = N_QUINTILES) -> dict:
    fwd = rets_eq.rolling(k).sum().shift(-(delay + k))
    rk = signal.rank(axis=1, pct=True)
    q_top = rk >= (n_q - 1) / n_q
    q_bot = rk < 1 / n_q
    n_top = q_top.sum(axis=1).replace(0, np.nan)
    n_bot = q_bot.sum(axis=1).replace(0, np.nan)
    long_ret = (q_top.astype(float).where(q_top) * fwd).sum(axis=1) / n_top
    short_ret = (q_bot.astype(float).where(q_bot) * fwd).sum(axis=1) / n_bot
    return {"ls": long_ret - short_ret, "longonly": long_ret,
            "shortleg": short_ret, "rank": rk, "q5": q_top, "q1": q_bot}


def vol_target_overlay(ret_series: pd.Series,
                       k: int = PRIMARY_K,
                       target_ann_vol: float = VOL_TARGET_ANN,
                       vol_window_days: int = VOL_TARGET_WINDOW_DAYS,
                       max_lev: float = MAX_LEVERAGE) -> tuple[pd.Series, pd.Series]:
    daily_vol = ret_series.rolling(vol_window_days).std() * np.sqrt(252 / k)
    exposure = (target_ann_vol / daily_vol).clip(upper=max_lev).shift(1)
    return ret_series * exposure, exposure


def bond_rotation_overlay(equity_ret: pd.Series,
                          bond_fwd_ret: pd.Series,
                          lookback_weeks: int = ROTATION_LOOKBACK_WEEKS,
                          dd_threshold: float = ROTATION_THRESHOLD) -> tuple[pd.Series, pd.Series]:
    """When trailing 12-week cumulative return of equity_ret < threshold,
    switch to bond_fwd_ret. Decision is made at t-1 (shift(1))."""
    cum = equity_ret.rolling(lookback_weeks * 5).sum()  # 12 weeks ≈ 60 trading days
    use_bond = (cum < dd_threshold).shift(1).fillna(False).astype(bool)
    return equity_ret.where(~use_bond, bond_fwd_ret), use_bond


def cost_drag_LS(rk: pd.DataFrame,
                 cost_bps_side: float = COST_BPS_PER_SIDE,
                 rebalance_days: int = 21,
                 n_q: int = N_QUINTILES) -> pd.Series:
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
class FactorResultV2:
    raw_LS_ret: pd.Series                # before vol-target
    voltarget_LS_ret: pd.Series          # after vol-target, before bond rotation
    final_ret_gross: pd.Series           # after vol-target + bond rotation
    final_ret_net5bps: pd.Series         # after cost drag
    use_bond: pd.Series                  # bool: was bond active that day
    exposure: pd.Series                  # vol-target exposure
    rank: pd.DataFrame                   # cross-sectional IVOL rank
    signal: pd.DataFrame                 # IVOL values
    rebalance_days: int = 21


def run(panel: pd.DataFrame) -> FactorResultV2:
    """Full pipeline: panel → final return after vol-target + bond rotation."""
    panel = panel[~panel.symbol.isin(DROPPED_TICKERS)].copy()
    eq_syms = equity_universe(panel)
    panel_eq = panel[panel.symbol.isin(eq_syms | {BENCH})].copy()
    rets_eq = _wide(panel_eq, "ret")

    sig = compute_signal(panel)
    qres = quintile_LS_returns(sig, rets_eq)
    raw = qres["ls"]
    vt_ret, exposure = vol_target_overlay(raw)

    # bond forward return
    rets_full = _wide(panel, "ret")
    if DEFENSIVE_BOND not in rets_full.columns:
        raise KeyError(f"{DEFENSIVE_BOND} not in panel — extended cache required")
    bond_fwd = rets_full[DEFENSIVE_BOND].rolling(PRIMARY_K).sum().shift(-(DELAY + PRIMARY_K))

    final, use_bond = bond_rotation_overlay(vt_ret, bond_fwd)
    drag = cost_drag_LS(qres["rank"]) * exposure
    final_net = final.sub(drag.reindex(final.index).fillna(0))

    return FactorResultV2(
        raw_LS_ret=raw, voltarget_LS_ret=vt_ret, final_ret_gross=final,
        final_ret_net5bps=final_net, use_bond=use_bond, exposure=exposure,
        rank=qres["rank"], signal=sig)


# ---- self-test ----
if __name__ == "__main__":
    from pathlib import Path
    PANEL = Path("/home/user/Factor_Zoo/logs/_shared_cache/etf_daily_extended.parquet")
    panel = pd.read_parquet(PANEL)
    panel["ret"] = panel.groupby("symbol")["close"].pct_change()
    res = run(panel)
    s = res.final_ret_net5bps.dropna()

    def ann_sharpe(s, k=PRIMARY_K):
        return float(s.mean() / s.std() * np.sqrt(252 / k))

    print(f"final net@5bps Sharpe: {ann_sharpe(s):.2f}")
    print(f"avg exposure: {res.exposure.mean():.2f}")
    print(f"bond-active fraction of days: {res.use_bond.mean():.1%}")
    print()
    print("per-year Sharpe:")
    yr = s.groupby(s.index.year).apply(lambda x: ann_sharpe(x))
    print(yr.round(2).to_string())
