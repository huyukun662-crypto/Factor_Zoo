"""E3 — log vol-ratio, 20d window, 252d z-score."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import daily_log_return, realized_vol, rolling_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    r300 = daily_log_return(panel["idx300_close"])
    r1000 = daily_log_return(panel["idx1000_close"])
    v300 = realized_vol(r300, 20).clip(lower=1e-8)
    v1000 = realized_vol(r1000, 20).clip(lower=1e-8)
    raw = np.log(v1000 / v300)
    raw = raw.replace([np.inf, -np.inf], np.nan)
    return -rolling_zscore(raw, 252)


register(Factor(
    name="r1_e3_logvolratio_20d",
    thesis_sign=+1,
    horizon=5,
    fn=_gen,
    rationale="log(vol1000/vol300) over 20d, z-scored over 252d. Symmetric in log space.",
))
