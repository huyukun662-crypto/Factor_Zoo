"""R3 E2 — single-leg amount acceleration MA5/MA60, negated.

This is R2 E3 negated. The R2 E3 had TRAIN IC = -0.196 with t = -5.93;
negated, this targets +0.196 IC. Direct test of the R2 finding.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import rolling_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    a = panel["idx1000_amount"].clip(lower=1.0)
    fast = a.rolling(5, min_periods=3).mean()
    slow = a.rolling(60, min_periods=20).mean().clip(lower=1.0)
    raw = np.log(fast / slow)
    return -rolling_zscore(raw, 252)


register(Factor(
    name="r3_e2_amt_accel_5_60_neg",
    thesis_sign=+1,
    horizon=20,
    fn=_gen,
    rationale="-z(log(MA5/MA60)(amt_1000)). R2 E3 negated; primary R3 lead.",
))
