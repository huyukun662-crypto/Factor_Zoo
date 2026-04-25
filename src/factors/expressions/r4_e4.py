"""R4 E4 — R3 E4 base × max(0, tanh(vol_spread_z)).

ONE-SIDED gate: amplifies the signal in elevated-vol regimes but
NEVER flips it. In low-vol regimes the signal is dampened toward 0,
not reversed. Tests whether the 2025 failure was due to the sign
flipping (rescue-able by one-sided gate) or due to the magnitude
shrinking and being dominated by cost (one-sided gate makes it
worse, not better).
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
    gate = np.clip(np.tanh(vol_spread_zscore(panel)), 0.0, 1.0)
    return base * gate


register(Factor(
    name="r4_e4_e4_x_volgate_oneside",
    thesis_sign=+1,
    horizon=20,
    fn=_gen,
    rationale="R3 E4 base * max(0, tanh(vol_spread_z)). One-sided gate — never flips, only dampens.",
))
