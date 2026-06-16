"""R5 E4 — R3 E4 × max(0, tanh(-vol_spread_z)).

One-sided CALM gate: amplifies M3 in calm regimes (vol_spread_z < 0)
and dampens to ZERO in elevated-vol regimes. Never flips sign.
Distinct from R5 E1 (which flips sign in elevated-vol).
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
    gate = np.clip(np.tanh(-vol_spread_zscore(panel)), 0.0, 1.0)
    return base * gate


register(Factor(
    name="r5_e4_e4_x_neg_volgate_oneside",
    thesis_sign=+1,
    horizon=20,
    fn=_gen,
    rationale="R3 E4 * max(0, tanh(-vol_spread_z)). One-sided calm-only gate; never flips.",
))
