"""R3 E6 — spread of accelerations: 1000-minus-300, MA5/MA60, negated.

Slower-baseline version of E5.
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
    raw = _accel(a1000, 5, 60) - _accel(a300, 5, 60)
    return -rolling_zscore(raw, 252)


register(Factor(
    name="r3_e6_amt_accel_spread_5_60_neg",
    thesis_sign=+1,
    horizon=20,
    fn=_gen,
    rationale="-z((MA5/MA60 accel)(1000) - same(300)). Slower-baseline acceleration spread.",
))
