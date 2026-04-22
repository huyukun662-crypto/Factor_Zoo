"""
Round 2 — Idiosyncratic Skewness family (VECTORIZED).

Speed-ups vs 06_build:
  - Rolling skew computed via moments (mean, std, 3rd central moment) — fully vectorized
  - rolling top-k / bottom-k computed via numpy.partition over stride-tricks window views
  - Per-stock processing in one pass using sliding_window_view
"""
import os, time, numpy as np, pandas as pd

SESSION = "/home/user/Factor_Zoo/logs/20260421_volprice_max_lottery"
CACHE = "/home/user/Factor_Zoo/.cache"

t0 = time.time()
print("=== load base data ===")
daily = pd.read_parquet(f"{CACHE}/daily.parquet")
adj = pd.read_parquet(f"{CACHE}/adj_factor.parquet")
dbasic = pd.read_parquet(f"{CACHE}/daily_basic.parquet")
panel_old = pd.read_parquet(f"{CACHE}/panel.parquet", columns=["ts_code", "industry"]).drop_duplicates("ts_code")

df = daily.merge(adj, on=["ts_code","trade_date"], how="left").merge(dbasic, on=["ts_code","trade_date"], how="left")
df = df.sort_values(["ts_code","trade_date"]).reset_index(drop=True)
df["close_adj"] = df["close"] * df["adj_factor"]
df["log_ret"] = np.log(df["close_adj"] / df.groupby("ts_code")["close_adj"].shift(1))
df["log_ret"] = df["log_ret"].clip(-0.105, 0.105)
df["turnover"] = (df["amount"] / (df["circ_mv"] * 10.0)).replace([np.inf, -np.inf], np.nan)
mkt = df.groupby("trade_date")["log_ret"].mean().rename("mkt_log_ret").reset_index()
df = df.merge(mkt, on="trade_date", how="left")
df["idio"] = df["log_ret"] - df["mkt_log_ret"]
print(f"loaded {len(df):,} rows  elapsed={time.time()-t0:.0f}s")


# Vectorized rolling via per-stock sliding_window_view
def rolling_features_per_stock(arr, window, min_periods):
    """Given 1D array, return windowed features (mean, std, skew, top5, bot5, max)."""
    n = len(arr)
    if n < window:
        nan_arr = np.full(n, np.nan)
        return {k: nan_arr.copy() for k in ["mean","std","skew","top5","bot5","top10","max","median","jump_count"]}
    # pad nan on the left to align "at end of window" semantics
    views = np.lib.stride_tricks.sliding_window_view(arr, window)  # shape (n-window+1, window)
    # Compute masks
    masks = ~np.isnan(views)
    counts = masks.sum(axis=1)
    valid = counts >= min_periods
    # Replace NaN with 0 for sum ops but we'll fix with masks
    safe = np.where(masks, views, 0.0)
    sums = safe.sum(axis=1)
    means = np.where(valid, sums / np.where(counts > 0, counts, 1), np.nan)
    diffs = (safe - means[:, None]) * masks
    var_num = (diffs ** 2).sum(axis=1)
    stds = np.sqrt(np.where(valid & (counts > 1), var_num / np.where(counts > 1, counts - 1, 1), np.nan))
    # skew = mean((x-mu)^3) / std^3 ; unbiased adjustment omitted (large-N ~equivalent)
    m3 = (diffs ** 3).sum(axis=1) / np.where(counts > 0, counts, 1)
    skews = np.where(valid & (stds > 1e-9), m3 / (stds ** 3 + 1e-30), np.nan)
    # top-k / bot-k via partition; for NaN we replaced with 0 which could bias — use views with -inf
    viewsN = np.where(masks, views, -np.inf)
    # top-k: partial-sort top k at end
    if window >= 10:
        part_top5 = -np.partition(-viewsN, 5, axis=1)[:, :5].mean(axis=1)
        part_bot5 = np.partition(np.where(masks, views, np.inf), 5, axis=1)[:, :5].mean(axis=1)
        part_top10 = -np.partition(-viewsN, 10, axis=1)[:, :10].mean(axis=1) if window >= 20 else np.full(len(viewsN), np.nan)
    else:
        part_top5 = np.full(len(viewsN), np.nan)
        part_bot5 = np.full(len(viewsN), np.nan)
        part_top10 = np.full(len(viewsN), np.nan)
    maxs = viewsN.max(axis=1)
    # median: use nanmedian
    medians = np.nanmedian(np.where(masks, views, np.nan), axis=1)
    # Pad to length n
    out = {}
    pad = n - len(means)  # = window - 1
    nan_pad = np.full(pad, np.nan)
    for name, vec in [("mean", means), ("std", stds), ("skew", skews),
                       ("top5", part_top5), ("bot5", part_bot5), ("top10", part_top10),
                       ("max", maxs), ("median", medians)]:
        out[name] = np.concatenate([nan_pad, vec])
    return out


def rolling_count_cond_per_stock(arr, cond_arr, window, min_periods):
    """Count True values in cond_arr over rolling window of length `window`."""
    n = len(arr)
    if n < window:
        return np.full(n, np.nan)
    views = np.lib.stride_tricks.sliding_window_view(cond_arr.astype(float), window)
    masks = ~np.isnan(np.lib.stride_tricks.sliding_window_view(arr, window))
    counts = masks.sum(axis=1)
    valid = counts >= min_periods
    summed = np.where(masks, views, 0.0).sum(axis=1)
    out = np.where(valid, summed, np.nan)
    nan_pad = np.full(window - 1, np.nan)
    return np.concatenate([nan_pad, out])


# Process each stock
print("=== per-stock vectorized rolling ===")
cols_wanted = [
    "sigma_20","sigma_60","turnover_20","ret_5","ret_20",
    "skew_20_idio","skew_60_idio",
    "top5_ret","bot5_ret","median_ret","mean_ret","max_ret",
    "skew_pearson_raw",
    "jump_up_20",
]
for c in cols_wanted:
    df[c] = np.nan

# Need fwd_ret too
for k in [1, 5, 20, 60]:
    df[f"fwd_ret_{k}"] = np.nan

grp_idx = df.groupby("ts_code", sort=False).indices

processed = 0
for code, idx in grp_idx.items():
    # ensure sorted
    log_ret = df.iloc[idx]["log_ret"].values
    idio = df.iloc[idx]["idio"].values
    turnover = df.iloc[idx]["turnover"].values

    feat20 = rolling_features_per_stock(log_ret, 20, 15)
    feat60 = rolling_features_per_stock(log_ret, 60, 45)
    feat20_idio = rolling_features_per_stock(idio, 20, 15)
    feat60_idio = rolling_features_per_stock(idio, 60, 45)
    # turnover_20 via mean
    feat20_turn = rolling_features_per_stock(turnover, 20, 15)

    n = len(idx)
    df.iloc[idx, df.columns.get_loc("sigma_20")] = feat20["std"]
    df.iloc[idx, df.columns.get_loc("sigma_60")] = feat60["std"]
    df.iloc[idx, df.columns.get_loc("turnover_20")] = feat20_turn["mean"]
    df.iloc[idx, df.columns.get_loc("max_ret")] = feat20["max"]
    df.iloc[idx, df.columns.get_loc("top5_ret")] = feat20["top5"]
    df.iloc[idx, df.columns.get_loc("bot5_ret")] = feat20["bot5"]
    df.iloc[idx, df.columns.get_loc("median_ret")] = feat20["median"]
    df.iloc[idx, df.columns.get_loc("mean_ret")] = feat20["mean"]
    df.iloc[idx, df.columns.get_loc("skew_20_idio")] = feat20_idio["skew"]
    df.iloc[idx, df.columns.get_loc("skew_60_idio")] = feat60_idio["skew"]
    # Pearson skew numerator: 3*(mean - median)
    df.iloc[idx, df.columns.get_loc("skew_pearson_raw")] = 3.0 * (feat20["mean"] - feat20["median"])
    # ret_5, ret_20 = rolling sum
    # simple trick: rolling mean * window
    feat5 = rolling_features_per_stock(log_ret, 5, 4)
    df.iloc[idx, df.columns.get_loc("ret_5")] = feat5["mean"] * 5
    df.iloc[idx, df.columns.get_loc("ret_20")] = feat20["mean"] * 20

    # jump_up_20: count(log_ret > 2*sigma_60_lag1) in rolling 20
    sigma60_lag1 = np.roll(feat60["std"], 1); sigma60_lag1[0] = np.nan
    cond = (log_ret > 2 * sigma60_lag1).astype(float)
    cond[np.isnan(log_ret) | np.isnan(sigma60_lag1)] = np.nan
    df.iloc[idx, df.columns.get_loc("jump_up_20")] = rolling_count_cond_per_stock(log_ret, cond, 20, 15)

    # fwd_ret: sum log_ret from t+2 to t+1+k, then expm1
    # compute via cumsum trick: cs[i] = sum log_ret[0..i-1]; sum[t+2..t+1+k] = cs[t+2+k] - cs[t+2]
    cs = np.concatenate([[0.0], np.nancumsum(log_ret)])
    # Number of valid obs in window
    cs_cnt = np.concatenate([[0], np.cumsum(~np.isnan(log_ret))])
    for k in [1, 5, 20, 60]:
        vals = np.full(n, np.nan)
        for t in range(n - 1 - k):
            s = cs[t + 2 + k] - cs[t + 2]
            # require all k obs
            if cs_cnt[t + 2 + k] - cs_cnt[t + 2] == k:
                vals[t] = np.expm1(s)
        df.iloc[idx, df.columns.get_loc(f"fwd_ret_{k}")] = vals

    processed += 1
    if processed % 500 == 0:
        print(f"   {processed}/{len(grp_idx)} stocks  elapsed={time.time()-t0:.0f}s")

print(f"rolling features done  elapsed={time.time()-t0:.0f}s")

# Build raw alphas
print("=== raw alphas ===")
df["raw_09"] = -df["skew_20_idio"]
df["raw_10"] = -df["skew_60_idio"]
# α_11 coskew: cov(idio, (mkt-mkt_mean)^2) over 60d / sigma_20^2
# simple proxy: skew_60_idio weighted by mkt_vol — but let's use actual formula
mkt_mean_60 = mkt.rolling_mean = mkt["mkt_log_ret"].rolling(60, min_periods=45).mean()
mkt_dev2 = (mkt["mkt_log_ret"] - mkt_mean_60) ** 2
mkt_lookup = dict(zip(mkt["trade_date"], mkt_dev2))
df["mkt_dev2"] = df["trade_date"].map(mkt_lookup)
df["coskew_raw"] = df["idio"] * df["mkt_dev2"]
# rolling 60d mean of coskew_raw per stock
for code, idx in grp_idx.items():
    cr = df.iloc[idx]["coskew_raw"].values
    feat60c = rolling_features_per_stock(cr, 60, 45)
    df.iloc[idx, df.columns.get_loc("coskew_raw")] = feat60c["mean"]
df["raw_11"] = -(df["coskew_raw"] / (df["sigma_20"] ** 2).replace(0, np.nan))

df["raw_12"] = -(df["top5_ret"] - np.abs(df["bot5_ret"])) / df["sigma_20"].replace(0, np.nan)
df["raw_13"] = -(df["raw_09"].fillna(0) + 0.5 * df["top5_ret"] / df["sigma_20"].replace(0, np.nan))
df["raw_14"] = -df["skew_pearson_raw"] / df["sigma_20"].replace(0, np.nan)
df["raw_15"] = -df["jump_up_20"]
# raw_16 computed per date (needs cs_z turnover_20)
df["raw_16"] = np.nan

print("=== attach industry ===")
df = df.merge(panel_old, on="ts_code", how="left")
df["industry"] = df["industry"].fillna("Unknown")

print("=== per-date xsection (winsor+ind demean+zscore) ===")


def xsection(g_df, col):
    x = g_df[col].values.astype(float)
    if np.isfinite(x).sum() < 30:
        return np.full_like(x, np.nan, dtype=float)
    lo, hi = np.nanpercentile(x, [1, 99])
    xw = np.clip(x, lo, hi)
    ind = g_df["industry"].values
    # industry demean via pandas
    ser = pd.Series(xw)
    ind_mean = ser.groupby(ind).transform("mean").values
    demean = xw - ind_mean
    mu, sd = np.nanmean(demean), np.nanstd(demean)
    return (demean - mu) / sd if sd > 1e-12 else np.zeros_like(demean)


RAWS = [f"raw_{i:02d}" for i in [9,10,11,12,13,14,15,16]]
OUTS = [f"alpha_{i:02d}" for i in [9,10,11,12,13,14,15,16]]
for c in OUTS:
    df[c] = np.nan

dates = df["trade_date"].unique()
for i, d in enumerate(dates):
    idx = df.index[df["trade_date"] == d]
    sub = df.loc[idx]
    # α_16 first: needs cs_z(turnover_20)
    tz = sub["turnover_20"].values.astype(float)
    if np.isfinite(tz).sum() >= 30:
        lo, hi = np.nanpercentile(tz, [1, 99])
        tzw = np.clip(tz, lo, hi)
        mu, sd = np.nanmean(tzw), np.nanstd(tzw)
        z = (tzw - mu) / sd if sd > 1e-12 else np.zeros_like(tzw)
    else:
        z = np.zeros_like(tz)
    df.loc[idx, "raw_16"] = sub["raw_09"].values * z  # -skew * attention; sign via raw_09
    sub2 = df.loc[idx]
    for col, out in zip(RAWS, OUTS):
        df.loc[idx, out] = xsection(sub2, col)
    if (i+1) % 200 == 0:
        print(f"   {i+1}/{len(dates)} dates  elapsed={time.time()-t0:.0f}s")

keep = ["ts_code","trade_date","industry"] + OUTS + [
    "fwd_ret_1","fwd_ret_5","fwd_ret_20","fwd_ret_60",
    "total_mv","circ_mv","turnover_20","sigma_20","sigma_60","ret_5","ret_20"
]
out = df[keep].copy()
OUT_PATH = f"{SESSION}/outputs/panel_round2_skew.parquet"
out.to_parquet(OUT_PATH, index=False)
print(f"wrote {OUT_PATH}  rows={len(out)}  elapsed={time.time()-t0:.0f}s")
