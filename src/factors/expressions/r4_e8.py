"""R4 E8 — R3 E4 base × tanh(market_60d_return_z).

Bull/bear market regime gate using trailing 60d log-return of CSI1000
itself (a market-state proxy). When market is trending up (recent
60d return positive), small-cap continuation has more empirical
support; when market is trending down, the same signal can reverse.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import daily_log_return, rolling_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    a = panel["idx1000_amount"].clip(lower=1.0)
    fast = a.rolling(5, min_periods=3).mean()
    slow = a.rolling(120, min_periods=40).mean().clip(lower=1.0)
    base = -rolling_zscore(np.log(fast / slow), 252)
    r1000 = daily_log_return(panel["idx1000_close"])
    market_60d = r1000.rolling(60, min_periods=20).sum()
    gate = np.tanh(rolling_zscore(market_60d, 252) / 1.0)
    return base * gate


register(Factor(
    name="r4_e8_e4_x_market_60d_gate",
    thesis_sign=+1,
    horizon=20,
    fn=_gen,
    rationale="R3 E4 base * tanh(z(60d log-return of idx1000)). Bull/bear market regime gate.",
))
