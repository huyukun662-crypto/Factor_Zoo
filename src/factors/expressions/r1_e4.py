"""E4 — faster vol-spread, 10d window, 252d z-score."""
from __future__ import annotations

import pandas as pd

from ..base import Factor, register
from ..util import daily_log_return, realized_vol, rolling_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    r300 = daily_log_return(panel["idx300_close"])
    r1000 = daily_log_return(panel["idx1000_close"])
    raw = realized_vol(r1000, 10) - realized_vol(r300, 10)
    return -rolling_zscore(raw, 252)


register(Factor(
    name="r1_e4_volspread_10d",
    thesis_sign=+1,
    horizon=5,
    fn=_gen,
    rationale="Faster vol-spread (10d window), z-scored over 252d. Reacts to vol shocks faster than E1.",
))
