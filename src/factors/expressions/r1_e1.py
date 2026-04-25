"""E1 — raw vol-spread, 20d window, 252d z-score, NEGATED at source.

score = -z(realized_vol(r_1000, 20) − realized_vol(r_300, 20))

Negation applied after Stage-4 v1 found IC sign across all 8 expressions
flipped relative to the original M1 thesis. Per Agent-2 hypothesis revision
to M1' (vol-spread → small-cap mean-reversion / contrarian), and per
validation-gates.md:140 ("always negate at source so 'high signal = long'
holds by construction"), the score is negated here so that thesis_sign=+1
still points to "favour 300".
"""
from __future__ import annotations

import pandas as pd

from ..base import Factor, register
from ..util import daily_log_return, realized_vol, rolling_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    r300 = daily_log_return(panel["idx300_close"])
    r1000 = daily_log_return(panel["idx1000_close"])
    raw = realized_vol(r1000, 20) - realized_vol(r300, 20)
    return -rolling_zscore(raw, 252)


register(Factor(
    name="r1_e1_volspread_20d",
    thesis_sign=+1,
    horizon=5,
    fn=_gen,
    rationale="−z(σ20(r1000) − σ20(r300)), 252d rolling z. After M1' revision: high vol-spread → small-cap mean-reversion → favour 1000; low vol-spread → favour 300.",
))
