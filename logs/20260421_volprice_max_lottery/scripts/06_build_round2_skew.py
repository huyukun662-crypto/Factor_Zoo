"""
Round 2 — Idiosyncratic Skewness family.

Build 8 new alphas α_09..α_16 and store in panel_round2.parquet (replacing prior).
"""
import os, time, numpy as np, pandas as pd
from scipy.stats import skew as sp_skew

SESSION = "/home/user/Factor_Zoo/logs/20260421_volprice_max_lottery"
CACHE = "/home/user/Factor_Zoo/.cache"

t0 = time.time()
print("=== load base data ===")
daily = pd.read_parquet(f"{CACHE}/daily.parquet")
adj = pd.read_parquet(f"{CACHE}/adj_factor.parquet")
dbasic = pd.read_parquet(f"{CACHE}/daily_basic.parquet")
panel_old = pd.read_parquet(f"{CACHE}/panel.parquet", columns=["ts_code", "industry"]).drop_duplicates("ts_code")

df = daily.merge(adj, on=["ts_code", "trade_date"], how="left").merge(dbasic, on=["ts_code", "trade_date"], how="left")
df = df.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)
df["close_adj"] = df["close"] * df["adj_factor"]
df["log_ret"] = np.log(df["close_adj"] / df.groupby("ts_code")["close_adj"].shift(1))
df["log_ret"] = df["log_ret"].clip(-0.105, 0.105)
df["ret"] = np.expm1(df["log_ret"])
df["turnover"] = df["amount"] / (df["circ_mv"] * 10.0)
df["turnover"] = df["turnover"].replace([np.inf, -np.inf], np.nan)

# market return (universe mean log_ret)
mkt = df.groupby("trade_date")["log_ret"].mean().rename("mkt_log_ret").reset_index()
df = df.merge(mkt, on="trade_date", how="left")
df["idio"] = df["log_ret"] - df["mkt_log_ret"]

g = df.groupby("ts_code")
print("=== controls (sigma_20, turnover_20, ret_5/20, sigma_60) ===")
df["sigma_20"] = g["log_ret"].transform(lambda s: s.rolling(20, min_periods=15).std())
df["sigma_60"] = g["log_ret"].transform(lambda s: s.rolling(60, min_periods=45).std())
df["turnover_20"] = g["turnover"].transform(lambda s: s.rolling(20, min_periods=15).mean())
df["ret_5"] = g["log_ret"].transform(lambda s: s.rolling(5, min_periods=4).sum())
df["ret_20"] = g["log_ret"].transform(lambda s: s.rolling(20, min_periods=15).sum())

print("=== fwd_ret (delay=1) ===")
for k in [1, 5, 20, 60]:
    df[f"fwd_ret_{k}"] = np.expm1(
        g["log_ret"].transform(lambda s: s.shift(-2).rolling(k, min_periods=k).sum().shift(-(k-1)))
    )


def _topk(x, k):
    x = x[~np.isnan(x)]
    if len(x) == 0: return np.nan
    return np.sort(x)[-min(k, len(x)):].mean()


def _botk(x, k):
    x = x[~np.isnan(x)]
    if len(x) == 0: return np.nan
    return np.sort(x)[:min(k, len(x))].mean()


def _skew(x):
    x = x[~np.isnan(x)]
    if len(x) < 5 or np.std(x) < 1e-9: return np.nan
    return sp_skew(x)


def _median(x):
    x = x[~np.isnan(x)]
    return np.median(x) if len(x) else np.nan


def _count_hi(x_tuple, two_sigma):
    # x_tuple is (ret over w20, sigma_60_at_t which is a scalar)
    pass  # implemented inline below


print("=== α_09 idio_skew_20 ===")
df["raw_09"] = -g["idio"].transform(lambda s: s.rolling(20, min_periods=15).apply(_skew, raw=True))

print("=== α_10 idio_skew_60 ===")
df["raw_10"] = -g["idio"].transform(lambda s: s.rolling(60, min_periods=45).apply(_skew, raw=True))

print("=== α_11 coskew ===")
# Build df["r_ret_mkt2"] = idio_t * (mkt - mean_60)^2 rolling
df["mkt_dev"] = df["mkt_log_ret"] - df.groupby("ts_code")["mkt_log_ret"].transform(
    lambda s: s.rolling(60, min_periods=45).mean())
df["coskew_raw"] = df["idio"] * (df["mkt_dev"] ** 2)
df["coskew_60"] = df.groupby("ts_code")["coskew_raw"].transform(
    lambda s: s.rolling(60, min_periods=45).mean())
df["raw_11"] = -(df["coskew_60"] / (df["sigma_20"] ** 2).replace(0, np.nan))

print("=== α_12 tail_asymmetry ===")
df["_top5"] = g["log_ret"].transform(lambda s: s.rolling(20, min_periods=15).apply(lambda x: _topk(x, 5), raw=True))
df["_bot5"] = g["log_ret"].transform(lambda s: s.rolling(20, min_periods=15).apply(lambda x: _botk(x, 5), raw=True))
df["raw_12"] = -(df["_top5"] - np.abs(df["_bot5"])) / df["sigma_20"].replace(0, np.nan)

print("=== α_13 expected_skew (BMV 2010 proxy) ===")
df["raw_13"] = -(df["raw_09"].fillna(0) + 0.5 * df["_top5"] / df["sigma_20"].replace(0, np.nan))

print("=== α_14 pearson_skew ===")
df["_median_20"] = g["log_ret"].transform(
    lambda s: s.rolling(20, min_periods=15).apply(_median, raw=True))
df["_mean_20"] = g["log_ret"].transform(
    lambda s: s.rolling(20, min_periods=15).mean())
df["raw_14"] = -(3 * (df["_mean_20"] - df["_median_20"])) / df["sigma_20"].replace(0, np.nan)

print("=== α_15 jump_up_freq ===")
# count(ret > 2*sigma_60) over w(20) — use sigma_60 lagged one day to avoid look-ahead
df["_sig60_lag1"] = g["sigma_60"].shift(1)
df["_jump_up"] = ((df["log_ret"] > 2 * df["_sig60_lag1"]) & df["log_ret"].notna()).astype(float)
df["raw_15"] = -g["_jump_up"].transform(lambda s: s.rolling(20, min_periods=15).sum())

print("=== α_16 skew_attention ===")
# We'll build after cs_z of turnover (per date); compute later
print("=== attach industry ===")
df = df.merge(panel_old, on="ts_code", how="left")
df["industry"] = df["industry"].fillna("Unknown")

print("=== xsection processing ===")


def xsection(g_df, col):
    x = g_df[col].values.astype(float)
    if np.isfinite(x).sum() < 30:
        return np.full_like(x, np.nan, dtype=float)
    lo, hi = np.nanpercentile(x, [1, 99])
    xw = np.clip(x, lo, hi)
    ind = g_df["industry"].values
    ser = pd.Series(xw, index=ind)
    demean = xw - ser.groupby(ind).transform("mean").values
    mu, sd = np.nanmean(demean), np.nanstd(demean)
    return (demean - mu) / sd if sd > 1e-12 else np.zeros_like(demean)


# α_16 needs cs_z of turnover_20 first per date
print("   building raw_16 (skew × cs_z(turnover_20))")
df["raw_16"] = np.nan
RAWS = [f"raw_{i:02d}" for i in [9,10,11,12,13,14,15,16]]
OUTS = [f"alpha_{i:02d}" for i in [9,10,11,12,13,14,15,16]]
for c in OUTS:
    df[c] = np.nan


dates = df["trade_date"].unique()
for i, d in enumerate(dates):
    idx = df.index[df["trade_date"] == d]
    sub = df.loc[idx]
    tz = sub["turnover_20"].values.astype(float)
    if np.isfinite(tz).sum() >= 30:
        lo, hi = np.nanpercentile(tz, [1, 99])
        tzw = np.clip(tz, lo, hi)
        mu, sd = np.nanmean(tzw), np.nanstd(tzw)
        z = (tzw - mu) / sd if sd > 1e-12 else np.zeros_like(tzw)
    else:
        z = np.zeros_like(tz)
    df.loc[idx, "raw_16"] = -sub["raw_09"].values * z
    # Re-read sub for raw_16 just assigned
    sub2 = df.loc[idx]
    for col, out in zip(RAWS, OUTS):
        df.loc[idx, out] = xsection(sub2, col)
    if (i+1) % 200 == 0:
        print(f"   {i+1}/{len(dates)} elapsed={time.time()-t0:.0f}s")

keep = ["ts_code", "trade_date", "industry"] + OUTS + [
    "fwd_ret_1","fwd_ret_5","fwd_ret_20","fwd_ret_60",
    "total_mv","circ_mv","turnover_20","sigma_20","sigma_60","ret_5","ret_20"
]
out = df[keep].copy()
OUT_PATH = f"{SESSION}/outputs/panel_round2_skew.parquet"
out.to_parquet(OUT_PATH, index=False)
print(f"wrote {OUT_PATH}  rows={len(out)}  elapsed={time.time()-t0:.0f}s")
