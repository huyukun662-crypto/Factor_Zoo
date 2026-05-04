"""Defensive asset CATEGORIES (大类) for matrix-based routing.

The macro matrix maps each (axis1 × axis2) cell to ONE category.
Within a category, weights are equal-weight (could be vol-parity later).

Categories defined here all have IS coverage starting reasonably early.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


CATEGORIES: dict[str, dict] = {
    "长债": {
        "constituents": ["511010", "511260"],     # 10Y国债, 10Y国开
        "weight": "equal",
        "intuition": "衰退/通缩/利率下行受益",
    },
    "货币": {
        "constituents": ["511880"],                # 银华日利
        "weight": "equal",
        "intuition": "不确定环境/短期避险/默认",
    },
    "黄金": {
        "constituents": ["518880"],                # 黄金
        "weight": "equal",
        "intuition": "通胀对冲/全球风险事件/USD 走弱",
    },
    "红利低波": {
        "constituents": ["515080"],                # 红利低波 (上市 2019-12)
        "weight": "equal",
        "intuition": "低波价值/中通胀+增长温和",
    },
    "商品": {
        "constituents": ["518880", "162411", "515220"],  # 黄金+油气+煤炭 (能源/资源)
        "weight": "equal",
        "intuition": "高通胀/顺周期/USD 弱势",
    },
    "海外股": {
        "constituents": ["513100", "513500", "513050", "159920"],  # 纳指+标普+中概互联+恒生
        "weight": "equal",
        "intuition": "RMB 贬值受益/A 股弱势对冲",
    },
}


def build_category_returns(close: pd.DataFrame) -> pd.DataFrame:
    """Equal-weight daily simple-return series for each category.

    Returns DataFrame indexed by date with one column per category.
    Symbols not present in close are skipped; if a row has all-NaN constituents,
    the category return for that day is NaN.
    """
    out = pd.DataFrame(index=close.index)
    for name, cfg in CATEGORIES.items():
        cols = [c for c in cfg["constituents"] if c in close.columns]
        if not cols:
            out[name] = np.nan
            continue
        sub = close[cols].pct_change()
        # equal-weight average across constituents available that day
        out[name] = sub.mean(axis=1, skipna=True)
    return out


def build_category_weights(category: str, all_symbols: list[str]) -> pd.Series:
    """Per-symbol weight vector for a single category. Sums to 1 across cols."""
    w = pd.Series(0.0, index=all_symbols)
    if category not in CATEGORIES:
        return w
    cols = [c for c in CATEGORIES[category]["constituents"] if c in all_symbols]
    if cols:
        w[cols] = 1.0 / len(cols)
    return w


def category_for(symbol: str) -> str | None:
    """Reverse lookup: which category owns this symbol (first match)."""
    for name, cfg in CATEGORIES.items():
        if symbol in cfg["constituents"]:
            return name
    return None
