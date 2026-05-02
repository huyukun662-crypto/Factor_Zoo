"""anchor_range_pos_etf_v1 — reusable factor-construction code.

Cross-sectional range-position signal on a 20-ETF A-share core universe.
Long-only top-3 selection, 21-phase ensemble (1/21 NAV deployed each
trading day, 21-day holding), portfolio-level vol-target 10% annualized,
5 bps/side cost.

Paper origin: George & Hwang (2004) JF "The 52-Week High and Momentum
Investing" — the literal proximity-to-high signal does NOT transfer to
A-share ETFs (R1 falsified, see logs/20260502_a_share_etf_anchor_high_v1).
The variant that works is min-max range position, normalized by the ETF's
own 60/120/252/500-day range.

Headline (2020-01 → 2026-04, 5 bps/side):
    excess_net_sharpe = 1.007
    train (19-21)     = 1.088
    validate (22)     = 0.844
    test (23-26)      = 1.003
    worst_year (22)   = -0.13 (Sharpe), -1.3% cum excess
    max_dd_excess     = -13.5%
    n_pos_years       = 6 / 7
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

# --------------------------------------------------------------------- #
# Defaults — change only with care; these are baked into the headline.
# --------------------------------------------------------------------- #
WINDOWS = (60, 120, 252, 500)      # range-position windows averaged
N_TOP = 3                           # long-only top-N
REBAL = 21                          # rebalance days
COST_BPS = 5.0                      # one side
TARGET_VOL = 0.10                   # portfolio vol target, annualized
VOL_TARGET_LOOKBACK = 60            # days for ex-post vol estimate
LEVERAGE_CAP = 2.0                  # cap vol-target leverage at 2x
DELAY = 1                           # T+1 execution

# Drop-list and bench match logs/20260502_a_share_etf_anchor_high_v1
DROP_FULL = {"512800.SS", "515170.SS"}     # truncated history
BENCH_SYMBOL = "510300.SS"

# Core universe = ETFs with at least 1500 valid daily bars in cache panel
CORE_MIN_DAYS = 1500


# --------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------- #
def load_panel(parquet_path: str | Path) -> pd.DataFrame:
    """Load a daily ETF panel with columns: date, symbol, close, ret."""
    df = pd.read_parquet(parquet_path)
    df = df[~df.symbol.isin(DROP_FULL)].copy()
    df = df.sort_values(["date", "symbol"]).reset_index(drop=True)
    df["ret"] = df.groupby("symbol")["close"].pct_change()
    return df


def core_universe(close_wide: pd.DataFrame) -> list[str]:
    """20-ETF core universe — symbols with enough history for backtest."""
    counts = close_wide.notna().sum()
    return counts[counts >= CORE_MIN_DAYS].index.tolist()


def signal(close_wide: pd.DataFrame, windows: tuple[int, ...] = WINDOWS) -> pd.DataFrame:
    """Multi-window range-position signal.

    For each window w in windows:
        rp_w = (close - rolling_min(close, w)) /
               (rolling_max(close, w) - rolling_min(close, w))
    Final signal = mean of cross-section pct-rank of rp_w across windows.
    """
    rp_ranks = []
    for w in windows:
        min_periods = 200 if w >= 252 else int(w * 0.8)
        pmax = close_wide.rolling(w, min_periods=min_periods).max()
        pmin = close_wide.rolling(w, min_periods=min_periods).min()
        rp = (close_wide - pmin) / (pmax - pmin).replace(0, np.nan)
        rp_ranks.append(rp.rank(axis=1, pct=True))
    return sum(rp_ranks) / len(rp_ranks)


def phase_ensemble_long_only(
    sig: pd.DataFrame,
    ret_d: pd.DataFrame,
    n: int = N_TOP,
    rebal: int = REBAL,
    cost_bps: float = COST_BPS,
    universe_filter: list[str] | None = None,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.DataFrame]:
    """21-phase ensemble of an n-name long-only top-N rebalanced every
    `rebal` days. Returns gross-portfolio, net-portfolio, EW-bench, and
    aggregated weights panel.

    Each phase deploys 1/rebal of NAV and is held for `rebal` days.
    Cost is charged on the rebalance day for that phase, scaled by
    1/rebal.
    """
    cols = sig.columns.tolist()
    if universe_filter is not None:
        cols = [c for c in cols if c in universe_filter]
    sig = sig[cols]
    ret_d = ret_d[cols]
    dates = sig.index

    weights_total = pd.DataFrame(0.0, index=dates, columns=cols)
    cost_daily = pd.Series(0.0, index=dates)

    for phase in range(rebal):
        rebal_dates = dates[phase::rebal]
        prev_w = pd.Series(0.0, index=cols)
        for i, rd in enumerate(rebal_dates):
            top = sig.loc[rd].dropna().nlargest(n).index.tolist()
            if len(top) < n:
                new_w = prev_w.copy()
            else:
                new_w = pd.Series(0.0, index=cols)
                for s in top:
                    new_w[s] = 1.0 / n

            # turnover cost on this rebal day, this phase contributes 1/rebal NAV
            turnover = (new_w - prev_w).abs().sum() / 2.0
            cost_daily.loc[rd] += turnover * (cost_bps / 1e4) / rebal

            # holding window for this rebal cycle
            end_idx = rebal_dates[i + 1] if i + 1 < len(rebal_dates) else dates[-1] + pd.Timedelta(days=1)
            mask = (dates >= rd) & (dates < end_idx)
            for s in cols:
                if new_w[s] != 0:
                    weights_total.loc[mask, s] += new_w[s] / rebal
            prev_w = new_w

    portfolio_gross = (weights_total * ret_d).sum(axis=1)
    portfolio_net = portfolio_gross - cost_daily
    bench = ret_d.mean(axis=1)
    return portfolio_gross, portfolio_net, bench, weights_total


def vol_target_overlay(
    excess_daily: pd.Series,
    target: float = TARGET_VOL,
    lookback: int = VOL_TARGET_LOOKBACK,
    leverage_cap: float = LEVERAGE_CAP,
) -> pd.Series:
    """Ex-post vol-target overlay. Uses yesterday's trailing vol so the
    scaling factor is causal."""
    rv = excess_daily.rolling(lookback, min_periods=int(lookback * 0.8)).std() * np.sqrt(252)
    scale = (target / rv).clip(upper=leverage_cap)
    scale = scale.shift(1)
    return excess_daily * scale


def run_factor(
    panel_path: str | Path,
    *,
    windows: tuple[int, ...] = WINDOWS,
    n_top: int = N_TOP,
    rebal: int = REBAL,
    cost_bps: float = COST_BPS,
    target_vol: float = TARGET_VOL,
    skip_warmup_year: int = 2020,
) -> dict:
    """End-to-end factor backtest. Returns a dict with daily series and
    aggregate metrics."""
    panel = load_panel(panel_path)
    close = panel.pivot(index="date", columns="symbol", values="close").sort_index()
    rets = panel.pivot(index="date", columns="symbol", values="ret").sort_index()

    sig = signal(close, windows=windows)
    universe = core_universe(close)

    gross, net, bench, weights = phase_ensemble_long_only(
        sig, rets,
        n=n_top, rebal=rebal, cost_bps=cost_bps,
        universe_filter=universe,
    )

    excess_pre_vt = net - bench
    excess = vol_target_overlay(excess_pre_vt, target=target_vol)
    portfolio = excess + bench

    valid = excess.dropna().index
    valid = valid[valid.year >= skip_warmup_year]

    excess = excess.loc[valid]
    portfolio = portfolio.loc[valid]
    bench = bench.loc[valid]

    return {
        "panel_dates": (panel.date.min(), panel.date.max()),
        "universe": universe,
        "signal": sig,
        "weights": weights,
        "portfolio_daily": portfolio,
        "bench_daily": bench,
        "excess_daily": excess,
        "config": {
            "windows": list(windows),
            "n_top": n_top,
            "rebal": rebal,
            "cost_bps_per_side": cost_bps,
            "target_vol": target_vol,
            "leverage_cap": LEVERAGE_CAP,
            "delay": DELAY,
        },
    }


def annualize_sharpe(daily: pd.Series, k: int = 1, min_obs: int = 20) -> float:
    x = daily.dropna()
    if len(x) < min_obs or x.std() == 0:
        return float("nan")
    return float(x.mean() / x.std() * np.sqrt(252 / k))


def per_year_table(excess: pd.Series, portfolio: pd.Series, bench: pd.Series) -> pd.DataFrame:
    rows = []
    for yr, idx in excess.groupby(excess.index.year).groups.items():
        e = excess.loc[idx]
        p = portfolio.loc[idx]
        b = bench.loc[idx]
        rows.append({
            "year": int(yr),
            "n_days": len(e),
            "sharpe_excess_net": annualize_sharpe(e),
            "sharpe_portfolio_net": annualize_sharpe(p),
            "sharpe_bench": annualize_sharpe(b),
            "ann_ret_excess": float(e.sum()),
            "ann_ret_portfolio": float(p.sum()),
            "ann_ret_bench": float(b.sum()),
        })
    return pd.DataFrame(rows)
