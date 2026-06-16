"""R2 E6 — turnover-residualized-by-vol.

Concern: amount and realized vol are mechanically correlated (more vol →
more trading by definition). To ensure M2 is not just M1 in disguise,
this expression projects log(amount1000) onto log(vol1000) over a rolling
window and uses the RESIDUAL spread as the signal.

score = z(residual_log_amount_1000 - residual_log_amount_300)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import Factor, register
from ..util import daily_log_return, realized_vol, rolling_zscore


def _residualize_vs_vol(amount: pd.Series, returns: pd.Series, win: int = 252) -> pd.Series:
    """Rolling beta-residualize log(amount) against log(realized_vol(returns, 20))."""
    log_amt = np.log(amount.clip(lower=1.0))
    log_vol = np.log(realized_vol(returns, 20).clip(lower=1e-8))
    df = pd.DataFrame({"y": log_amt, "x": log_vol}).dropna()
    # Rolling residual via centered ratios
    cov = df["x"].rolling(win, min_periods=60).cov(df["y"])
    var = df["x"].rolling(win, min_periods=60).var(ddof=1)
    beta = cov / var
    mean_y = df["y"].rolling(win, min_periods=60).mean()
    mean_x = df["x"].rolling(win, min_periods=60).mean()
    alpha = mean_y - beta * mean_x
    pred = alpha + beta * df["x"]
    resid = (df["y"] - pred).reindex(amount.index)
    return resid


def _gen(panel: pd.DataFrame) -> pd.Series:
    r300 = daily_log_return(panel["idx300_close"])
    r1000 = daily_log_return(panel["idx1000_close"])
    res_1000 = _residualize_vs_vol(panel["idx1000_amount"], r1000).rolling(20, min_periods=5).mean()
    res_300 = _residualize_vs_vol(panel["idx300_amount"], r300).rolling(20, min_periods=5).mean()
    raw = res_1000 - res_300
    return rolling_zscore(raw, 252)


register(Factor(
    name="r2_e6_amount_resid_vs_vol_spread",
    thesis_sign=+1,
    horizon=5,
    fn=_gen,
    rationale="z(MA20(resid log(amount1000) | log(vol1000))) − same for 300. Removes mechanical vol-driven trading; isolates pure attention/flow.",
))
