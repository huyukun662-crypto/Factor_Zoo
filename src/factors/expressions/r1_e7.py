"""E7 — vol acceleration spread.

(vol_5d_1000 − vol_20d_1000) − (vol_5d_300 − vol_20d_300)

Captures the *change* in vol regime within each index, then takes the
1000−300 spread. High → small-cap vol is accelerating relative to its own
trend faster than large-cap is.
"""
from __future__ import annotations

import pandas as pd

from ..base import Factor, register
from ..util import daily_log_return, realized_vol, rolling_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    r300 = daily_log_return(panel["idx300_close"])
    r1000 = daily_log_return(panel["idx1000_close"])
    accel_1000 = realized_vol(r1000, 5) - realized_vol(r1000, 20)
    accel_300 = realized_vol(r300, 5) - realized_vol(r300, 20)
    raw = accel_1000 - accel_300
    return -rolling_zscore(raw, 252)


register(Factor(
    name="r1_e7_vol_accel_spread",
    thesis_sign=+1,
    horizon=5,
    fn=_gen,
    rationale="Vol-acceleration spread: (5d-20d vol of 1000) minus same of 300, z-scored 252d. Captures the rate of change of relative vol regime.",
))
