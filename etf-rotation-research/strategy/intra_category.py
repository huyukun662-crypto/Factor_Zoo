"""Intra-category selection: pick top-K within a defensive category by signal,
or apply EPO (Enhanced Portfolio Optimization, Pedersen et al. 2021) weighting.

EPO formula (simplified for our use):
  w_EPO ∝ ((1 - w_shrink) * diag(Σ) + w_shrink * Σ)^(-1) * μ
  w_shrink ∈ [0, 1]:
      0 → 1/N (equal-weight, ignores covariance structure)
      1 → standard mean-variance optimization
  Output normalized to sum to 1 (long-only by clipping at 0 + renormalize).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategy.categories import CATEGORIES


def _normalize_long_only(w: np.ndarray) -> np.ndarray:
    w = np.where(np.isfinite(w), w, 0.0)
    w = np.clip(w, 0.0, None)
    s = w.sum()
    return w / s if s > 1e-12 else w


def _available_mask(close: pd.DataFrame, constituents: list[str]) -> pd.DataFrame:
    """Per-day per-symbol True iff close has a non-NaN value (i.e. listed/traded)."""
    sub = close[[c for c in constituents if c in close.columns]]
    return sub.notna()


def intra_category_topk_aware(score: pd.DataFrame, close: pd.DataFrame,
                                category: str, k: int = 1,
                                all_symbols: list[str] | None = None
                                ) -> pd.DataFrame:
    """Top-K within category, INCEPTION-AWARE.

    On each row, only consider constituents with non-NaN close. If fewer than
    k are available, equal-weight all that ARE available. If none, all-zero.
    """
    if category not in CATEGORIES:
        raise ValueError(f"unknown category {category}")
    constituents = [c for c in CATEGORIES[category]["constituents"] if c in score.columns]
    cols_all = all_symbols if all_symbols is not None else list(score.columns)
    out = pd.DataFrame(0.0, index=score.index, columns=cols_all)
    if not constituents:
        return out
    avail = _available_mask(close, constituents).reindex(index=score.index).fillna(False)
    masked_score = score[constituents].where(avail, other=-np.inf)

    # rank per row, but only among available
    rank = masked_score.rank(axis=1, method="first", ascending=False)
    chosen = (rank <= k) & masked_score.gt(-np.inf)
    counts = chosen.sum(axis=1).replace(0, np.nan)
    weights = chosen.astype(float).div(counts, axis=0).fillna(0.0)
    for c in constituents:
        out[c] = weights[c].values
    return out


def intra_category_vol_parity(close: pd.DataFrame, category: str,
                                vol_lookback: int = 60,
                                top_k: int | None = None,
                                score: pd.DataFrame | None = None,
                                all_symbols: list[str] | None = None,
                                ) -> pd.DataFrame:
    """Vol-parity weighting within category. If top_k is set + score provided,
    first restrict to top_k by score then apply vol parity within selection.

    Returns DataFrame indexed by close.index with columns = all_symbols.
    """
    constituents = [c for c in CATEGORIES[category]["constituents"] if c in close.columns]
    cols_all = all_symbols if all_symbols is not None else list(close.columns)
    out = pd.DataFrame(0.0, index=close.index, columns=cols_all)
    if not constituents:
        return out
    daily_ret = close[constituents].pct_change()
    sigma = daily_ret.rolling(vol_lookback, min_periods=20).std()
    inv_vol = (1.0 / sigma.replace(0, np.nan)).fillna(0)
    avail = _available_mask(close, constituents).fillna(False)

    if top_k is not None and score is not None:
        # Restrict to top-k by score among available constituents
        masked_score = score[constituents].where(avail, other=-np.inf)
        rank = masked_score.rank(axis=1, method="first", ascending=False)
        chosen = (rank <= top_k) & masked_score.gt(-np.inf)
        inv_vol = inv_vol.where(chosen, 0.0)

    # zero out unavailable
    inv_vol = inv_vol.where(avail, 0.0)
    s = inv_vol.sum(axis=1).replace(0, np.nan)
    w = inv_vol.div(s, axis=0).fillna(0.0)
    for c in constituents:
        out[c] = w[c].values
    return out


def intra_category_sharpe_weighted(close: pd.DataFrame, category: str,
                                       lookback: int = 60,
                                       top_k: int | None = None,
                                       all_symbols: list[str] | None = None,
                                       ) -> pd.DataFrame:
    """Sharpe-weighted top-K within category.

    Computes recent Sharpe (mean / std * sqrt(252)) per constituent over `lookback`
    days. Picks top-k by Sharpe (only among available), weight = max(0, Sharpe)
    normalized.
    """
    constituents = [c for c in CATEGORIES[category]["constituents"] if c in close.columns]
    cols_all = all_symbols if all_symbols is not None else list(close.columns)
    out = pd.DataFrame(0.0, index=close.index, columns=cols_all)
    if not constituents:
        return out
    daily_ret = close[constituents].pct_change()
    mu = daily_ret.rolling(lookback, min_periods=20).mean()
    sd = daily_ret.rolling(lookback, min_periods=20).std().replace(0, np.nan)
    sharpe = (mu / sd) * np.sqrt(252)  # daily Sharpe annualized

    avail = _available_mask(close, constituents).fillna(False)
    masked = sharpe.where(avail, other=-np.inf)

    if top_k is not None:
        rank = masked.rank(axis=1, method="first", ascending=False)
        chosen = (rank <= top_k) & masked.gt(-np.inf)
        score = sharpe.where(chosen, 0.0)
    else:
        score = sharpe.where(avail, 0.0)

    score = score.clip(lower=0).fillna(0)
    s = score.sum(axis=1).replace(0, np.nan)
    w = score.div(s, axis=0).fillna(0.0)
    for c in constituents:
        out[c] = w[c].values
    return out


def intra_category_topk(score: pd.DataFrame, category: str,
                          k: int = 1, all_symbols: list[str] | None = None
                          ) -> pd.DataFrame:
    """For each row, place equal weight on top-k constituents of `category` by `score`.

    Returns DataFrame indexed by score's rows, columns = all_symbols (others = 0).
    """
    if category not in CATEGORIES:
        raise ValueError(f"unknown category {category}")
    constituents = [c for c in CATEGORIES[category]["constituents"] if c in score.columns]
    if not constituents:
        cols = all_symbols if all_symbols is not None else list(score.columns)
        return pd.DataFrame(0.0, index=score.index, columns=cols)

    sub = score[constituents]
    if len(constituents) <= k:
        # All available -> equal weight
        ew = 1.0 / len(constituents)
        out_cols = all_symbols if all_symbols is not None else list(score.columns)
        out = pd.DataFrame(0.0, index=score.index, columns=out_cols)
        for c in constituents:
            out[c] = ew
        return out

    # Top-k per row
    rank = sub.rank(axis=1, method="first", ascending=False)
    chosen = rank <= k
    counts = chosen.sum(axis=1).replace(0, np.nan)
    weights = chosen.astype(float).div(counts, axis=0).fillna(0.0)
    # Embed into all_symbols frame
    cols_all = all_symbols if all_symbols is not None else list(score.columns)
    out = pd.DataFrame(0.0, index=score.index, columns=cols_all)
    for c in constituents:
        out[c] = weights[c].values
    return out


def intra_category_epo(returns_panel: pd.DataFrame, category: str,
                        signal_t: pd.Series, w_shrink: float = 0.5,
                        cov_window: int = 252,
                        all_symbols: list[str] | None = None,
                        ) -> dict[str, float]:
    """EPO weight for ONE day, using lookback `cov_window` of returns.

    Returns dict {symbol: weight} with weights summing to 1 across category constituents.
    """
    constituents = [c for c in CATEGORIES[category]["constituents"] if c in returns_panel.columns]
    if not constituents:
        return {}
    if len(constituents) == 1:
        return {constituents[0]: 1.0}

    sub = returns_panel[constituents].iloc[-cov_window:].dropna(how="all")
    if len(sub) < 30:
        return {c: 1.0 / len(constituents) for c in constituents}

    cov = sub.cov().values  # full sample covariance
    diag = np.diag(np.diag(cov))
    cov_shrunk = (1 - w_shrink) * diag + w_shrink * cov

    # signal: use signal_t for these constituents
    mu = np.array([float(signal_t.get(c, 0.0)) for c in constituents])
    if np.allclose(mu, 0):
        return {c: 1.0 / len(constituents) for c in constituents}

    # Solve Σ_shrunk @ w ∝ mu
    try:
        w = np.linalg.solve(cov_shrunk, mu)
    except np.linalg.LinAlgError:
        w = np.linalg.lstsq(cov_shrunk, mu, rcond=None)[0]

    w = _normalize_long_only(w)
    if w.sum() < 1e-12:
        w = np.ones(len(constituents)) / len(constituents)
    return {c: float(w[i]) for i, c in enumerate(constituents)}


def intra_category_epo_panel(returns_panel: pd.DataFrame, category: str,
                                score_panel: pd.DataFrame, w_shrink: float = 0.5,
                                cov_window: int = 252,
                                rebal_freq: int = 21,
                                all_symbols: list[str] | None = None,
                                ) -> pd.DataFrame:
    """Build a daily weight panel for `category` using EPO.

    Recomputes EPO weights every `rebal_freq` days to control cost.
    """
    cols_all = all_symbols if all_symbols is not None else list(returns_panel.columns)
    out = pd.DataFrame(0.0, index=returns_panel.index, columns=cols_all)
    constituents = [c for c in CATEGORIES[category]["constituents"] if c in returns_panel.columns]
    if not constituents:
        return out
    if len(constituents) == 1:
        out[constituents[0]] = 1.0
        return out

    last_w = {c: 1.0 / len(constituents) for c in constituents}
    last_t = -10**9
    for i, dt in enumerate(returns_panel.index):
        if i < cov_window:
            for c in constituents:
                out.at[dt, c] = 1.0 / len(constituents)
            continue
        if i - last_t >= rebal_freq:
            sub = returns_panel.iloc[max(0, i - cov_window): i][constituents].dropna(how="all")
            if len(sub) >= 30:
                signal_t = score_panel.iloc[i] if i < len(score_panel) else score_panel.iloc[-1]
                last_w = intra_category_epo(returns_panel.iloc[: i + 1], category,
                                              signal_t, w_shrink=w_shrink,
                                              cov_window=cov_window)
                last_t = i
        for c, w in last_w.items():
            out.at[dt, c] = w
    return out
