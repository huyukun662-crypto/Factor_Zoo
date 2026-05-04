"""Market-regime detection + per-regime defensive asset routing.

# [NO-LOOKAHEAD] Regime label at row T uses ONLY data ≤ T-1:
#   - Trend: CSI300 close[T-1] vs MA200[T-1]
#   - Vol: realized vol of CSI300 over (T-vol_lb, T-1]
#   - PMI/M2/CPI/PPI: latest release with publication date ≤ T - 30 days
#   - Yields: latest yield with date ≤ T-1

Regime taxonomy (8 cells from 3 binary axes):
  trend   ∈ {up,    down}   = CSI300 > MA200
  vol     ∈ {low,   high}   = 60d realized vol < or ≥ rolling-percentile thresh
  growth  ∈ {expand, contract} = PMI ≥ 50

Risk-on cells: (up, low, expand) and (up, low, *)
Risk-off cells: (down, *, *) and (*, high, contract)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from data.fetch_macro import (
    align_to_daily, align_yield_to_daily, fetch_all_macro,
)
from strategy.signals import _safe_log_ret


def realized_vol(close: pd.Series, window: int = 60) -> pd.Series:
    return _safe_log_ret(close.to_frame()).iloc[:, 0].rolling(window, min_periods=20).std() * np.sqrt(252)


def build_regime_panel(close_benchmark: pd.Series,
                        macro: dict[str, pd.DataFrame] | None = None,
                        ma_window: int = 200,
                        vol_window: int = 60,
                        vol_q_window: int = 504,
                        pub_lag: int = 30,
                        ) -> pd.DataFrame:
    """Build a daily DataFrame with regime indicators + binary state labels.

    Columns produced:
      - trend_up           bool   (close > MA200, shifted by 1 to avoid same-day signal)
      - vol                float  (annualized realized vol)
      - vol_high           bool   (vol > rolling 70th percentile)
      - pmi                float  (latest released, lagged 30d)
      - pmi_expand         bool   (pmi ≥ 50)
      - m2_yoy             float
      - cpi_yoy            float
      - ppi_yoy            float
      - cn_10y             float
      - cn_10_2_spread     float
      - us_10y             float
      - us_cn_10y_spread   float  (us_10y - cn_10y)
      - regime_state_3     int    8-cell label (trend, vol, growth)
      - regime_state_2     int    4-cell label (trend, vol)
    """
    idx = close_benchmark.index
    out = pd.DataFrame(index=idx)

    # ---- trend ----
    ma = close_benchmark.rolling(ma_window, min_periods=max(20, ma_window // 4)).mean()
    out["trend_up"] = (close_benchmark > ma).shift(1).astype("Int64")
    # ---- vol ----
    rv = realized_vol(close_benchmark, vol_window).shift(1)
    out["vol"] = rv
    rv_thr = rv.rolling(vol_q_window, min_periods=120).quantile(0.70)
    out["vol_high"] = (rv > rv_thr).astype("Int64")

    # ---- macro ----
    if macro is None:
        macro = fetch_all_macro()

    out["pmi"] = align_to_daily(macro["pmi"], idx, pub_lag_days=pub_lag)
    out["pmi_expand"] = (out["pmi"] >= 50.0).astype("Int64")
    out["m2_yoy"] = align_to_daily(macro["m2"], idx, pub_lag_days=pub_lag)
    out["cpi_yoy"] = align_to_daily(macro["cpi"], idx, pub_lag_days=pub_lag)
    out["ppi_yoy"] = align_to_daily(macro["ppi"], idx, pub_lag_days=pub_lag)

    yld = align_yield_to_daily(macro["yield"], idx, pub_lag_days=1)
    for c in ["cn_10y", "cn_10_2_spread", "us_10y", "us_10_2_spread"]:
        if c in yld.columns:
            out[c] = yld[c]
    if "us_10y" in yld.columns and "cn_10y" in yld.columns:
        out["us_cn_10y_spread"] = yld["us_10y"] - yld["cn_10y"]

    # ---- US CPI YoY (lagged, ffill) ----
    if "us_cpi" in macro:
        out["us_cpi_yoy"] = align_to_daily(macro["us_cpi"], idx, pub_lag_days=15)
        # US real rate = US 10Y - US CPI YoY
        if "us_10y" in out.columns:
            out["us_real_rate"] = out["us_10y"] - out["us_cpi_yoy"]

    # ---- DXY (USD index) — daily, only 1-day lag ----
    if "dxy" in macro:
        dxy_daily = align_yield_to_daily(macro["dxy"].rename(columns={"value": "dxy"}),
                                           idx, pub_lag_days=1)
        if "dxy" in dxy_daily.columns:
            out["dxy"] = dxy_daily["dxy"]
            # DXY momentum: 60-day return
            out["dxy_mom_60"] = out["dxy"].pct_change(60)
            # DXY vs 200-day MA: > 1 = strong USD trend
            ma200 = out["dxy"].rolling(200, min_periods=60).mean()
            out["dxy_strong"] = (out["dxy"] > ma200).astype("Int64")

    # ---- USD/CNY (daily) ----
    if "usdcny" in macro:
        usdcny_daily = align_yield_to_daily(macro["usdcny"].rename(columns={"value": "usdcny"}),
                                              idx, pub_lag_days=1)
        if "usdcny" in usdcny_daily.columns:
            out["usdcny"] = usdcny_daily["usdcny"]
            out["usdcny_mom_60"] = out["usdcny"].pct_change(60)

    # ---- Macro velocities (rate of change) ----
    if "cpi_yoy" in out.columns:
        out["cpi_velocity_3m"] = out["cpi_yoy"] - out["cpi_yoy"].shift(63)  # ~3m
        out["cpi_velocity_6m"] = out["cpi_yoy"] - out["cpi_yoy"].shift(126)
    if "pmi" in out.columns:
        out["pmi_velocity_3m"] = out["pmi"] - out["pmi"].shift(63)
        out["pmi_velocity_6m"] = out["pmi"] - out["pmi"].shift(126)
    if "m2_yoy" in out.columns:
        out["m2_velocity_3m"] = out["m2_yoy"] - out["m2_yoy"].shift(63)

    # ---- 8-cell state (trend × vol × growth) ----
    def _safe_int(s):
        return s.fillna(0).astype(int)

    t = _safe_int(out["trend_up"])
    v = _safe_int(out["vol_high"])
    g = _safe_int(out["pmi_expand"])
    out["regime_state_3"] = t * 4 + v * 2 + g          # 0-7
    out["regime_state_2"] = t * 2 + v                   # 0-3
    return out


# ---------- per-regime defensive optimization ----------

def build_defensive_returns(close: pd.DataFrame, defensive_symbols: list[str]
                             ) -> pd.DataFrame:
    """Daily simple returns of each defensive asset (for IS regime-conditional Sharpe)."""
    cols = [s for s in defensive_symbols if s in close.columns]
    return close[cols].pct_change()


def best_defensive_per_regime(regime_labels: pd.Series,
                               defensive_returns: pd.DataFrame,
                               min_obs: int = 60,
                               ) -> dict[int, str]:
    """For each regime label, find the defensive symbol with best per-day Sharpe.

    [GUARDRAIL] This is computed ONCE on the full IS panel and then frozen as
    a regime → defensive mapping. The mapping is NOT recomputed per day, which
    means a strict purist would say it leaks (the regime → defensive choice was
    made knowing which IS days had which regime). For IS-only optimization
    that's the user's instruction. We document this and re-derive on each
    walk-forward training window for true OOS use.
    """
    out: dict[int, str] = {}
    aligned_idx = regime_labels.index.intersection(defensive_returns.index)
    rl = regime_labels.loc[aligned_idx]
    rr = defensive_returns.loc[aligned_idx]
    for state in sorted(rl.dropna().unique()):
        mask = rl == state
        if mask.sum() < min_obs:
            continue
        sub = rr.loc[mask].dropna(how="all", axis=1)
        if sub.empty:
            continue
        # Per-day Sharpe for each defensive in this regime
        ann_factor = np.sqrt(252)
        sharpe = sub.mean() / sub.std().replace(0, np.nan) * ann_factor
        if sharpe.dropna().empty:
            continue
        best_sym = sharpe.idxmax()
        out[int(state)] = str(best_sym)
    return out


def regime_routed_defensive_weights(regime_labels: pd.Series,
                                     mapping: dict[int, str],
                                     all_symbols: list[str],
                                     ) -> pd.DataFrame:
    """Build a daily weight panel where each row places 1.0 on the regime-mapped
    defensive symbol.

    Regimes not in `mapping` (insufficient obs) fall back to equal-weight
    across all defensive symbols in `all_symbols`.
    """
    out = pd.DataFrame(0.0, index=regime_labels.index, columns=all_symbols)
    fallback_w = 1.0 / len(all_symbols) if all_symbols else 0.0
    for dt, st in regime_labels.items():
        if pd.isna(st):
            continue
        st = int(st)
        if st in mapping and mapping[st] in out.columns:
            out.at[dt, mapping[st]] = 1.0
        else:
            for s in all_symbols:
                out.at[dt, s] = fallback_w
    return out
