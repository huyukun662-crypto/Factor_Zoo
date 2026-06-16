"""R2 E7 — turnover acceleration spread (5d-20d) cross 1000-vs-300.

Analogue of R1 E7 (vol acceleration), but on log amounts.
score = z((MA5 − MA20)(log_amt_1000) − (MA5 − MA20)(log_amt_300))
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import rolling_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    a300 = panel["idx300_amount"].clip(lower=1.0)
    a1000 = panel["idx1000_amount"].clip(lower=1.0)
    la300, la1000 = np.log(a300), np.log(a1000)
    accel_1000 = la1000.rolling(5, min_periods=3).mean() - la1000.rolling(20, min_periods=5).mean()
    accel_300 = la300.rolling(5, min_periods=3).mean() - la300.rolling(20, min_periods=5).mean()
    raw = accel_1000 - accel_300
    return rolling_zscore(raw, 252)


register(Factor(
    name="r2_e7_log_amount_accel_spread",
    thesis_sign=+1,
    horizon=5,
    fn=_gen,
    rationale="z((MA5-MA20)(log_amt_1000) - (MA5-MA20)(log_amt_300)). Turnover acceleration spread.",
))
