"""R3 E1 — single-leg amount acceleration MA5/MA20, negated.

score = -z(log(MA5(amt_1000) / MA20(amt_1000)))

Faster baseline window than R2 E3 (60d → 20d). Tests whether the
acceleration-as-momentum signal holds with a tighter baseline.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import rolling_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    a = panel["idx1000_amount"].clip(lower=1.0)
    fast = a.rolling(5, min_periods=3).mean()
    slow = a.rolling(20, min_periods=5).mean().clip(lower=1.0)
    raw = np.log(fast / slow)
    return -rolling_zscore(raw, 252)


register(Factor(
    name="r3_e1_amt_accel_5_20_neg",
    thesis_sign=+1,
    horizon=20,
    fn=_gen,
    rationale="-z(log(MA5/MA20)(amt_1000)). Single-leg fast acceleration, momentum-direction.",
))
