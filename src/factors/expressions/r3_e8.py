"""R3 E8 — regime-conditional acceleration: signal active only in elevated-vol regimes.

base = -z(log(MA5/MA60)(amt_1000))   # same as E2
gate = z(realized_vol(r_1000, 20) − realized_vol(r_300, 20)) over 252d  # raw R1 vol-spread z-score

score(t) = base(t)  if gate(t) > 0    (high relative-vol regime)
         = 0        otherwise

Tests whether the acceleration-momentum signal is concentrated in
high-vol regimes (which would explain why M2 level signals failed
test — the test window had less of the favourable regime).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import daily_log_return, realized_vol, rolling_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    # Acceleration leg
    a = panel["idx1000_amount"].clip(lower=1.0)
    fast = a.rolling(5, min_periods=3).mean()
    slow = a.rolling(60, min_periods=20).mean().clip(lower=1.0)
    base = -rolling_zscore(np.log(fast / slow), 252)

    # Regime gate from R1 raw vol-spread (same construction as r1_e1 BEFORE negation)
    r300 = daily_log_return(panel["idx300_close"])
    r1000 = daily_log_return(panel["idx1000_close"])
    gate = rolling_zscore(realized_vol(r1000, 20) - realized_vol(r300, 20), 252)

    score = base.where(gate > 0, 0.0)
    return score


register(Factor(
    name="r3_e8_accel_high_vol_regime",
    thesis_sign=+1,
    horizon=20,
    fn=_gen,
    rationale="r3_e2 acceleration signal, gated to be active only when R1 raw vol-spread z > 0 (small-cap relative vol elevated). Tests regime concentration.",
))
