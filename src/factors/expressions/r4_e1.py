"""R4 E1 — R3 E4 base × tanh(vol_spread_z / 1.0).

Smooth regime gate. When R1 vol-spread z is high (small-cap relatively
volatile, "risk-on attention" regime), the M3 momentum signal is
amplified. When vol-spread z is negative (calm/risk-off), the signal
is dampened or flipped.
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
    gate = np.tanh(vol_spread_zscore(panel) / 1.0)
    return base * gate


register(Factor(
    name="r4_e1_e4_x_volgate_tanh_t1",
    thesis_sign=+1,
    horizon=20,
    fn=_gen,
    rationale="R3 E4 base * tanh(vol_spread_z/1.0). Smooth vol-regime gating.",
))
