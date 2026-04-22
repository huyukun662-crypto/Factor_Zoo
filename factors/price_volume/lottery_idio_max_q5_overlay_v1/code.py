"""
lottery_idio_max_q5_overlay_v1
===============================

Reusable factor builder for the size-regime-gated lottery (idio-MAX) Q5
long-only index-enhancement factor.

Mechanism (Bali-Cakici-Whitelaw 2011 × A-share size-regime overlay):
- α_17: σ-bucket rank of idio-MAX (α_08), from the lottery session. Captures
  the well-documented "lottery premium": high idiosyncratic-MAX stocks
  systematically underperform next period, conditional on controlling for
  volatility via σ-bucket rank.
- Size-regime overlay: compute size_q5q1_12m_sh = trailing-252d Sharpe of
  (top-mv-quintile daily returns − bottom-mv-quintile daily returns). Gate
  α_17 OFF (hold benchmark) when size_q5q1_12m_sh exceeds the 97th
  percentile of its 63d trailing distribution — this identifies sustained
  megacap-rally regimes where A-share lottery premium is extinguished
  (2020 was the canonical failure year without the overlay).
- Deployment form: Q5 long-only (top 20% of industry-demeaned α_17),
  equal-weight, monthly rebalance, 5 bps/side turnover-aware cost. When
  gate = 0, hold equal-weight universe (benchmark) as passive fallback.

Inputs (Tushare via cached parquets in .cache/):
  daily.parquet, adj_factor.parquet, daily_basic.parquet — OHLCV + total_mv
  panel.parquet — industry mapping (CITIC L1)

  ALSO requires α_17 panel (computed in
  logs/20260421_volprice_max_lottery/ session). This code uses the saved
  panel_round3.parquet directly; full rebuild of α_17 is out of scope (see
  that session's scripts 01, 06b, 08).

Output:
  pandas DataFrame of per-rebalance holdings:
    trade_date, ts_code, weight, gate, abs_ret, exc_ret, tov, cost
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


CACHE = Path("/home/user/Factor_Zoo/.cache")
LOT_PANEL = Path(
    "/home/user/Factor_Zoo/logs/20260421_volprice_max_lottery/outputs/panel_round3.parquet"
)


@dataclass
class FactorConfig:
    # Alpha side
    top_pct: float = 0.20                       # Q5 = top 20 %
    industry_demean: bool = True                # subtract industry mean of α_17 per date

    # Size-regime overlay
    size_lookback: int = 252                    # rolling-Sharpe window of Q5−Q1 size spread
    gate_lookback: int = 63                     # rolling percentile window
    gate_percentile: int = 97                   # gate ON when size_q5q1_12m_sh < 97th pct
    gate_min_periods: int = 44                  # 63 × 0.7

    # Backtest mechanics
    rebalance_days: int = 20
    delay: int = 1                              # T+1 execution (inherited from α_17 panel)
    cost_bps_per_side: int = 5
    fallback: str = "benchmark"                 # gate=0 → hold equal-weight universe


# --------------------------------------------------------------------- #
# Building blocks                                                       #
# --------------------------------------------------------------------- #

def industry_demean(df: pd.DataFrame, col: str) -> pd.Series:
    return df[col] - df.groupby(["trade_date", "industry"])[col].transform("mean")


def build_size_regime_signal(cfg: FactorConfig) -> pd.Series:
    """size_q5q1_12m_sh = trailing-252d Sharpe of top-mv-quintile daily returns
    minus bottom-mv-quintile daily returns. Returns daily series indexed by
    trade_date."""
    daily = pd.read_parquet(CACHE / "daily.parquet").merge(
        pd.read_parquet(CACHE / "adj_factor.parquet"),
        on=["ts_code", "trade_date"], how="left",
    ).merge(
        pd.read_parquet(CACHE / "daily_basic.parquet")[["ts_code", "trade_date", "total_mv"]],
        on=["ts_code", "trade_date"], how="left",
    )
    daily["adj_factor"] = daily["adj_factor"].fillna(1.0)
    daily["P"] = daily["close"] * daily["adj_factor"]
    daily = daily.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)
    daily["trade_date"] = pd.to_datetime(daily["trade_date"])
    daily["log_ret"] = daily.groupby("ts_code")["P"].transform(lambda s: np.log(s).diff())
    daily = daily.dropna(subset=["total_mv"])

    # Per-date size quintile via cross-section rank of total_mv
    daily["size_rank"] = daily.groupby("trade_date")["total_mv"].rank(method="first", pct=True)
    daily["size_q"] = daily.groupby("trade_date")["size_rank"].transform(
        lambda s: pd.qcut(s.rank(method="first"), 5, labels=False, duplicates="drop")
    )
    q5 = daily[daily["size_q"] == 4].groupby("trade_date")["log_ret"].mean()
    q1 = daily[daily["size_q"] == 0].groupby("trade_date")["log_ret"].mean()
    spread = (q5 - q1).rename("size_q5q1_ret")
    ann = spread.rolling(cfg.size_lookback, min_periods=int(cfg.size_lookback * 0.5)).mean() * 252
    vol = spread.rolling(cfg.size_lookback, min_periods=int(cfg.size_lookback * 0.5)).std(ddof=0) * np.sqrt(252)
    return (ann / vol).rename("size_q5q1_12m_sh")


def build_gate(signal: pd.Series, cfg: FactorConfig) -> pd.Series:
    """Trailing rolling-percentile gate. gate=1 iff signal(t) < p-th percentile
    of signal over trailing gate_lookback days."""
    threshold = signal.rolling(
        cfg.gate_lookback, min_periods=cfg.gate_min_periods
    ).quantile(cfg.gate_percentile / 100.0)
    gate = (signal < threshold).astype(int).where(~threshold.isna(), 0)
    gate.name = "gate"
    return gate


# --------------------------------------------------------------------- #
# Portfolio builder (Q5 long-only with gate fallback)                   #
# --------------------------------------------------------------------- #

def build_portfolio(cfg: FactorConfig | None = None) -> pd.DataFrame:
    """Main entry — returns per-rebalance return + holding breakdown.

    Output columns per (trade_date):
        gate                0/1 overlay state at rebalance
        abs_ret             portfolio raw return (gross of cost)
        exc_ret             excess vs universe equal-weight
        uni                 universe equal-weight return
        tov                 turnover for this rebalance (0..1)
        cost                cost charged for this rebalance (decimal)
        abs_net             abs_ret − cost
        exc_net             exc_ret − cost
    """
    cfg = cfg or FactorConfig()
    t0 = time.time()
    print("[factor] loading α_17 lottery panel...")
    lot = pd.read_parquet(LOT_PANEL,
                          columns=["ts_code", "trade_date", "industry",
                                   "alpha_17", "fwd_ret_20"])
    lot["trade_date"] = pd.to_datetime(lot["trade_date"])
    lot = lot.dropna(subset=["industry"])
    if cfg.industry_demean:
        lot["alpha_17_signal"] = industry_demean(lot, "alpha_17")
    else:
        lot["alpha_17_signal"] = lot["alpha_17"]
    print(f"  loaded {len(lot):,} rows  {time.time()-t0:.1f}s")

    print("[factor] computing size-regime overlay...")
    sig = build_size_regime_signal(cfg).dropna()
    gate = build_gate(sig, cfg)
    print(f"  gate on-fraction (daily) = {gate.mean():.3f}  {time.time()-t0:.1f}s")

    # Rebalance grid
    dates = pd.Index(sorted(lot["trade_date"].unique()))
    rebal_dates = dates[::cfg.rebalance_days]
    gate_d = gate.to_dict()

    rows = []
    prev_set = set(); prev_state = 0
    panel_l = lot[["trade_date", "ts_code", "alpha_17_signal", "fwd_ret_20"]].dropna()
    for t in rebal_dates:
        g = int(gate_d.get(t, 0))
        snap = panel_l[panel_l["trade_date"] == t]
        if len(snap) < 100:
            continue
        uni_mean = snap["fwd_ret_20"].mean()
        if g == 0:
            # fallback = benchmark: hold equal-weight universe
            if cfg.fallback == "benchmark":
                abs_r = uni_mean; exc_r = 0.0
            elif cfg.fallback == "cash":
                abs_r = 0.0; exc_r = -uni_mean
            else:
                raise ValueError(f"unknown fallback {cfg.fallback!r}")
            tov = 1.0 if prev_state == 1 and prev_set else 0.0
            rows.append(dict(trade_date=t, gate=0, abs_ret=abs_r, exc_ret=exc_r,
                             uni=uni_mean, tov=tov,
                             cost=tov * cfg.cost_bps_per_side / 1e4))
            prev_state = 0; prev_set = set()
            continue
        snap_sorted = snap.sort_values("alpha_17_signal", ascending=False)
        k = max(int(len(snap_sorted) * cfg.top_pct), 20)
        top = snap_sorted.head(k)
        cur_set = set(top["ts_code"])
        mean_ret = top["fwd_ret_20"].mean()
        if prev_state == 1 and prev_set:
            tov = 1.0 - len(cur_set & prev_set) / max(len(cur_set), 1)
        else:
            tov = 1.0  # open from flat/fallback
        rows.append(dict(trade_date=t, gate=1, abs_ret=mean_ret,
                         exc_ret=mean_ret - uni_mean, uni=uni_mean,
                         tov=tov, cost=tov * cfg.cost_bps_per_side / 1e4))
        prev_state = 1; prev_set = cur_set

    df = pd.DataFrame(rows).set_index("trade_date").sort_index()
    df["abs_net"] = df["abs_ret"] - df["cost"]
    df["exc_net"] = df["exc_ret"] - df["cost"]
    print(f"[factor] {len(df)} rebalances, on-frac = {df['gate'].mean():.3f}  "
          f"done {time.time()-t0:.1f}s")
    return df


if __name__ == "__main__":
    tape = build_portfolio()
    print("\ntape head:")
    print(tape.head())
    print(f"\nfull-sample stats:")
    r = tape["exc_net"]
    ann = r.mean() * 12; vol = r.std(ddof=0) * np.sqrt(12)
    eq = (1 + r).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    print(f"  excess IR: {ann/vol:.3f}  ann: {ann*100:+.2f}%  MaxDD: {dd*100:+.2f}%")
