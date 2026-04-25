"""R3 E3 — slower numerator: MA10/MA60, negated.

Tests whether broadening the "current attention" window from 5d to 10d
preserves the momentum signal (less noise, slower reaction).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import rolling_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    a = panel["idx1000_amount"].clip(lower=1.0)
    fast = a.rolling(10, min_periods=5).mean()
    slow = a.rolling(60, min_periods=20).mean().clip(lower=1.0)
    raw = np.log(fast / slow)
    return -rolling_zscore(raw, 252)


register(Factor(
    name="r3_e3_amt_accel_10_60_neg",
    thesis_sign=+1,
    horizon=20,
    fn=_gen,
    rationale="-z(log(MA10/MA60)(amt_1000)). Slower numerator window.",
))
