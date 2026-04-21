"""
Round 3 — σ-decoupled iteration of α_05, α_08, α_15.

Input:
  - panel_volprice.parquet   (α_01..α_08, controls)
  - panel_round2_skew.parquet (α_15 = -jump_up_20; we also have jump_up_20 raw column)

Output:
  - panel_round3.parquet with α_17..α_24
  - backtest + audit all 8
"""
import os, json, time, numpy as np, pandas as pd
from numpy.linalg import lstsq

SESSION = "/home/user/Factor_Zoo/logs/20260421_volprice_max_lottery"
OUT = f"{SESSION}/outputs"

t0 = time.time()
print("=== load base panels ===")
p1 = pd.read_parquet(f"{OUT}/panel_volprice.parquet")  # has α_01..α_08, ret_5/20, σ_20, turnover_20, log-mv base, fwd_ret_20
p2 = pd.read_parquet(f"{OUT}/panel_round2_skew.parquet",
                     columns=["ts_code","trade_date","alpha_15","sigma_60"])
print(f"   p1 {p1.shape}, p2 {p2.shape}")

p = p1.merge(p2, on=["ts_code","trade_date"], how="left")
p["log_mv"] = np.log1p(p["total_mv"])
print(f"   merged {p.shape}  elapsed={time.time()-t0:.0f}s")


def cs_z(s):
    """Cross-section z-score per date (no groupby key needed — s is one-date slice)."""
    mu, sd = np.nanmean(s), np.nanstd(s)
    if sd < 1e-12: return np.zeros_like(s)
    return (s - mu) / sd


def industry_demean_zscore(df, col):
    out = np.full(len(df), np.nan)
    for d, sub in df.groupby("trade_date", sort=False):
        x = sub[col].values.astype(float)
        if np.isfinite(x).sum() < 30:
            continue
        lo, hi = np.nanpercentile(x, [1, 99])
        xw = np.clip(x, lo, hi)
        ind = sub["industry"].values
        ser = pd.Series(xw, index=sub.index)
        ind_mean = ser.groupby(ind).transform("mean")
        demean = xw - ind_mean.values
        out[sub.index - df.index[0]] = cs_z(demean)  # simplistic — relies on contiguous index
    # re-do robustly
    out2 = np.full(len(df), np.nan)
    for d, sub in df.groupby("trade_date", sort=False):
        x = sub[col].values.astype(float)
        if np.isfinite(x).sum() < 30:
            continue
        lo, hi = np.nanpercentile(x, [1, 99])
        xw = np.clip(x, lo, hi)
        ind = sub["industry"].values
        ser = pd.Series(xw)
        ind_mean = ser.groupby(ind).transform("mean").values
        demean = xw - ind_mean
        out2[sub.index.values - 0] = 0  # placeholder
        # use sub.index (integer) relative to df's RangeIndex
    # Simplest: write back via loc
    out2 = pd.Series(np.nan, index=df.index)
    for d, sub in df.groupby("trade_date", sort=False):
        x = sub[col].values.astype(float)
        if np.isfinite(x).sum() < 30:
            continue
        lo, hi = np.nanpercentile(x, [1, 99])
        xw = np.clip(x, lo, hi)
        ind = sub["industry"].values
        ser = pd.Series(xw, index=sub.index)
        ind_mean = ser.groupby(ind).transform("mean")
        demean = xw - ind_mean
        mu, sd = np.nanmean(demean), np.nanstd(demean)
        z = (demean - mu) / sd if sd > 1e-12 else demean * 0
        out2.loc[sub.index] = z.values
    return out2.values


def sigma_bucket_rank(df, base_col, sigma_col="sigma_20", n_bucket=5):
    """Per-date: sort into σ quintiles, compute rank of base_col within each bucket."""
    res = pd.Series(np.nan, index=df.index)
    for d, sub in df.groupby("trade_date", sort=False):
        s = sub[[base_col, sigma_col]].dropna()
        if len(s) < n_bucket * 20:
            continue
        try:
            s["bucket"] = pd.qcut(s[sigma_col], n_bucket, labels=False, duplicates="drop")
        except ValueError:
            continue
        # rank within bucket
        s["rank_within"] = s.groupby("bucket")[base_col].rank(pct=True) - 0.5
        res.loc[s.index] = s["rank_within"].values
    return res.values


def double_bucket_rank(df, base_col, col1="sigma_20", col2="turnover_20", n1=5, n2=5):
    res = pd.Series(np.nan, index=df.index)
    for d, sub in df.groupby("trade_date", sort=False):
        s = sub[[base_col, col1, col2]].dropna()
        if len(s) < n1*n2*10:
            continue
        try:
            s["b1"] = pd.qcut(s[col1], n1, labels=False, duplicates="drop")
            s["b2"] = pd.qcut(s[col2], n2, labels=False, duplicates="drop")
        except ValueError:
            continue
        s["rank_within"] = s.groupby(["b1","b2"])[base_col].rank(pct=True) - 0.5
        res.loc[s.index] = s["rank_within"].values
    return res.values


def ts_residualize_per_stock(df, target_col, control_col):
    """Per stock: residualize target on control via OLS over all obs."""
    res = pd.Series(np.nan, index=df.index)
    for code, sub in df.groupby("ts_code", sort=False):
        s = sub[[target_col, control_col]].dropna()
        if len(s) < 100:
            continue
        X = s[control_col].values
        X = np.vstack([X, np.ones_like(X)]).T
        y = s[target_col].values
        try:
            beta, *_ = lstsq(X, y, rcond=None)
        except np.linalg.LinAlgError:
            continue
        pred = X @ beta
        resid = y - pred
        res.loc[s.index] = resid
    return res.values


# --- raw α_05/08/15 are the industry-demeaned z-scored versions already in panel_volprice;
# --- for σ-bucket we want the RAW SIGNAL (before ind-demean) so the bucket sort can be rebuilt.
# --- Approximation: use the already-normalized alpha as base; σ-bucket within-date is still valid.

print("=== α_17 σ-bucket rank of α_08 ===")
p["raw_17"] = sigma_bucket_rank(p, "alpha_08", "sigma_20", 5)

print("=== α_18 σ-bucket rank of α_05 ===")
p["raw_18"] = sigma_bucket_rank(p, "alpha_05", "sigma_20", 5)

print("=== α_19 σ-bucket rank of α_15 ===")
p["raw_19"] = sigma_bucket_rank(p, "alpha_15", "sigma_20", 5)

print("=== α_20 = α_17 × α_19 interaction ===")
p["raw_20"] = p["raw_17"] * p["raw_19"]

print("=== α_21 fixed-threshold jump count 5% ===")
# Reuse panel_round2_skew which has jump up counts? We don't have jump_up_fixed. Rebuild from .cache daily.
from pathlib import Path
CACHE = "/home/user/Factor_Zoo/.cache"
daily = pd.read_parquet(f"{CACHE}/daily.parquet")
adj = pd.read_parquet(f"{CACHE}/adj_factor.parquet")
df = daily.merge(adj, on=["ts_code","trade_date"], how="left").sort_values(["ts_code","trade_date"]).reset_index(drop=True)
df["close_adj"] = df["close"] * df["adj_factor"]
df["log_ret"] = np.log(df["close_adj"] / df.groupby("ts_code")["close_adj"].shift(1)).clip(-0.105, 0.105)

# market ret for idio
mkt = df.groupby("trade_date")["log_ret"].mean().rename("mkt_log_ret").reset_index()
df = df.merge(mkt, on="trade_date", how="left")
df["idio"] = df["log_ret"] - df["mkt_log_ret"]

# α_21: count(log_ret > 0.05) in 20d
df["jump_5pct"] = (df["log_ret"] > 0.05).astype(float)
df["jump_5pct"] = df["jump_5pct"].where(df["log_ret"].notna(), np.nan)
df["raw_21_stock"] = -df.groupby("ts_code")["jump_5pct"].transform(
    lambda s: s.rolling(20, min_periods=15).sum()
)
# α_22: count(idio > 0.03) in 20d
df["jump_idio_3pct"] = (df["idio"] > 0.03).astype(float)
df["jump_idio_3pct"] = df["jump_idio_3pct"].where(df["idio"].notna(), np.nan)
df["raw_22_stock"] = -df.groupby("ts_code")["jump_idio_3pct"].transform(
    lambda s: s.rolling(20, min_periods=15).sum()
)

# merge raw_21/22 back into panel p (they are stock-time-series independent of x-section)
p = p.merge(df[["ts_code","trade_date","raw_21_stock","raw_22_stock"]], on=["ts_code","trade_date"], how="left")
p["raw_21"] = p["raw_21_stock"]
p["raw_22"] = p["raw_22_stock"]

print("=== α_23 time-series pre-residualize top5 vs σ_20 per stock ===")
# we need top5 over 20d. Not in panel. Rebuild.
g = df.groupby("ts_code")
df["sigma_20"] = g["log_ret"].transform(lambda s: s.rolling(20, min_periods=15).std())
def _topk(x, k=5):
    x = x[~np.isnan(x)]
    if len(x) == 0: return np.nan
    return np.sort(x)[-min(k, len(x)):].mean()
# slow — use sliding_window_view
print("   computing top5_ret via stride tricks ...")
def top5_per_stock(arr, window=20, min_p=15):
    n = len(arr)
    if n < window:
        return np.full(n, np.nan)
    views = np.lib.stride_tricks.sliding_window_view(arr, window)
    masks = ~np.isnan(views)
    counts = masks.sum(axis=1)
    valid = counts >= min_p
    viewsN = np.where(masks, views, -np.inf)
    if window >= 5:
        part = -np.partition(-viewsN, 5, axis=1)[:, :5].mean(axis=1)
    else:
        part = viewsN.max(axis=1)
    part = np.where(valid, part, np.nan)
    return np.concatenate([np.full(window-1, np.nan), part])

grp_idx = df.groupby("ts_code", sort=False).indices
df["top5_20"] = np.nan
for code, idx in grp_idx.items():
    lr = df.iloc[idx]["log_ret"].values
    df.iloc[idx, df.columns.get_loc("top5_20")] = top5_per_stock(lr, 20, 15)

# Per-stock OLS: top5_20 = α_i + β_i * σ_20 + ε
df["top5_resid"] = np.nan
for code, idx in grp_idx.items():
    s = df.iloc[idx][["top5_20","sigma_20"]].dropna()
    if len(s) < 100:
        continue
    X = s["sigma_20"].values
    X = np.vstack([X, np.ones_like(X)]).T
    y = s["top5_20"].values
    try:
        beta, *_ = lstsq(X, y, rcond=None)
    except np.linalg.LinAlgError:
        continue
    pred = X @ beta
    df.iloc[s.index, df.columns.get_loc("top5_resid")] = y - pred

p = p.merge(df[["ts_code","trade_date","top5_resid"]], on=["ts_code","trade_date"], how="left")
p["raw_23"] = -p["top5_resid"]  # high residual → overperformed on MAX given their σ → short

print("=== α_24 σ × turnover double-bucket on α_08 ===")
p["raw_24"] = double_bucket_rank(p, "alpha_08", "sigma_20", "turnover_20", 5, 5)

# --- Cross-section process: industry demean + z-score
print("=== per-date xsection ===")
RAWS = [f"raw_{i}" for i in [17,18,19,20,21,22,23,24]]
OUTS = [f"alpha_{i}" for i in [17,18,19,20,21,22,23,24]]
for c in OUTS:
    p[c] = np.nan

for col, out in zip(RAWS, OUTS):
    p[out] = industry_demean_zscore(p, col)
    print(f"   {out}: coverage={p[out].notna().mean():.3f}  std={p[out].std():.3f}")

keep = ["ts_code","trade_date","industry",
        "alpha_17","alpha_18","alpha_19","alpha_20","alpha_21","alpha_22","alpha_23","alpha_24",
        "fwd_ret_1","fwd_ret_5","fwd_ret_20","fwd_ret_60",
        "total_mv","circ_mv","turnover_20","sigma_20","ret_5","ret_20"]
out_df = p[keep].copy()
OUT_PATH = f"{OUT}/panel_round3.parquet"
out_df.to_parquet(OUT_PATH, index=False)
print(f"\nwrote {OUT_PATH}  rows={len(out_df)}  elapsed={time.time()-t0:.0f}s")
