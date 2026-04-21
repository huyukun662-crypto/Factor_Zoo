"""
Volume-Price Panel Builder — MAX Effect / Lottery Demand

Input (from cache):
  - .cache/daily.parquet         (open, close, vol, amount)
  - .cache/adj_factor.parquet    (adj_factor)
  - .cache/daily_basic.parquet   (total_mv, circ_mv)
  - .cache/panel.parquet         (industry, size_bin — reused from accruals session)

Output:
  - logs/20260421_volprice_max_lottery/outputs/panel_volprice.parquet

Pipeline (strict order):
  1. Build adjusted close and daily log return with ±10.5% winsor
  2. Compute controls: sigma_20, turnover_20, ret_5, ret_20, amihud_20
  3. Compute 8 raw alphas per (ts_code, trade_date) via rolling windows
  4. Join industry from panel.parquet (ts_code → industry mapping)
  5. Winsorize raw alphas at 1%/99% per trade_date
  6. Industry-demean per trade_date
  7. Cross-sectional z-score per trade_date (unit variance)
  8. Forward returns: fwd_ret_k = exp(sum log_return over [t+1+delay, t+k+delay]) - 1, delay=1
     Invariant: target_shift = -(1+delay) = -2
"""

import os, sys, time
import numpy as np
import pandas as pd

SESSION = "/home/user/Factor_Zoo/logs/20260421_volprice_max_lottery"
CACHE = "/home/user/Factor_Zoo/.cache"
OUT = f"{SESSION}/outputs/panel_volprice.parquet"

t0 = time.time()
print("=== loading cached data ===")
daily = pd.read_parquet(f"{CACHE}/daily.parquet")
adj = pd.read_parquet(f"{CACHE}/adj_factor.parquet")
dbasic = pd.read_parquet(f"{CACHE}/daily_basic.parquet")
panel_old = pd.read_parquet(f"{CACHE}/panel.parquet", columns=["ts_code", "industry"]).drop_duplicates("ts_code")
print(f"daily {daily.shape}, adj {adj.shape}, dbasic {dbasic.shape}, panel {panel_old.shape}")

print("=== merge daily + adj + dbasic ===")
df = daily.merge(adj, on=["ts_code", "trade_date"], how="left")
df = df.merge(dbasic, on=["ts_code", "trade_date"], how="left")
df = df.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)

# adjusted close
df["close_adj"] = df["close"] * df["adj_factor"]
df["ret"] = df.groupby("ts_code")["close_adj"].pct_change()
df["log_ret"] = np.log1p(df["ret"])
# winsorize at A-share daily limit
df["log_ret"] = df["log_ret"].clip(lower=-0.105, upper=0.105)
df["ret"] = np.expm1(df["log_ret"])

# turnover = amount / circ_mv  (circ_mv in units of 10k RMB, amount in units of 1k RMB)
# amount / (circ_mv * 10) gives turnover as decimal
df["turnover"] = df["amount"] / (df["circ_mv"] * 10.0)
df["turnover"] = df["turnover"].replace([np.inf, -np.inf], np.nan)

print("=== rolling controls (sigma_20, turnover_20, ret_5/20, amihud_20) ===")
g = df.groupby("ts_code")
df["sigma_20"] = g["log_ret"].transform(lambda s: s.rolling(20, min_periods=15).std())
df["turnover_20"] = g["turnover"].transform(lambda s: s.rolling(20, min_periods=15).mean())
df["ret_5"] = g["log_ret"].transform(lambda s: s.rolling(5, min_periods=4).sum())
df["ret_20"] = g["log_ret"].transform(lambda s: s.rolling(20, min_periods=15).sum())

# Amihud illiquidity: |ret| / (amount in 1k RMB)  -> daily, then mean
df["illiq_daily"] = df["log_ret"].abs() / df["amount"].replace(0, np.nan)
df["amihud_20"] = g["illiq_daily"].transform(lambda s: s.rolling(20, min_periods=15).mean())

print("=== alpha 1-2-3-4-5-6-7 (single-stock rolling) ===")


def _topk_mean(x, k):
    x = np.asarray(x, dtype=float)
    if np.isnan(x).all():
        return np.nan
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return np.nan
    kk = min(k, len(x))
    return np.sort(x)[-kk:].mean()


def _botk_mean(x, k):
    x = np.asarray(x, dtype=float)
    if np.isnan(x).all():
        return np.nan
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return np.nan
    kk = min(k, len(x))
    return np.sort(x)[:kk].mean()


# alpha_01: -max(r_t) over 20d
df["raw_01"] = -g["log_ret"].transform(lambda s: s.rolling(20, min_periods=15).max())
# alpha_02: -mean(top5) over 20d
df["raw_02"] = -g["log_ret"].transform(
    lambda s: s.rolling(20, min_periods=15).apply(lambda x: _topk_mean(x, 5), raw=True)
)
# alpha_03: -mean(top10) over 60d
df["raw_03"] = -g["log_ret"].transform(
    lambda s: s.rolling(60, min_periods=45).apply(lambda x: _topk_mean(x, 10), raw=True)
)
# alpha_04: -(mean(top5)/sigma_20)
df["_m5_20"] = g["log_ret"].transform(
    lambda s: s.rolling(20, min_periods=15).apply(lambda x: _topk_mean(x, 5), raw=True)
)
df["raw_04"] = -(df["_m5_20"] / df["sigma_20"].replace(0, np.nan))
# alpha_05: -mean(top5) * cs_z(turnover_20)  (turnover z-score done per date after we compute)
# we store -m5_20 * turnover_20 here; cs_z applied later inside attention-weight step
# Actually cleaner: compute cs_z(turnover_20) first then multiply. Defer.
# We'll build raw_05 after cs_z of turnover.
# alpha_06: -(m_pos_top5 - m_neg_bot5) over 20d
df["_mbot5_20"] = g["log_ret"].transform(
    lambda s: s.rolling(20, min_periods=15).apply(lambda x: _botk_mean(x, 5), raw=True)
)
df["raw_06"] = -(df["_m5_20"] - df["_mbot5_20"])
# alpha_07: -(max - mean)/sigma  over 20d
df["_max_20"] = g["log_ret"].transform(lambda s: s.rolling(20, min_periods=15).max())
df["_mean_20"] = g["log_ret"].transform(lambda s: s.rolling(20, min_periods=15).mean())
df["raw_07"] = -((df["_max_20"] - df["_mean_20"]) / df["sigma_20"].replace(0, np.nan))

print("=== alpha 08 (abnormal-max vs market) ===")
# Equal-weight market return per day from the sample itself (ex-ST approx: just mean of log_ret)
mkt = df.groupby("trade_date")["log_ret"].mean().rename("mkt_log_ret").reset_index()
df = df.merge(mkt, on="trade_date", how="left")
df["ab_ret"] = df["log_ret"] - df["mkt_log_ret"]
g2 = df.groupby("ts_code")
df["raw_08"] = -g2["ab_ret"].transform(
    lambda s: s.rolling(20, min_periods=15).apply(lambda x: _topk_mean(x, 5), raw=True)
)

print("=== forward returns (delay=1, target_shift=-2) ===")
# fwd_ret_k computed as sum of log_ret from t+2 to t+1+k, then expm1
# But we'll reuse formula: shift group log_ret by -(1+delay) = -2 to align start,
# then rolling sum over k, shift forward alignment ensures we're using future.
# Simplest: r_fwd_k(t) = sum(log_ret[t+2 .. t+1+k]) = (cumsum[t+1+k] - cumsum[t+1])
g3 = df.groupby("ts_code")
for k in [1, 5, 20, 60]:
    df[f"fwd_ret_{k}"] = np.expm1(
        g3["log_ret"].transform(lambda s: s.shift(-(1 + 1)).rolling(k, min_periods=k).sum().shift(-(k - 1)))
    )
# The transform above: shift(-2) aligns next period's start at t; rolling(k) sums k days ending at t+1+k;
# final shift(-(k-1)) moves the sum value back to t so label is at signal time t.
# Verify sign: for k=1 this equals log_ret at t+2, i.e. one-day return two days ahead — delay=1.

print("=== attach industry ===")
df = df.merge(panel_old, on="ts_code", how="left")
df["industry"] = df["industry"].fillna("Unknown")

print("=== xsection winsor + industry demean + z-score ===")
ALPHAS = ["raw_01", "raw_02", "raw_03", "raw_04", "raw_06", "raw_07", "raw_08"]


def xsection_process(g_df, col):
    x = g_df[col].values.astype(float)
    if np.isfinite(x).sum() < 30:
        return np.full_like(x, np.nan, dtype=float)
    lo, hi = np.nanpercentile(x, [1, 99])
    xw = np.clip(x, lo, hi)
    # industry demean
    ind = g_df["industry"].values
    ser = pd.Series(xw, index=ind)
    demean = xw - ser.groupby(ind).transform("mean").values
    # z-score cross-section
    mu, sd = np.nanmean(demean), np.nanstd(demean)
    return (demean - mu) / sd if sd > 1e-12 else np.zeros_like(demean)


# Build alpha_05 raw now: need cs_z(turnover_20) per date, then multiply by -_m5_20
print("   building raw_05 (attention-weighted)")


def make_raw_05(g_df):
    tz = g_df["turnover_20"].values.astype(float)
    lo, hi = np.nanpercentile(tz, [1, 99])
    tzw = np.clip(tz, lo, hi)
    mu, sd = np.nanmean(tzw), np.nanstd(tzw)
    z = (tzw - mu) / sd if sd > 1e-12 else np.zeros_like(tzw)
    return -g_df["_m5_20"].values * z


df["raw_05"] = np.nan
for d, sub in df.groupby("trade_date"):
    df.loc[sub.index, "raw_05"] = make_raw_05(sub)

ALPHAS_FULL = ["raw_01", "raw_02", "raw_03", "raw_04", "raw_05", "raw_06", "raw_07", "raw_08"]
ALPHA_OUT = [f"alpha_{i:02d}" for i in range(1, 9)]

print("=== per-date xsection processing ===")
for col, out in zip(ALPHAS_FULL, ALPHA_OUT):
    df[out] = np.nan

# Vectorized-ish per-date loop
dates = df["trade_date"].unique()
for i, d in enumerate(dates):
    idx = df.index[df["trade_date"] == d]
    sub = df.loc[idx]
    for col, out in zip(ALPHAS_FULL, ALPHA_OUT):
        df.loc[idx, out] = xsection_process(sub, col)
    if (i + 1) % 200 == 0:
        print(f"   processed {i+1}/{len(dates)} dates  elapsed={time.time()-t0:.0f}s")

print("=== finalize + dump ===")
keep = [
    "ts_code", "trade_date", "industry",
    "alpha_01", "alpha_02", "alpha_03", "alpha_04",
    "alpha_05", "alpha_06", "alpha_07", "alpha_08",
    "fwd_ret_1", "fwd_ret_5", "fwd_ret_20", "fwd_ret_60",
    "total_mv", "circ_mv", "turnover_20", "sigma_20",
    "ret_5", "ret_20", "amihud_20",
]
out = df[keep].copy()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
out.to_parquet(OUT, index=False)
print(f"wrote {OUT}  rows={len(out)}  elapsed={time.time()-t0:.0f}s")
