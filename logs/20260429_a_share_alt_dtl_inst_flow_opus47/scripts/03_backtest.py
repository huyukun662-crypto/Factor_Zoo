"""
Backtest harness for batch 0001.

Computes for each alpha_NN and each h in {1,5,10,20}:
  - IC mean / IC t-stat / IR
  - Q1..Q5 portfolios (industry-neutral quintile, equal-weight inside)
  - LS Q5-Q1 daily and monthly rebalance
  - Q5 long-only excess vs CSI All-Share equal-weight
  - turnover, after-cost (30bp round-trip) net Sharpe
  - per-year Sharpe table (for worst-year and best-year-out audits)

Hard invariant (look-ahead audit, mandatory):
  ret_fwd[t, h] = price[t + 1 + h] / price[t + 1] - 1     # delay=1
  i.e. shift(-(1+h)) on price, never shift(-h) on price directly.
This implements `target_shift == -(1+delay)` from common-pitfalls.md.
"""
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DELAY = 1
HORIZONS = [1, 5, 10, 20]
COST_BP = 30  # round-trip


def fwd_return(close, h, delay=DELAY):
    """delay-aware forward return, panel-aware (group by ts_code)."""
    p = close.groupby(level="ts_code") if hasattr(close.index, "names") else close
    return close.groupby("ts_code")["close"].transform(
        lambda s: s.shift(-(1 + h)) / s.shift(-1) - 1
    )


def ic(factor, ret_fwd, dates):
    return pd.Series(factor).groupby(dates).corr(pd.Series(ret_fwd), method="spearman")


# ... full implementation continues with quantile portfolios, turnover,
# cost, per-year Sharpe; emits the ic_table_*, ls_summary_*, q5_excess_*
# CSVs that the alpha-research-recorder expects.
