"""
Build trend panel for batch 0001.

Inputs:
  .cache/daily.parquet      (ts_code, trade_date, open, close, vol, amount)
  .cache/adj_factor.parquet (ts_code, trade_date, adj_factor)
  .cache/daily_basic.parquet(ts_code, trade_date, total_mv, circ_mv)
  .cache/panel.parquet      provides industry mapping per ts_code

Output:
  logs/20260422_trend_technical_alpha/outputs/panel_trend.parquet
  Columns: ts_code, trade_date, industry, total_mv,
           alpha_01..alpha_08,
           fwd_ret_1, fwd_ret_5, fwd_ret_20, fwd_ret_60

Performance budget: ≤ 5 minutes on 5614 stocks × ~1740 trade dates.
"""
from __future__ import annotations
import time
import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

CACHE = "/home/user/Factor_Zoo/.cache"
OUT = "/home/user/Factor_Zoo/logs/20260422_trend_technical_alpha/outputs/panel_trend.parquet"

DELAY = 1


def load_base() -> pd.DataFrame:
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
    df = df.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)
    return df


def fwd_ret(group_ret: pd.Series, K: int, delay: int = DELAY) -> pd.Series:
    return group_ret.shift(-(1 + delay)).rolling(K).sum().shift(-(K - 1))


def trend_tstat_per_stock(log_p: np.ndarray, w: int) -> np.ndarray:
    """Vectorized OLS slope-t over rolling window w on a 1-D log-price series."""
    n = len(log_p)
    out = np.full(n, np.nan, dtype=np.float64)
    if n < w + 1:
        return out
    view = sliding_window_view(log_p, w)  # shape (n-w+1, w)
    valid = ~np.isnan(view).any(axis=1)
    x = np.arange(w, dtype=np.float64)
    x_bar = (w - 1) / 2.0
    sum_xx_centered = w * (w * w - 1) / 12.0
    sum_y = view.sum(axis=1)
    y_bar = sum_y / w
    sum_xy = view @ x
    sum_xy_centered = sum_xy - w * x_bar * y_bar
    beta = sum_xy_centered / sum_xx_centered
    sum_yy = (view * view).sum(axis=1)
    SS_tot = sum_yy - w * y_bar * y_bar
    SS_res = SS_tot - beta * sum_xy_centered
    SS_res = np.clip(SS_res, 0.0, None)
    sigma2 = SS_res / (w - 2)
    SE_beta = np.sqrt(sigma2 / sum_xx_centered)
    with np.errstate(divide="ignore", invalid="ignore"):
        t_stat = beta / SE_beta
    t_stat = np.where(valid, t_stat, np.nan)
    out[w - 1 :] = t_stat
    return out


def build_alphas(df: pd.DataFrame) -> pd.DataFrame:
    df["log_p"] = np.log(df["P"])
    df["ret"] = df.groupby("ts_code")["log_p"].diff()

    g = df.groupby("ts_code", group_keys=False)
    print("[panel] computing rolling MAs...")

    # MA_k on adjusted price
    horizons = [3, 5, 10, 20, 50, 60, 100, 120, 200, 252]
    for k in horizons:
        df[f"MA_{k}"] = g["P"].transform(lambda s, k=k: s.rolling(k, min_periods=int(k * 0.8)).mean())

    # ---- alpha_01: Han-Zhou-Zhu trend signal ----
    print("[panel] alpha_01...")
    K1 = [3, 5, 10, 20, 50, 100, 200]
    ratios = pd.concat(
        [(df["P"] / df[f"MA_{k}"] - 1.0).rename(f"r{k}") for k in K1], axis=1
    )
    df["trend_raw"] = ratios.mean(axis=1)
    df["alpha_01"] = df.groupby("trade_date")["trend_raw"].transform(
        lambda s: (s - s.mean()) / s.std(ddof=0)
    )

    # ---- alpha_02 / alpha_03: trend t-stat ----
    print("[panel] alpha_02 (60d t-stat)...")
    df["alpha_02"] = np.nan
    df["alpha_03"] = np.nan

    out_arr_60 = np.full(len(df), np.nan, dtype=np.float64)
    out_arr_120 = np.full(len(df), np.nan, dtype=np.float64)
    log_p = df["log_p"].values
    grp_codes = df["ts_code"].values

    starts = df.groupby("ts_code", sort=False).indices
    n_groups = len(starts)
    t0 = time.time()
    for i, (code, idx) in enumerate(starts.items()):
        if (i + 1) % 1000 == 0:
            print(f"  tstat group {i+1}/{n_groups}  elapsed={time.time()-t0:.1f}s")
        seg = log_p[idx]
        out_arr_60[idx] = trend_tstat_per_stock(seg, 60)
        out_arr_120[idx] = trend_tstat_per_stock(seg, 120)
    df["alpha_02"] = out_arr_60
    df["alpha_03"] = out_arr_120

    # ---- alpha_04: MA-crossover stack ----
    print("[panel] alpha_04...")
    df["alpha_04"] = (
        np.sign(df["MA_20"] - df["MA_60"])
        + np.sign(df["MA_60"] - df["MA_120"])
        + np.sign(df["MA_120"] - df["MA_252"])
    )

    # ---- alpha_05: 252-day rolling close-max proximity ----
    print("[panel] alpha_05...")
    df["max_252"] = g["P"].transform(lambda s: s.rolling(252, min_periods=200).max())
    df["alpha_05"] = df["P"] / df["max_252"]

    # ---- alpha_06: frog-in-the-pan 60d ----
    print("[panel] alpha_06...")
    pos = (df["ret"] > 0).astype(np.float64)
    df["pos_frac_60"] = g.apply(lambda d: pos.loc[d.index].rolling(60, min_periods=40).mean()).reset_index(level=0, drop=True)
    # Above is slow; rewrite using groupby + transform:
    # but groupby + transform on a derived column with NaN for first ret is fine:
    # use the simpler form
    df.drop(columns=["pos_frac_60"], inplace=True)
    df["pos_frac_60"] = (df["ret"] > 0).astype(np.float64).groupby(df["ts_code"]).transform(
        lambda s: s.rolling(60, min_periods=40).mean()
    )
    df["sum_60"] = df.groupby("ts_code")["ret"].transform(lambda s: s.rolling(60, min_periods=40).sum())
    df["alpha_06"] = df["pos_frac_60"] * np.sign(df["sum_60"])

    # ---- alpha_07: 120d trend Sharpe ----
    print("[panel] alpha_07...")
    mean_120 = df.groupby("ts_code")["ret"].transform(lambda s: s.rolling(120, min_periods=80).mean())
    std_120 = df.groupby("ts_code")["ret"].transform(lambda s: s.rolling(120, min_periods=80).std(ddof=0))
    df["alpha_07"] = mean_120 / std_120.replace(0, np.nan)

    # ---- alpha_08: classic 12-1 momentum ----
    print("[panel] alpha_08...")
    cum_252 = df.groupby("ts_code")["ret"].transform(lambda s: s.rolling(252, min_periods=200).sum())
    cum_21 = df.groupby("ts_code")["ret"].transform(lambda s: s.rolling(21, min_periods=15).sum())
    df["alpha_08"] = cum_252 - cum_21

    # ---- forward returns ----
    print("[panel] forward returns...")
    for K in [1, 5, 20, 60]:
        df[f"fwd_ret_{K}"] = df.groupby("ts_code")["ret"].transform(lambda s, K=K: fwd_ret(s, K))

    keep = (
        ["ts_code", "trade_date", "industry", "total_mv"]
        + [f"alpha_0{k}" for k in range(1, 9)]
        + [f"fwd_ret_{K}" for K in [1, 5, 20, 60]]
    )
    out = df[keep].copy()
    return out


def main():
    t0 = time.time()
    print("[panel] loading base...")
    df = load_base()
    print(f"[panel] base shape: {df.shape}, elapsed={time.time()-t0:.1f}s")
    out = build_alphas(df)
    print(f"[panel] panel shape: {out.shape}, elapsed={time.time()-t0:.1f}s")
    print("[panel] alpha NaN frac:")
    for c in [f"alpha_0{k}" for k in range(1, 9)]:
        print(f"  {c}: {out[c].isna().mean():.3f}")
    out.to_parquet(OUT, index=False)
    print(f"[panel] wrote {OUT}, elapsed={time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
