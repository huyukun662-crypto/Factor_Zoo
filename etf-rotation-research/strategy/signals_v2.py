"""V2 signal building blocks: extensions to signals.py for R7-R12.

# [NO-LOOKAHEAD] All signals here use rolling windows over data ≤ T close;
# the engine still applies the additional shift(1) before pricing.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategy.signals import _safe_log_ret, _xs_zscore, momentum_panel, rsrs_panel


def reversal_panel(close: pd.DataFrame, L: int = 5) -> pd.DataFrame:
    """Negative of short-window cumulative return → high score = recently sold off."""
    return -np.log(close).diff(L)


def skip_momentum_panel(close: pd.DataFrame, L: int, skip: int) -> pd.DataFrame:
    """log(close[T-skip] / close[T-L])  (12-1 style)."""
    return np.log(close.shift(skip)).diff(L - skip)


def multi_horizon_momentum(close: pd.DataFrame, horizons: tuple[int, ...] = (60, 120, 252),
                            weights: tuple[float, ...] | None = None) -> pd.DataFrame:
    """Weighted average of cross-sectionally z-scored momentum at multiple horizons."""
    weights = weights or tuple([1.0 / len(horizons)] * len(horizons))
    out = None
    for h, w in zip(horizons, weights):
        z = _xs_zscore(momentum_panel(close, h))
        out = w * z if out is None else out + w * z
    return out


def multi_horizon_rsrs(high: pd.DataFrame, low: pd.DataFrame,
                        configs: tuple[tuple[int, int], ...] = ((18, 600), (60, 600)),
                        weights: tuple[float, ...] | None = None) -> pd.DataFrame:
    """Weighted average of multiple RSRS_skew configs (different N)."""
    weights = weights or tuple([1.0 / len(configs)] * len(configs))
    out = None
    for (n, m), w in zip(configs, weights):
        z = _xs_zscore(rsrs_panel(high, low, n=n, m=m, form="rsrs_skew"))
        out = w * z if out is None else out + w * z
    return out


def bucket_relative_score(score: pd.DataFrame, universe_df: pd.DataFrame
                           ) -> pd.DataFrame:
    """Demean score by bucket per row (industry-neutral cross-section).

    universe_df must have ['symbol', 'bucket'] columns.
    Symbols not present in universe_df are passed through unchanged (z-score only).
    """
    bucket_map = dict(zip(universe_df["symbol"].astype(str), universe_df["bucket"]))
    out = score.copy()
    # Group columns by bucket
    by_bucket: dict[str, list[str]] = {}
    for col in score.columns:
        b = bucket_map.get(str(col), "_other")
        by_bucket.setdefault(b, []).append(col)
    for b, cols in by_bucket.items():
        if len(cols) <= 1:
            continue
        sub = score[cols]
        mu = sub.mean(axis=1)
        sd = sub.std(axis=1).replace(0, np.nan)
        out[cols] = sub.sub(mu, axis=0).div(sd, axis=0)
    return out


def apply_vol_target(weights: pd.DataFrame, close: pd.DataFrame,
                     target_vol: float = 0.12, vol_lookback: int = 60,
                     max_leverage: float = 1.0) -> pd.DataFrame:
    """Scale total exposure each day so realized portfolio vol ≈ target.

    Uses rolling per-symbol vol; scaling factor = target_vol / portfolio_vol.
    Caps leverage at max_leverage (no margin).
    """
    daily_ret = _safe_log_ret(close)
    # portfolio realized vol estimate ≈ sqrt(sum(w * sigma)^2 * 252) — approx, ignores corr
    sigma = daily_ret.rolling(vol_lookback, min_periods=20).std()
    # Use a coarse weighted-vol estimate (assume positive correlation 1, conservative)
    port_vol = (weights.abs() * sigma).sum(axis=1) * np.sqrt(252)
    scale = (target_vol / port_vol.replace(0, np.nan)).clip(upper=max_leverage).fillna(0.0)
    # Don't scale up if portfolio empty (sum of weights == 0)
    return weights.mul(scale, axis=0)


def smooth_equity_frac(agg_signal: pd.Series, theta_off: float, theta_on: float
                        ) -> pd.Series:
    """Smooth (linear) ramp from 0 to 1 between theta_off and theta_on
    instead of the step {0, 0.5, 1}. Reduces cost from regime jumps.
    """
    if theta_on <= theta_off:
        # degenerate; fall back to step
        return (agg_signal >= theta_off).astype(float)
    span = theta_on - theta_off
    frac = (agg_signal - theta_off) / span
    return frac.clip(lower=0.0, upper=1.0)


def drawdown_scale(equity: pd.Series, max_scale_dd: float = 0.10,
                    floor: float = 0.3) -> pd.Series:
    """Scale current equity allocation by min(1, 1 - dd/max_scale_dd).
    Floor at `floor` so we never zero out completely.
    NOTE: this needs equity from PREVIOUS day's pnl — used post-hoc in
    a feedback-aware engine, but here we use it as a pre-computed proxy
    via a forward-fill of daily-rebalanced weights' realized pnl signal.
    For research speed we apply on shifted equity.
    """
    peak = equity.cummax().shift(1).fillna(equity.iloc[0])
    dd = (equity.shift(1) / peak - 1.0).fillna(0)
    scale = (1.0 + dd / max_scale_dd).clip(lower=floor, upper=1.0)
    return scale
