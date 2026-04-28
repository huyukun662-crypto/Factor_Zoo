"""
Panel builder — Overnight-Intraday session.

Inputs (from .cache/):
  daily.parquet        : open, close, pre_close, vol, amount
  adj_factor.parquet   : adj_factor
  daily_basic.parquet  : total_mv, circ_mv, turnover_rate_f
  stock_basic.parquet  : industry, name, market, list_date

Output:
  logs/20260428_a_share_overnight_intraday_alpha/outputs/panel_overnight.parquet

Pipeline:
  1. Merge daily + adj_factor + daily_basic
  2. Filter universe: exclude ST/*ST in name; exclude vol == 0 bars
  3. Compute primitives:
       log_ON = log( open_t * adj_t / (close_{t-1} * adj_{t-1}) ).clip(-0.105, 0.105)
       log_ID = log( close_t / open_t                          ).clip(-0.105, 0.105)
       log_CC = log( close_t * adj_t / (close_{t-1} * adj_{t-1}) ).clip(-0.105, 0.105)
       turnover = amount / (circ_mv * 10)
  4. Compute the 8 raw alphas (rolling on past bars only)
  5. Compute controls: log_mv, sigma_20 (CC), ret_5 (CC), ret_20 (CC), turnover_20
  6. Forward returns: fwd_ret_k = exp(sum(log_CC over [t+1+delay, t+k+delay])) - 1, delay=1
       Invariant: target_shift = -(1+delay) = -2
  7. Per-date pipeline applied LATER in 02_compute_alphas.py (winsor + ind-demean + cs-z)
"""
from __future__ import annotations
import os, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

CACHE   = Path("/home/user/Factor_Zoo/.cache")
SESSION = Path("/home/user/Factor_Zoo/logs/20260428_a_share_overnight_intraday_alpha")
OUT     = SESSION / "outputs" / "panel_overnight.parquet"
DELAY   = 1

t0 = time.time()
print("=== load cache ===", flush=True)
daily = pd.read_parquet(CACHE / "daily.parquet")
adj   = pd.read_parquet(CACHE / "adj_factor.parquet")
db    = pd.read_parquet(CACHE / "daily_basic.parquet")
sb    = pd.read_parquet(CACHE / "stock_basic.parquet",
                        columns=["ts_code", "name", "industry", "market", "list_date"])
print(f"  daily {daily.shape}  adj {adj.shape}  db {db.shape}  sb {sb.shape}")

print("=== merge ===", flush=True)
df = daily.merge(adj, on=["ts_code", "trade_date"], how="left")
df = df.merge(db,  on=["ts_code", "trade_date"], how="left")
df = df.merge(sb,  on="ts_code", how="left")
df["trade_date"] = df["trade_date"].astype(str)
df = df.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)
print(f"  merged {df.shape}")

# Universe filter
print("=== universe filter ===", flush=True)
n0 = len(df)
df = df[~df["name"].fillna("").str.contains("ST")]
print(f"  drop ST/*ST: {n0 - len(df)} rows removed; {len(df)} remain")
n0 = len(df)
df = df[df["vol"].fillna(0) > 0]
print(f"  drop vol==0: {n0 - len(df)} rows removed; {len(df)} remain")

# Primitives
print("=== primitives ===", flush=True)
g = df.groupby("ts_code", sort=False)
df["close_adj_prev"] = g["close"].shift(1) * g["adj_factor"].shift(1)
df["close_adj"]      = df["close"] * df["adj_factor"]
df["open_adj"]       = df["open"]  * df["adj_factor"]

df["ret_ON"] = df["open_adj"]  / df["close_adj_prev"] - 1.0
df["ret_ID"] = df["close"]     / df["open"] - 1.0
df["ret_CC"] = df["close_adj"] / df["close_adj_prev"] - 1.0

for c in ["ret_ON", "ret_ID", "ret_CC"]:
    df[f"log_{c[4:]}"] = np.log1p(df[c]).clip(-0.105, 0.105)

df["turnover"] = df["amount"] / (df["circ_mv"] * 10.0)
df["turnover"] = df["turnover"].replace([np.inf, -np.inf], np.nan)

# Rolling controls (close-to-close based)
print("=== controls (sigma_20, ret_5, ret_20, turnover_20, log_mv) ===", flush=True)
g = df.groupby("ts_code", sort=False)
df["sigma_20"]    = g["log_CC"].transform(lambda s: s.rolling(20, min_periods=15).std())
df["ret_5"]       = g["log_CC"].transform(lambda s: s.rolling(5,  min_periods=4 ).sum())
df["ret_20"]      = g["log_CC"].transform(lambda s: s.rolling(20, min_periods=15).sum())
df["turnover_20"] = g["turnover"].transform(lambda s: s.rolling(20, min_periods=15).mean())
df["log_mv"]      = np.log(df["total_mv"].replace(0, np.nan))

# 8 raw alphas (rolling on past bars only)
print("=== 8 raw alphas ===", flush=True)
df["alpha_01_raw"] = g["log_ON"].transform(lambda s: s.rolling(20, min_periods=15).sum())
df["alpha_02_raw"] = g["log_ON"].transform(lambda s: s.rolling(5,  min_periods=4 ).sum())
df["alpha_03_raw"] = g["log_ON"].transform(lambda s: s.rolling(60, min_periods=44).sum())
df["sum_ID_20"]    = g["log_ID"].transform(lambda s: s.rolling(20, min_periods=15).sum())
df["alpha_04_raw"] = df["alpha_01_raw"] - df["sum_ID_20"]
df["std_ON_20"]    = g["log_ON"].transform(lambda s: s.rolling(20, min_periods=15).std())
df["alpha_05_raw"] = df["alpha_01_raw"] / df["std_ON_20"].clip(lower=1e-4)
df["mean_tov_20"]  = df["turnover_20"]
# turnover cs-zscore done later per-date; here we use raw mean turnover, then mult by zscore in step 02
df["alpha_06_raw_pre"] = df["alpha_01_raw"]   # placeholder; multiply by zscore(mean_tov_20) per date in step 02
df["alpha_07_raw"] = g["log_ON"].transform(lambda s: (s > 0).rolling(20, min_periods=15).mean())
df["mean_ON_20"]   = g["log_ON"].transform(lambda s: s.rolling(20, min_periods=15).mean())
df["alpha_08_raw"] = df["mean_ON_20"] / df["std_ON_20"].clip(lower=1e-4)

# Forward returns (target) — invariant: target_shift = -(1+delay)
# At date T with delay=1: signal observed at close T, executed at close T+1.
# fwd_ret_k must therefore be the cumulative log return from T+1+delay to T+k+delay,
# i.e. from T+2 to T+1+k for delay=1.
# Implementation: shift(-(1+k)) places s_{T+1+k} at row T; rolling(k).sum() then
# sums s_{T+2}..s_{T+1+k}. Confirmed by future-perturbation audit (script 04).
print("=== fwd returns delay=1 ===", flush=True)
g = df.groupby("ts_code", sort=False)
for k in [1, 5, 10, 20, 60]:
    df[f"fwd_ret_{k}"] = g["log_CC"].transform(
        lambda s: s.shift(-(1 + k)).rolling(k, min_periods=max(1, k - 2)).sum()
    )
    df[f"fwd_ret_{k}"] = np.expm1(df[f"fwd_ret_{k}"])
print(f"  invariant: target_shift == -(1+delay) == {-(1 + DELAY)}  (delay={DELAY})", flush=True)

# Save
keep = [
    "ts_code", "trade_date", "industry", "market", "list_date",
    "open", "close", "vol", "amount", "adj_factor",
    "total_mv", "circ_mv", "turnover_rate_f",
    "log_ON", "log_ID", "log_CC", "turnover",
    "sigma_20", "ret_5", "ret_20", "turnover_20", "log_mv",
    "alpha_01_raw", "alpha_02_raw", "alpha_03_raw", "alpha_04_raw",
    "alpha_05_raw", "alpha_06_raw_pre", "alpha_07_raw", "alpha_08_raw",
    "mean_tov_20",
    "fwd_ret_1", "fwd_ret_5", "fwd_ret_10", "fwd_ret_20", "fwd_ret_60",
]
out = df[keep].copy()
out.to_parquet(OUT, index=False)
print(f"WROTE {OUT}  shape={out.shape}  elapsed={time.time()-t0:.1f}s", flush=True)
