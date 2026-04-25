"""R5 E6 — R3 E2 base × tanh(-vol_spread_z / 1.0). Mirror of R4 E6, E2 base."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import rolling_zscore, vol_spread_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    a = panel["idx1000_amount"].clip(lower=1.0)
    fast = a.rolling(5, min_periods=3).mean()
    slow = a.rolling(60, min_periods=20).mean().clip(lower=1.0)
    base = -rolling_zscore(np.log(fast / slow), 252)
    gate = np.tanh(-vol_spread_zscore(panel) / 1.0)
    return base * gate


register(Factor(
    name="r5_e6_e2_x_neg_volgate_tanh_t1",
    thesis_sign=+1,
    horizon=20,
    fn=_gen,
    rationale="R3 E2 (5/60) base * tanh(-vol_spread_z/1.0). Mirror of R4 E6.",
))
