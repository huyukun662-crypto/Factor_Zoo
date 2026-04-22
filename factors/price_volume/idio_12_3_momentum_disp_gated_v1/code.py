"""
alpha_02_idio_12_3_momentum_disp_gated_v1
==========================================

Reusable factor builder for the dispersion-gated 12-3 idiosyncratic
momentum factor. Output is a daily panel of factor values that downstream
backtest / deployment code consumes.

Mechanism (Stivers-Sun 2010 RFS):
- Idiosyncratic 12-3 momentum  = past 252-day cumulative log return minus
  past 63-day cumulative log return, then cross-section residualized
  per trade_date against {log_mv, sigma_120, ret_20}.
- Dispersion gate              = 1 if cross-sectional std of past-20-day
  return at trade_date t exceeds its rolling 252-day median; else 0.
- Final factor                 = idio momentum (industry-demeaned) × gate.
- Deployment                   = monthly rebalance, Q5 long / Q1 short,
  equal-weight within quintile, 5 bps per side turnover-aware cost.
- When gate = 0, hold cash and pay full liquidation turnover at boundary.

Inputs (Tushare via cached parquets in `.cache/`):
  daily.parquet         ts_code, trade_date, open, close, vol, amount
  adj_factor.parquet    ts_code, trade_date, adj_factor
  daily_basic.parquet   ts_code, trade_date, total_mv, circ_mv
  panel.parquet         (used only for industry mapping per ts_code)

Output:
  pandas DataFrame indexed (ts_code, trade_date) with columns:
      alpha_idio_12_3       — cs-residualized 12-3 momentum
      alpha_n               — industry-demeaned (ready for ranking)
      mkt_disp              — date-level dispersion (replicated to row)
      mkt_disp_med252       — date-level threshold (replicated to row)
      gate                  — 0/1 gate value at each date
      alpha_final           — alpha_n * gate

Run:
  python code.py                              # rebuilds from .cache
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view


CACHE = "/home/user/Factor_Zoo/.cache"


@dataclass
class FactorConfig:
    start_trade_date: str = "20180102"
    end_trade_date: str = "20250418"

    momentum_long_window: int = 252      # cum_252
    momentum_skip_window: int = 63       # cum_63 (skip last 3 months)
    sigma_window: int = 120              # σ_120 control
    short_return_window: int = 20        # ret_20 control

    dispersion_window: int = 20          # cs std of ret_K
    dispersion_lookback: int = 252       # rolling median lookback for gate
    dispersion_lookback_min: int = 180   # min_periods for gate threshold

    rebalance_days: int = 20
    delay: int = 1
    cost_bps_per_side: int = 5
    quintiles: int = 5


# --------------------------------------------------------------------- #
# Building blocks                                                       #
# --------------------------------------------------------------------- #

def load_base(cfg: FactorConfig) -> pd.DataFrame:
    daily = pd.read_parquet(f"{CACHE}/daily.parquet")
    adj = pd.read_parquet(f"{CACHE}/adj_factor.parquet")
    db = pd.read_parquet(f"{CACHE}/daily_basic.parquet")
    panel = pd.read_parquet(f"{CACHE}/panel.parquet")[
        ["ts_code", "industry"]
    ].drop_duplicates("ts_code")

    df = daily.merge(adj, on=["ts_code", "trade_date"], how="left")
    df = df.merge(db[["ts_code", "trade_date", "total_mv"]], on=["ts_code", "trade_date"], how="left")
    df = df.merge(panel, on="ts_code", how="left")
    df["adj_factor"] = df["adj_factor"].fillna(1.0)
    df["P"] = df["close"] * df["adj_factor"]
    df["log_p"] = np.log(df["P"])
    df["log_mv"] = np.log(df["total_mv"].replace(0, np.nan))
    df = df.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df


def add_returns_and_controls(df: pd.DataFrame, cfg: FactorConfig) -> pd.DataFrame:
    df["ret"] = df.groupby("ts_code")["log_p"].diff()
    g = df.groupby("ts_code")["ret"]
    df[f"cum_{cfg.momentum_long_window}"] = g.transform(
        lambda s: s.rolling(cfg.momentum_long_window, min_periods=int(cfg.momentum_long_window * 0.8)).sum()
    )
    df[f"cum_{cfg.momentum_skip_window}"] = g.transform(
        lambda s: s.rolling(cfg.momentum_skip_window, min_periods=int(cfg.momentum_skip_window * 0.7)).sum()
    )
    df[f"sigma_{cfg.sigma_window}"] = g.transform(
        lambda s: s.rolling(cfg.sigma_window, min_periods=int(cfg.sigma_window * 0.7)).std(ddof=0)
    )
    df[f"ret_{cfg.short_return_window}"] = g.transform(
        lambda s: s.rolling(cfg.short_return_window, min_periods=int(cfg.short_return_window * 0.75)).sum()
    )
    df["raw_idio_12_3"] = (
        df[f"cum_{cfg.momentum_long_window}"] - df[f"cum_{cfg.momentum_skip_window}"]
    )
    return df


def cs_residualize(df: pd.DataFrame, target: str, controls: list[str]) -> pd.Series:
    """Per-date OLS residualization. Walk-forward-safe by construction."""
    out = pd.Series(np.nan, index=df.index, dtype=np.float64)
    sub = df[["trade_date", target] + controls].copy()
    for d, idx in sub.groupby("trade_date").indices.items():
        rows = sub.loc[idx]
        m = rows[[target] + controls].dropna()
        if len(m) < 50:
            continue
        y = m[target].values
        X = np.column_stack([np.ones(len(m))] + [m[c].values for c in controls])
        try:
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
            out.loc[m.index] = y - X @ beta
        except np.linalg.LinAlgError:
            continue
    return out


def industry_demean(df: pd.DataFrame, col: str) -> pd.Series:
    return df[col] - df.groupby(["trade_date", "industry"])[col].transform("mean")


def build_dispersion_gate(df: pd.DataFrame, cfg: FactorConfig) -> pd.Series:
    """Per-date dispersion gate, indexed by trade_date.
    Series value = {0, 1} indicating whether α should be deployed at that date."""
    disp = df.groupby("trade_date")[f"ret_{cfg.dispersion_window}"].std()
    disp_threshold = disp.rolling(cfg.dispersion_lookback, min_periods=cfg.dispersion_lookback_min).median()
    gate = (disp > disp_threshold).astype(int)
    gate.name = "gate"
    return gate


# --------------------------------------------------------------------- #
# Top-level builder                                                     #
# --------------------------------------------------------------------- #

def build_factor(cfg: FactorConfig | None = None) -> pd.DataFrame:
    """Returns the deployment-ready factor panel.

    Output columns:
      ts_code, trade_date, industry, total_mv, log_mv,
      sigma_<W>, ret_<W>, raw_idio_12_3,
      alpha_idio_12_3, alpha_n, mkt_disp, mkt_disp_med252, gate, alpha_final
    """
    cfg = cfg or FactorConfig()
    t0 = time.time()
    print("[factor] loading base...")
    df = load_base(cfg)
    print(f"  loaded {len(df):,} rows  {time.time()-t0:.1f}s")

    print("[factor] computing returns + controls...")
    df = add_returns_and_controls(df, cfg)

    print("[factor] cross-sectional residualization (per date)...")
    controls = ["log_mv", f"sigma_{cfg.sigma_window}", f"ret_{cfg.short_return_window}"]
    df["alpha_idio_12_3"] = cs_residualize(df, "raw_idio_12_3", controls)

    print("[factor] industry-demeaning...")
    df = df.dropna(subset=["industry"]).reset_index(drop=True)
    df["alpha_n"] = industry_demean(df, "alpha_idio_12_3")

    print("[factor] building dispersion gate...")
    gate = build_dispersion_gate(df, cfg)
    df["mkt_disp"] = df["trade_date"].map(
        df.groupby("trade_date")[f"ret_{cfg.dispersion_window}"].std()
    )
    disp_threshold = (
        df.groupby("trade_date")[f"ret_{cfg.dispersion_window}"].std()
        .rolling(cfg.dispersion_lookback, min_periods=cfg.dispersion_lookback_min)
        .median()
    )
    df["mkt_disp_med252"] = df["trade_date"].map(disp_threshold)
    df["gate"] = df["trade_date"].map(gate).fillna(0).astype(int)

    df["alpha_final"] = df["alpha_n"] * df["gate"]
    print(f"[factor] done in {time.time()-t0:.1f}s, "
          f"gate on-fraction = {gate.mean():.3f}")
    return df


# --------------------------------------------------------------------- #
# CLI                                                                   #
# --------------------------------------------------------------------- #

if __name__ == "__main__":
    cfg = FactorConfig()
    out = build_factor(cfg)
    print("\nfinal panel head:")
    print(out[["ts_code", "trade_date", "industry", "alpha_n", "gate", "alpha_final"]].head())
    print("\nNaN fractions of key columns:")
    for c in ["raw_idio_12_3", "alpha_idio_12_3", "alpha_n", "alpha_final"]:
        print(f"  {c}: {out[c].isna().mean():.3f}")
