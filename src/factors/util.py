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
