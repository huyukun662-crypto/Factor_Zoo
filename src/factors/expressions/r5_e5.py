"""R5 E5 — R3 E4 × tanh(-(vol_z + turnover_z) / 2 / 1.5). Composite mirror."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import rolling_zscore, turnover_level_zscore, vol_spread_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    a = panel["idx1000_amount"].clip(lower=1.0)
    fast = a.rolling(5, min_periods=3).mean()
    slow = a.rolling(120, min_periods=40).mean().clip(lower=1.0)
    base = -rolling_zscore(np.log(fast / slow), 252)
    composite = (vol_spread_zscore(panel) + turnover_level_zscore(panel)) / 2.0
    gate = np.tanh(-composite / 1.5)
    return base * gate


register(Factor(
    name="r5_e5_e4_x_neg_composite",
    thesis_sign=+1,
    horizon=20,
    fn=_gen,
    rationale="R3 E4 * tanh(-avg(vol_z, turnover_z)/1.5). Mirror of R4 E5.",
))
