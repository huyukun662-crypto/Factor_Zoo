"""R4 E2 — R3 E4 base × tanh(vol_spread_z / 2.0).

Softer regime gate (temperature 2.0). Less aggressive flipping in
extreme regimes; more weight on M3 base signal across regimes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import rolling_zscore, vol_spread_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    a = panel["idx1000_amount"].clip(lower=1.0)
    fast = a.rolling(5, min_periods=3).mean()
    slow = a.rolling(120, min_periods=40).mean().clip(lower=1.0)
    base = -rolling_zscore(np.log(fast / slow), 252)
    gate = np.tanh(vol_spread_zscore(panel) / 2.0)
    return base * gate


register(Factor(
    name="r4_e2_e4_x_volgate_tanh_t2",
    thesis_sign=+1,
    horizon=20,
    fn=_gen,
    rationale="R3 E4 base * tanh(vol_spread_z/2.0). Softer vol-regime gate.",
))
