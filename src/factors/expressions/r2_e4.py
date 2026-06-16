"""R2 E4 — abnormal amount SPREAD: small-cap acceleration minus large-cap acceleration.

Removes any market-wide flow regime; isolates the SMALL-CAP-SPECIFIC
attention spike.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import rolling_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    a300 = panel["idx300_amount"].clip(lower=1.0)
    a1000 = panel["idx1000_amount"].clip(lower=1.0)
    abn_1000 = np.log(a1000.rolling(5, min_periods=3).mean() / a1000.rolling(60, min_periods=20).mean().clip(lower=1.0))
    abn_300 = np.log(a300.rolling(5, min_periods=3).mean() / a300.rolling(60, min_periods=20).mean().clip(lower=1.0))
    raw = abn_1000 - abn_300
    return rolling_zscore(raw, 252)


register(Factor(
    name="r2_e4_abnormal_amount_spread",
    thesis_sign=+1,
    horizon=5,
    fn=_gen,
    rationale="z(abnormal_amount(1000) - abnormal_amount(300)). Small-cap-specific attention acceleration.",
))
