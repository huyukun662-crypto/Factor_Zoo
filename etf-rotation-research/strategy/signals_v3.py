"""V3 building blocks: smarter weighting & selection mechanics."""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategy.signals import _safe_log_ret


def rolling_percentile_threshold(series: pd.Series, q: float, window: int = 252,
                                  min_periods: int = 60) -> pd.Series:
    """Rolling q-quantile of series → adaptive threshold (e.g. RSRS-quantile gate)."""
    return series.rolling(window, min_periods=min_periods).quantile(q)


def two_stage_selection(score_a: pd.DataFrame, score_b: pd.DataFrame,
                         eligibility: pd.DataFrame, n_first: int, k_final: int
                         ) -> pd.DataFrame:
    """First filter to top n_first by score_a, then pick top k_final by score_b.

    Vectorized via rank-based masks.
    """
    masked_a = score_a.where(eligibility, other=-np.inf)
    rank_a = masked_a.rank(axis=1, method="first", ascending=False)
    pass1 = (rank_a <= n_first) & masked_a.gt(-np.inf)

    masked_b = score_b.where(pass1, other=-np.inf)
    rank_b = masked_b.rank(axis=1, method="first", ascending=False)
    chosen = (rank_b <= k_final) & masked_b.gt(-np.inf)

    counts = chosen.sum(axis=1).replace(0, np.nan)
    w = chosen.astype(float).div(counts, axis=0).fillna(0.0)
    return w


def score_weighted_topk(score: pd.DataFrame, eligibility: pd.DataFrame,
                         k: int, power: float = 1.0) -> pd.DataFrame:
    """Top-K but weight ∝ (rank-distance)**power instead of equal weight."""
    masked = score.where(eligibility, other=-np.inf)
    rank = masked.rank(axis=1, method="first", ascending=False)
    chosen = (rank <= k) & masked.gt(-np.inf)
    # Weight: (k - rank + 1)^power among chosen
    raw = ((k - rank + 1).clip(lower=0).pow(power) * chosen.astype(float))
    s = raw.sum(axis=1).replace(0, np.nan)
    return raw.div(s, axis=0).fillna(0.0)


def vol_parity_topk(score: pd.DataFrame, eligibility: pd.DataFrame,
                     close: pd.DataFrame, k: int, vol_lookback: int = 60
                     ) -> pd.DataFrame:
    """Top-K by score, weighted ∝ 1/vol within selected names (risk parity)."""
    masked = score.where(eligibility, other=-np.inf)
    rank = masked.rank(axis=1, method="first", ascending=False)
    chosen = (rank <= k) & masked.gt(-np.inf)
    daily_ret = _safe_log_ret(close)
    sigma = daily_ret.rolling(vol_lookback, min_periods=20).std()
    inv_sigma = (1.0 / sigma.replace(0, np.nan)).fillna(0)
    raw = inv_sigma.mul(chosen.astype(float))
    s = raw.sum(axis=1).replace(0, np.nan)
    return raw.div(s, axis=0).fillna(0.0)


def adaptive_regime_band(agg_signal: pd.Series, q_off: float = 0.30,
                          q_on: float = 0.70, window: int = 504,
                          min_periods: int = 120) -> tuple[pd.Series, pd.Series]:
    """Return (theta_off_t, theta_on_t) as rolling-quantile thresholds."""
    th_off = agg_signal.rolling(window, min_periods=min_periods).quantile(q_off)
    th_on = agg_signal.rolling(window, min_periods=min_periods).quantile(q_on)
    return th_off, th_on


def equity_frac_adaptive(agg_signal: pd.Series, theta_off_series: pd.Series,
                          theta_on_series: pd.Series) -> pd.Series:
    """Smooth ramp using time-varying thresholds."""
    span = (theta_on_series - theta_off_series).replace(0, np.nan)
    frac = (agg_signal - theta_off_series) / span
    return frac.clip(lower=0.0, upper=1.0).fillna(0.5)
