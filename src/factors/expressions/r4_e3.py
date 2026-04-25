"""R4 E3 — R3 E4 base × tanh(turnover_level_z / 1.5).

Use R2-level (turnover-ratio) as the regime gate instead of vol-spread.
When small-cap is consuming an unusually large share of trading flow
(R2 thesis territory), amplify the M3 momentum signal.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import rolling_zscore, turnover_level_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    a = panel["idx1000_amount"].clip(lower=1.0)
    fast = a.rolling(5, min_periods=3).mean()
    slow = a.rolling(120, min_periods=40).mean().clip(lower=1.0)
    base = -rolling_zscore(np.log(fast / slow), 252)
    gate = np.tanh(turnover_level_zscore(panel) / 1.5)
    return base * gate


register(Factor(
    name="r4_e3_e4_x_turnoverlevel_tanh",
    thesis_sign=+1,
    horizon=20,
    fn=_gen,
    rationale="R3 E4 base * tanh(R2_turnover_level_z/1.5). Turnover-level as regime gate.",
))
