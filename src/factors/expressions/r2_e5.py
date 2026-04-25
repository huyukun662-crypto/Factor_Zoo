"""R2 E5 — log amount ratio with longer 504d z-score baseline (regime-relative)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import rolling_zscore


def _gen(panel: pd.DataFrame) -> pd.Series:
    a300 = panel["idx300_amount"].clip(lower=1.0)
    a1000 = panel["idx1000_amount"].clip(lower=1.0)
    raw = np.log(a1000 / a300).rolling(20, min_periods=5).mean()
    return rolling_zscore(raw, 504)


register(Factor(
    name="r2_e5_log_amount_ratio_z504",
    thesis_sign=+1,
    horizon=5,
    fn=_gen,
    rationale="Same raw as r2_e1 but z over 504d. Captures longer (~2y) regime shifts in style turnover concentration.",
))
