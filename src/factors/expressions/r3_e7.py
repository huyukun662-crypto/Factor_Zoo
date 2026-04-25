"""R3 E7 — VOLUME-derived acceleration spread (shares, not CNY), negated.

Same construction as E6 but using `vol` (shares traded) instead of
`amount` (CNY). Tests whether the M3 momentum signal is in
share-volume or in CNY-flow.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import rolling_zscore


def _accel(s: pd.Series, fast: int, slow: int) -> pd.Series:
    s = s.clip(lower=1.0)
    return np.log(s.rolling(fast, min_periods=max(3, fast // 2)).mean()
                  / s.rolling(slow, min_periods=max(5, slow // 4)).mean().clip(lower=1.0))


def _gen(panel: pd.DataFrame) -> pd.Series:
    v1000 = panel["idx1000_vol"]
    v300 = panel["idx300_vol"]
    raw = _accel(v1000, 5, 60) - _accel(v300, 5, 60)
    return -rolling_zscore(raw, 252)


register(Factor(
    name="r3_e7_vol_accel_spread_5_60_neg",
    thesis_sign=+1,
    horizon=20,
    fn=_gen,
    rationale="-z((MA5/MA60 accel)(vol_1000) - same(vol_300)). Share-volume version of E6.",
))
