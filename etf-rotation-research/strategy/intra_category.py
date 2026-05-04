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
