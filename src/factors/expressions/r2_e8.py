"""R2 E8 — amount share: 1000 fraction of (1000+300) total amount.

share_1000 = amount_1000 / (amount_1000 + amount_300)

When share rises, small-cap is consuming a higher fraction of the
total broad-base trading flow. Z-score over 252d of the 20d-smoothed
share. Distinct from log ratio because it is bounded in [0, 1] and
interpretable as a flow-share rather than a relative magnitude.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import rolling_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    a300 = panel["idx300_amount"].clip(lower=1.0)
    a1000 = panel["idx1000_amount"].clip(lower=1.0)
    share = a1000 / (a1000 + a300)
    raw = share.rolling(20, min_periods=5).mean()
    return rolling_zscore(raw, 252)


register(Factor(
    name="r2_e8_amount_share_1000",
    thesis_sign=+1,
    horizon=5,
    fn=_gen,
    rationale="z(MA20(amount_1000 / (amount_1000 + amount_300))). Small-cap share of broad-base flow.",
))
