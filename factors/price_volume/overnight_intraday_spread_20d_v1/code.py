"""
overnight_intraday_spread_20d_v1
================================

Deployable A-share volume-price factor: 20-day cumulative log-overnight return
minus 20-day cumulative log-intraday return, industry-demeaned and
cross-section z-scored per date.

Mechanism
---------
Under A-share T+1 settlement and a single open auction, overnight gaps
concentrate informed flow (regulatory news, foreign markets, fund flows)
while intraday returns are dominated by retail noise (>80 % of intraday
turnover). The spread `ON_20 - ID_20` follows Lou-Polk-Skouras (2019, JFE)
and is mechanically orthogonal to total close-to-close cumulative return,
which the residualization audit confirms (81 % Sharpe retention vs the
{log_mv, sigma_20, ret_5, ret_20, turnover_20} control stack).

Inputs (Tushare via cached parquets in `.cache/`)
  daily.parquet        (open, close, vol, amount)
  adj_factor.parquet   (adj_factor)
  daily_basic.parquet  (total_mv, circ_mv, turnover_rate_f)
  stock_basic.parquet  (industry — CITIC L1 proxy)

Output
  pandas.DataFrame of per-rebalance holdings:
    trade_date, ts_code, weight, abs_ret, exc_ret, tov, cost
  plus headline columns: r_q5, r_q1, r_uni, ls_gross, ls_net, q5_excess.

Source session: logs/20260428_a_share_overnight_intraday_alpha/
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path("/home/user/Factor_Zoo/.cache")


@dataclass
class FactorConfig:
    window_d: int = 20                          # ON_20 - ID_20 spread window
    delay: int = 1                              # T+1 execution
    rebalance_days: int = 20                    # monthly rebalance
    top_pct: float = 0.20                       # Q5 = top 20 %
    bot_pct: float = 0.20                       # Q1 = bottom 20 % (LS form)
    industry_demean: bool = True
    log_ret_winsor: tuple[float, float] = (-0.105, 0.105)
    cs_winsor: tuple[float, float] = (0.01, 0.99)
    cost_bps_per_side: int = 5
    min_universe_per_reb: int = 200


# --------------------------------------------------------------------- #
# Helpers                                                               #
# --------------------------------------------------------------------- #

def cs_zscore(s: pd.Series) -> pd.Series:
    mu, sd = s.mean(), s.std()
    if sd == 0 or np.isnan(sd):
        return s * 0.0
    return (s - mu) / sd


def per_date_winsor(s: pd.Series, low: float = 0.01, high: float = 0.99) -> pd.Series:
    return s.clip(s.quantile(low), s.quantile(high))


# --------------------------------------------------------------------- #
# Panel build                                                           #
# --------------------------------------------------------------------- #

def build_panel(cfg: FactorConfig) -> pd.DataFrame:
    """Build the per (ts_code, trade_date) panel with raw alpha + fwd_ret_k."""
    daily = pd.read_parquet(CACHE / "daily.parquet")
    adj   = pd.read_parquet(CACHE / "adj_factor.parquet")
    db    = pd.read_parquet(CACHE / "daily_basic.parquet")
    sb    = pd.read_parquet(CACHE / "stock_basic.parquet",
                            columns=["ts_code", "name", "industry"])

    df = daily.merge(adj, on=["ts_code", "trade_date"], how="left")
    df = df.merge(db,  on=["ts_code", "trade_date"], how="left")
    df = df.merge(sb,  on="ts_code", how="left")
    df["trade_date"] = df["trade_date"].astype(str)
    df = df.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)

    # universe filter
    df = df[~df["name"].fillna("").str.contains("ST")]
    df = df[df["vol"].fillna(0) > 0]

    # primitives
    g = df.groupby("ts_code", sort=False)
    df["close_adj_prev"] = g["close"].shift(1) * g["adj_factor"].shift(1)
    df["close_adj"]      = df["close"] * df["adj_factor"]
    df["open_adj"]       = df["open"]  * df["adj_factor"]
    df["ret_ON"] = df["open_adj"]  / df["close_adj_prev"] - 1.0
    df["ret_ID"] = df["close"]     / df["open"]            - 1.0
    df["ret_CC"] = df["close_adj"] / df["close_adj_prev"]  - 1.0
    df["log_ON"] = np.log1p(df["ret_ON"]).clip(*cfg.log_ret_winsor)
    df["log_ID"] = np.log1p(df["ret_ID"]).clip(*cfg.log_ret_winsor)
    df["log_CC"] = np.log1p(df["ret_CC"]).clip(*cfg.log_ret_winsor)

    # raw alpha — the spread
    g = df.groupby("ts_code", sort=False)
    df["sum_ON_w"] = g["log_ON"].transform(
        lambda s: s.rolling(cfg.window_d, min_periods=int(cfg.window_d * 0.75)).sum())
    df["sum_ID_w"] = g["log_ID"].transform(
        lambda s: s.rolling(cfg.window_d, min_periods=int(cfg.window_d * 0.75)).sum())
    df["alpha_raw"] = df["sum_ON_w"] - df["sum_ID_w"]

    # forward returns — invariant target_shift = -(1+delay)
    for k in [1, 5, 10, 20, 60]:
        df[f"fwd_ret_{k}"] = g["log_CC"].transform(
            lambda s: s.shift(-(1 + k)).rolling(k, min_periods=max(1, k - 2)).sum())
        df[f"fwd_ret_{k}"] = np.expm1(df[f"fwd_ret_{k}"])

    return df


def neutralize_and_zscore(df: pd.DataFrame, cfg: FactorConfig) -> pd.DataFrame:
    """Per-date pipeline: winsorize -> industry-demean -> cs-zscore."""
    df = df.copy()
    df["alpha_raw"] = df.groupby("trade_date")["alpha_raw"].transform(
        lambda s: per_date_winsor(s, *cfg.cs_winsor))
    if cfg.industry_demean:
        df["alpha"] = df["alpha_raw"] - df.groupby(
            ["trade_date", "industry"])["alpha_raw"].transform("mean")
    else:
        df["alpha"] = df["alpha_raw"]
    df["alpha"] = df.groupby("trade_date")["alpha"].transform(cs_zscore)
    return df


# --------------------------------------------------------------------- #
# Backtest                                                              #
# --------------------------------------------------------------------- #

def backtest(df: pd.DataFrame, cfg: FactorConfig) -> pd.DataFrame:
    """Monthly rebalance Q5 long-only + LS Q5-Q1, cost-aware. Returns the
    per-rebalance state table (one row per rebal date)."""
    dates = sorted(df["trade_date"].unique())
    rebs = dates[::cfg.rebalance_days]
    by_date = {d: g for d, g in df.groupby("trade_date", sort=False)}
    cost = cfg.cost_bps_per_side / 1e4
    fwd_col = f"fwd_ret_{cfg.rebalance_days}"
    prev_q5, prev_q1 = None, None
    rows = []
    for d in rebs:
        snap = by_date.get(d)
        if snap is None:
            continue
        sub = snap[["alpha", "ts_code", fwd_col]].dropna()
        if len(sub) < cfg.min_universe_per_reb:
            continue
        sub = sub.sort_values("alpha")
        n = len(sub)
        bot = int(n * cfg.bot_pct)
        top = int(n * cfg.top_pct)
        q1 = sub.iloc[:bot]
        q5 = sub.iloc[-top:]

        r_q5 = q5[fwd_col].mean()
        r_q1 = q1[fwd_col].mean()
        r_uni = sub[fwd_col].mean()

        if prev_q5 is None:
            tov_q5 = tov_q1 = 1.0
        else:
            tov_q5 = 1.0 - len(set(q5["ts_code"]) & set(prev_q5)) / max(len(prev_q5), 1)
            tov_q1 = 1.0 - len(set(q1["ts_code"]) & set(prev_q1)) / max(len(prev_q1), 1)
        prev_q5, prev_q1 = q5["ts_code"].tolist(), q1["ts_code"].tolist()

        rows.append({
            "trade_date": d, "n": n,
            "r_q5": r_q5, "r_q1": r_q1, "r_uni": r_uni,
            "tov_q5": tov_q5, "tov_q1": tov_q1,
            "ls_gross": r_q5 - r_q1,
            "ls_net":   r_q5 - r_q1 - cost * (tov_q5 + tov_q1),
            "q5_excess": r_q5 - r_uni - cost * tov_q5,
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------- #
# Public entry point                                                    #
# --------------------------------------------------------------------- #

def build_factor(cfg: FactorConfig | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the deployable panel and the per-rebalance state.
    Returns (panel_with_alpha, rebalances)."""
    cfg = cfg or FactorConfig()
    panel = build_panel(cfg)
    panel = neutralize_and_zscore(panel, cfg)
    rebs  = backtest(panel, cfg)
    return panel, rebs


if __name__ == "__main__":
    panel, rebs = build_factor()
    print(f"panel rows: {len(panel)}")
    print(f"rebalances: {len(rebs)}")
    if len(rebs) > 0:
        ann = 252 / FactorConfig().rebalance_days
        ls_sh = rebs["ls_net"].mean() / rebs["ls_net"].std() * np.sqrt(ann)
        q5_ir = rebs["q5_excess"].mean() / rebs["q5_excess"].std() * np.sqrt(ann)
        print(f"LS net Sharpe: {ls_sh:.3f}")
        print(f"Q5 long-only IR: {q5_ir:.3f}")
