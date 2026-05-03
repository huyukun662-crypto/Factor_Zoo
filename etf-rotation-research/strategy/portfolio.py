"""Portfolio construction: top-K equal weight + risk-off overlay.

Public API:
    build_target_weights(score, eligibility, agg_rsrs, defensive_pool,
                          top_k, theta_off, theta_on, defensive_proxy_score)
    -> wide DataFrame of target weights (rows = date, cols = symbol),
       sums to <=1 per row, with risk-off allocation toward defensive bucket.

# [NO-LOOKAHEAD] All inputs are signal panels keyed at row T using only data
# observed up to T close. The backtest engine adds an additional shift(1)
# before pricing the trade.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _topk_equal_weight(score: pd.DataFrame, mask: pd.DataFrame, k: int) -> pd.DataFrame:
    """Vectorized top-K equal-weight per row, restricted to mask=True cells."""
    masked = score.where(mask, other=-np.inf)
    # rank highest=best (small ranks = top)
    rank = masked.rank(axis=1, method="first", ascending=False)
    chosen = (rank <= k) & masked.gt(-np.inf)
    counts = chosen.sum(axis=1).replace(0, np.nan)
    w = chosen.astype(float).div(counts, axis=0).fillna(0.0)
    return w


def _defensive_pick(defensive_proxy_score: pd.DataFrame) -> pd.DataFrame:
    """Pick the single best defensive ETF per day (equal weight = full to one).

    Rows where all defensives are NaN fall back to equal-weight across all
    defensive symbols (signal not yet usable -> diversify defensively).
    """
    if defensive_proxy_score is None or defensive_proxy_score.empty:
        return pd.DataFrame(index=[], columns=[])
    out = pd.DataFrame(0.0, index=defensive_proxy_score.index, columns=defensive_proxy_score.columns)
    valid_rows = defensive_proxy_score.notna().any(axis=1)
    if valid_rows.any():
        best = defensive_proxy_score.loc[valid_rows].idxmax(axis=1)
        for dt, sym in best.items():
            if isinstance(sym, str):
                out.at[dt, sym] = 1.0
    # rows without any valid defensive signal: equal-weight fallback
    fallback_cols = list(defensive_proxy_score.columns)
    if fallback_cols:
        ew = 1.0 / len(fallback_cols)
        out.loc[~valid_rows, fallback_cols] = ew
    return out


def _apply_rebal_threshold(weights: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Throttle: only update weights when L1 distance from previous > threshold.

    Vectorized via cumulative state — small loop over time but in numpy.
    """
    if threshold <= 0:
        return weights
    arr = weights.values.copy()
    n = arr.shape[0]
    held = arr[0].copy()
    out = np.zeros_like(arr)
    out[0] = held
    for i in range(1, n):
        target = arr[i]
        if np.abs(target - held).sum() > threshold:
            held = target.copy()
        out[i] = held
    return pd.DataFrame(out, index=weights.index, columns=weights.columns)


def build_target_weights(score: pd.DataFrame,
                          eligibility: pd.DataFrame,
                          agg_rsrs: pd.Series,
                          defensive_proxy_score: pd.DataFrame | None,
                          top_k: int = 5,
                          theta_off: float = -0.7,
                          theta_on: float = +0.7,
                          rebal_threshold: float = 0.0,
                          ) -> pd.DataFrame:
    """Build T-indexed target weights.

    Logic
    -----
    - equity_w = top-K equal-weight on `score` restricted to `eligibility`
    - regime equity_frac:
        agg_rsrs <  theta_off                : 0.0 (full risk-off)
        theta_off <= agg_rsrs <  theta_on    : 0.5
        agg_rsrs >= theta_on                  : 1.0
    - defensive_w = best-of(defensive_proxy_score) gets (1 - equity_frac)
    """
    equity_w = _topk_equal_weight(score, eligibility, top_k)
    equity_frac = pd.Series(0.5, index=score.index)
    equity_frac[agg_rsrs.reindex(score.index) < theta_off] = 0.0
    equity_frac[agg_rsrs.reindex(score.index) >= theta_on] = 1.0
    equity_part = equity_w.mul(equity_frac, axis=0)

    if defensive_proxy_score is not None and not defensive_proxy_score.empty:
        defensive_w = _defensive_pick(defensive_proxy_score)
        defensive_w = defensive_w.reindex(index=score.index, columns=score.columns, fill_value=0.0)
        defensive_part = defensive_w.mul(1.0 - equity_frac, axis=0)
    else:
        defensive_part = pd.DataFrame(0.0, index=score.index, columns=score.columns)

    out = equity_part.add(defensive_part, fill_value=0.0)
    out = out.reindex(columns=score.columns, fill_value=0.0)
    if rebal_threshold and rebal_threshold > 0:
        out = _apply_rebal_threshold(out, rebal_threshold)
    return out
