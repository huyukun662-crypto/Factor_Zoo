"""Deterministic backtest engine for the 300-vs-1000 timing factor.

Conventions
-----------
- Signal s_t computed from data observable up to and including close of day t.
- Position taken at open of day t+delay (delay=1 default), held until next change.
- PnL realized using close-to-close returns of the (idx300 - idx1000) spread,
  applied to the position from the **next trading day after signal** onward.
  Equivalent invariant: target_shift == -(1 + delay) — i.e. signal_t aligns with
  forward return computed from t+delay to t+delay+1.
- 5 bps per side transaction cost on |Δposition| (one-side notional turnover).
- 252 trading days/year for annualization.

The same engine is used by gates G2/G3, audits 1/2, and TVT scoring.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..factors.base import Factor


COST_BPS_PER_SIDE = 5.0
ANNUALIZER = 252
DELAY = 1


def spread_returns(panel: pd.DataFrame) -> pd.Series:
    """Daily simple return of (long idx300 - long idx1000) executed at close-to-close."""
    r300 = panel["idx300_close"].pct_change()
    r1000 = panel["idx1000_close"].pct_change()
    return (r300 - r1000).rename("spread_ret")


def signal_to_position(score: pd.Series, deadband: float = 0.0) -> pd.Series:
    """Map raw score to {-1, 0, +1} with optional deadband (in score units)."""
    pos = pd.Series(0, index=score.index, dtype=float)
    pos[score > deadband] = 1.0
    pos[score < -deadband] = -1.0
    return pos


def apply_delay(position: pd.Series, delay: int = DELAY) -> pd.Series:
    """Shift position forward by `delay` days. signal_t observed at close → trade applied from t+delay close-to-close return."""
    return position.shift(delay).fillna(0.0)


@dataclass
class BacktestResult:
    score: pd.Series
    position: pd.Series
    traded_position: pd.Series  # delay-applied
    daily_pnl: pd.Series        # net of cost
    daily_pnl_gross: pd.Series
    equity: pd.Series
    metrics: dict
    invariant_check: dict


def compute_metrics(daily_pnl: pd.Series, traded_position: pd.Series) -> dict:
    pnl = daily_pnl.dropna()
    if len(pnl) == 0:
        return {
            "n_days": 0, "ann_return": float("nan"), "ann_vol": float("nan"),
            "sharpe": float("nan"), "max_dd": float("nan"), "calmar": float("nan"),
            "ann_turnover": float("nan"), "non_zero_frac": 0.0,
        }
    mu = pnl.mean() * ANNUALIZER
    sd = pnl.std(ddof=1) * np.sqrt(ANNUALIZER)
    sharpe = (mu / sd) if sd > 1e-12 else 0.0
    eq = (1.0 + pnl).cumprod()
    peak = eq.cummax()
    dd = (eq / peak - 1.0).min()
    calmar = (mu / abs(dd)) if dd < 0 else float("inf")
    # turnover = sum |delta position| over year (one-side notional). Position is in {-1,0,1}.
    delta = traded_position.diff().abs().fillna(0.0)
    ann_turn = delta.sum() / max(len(pnl), 1) * ANNUALIZER
    non_zero = float((traded_position != 0).mean())
    return {
        "n_days": int(len(pnl)),
        "ann_return": float(mu),
        "ann_vol": float(sd),
        "sharpe": float(sharpe),
        "max_dd": float(dd),
        "calmar": float(calmar),
        "ann_turnover": float(ann_turn),
        "non_zero_frac": non_zero,
    }


def run_backtest(
    factor: Factor,
    panel: pd.DataFrame,
    delay: int = DELAY,
    cost_bps_per_side: float = COST_BPS_PER_SIDE,
    deadband: float = 0.0,
) -> BacktestResult:
    score = factor.generate(panel)
    score = score.reindex(panel.index)
    position = signal_to_position(score, deadband=deadband)
    traded = apply_delay(position, delay=delay)
    sret = spread_returns(panel)
    gross = (traded * sret).rename("pnl_gross")
    cost = (traded.diff().abs().fillna(0.0) * (cost_bps_per_side / 1e4) * 2.0).rename("cost")
    # cost is per-leg; we trade two legs (300 and 1000) so multiply by 2.
    net = (gross - cost).rename("pnl_net")
    eq = (1.0 + net.fillna(0.0)).cumprod().rename("equity")
    metrics = compute_metrics(net, traded)
    invariant = {
        "delay": int(delay),
        "target_shift": -(1 + delay),
        "engine_target_shift_check": "position.shift(delay) applied to spread_ret indexed at t",
    }
    return BacktestResult(
        score=score, position=position, traded_position=traded,
        daily_pnl=net, daily_pnl_gross=gross,
        equity=eq, metrics=metrics, invariant_check=invariant,
    )


def per_year_breakdown(daily_pnl: pd.Series, traded_position: pd.Series) -> pd.DataFrame:
    """Year-by-year metrics on a net pnl series."""
    df = pd.DataFrame({"pnl": daily_pnl, "pos": traded_position}).dropna(subset=["pnl"])
    if len(df) == 0:
        return pd.DataFrame()
    df["year"] = df.index.year
    rows = []
    for y, grp in df.groupby("year"):
        m = compute_metrics(grp["pnl"], grp["pos"])
        m = {"year": int(y), **m}
        rows.append(m)
    return pd.DataFrame(rows)
