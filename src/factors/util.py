"""Shared helpers for factor expressions."""
from __future__ import annotations

import numpy as np
import pandas as pd


def rolling_zscore(s: pd.Series, window: int = 252) -> pd.Series:
    mu = s.rolling(window, min_periods=max(60, window // 4)).mean()
    sd = s.rolling(window, min_periods=max(60, window // 4)).std(ddof=1)
    z = (s - mu) / sd
    return z.replace([np.inf, -np.inf], np.nan)


def daily_log_return(close: pd.Series) -> pd.Series:
    return np.log(close).diff()


def realized_vol(returns: pd.Series, window: int) -> pd.Series:
    return returns.rolling(window, min_periods=max(5, window // 4)).std(ddof=1)


def downside_vol(returns: pd.Series, window: int) -> pd.Series:
    neg = returns.clip(upper=0.0)
    return neg.rolling(window, min_periods=max(5, window // 4)).std(ddof=1)


def discretize_signal(s: pd.Series, period: int) -> pd.Series:
    """Sample the signal at every `period`-th index position and hold the value
    forward for `period` rows.

    Past-only: at index t, the held value comes from index `t - (t % period)`,
    which is a previous (or current) sample. No forward dependency.

    Used to simulate N-day rebalance from a daily signal: the score becomes
    constant within each rebalance window, which (combined with deadband)
    means the position changes only at window boundaries.
    """
    if period <= 1:
        return s.copy()
    out = s.copy()
    n = len(s)
    for i in range(0, n, period):
        end = min(i + period, n)
        out.iloc[i:end] = s.iloc[i]
    return out


def vol_spread_zscore(panel: pd.DataFrame, vol_window: int = 20, z_window: int = 252) -> pd.Series:
    """Reproduce the R1 raw vol-spread z-score (regime indicator).

    Returns z-score of (realized_vol(r_1000, vol_window) - realized_vol(r_300, vol_window))
    over rolling z_window. Past-only.
    """
    r300 = daily_log_return(panel["idx300_close"])
    r1000 = daily_log_return(panel["idx1000_close"])
    raw = realized_vol(r1000, vol_window) - realized_vol(r300, vol_window)
    return rolling_zscore(raw, z_window)


def turnover_level_zscore(panel: pd.DataFrame, smooth: int = 20, z_window: int = 252) -> pd.Series:
    """Reproduce the R2 E1 turnover-level z (1000 vs 300) as a regime indicator."""
    a300 = panel["idx300_amount"].clip(lower=1.0)
    a1000 = panel["idx1000_amount"].clip(lower=1.0)
    raw = np.log(a1000 / a300).rolling(smooth, min_periods=5).mean()
    return rolling_zscore(raw, z_window)
