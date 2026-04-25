"""E6 — downside-vol-spread, 20d window, 252d z-score.

Asymmetric: uses semivariance over negative returns only. Captures
risk-off panics rather than bidirectional vol.
"""
from __future__ import annotations

import pandas as pd

from ..base import Factor, register
from ..util import daily_log_return, downside_vol, rolling_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    r300 = daily_log_return(panel["idx300_close"])
    r1000 = daily_log_return(panel["idx1000_close"])
    raw = downside_vol(r1000, 20) - downside_vol(r300, 20)
    return -rolling_zscore(raw, 252)


register(Factor(
    name="r1_e6_downvolspread_20d",
    thesis_sign=+1,
    horizon=5,
    fn=_gen,
    rationale="Downside-vol spread (1000 minus 300, semivariance over negative returns), z-scored 252d. Asymmetric vol regime probe.",
))
