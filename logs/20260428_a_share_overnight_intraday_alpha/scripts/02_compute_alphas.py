"""
Apply per-date pipeline (winsorize -> industry-demean -> cs-zscore) to the 8 raw
alphas. Also resolve alpha_06 = alpha_01_raw * cs_zscore(mean_tov_20) per date.

Reads:  outputs/panel_overnight.parquet
Writes: outputs/panel_alphas.parquet  (only the 8 final z-scored alpha columns
                                        + ts_code, trade_date, industry, fwd_ret_*)
"""
from __future__ import annotations
import time
from pathlib import Path
import numpy as np
import pandas as pd

SESSION = Path("/home/user/Factor_Zoo/logs/20260428_a_share_overnight_intraday_alpha")
IN_  = SESSION / "outputs" / "panel_overnight.parquet"
OUT  = SESSION / "outputs" / "panel_alphas.parquet"

t0 = time.time()
df = pd.read_parquet(IN_)
print(f"loaded panel {df.shape}  dates={df['trade_date'].nunique()}", flush=True)

ALPHAS = ["alpha_01", "alpha_02", "alpha_03", "alpha_04",
          "alpha_05", "alpha_06", "alpha_07", "alpha_08"]


def per_date_winsor(s, low=0.01, high=0.99):
    lo = s.quantile(low)
    hi = s.quantile(high)
    return s.clip(lo, hi)


def cs_zscore(s):
    mu = s.mean(); sd = s.std()
    if sd == 0 or np.isnan(sd):
        return s * 0.0
    return (s - mu) / sd


def industry_demean(group):
    # group is a single trade_date slice
    return group.groupby("industry").transform(lambda x: x - x.mean())


# Resolve alpha_06: cs zscore of mean_tov_20 per date, then multiply by alpha_01_raw
print("=== resolve alpha_06 ===", flush=True)
df["tov_z"] = df.groupby("trade_date")["mean_tov_20"].transform(cs_zscore)
df["alpha_06_raw"] = df["alpha_01_raw"] * df["tov_z"]

# Drop placeholder
if "alpha_06_raw_pre" in df.columns:
    df.drop(columns=["alpha_06_raw_pre"], inplace=True)

# Per-date pipeline for each alpha
print("=== per-date winsor -> industry-demean -> cs-zscore ===", flush=True)
for a in ALPHAS:
    raw_col = f"{a}_raw"
    print(f"  {a}", flush=True)
    # winsorize per date
    df[raw_col] = df.groupby("trade_date")[raw_col].transform(per_date_winsor)
    # industry-demean per date
    # (works even with NaN industry — those rows become NaN and get dropped at IC step)
    df[a] = df[raw_col] - df.groupby(["trade_date", "industry"])[raw_col].transform("mean")
    # cs-zscore per date
    df[a] = df.groupby("trade_date")[a].transform(cs_zscore)

keep = ["ts_code", "trade_date", "industry", "log_mv", "sigma_20",
        "ret_5", "ret_20", "turnover_20",
        "fwd_ret_1", "fwd_ret_5", "fwd_ret_10", "fwd_ret_20", "fwd_ret_60"] + ALPHAS
out = df[keep].copy()
out.to_parquet(OUT, index=False)
print(f"WROTE {OUT}  shape={out.shape}  elapsed={time.time()-t0:.1f}s", flush=True)
