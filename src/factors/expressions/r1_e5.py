"""E5 — vol-spread regime-relative z-score with longer 504d (~2y) baseline.

Distinct from E1 by using a longer regime-relative baseline → emphasises
true regime change vs short-cycle noise.
"""
from __future__ import annotations

import pandas as pd

from ..base import Factor, register
from ..util import daily_log_return, realized_vol, rolling_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    r300 = daily_log_return(panel["idx300_close"])
    r1000 = daily_log_return(panel["idx1000_close"])
    raw = realized_vol(r1000, 20) - realized_vol(r300, 20)
    return -rolling_zscore(raw, 504)


register(Factor(
    name="r1_e5_volspread_20d_z504",
    thesis_sign=+1,
    horizon=5,
    fn=_gen,
    rationale="Same raw spread as E1 but z-scored over 504d (~2y). Captures longer regime shifts.",
))
