"""R2 E3 — abnormal amount: 5d MA over 60d MA, log ratio, 252d z-score.

Detects accelerating retail attention rather than steady-state level.
score = z(MA5(amount_1000) / MA60(amount_1000))  [scale-free, large-cap-agnostic]
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import rolling_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    a1000 = panel["idx1000_amount"].clip(lower=1.0)
    fast = a1000.rolling(5, min_periods=3).mean()
    slow = a1000.rolling(60, min_periods=20).mean()
    raw = np.log(fast / slow.clip(lower=1.0))
    return rolling_zscore(raw, 252)


register(Factor(
    name="r2_e3_abnormal_amount_1000",
    thesis_sign=+1,
    horizon=5,
    fn=_gen,
    rationale="z(log(MA5(amount1000)/MA60(amount1000))). Abnormal small-cap turnover acceleration.",
))
