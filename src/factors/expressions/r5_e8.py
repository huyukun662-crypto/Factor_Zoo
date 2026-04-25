"""R5 E8 — combo: reverse vol-gate × 20d signal-discretization (monthly rebalance).

Combines R5 E1 (calm-regime-amplified base) with the rebalance-frequency
reduction tested separately in R4 E7. If both refinements compound,
this should be the strongest R5 expression.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import discretize_signal, rolling_zscore, vol_spread_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    a = panel["idx1000_amount"].clip(lower=1.0)
    fast = a.rolling(5, min_periods=3).mean()
    slow = a.rolling(120, min_periods=40).mean().clip(lower=1.0)
    base = -rolling_zscore(np.log(fast / slow), 252)
    gate = np.tanh(-vol_spread_zscore(panel) / 1.0)
    raw = base * gate
    return discretize_signal(raw, period=20)


register(Factor(
    name="r5_e8_e4_x_neg_volgate_monthly",
    thesis_sign=+1,
    horizon=20,
    fn=_gen,
    rationale="R3 E4 * tanh(-vol_spread_z) discretized to 20d hold. Combines R5 E1 reverse gate with R4 E7 monthly rebalance.",
))
