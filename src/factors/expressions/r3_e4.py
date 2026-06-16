"""R3 E4 — long baseline MA5/MA120, negated.

Halve the baseline back to a longer regime (~5 months). Tests whether
the acceleration signal works against a longer reference.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import rolling_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    a = panel["idx1000_amount"].clip(lower=1.0)
    fast = a.rolling(5, min_periods=3).mean()
    slow = a.rolling(120, min_periods=40).mean().clip(lower=1.0)
    raw = np.log(fast / slow)
    return -rolling_zscore(raw, 252)


register(Factor(
    name="r3_e4_amt_accel_5_120_neg",
    thesis_sign=+1,
    horizon=20,
    fn=_gen,
    rationale="-z(log(MA5/MA120)(amt_1000)). Longer baseline (~5 months).",
))
