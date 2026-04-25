"""E8 — vol-spread normalized by long-run large-cap baseline vol.

(vol_20d_1000 − vol_20d_300) / rolling_mean(vol_20d_300, 252)

Distinct from E2: E2 normalises by CONTEMPORANEOUS large-cap vol (giving a
relative-spread measure), E8 normalises by the LONG-RUN average level of
large-cap vol (giving an "absolute spread relative to a typical vol regime"
measure). When large-cap vol itself is currently elevated, these can give
different signals.
"""
from __future__ import annotations

import pandas as pd

from ..base import Factor, register
from ..util import daily_log_return, realized_vol, rolling_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    r300 = daily_log_return(panel["idx300_close"])
    r1000 = daily_log_return(panel["idx1000_close"])
    v300 = realized_vol(r300, 20)
    v1000 = realized_vol(r1000, 20)
    baseline = v300.rolling(252, min_periods=60).mean().clip(lower=1e-8)
    raw = (v1000 - v300) / baseline
    return -rolling_zscore(raw, 252)


register(Factor(
    name="r1_e8_volspread_longbaseline",
    thesis_sign=+1,
    horizon=5,
    fn=_gen,
    rationale="(vol1000 - vol300)/rolling_mean(vol300,252) over 20d, z-scored 252d. Spread sized against the long-run baseline of large-cap vol.",
))
