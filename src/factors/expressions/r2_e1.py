"""R2 E1 — log amount ratio (1000/300), 20d MA, 252d z-score.

Captures the *level* of small-cap-vs-large-cap turnover concentration.
High ratio → retail crowding on small-caps → mean-revert in ~5d → favour 300.

Negation note: R1 found "high vol-spread → small-cap recovery". M2 thesis
is opposite: "high turnover-spread → small-cap reversal" (favour 300).
We do NOT negate at source; the natural sign is +1 here.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import rolling_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    a300 = panel["idx300_amount"].clip(lower=1.0)
    a1000 = panel["idx1000_amount"].clip(lower=1.0)
    raw = np.log(a1000 / a300).rolling(20, min_periods=5).mean()
    return rolling_zscore(raw, 252)


register(Factor(
    name="r2_e1_log_amount_ratio_20d",
    thesis_sign=+1,
    horizon=5,
    fn=_gen,
    rationale="z(MA20(log(amount1000/amount300))). Level of small-cap crowding, smoothed.",
))
