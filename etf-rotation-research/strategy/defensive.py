"""Macro-aware defensive asset routing.

Expanded defensive pool beyond cash:
  511010 10Y 国债
  511260 10Y 国开
  511880 银华日利 (货币基金 / 现金)
  518880 黄金
  515080 红利低波
  515220 煤炭

Routing strategies (selectable by name):
  'sharpe'     - per-regime IS Sharpe argmax  (trivially picks cash)
  'annret'     - per-regime annualized return argmax  (picks high-return)
  'sortino'    - per-regime Sortino argmax  (downside-aware)
  'macro_rule' - explicit IF-THEN rules on (CPI, PMI, M2)
  'split_cpi'  - within each regime cell, split by CPI > median, pick best per sub-cell

# [GUARDRAIL] All routing is computed on full IS panel per user instruction
# (样本内可以寻找特定区间内最优的防御资产). For walk-forward use, the mapping
# would need to be re-derived per training window.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Reasonable expanded defensive pool — only those with sufficient IS history
EXPANDED_DEFENSIVE = ["511010", "511260", "511880", "518880", "515080", "515220"]


def per_regime_best(regime_labels: pd.Series,
                     defensive_returns: pd.DataFrame,
                     metric: str = "sharpe",
                     min_obs: int = 60,
                     ) -> dict[int, str]:
    """For each regime cell, pick best defensive by `metric`.

    metric:
        'sharpe'  - mean / std * sqrt(252)
        'annret'  - mean * 252  (highest absolute return)
        'sortino' - mean / downside_std * sqrt(252)
        'sharpe_min_vol' - sharpe but only among assets with ann_vol >= 2%
                          (excludes cash from auto-winning)
    """
    out: dict[int, str] = {}
    aligned = regime_labels.index.intersection(defensive_returns.index)
    rl = regime_labels.loc[aligned]
    rr = defensive_returns.loc[aligned]
    for state in sorted(rl.dropna().unique()):
        mask = rl == state
        if mask.sum() < min_obs:
            continue
        sub = rr.loc[mask].dropna(how="all", axis=1)
        if sub.empty:
            continue
        ann_factor = np.sqrt(252)
        mu = sub.mean()
        std = sub.std().replace(0, np.nan)

        if metric == "sharpe":
            score = mu / std * ann_factor
        elif metric == "annret":
            score = mu * 252
        elif metric == "sortino":
            downside = sub.where(sub < 0).std().replace(0, np.nan)
            score = mu / downside * ann_factor
        elif metric == "sharpe_min_vol":
            ann_vol = std * ann_factor
            sh = mu / std * ann_factor
            score = sh.where(ann_vol >= 0.02)  # 2% min ann vol
        else:
            raise ValueError(f"unknown metric {metric}")
        score = score.dropna()
        if score.empty:
            continue
        out[int(state)] = str(score.idxmax())
    return out


def macro_rule_router(regime_panel: pd.DataFrame,
                       defensive_pool: list[str] | None = None,
                       ) -> pd.Series:
    """Hand-coded IF-THEN rules based on macro state.

    Returns a per-day Series of defensive symbol to use.

    Rules:
      - CPI YoY ≥ 3.0  AND  PMI ≥ 50           -> 515220 (煤炭)  [inflation+growth]
      - CPI YoY ≥ 3.0  AND  PMI < 50           -> 518880 (黄金)  [inflation+slowdown]
      - CPI YoY < 1.0  AND  PMI < 50           -> 511010 (国债)  [deflation+recession]
      - CPI YoY < 1.0  AND  PMI ≥ 50           -> 515080 (红利低波) [low-infl+growth]
      - 1.0 ≤ CPI < 3.0 AND high vol           -> 518880 (黄金)  [risk-off]
      - 1.0 ≤ CPI < 3.0 AND PMI ≥ 52           -> 515080 (红利低波) [growth, mid-CPI]
      - default                                 -> 511880 (货币基金)
    """
    cpi = regime_panel["cpi_yoy"]
    pmi = regime_panel["pmi"]
    vol_high = regime_panel.get("vol_high", pd.Series(0, index=regime_panel.index)).fillna(0).astype(int)

    out = pd.Series("511880", index=regime_panel.index)  # default

    high_inflation = cpi >= 3.0
    low_inflation = cpi < 1.0
    pmi_expand = pmi >= 50.0
    pmi_strong = pmi >= 52.0

    out[(high_inflation) & (pmi_expand)] = "515220"
    out[(high_inflation) & (~pmi_expand)] = "518880"
    out[(low_inflation) & (~pmi_expand)] = "511010"
    out[(low_inflation) & (pmi_expand)] = "515080"
    out[(~high_inflation) & (~low_inflation) & (vol_high == 1)] = "518880"
    out[(~high_inflation) & (~low_inflation) & (pmi_strong) & (vol_high == 0)] = "515080"

    # Filter to pool (in case some symbol unavailable)
    if defensive_pool is not None:
        out = out.where(out.isin(defensive_pool), other="511880")
    return out


def per_regime_per_macro_best(regime_labels: pd.Series,
                                macro_state: pd.Series,
                                defensive_returns: pd.DataFrame,
                                metric: str = "sharpe_min_vol",
                                min_obs: int = 30,
                                ) -> dict[tuple, str]:
    """Pick best defensive within each (regime_cell, macro_state) bucket.

    Returns mapping (regime, macro) -> symbol.
    """
    out: dict[tuple, str] = {}
    aligned = regime_labels.index.intersection(defensive_returns.index).intersection(macro_state.index)
    rl = regime_labels.loc[aligned]
    ms = macro_state.loc[aligned]
    rr = defensive_returns.loc[aligned]

    ann_factor = np.sqrt(252)
    for r_state in sorted(rl.dropna().unique()):
        for m_state in sorted(ms.dropna().unique()):
            mask = (rl == r_state) & (ms == m_state)
            if mask.sum() < min_obs:
                continue
            sub = rr.loc[mask].dropna(how="all", axis=1)
            if sub.empty:
                continue
            mu = sub.mean(); std = sub.std().replace(0, np.nan)
            if metric == "sharpe":
                score = mu / std * ann_factor
            elif metric == "annret":
                score = mu * 252
            elif metric == "sharpe_min_vol":
                ann_vol = std * ann_factor
                score = (mu / std * ann_factor).where(ann_vol >= 0.02)
            elif metric == "sortino":
                downside = sub.where(sub < 0).std().replace(0, np.nan)
                score = mu / downside * ann_factor
            else:
                raise ValueError(f"unknown {metric}")
            score = score.dropna()
            if score.empty:
                continue
            out[(int(r_state), str(m_state))] = str(score.idxmax())
    return out


def routed_defensive_weights(regime_labels: pd.Series,
                               mapping_or_series,
                               all_symbols: list[str],
                               macro_state: pd.Series | None = None,
                               default_symbol: str = "511880",
                               ) -> pd.DataFrame:
    """Build per-day weight panel placing 1.0 on the chosen defensive.

    `mapping_or_series` can be:
      - dict[int, str]                : regime_cell -> symbol
      - dict[(int, str), str]         : (regime_cell, macro_state) -> symbol
      - pd.Series indexed by date     : direct symbol per day
    """
    out = pd.DataFrame(0.0, index=regime_labels.index, columns=all_symbols)

    if isinstance(mapping_or_series, pd.Series):
        for dt, sym in mapping_or_series.items():
            if dt in out.index and sym in out.columns:
                out.at[dt, sym] = 1.0
            elif dt in out.index and default_symbol in out.columns:
                out.at[dt, default_symbol] = 1.0
        return out

    # dict mapping
    fallback = default_symbol if default_symbol in all_symbols else (all_symbols[0] if all_symbols else None)
    for dt, st in regime_labels.items():
        if pd.isna(st):
            if fallback:
                out.at[dt, fallback] = 1.0
            continue
        st = int(st)
        # Try (regime, macro) tuple key first
        sym = None
        if macro_state is not None and len(mapping_or_series) and isinstance(next(iter(mapping_or_series.keys())), tuple):
            ms = macro_state.get(dt)
            if ms is not None and not pd.isna(ms):
                sym = mapping_or_series.get((st, str(ms)))
        if sym is None:
            sym = mapping_or_series.get(st) if not isinstance(next(iter(mapping_or_series.keys())) if mapping_or_series else 0, tuple) else None
        if sym is None and fallback:
            sym = fallback
        if sym and sym in out.columns:
            out.at[dt, sym] = 1.0
    return out
