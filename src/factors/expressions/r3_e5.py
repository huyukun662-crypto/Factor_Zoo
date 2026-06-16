"""R3 E5 — spread of accelerations: 1000-minus-300, MA5/MA20, negated.

Removes any market-wide attention regime by differencing the small-cap
acceleration against the large-cap acceleration on the same windows.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import rolling_zscore


def _accel(amt: pd.Series, fast: int, slow: int) -> pd.Series:
    a = amt.clip(lower=1.0)
    return np.log(a.rolling(fast, min_periods=max(3, fast // 2)).mean()
                  / a.rolling(slow, min_periods=max(5, slow // 4)).mean().clip(lower=1.0))


def _gen(panel: pd.DataFrame) -> pd.Series:
    a1000 = panel["idx1000_amount"]
    a300 = panel["idx300_amount"]
    raw = _accel(a1000, 5, 20) - _accel(a300, 5, 20)
    return -rolling_zscore(raw, 252)


register(Factor(
    name="r3_e5_amt_accel_spread_5_20_neg",
    thesis_sign=+1,
    horizon=20,
    fn=_gen,
    rationale="-z((MA5/MA20 accel)(1000) - same(300)). Spread-of-accels removes market-wide attention.",
))
