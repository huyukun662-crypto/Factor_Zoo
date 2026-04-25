"""R2 E2 — fast log amount ratio (1000/300), 5d MA, 252d z-score."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import rolling_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    a300 = panel["idx300_amount"].clip(lower=1.0)
    a1000 = panel["idx1000_amount"].clip(lower=1.0)
    raw = np.log(a1000 / a300).rolling(5, min_periods=3).mean()
    return rolling_zscore(raw, 252)


register(Factor(
    name="r2_e2_log_amount_ratio_5d",
    thesis_sign=+1,
    horizon=5,
    fn=_gen,
    rationale="z(MA5(log(amount1000/amount300))). Faster crowding signal.",
))
