"""R4 E7 — R3 E4 with 20d signal-discretization (monthly rebalance proxy).

The signal is sampled every 20 trading days and held constant for the
intervening 20 days. Combined with the engine's deadband mechanism,
this means the position changes only at month-boundaries — turnover
should drop by ~5× vs daily rebalance, reducing cost from ~150 bps/yr
to ~30 bps/yr on the same gross signal.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import discretize_signal, rolling_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    a = panel["idx1000_amount"].clip(lower=1.0)
    fast = a.rolling(5, min_periods=3).mean()
    slow = a.rolling(120, min_periods=40).mean().clip(lower=1.0)
    base = -rolling_zscore(np.log(fast / slow), 252)
    return discretize_signal(base, period=20)


register(Factor(
    name="r4_e7_e4_monthly_rebalance",
    thesis_sign=+1,
    horizon=20,
    fn=_gen,
    rationale="R3 E4 base discretized every 20 trading days (monthly rebalance proxy). Tests rebalance-frequency sensitivity.",
))
