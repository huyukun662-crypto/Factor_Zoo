"""
Build the 8 accruals-family alphas on the A-share panel with strict ann_date gating.

Pipeline
--------
1. Load fundamentals (income/balancesheet/cashflow) + daily price/adj/mv + stock_basic.
2. Universe filter: ex-financials, listed >= 252 trading days, non-ST at date.
3. Quarterly -> daily forward-fill at `ann_date + 1 trade day`.
4. Compute TTM aggregates and derived fields.
5. Cross-sectional ranks per trade_date.
6. Save:
     .cache/panel.parquet        (ts_code, trade_date, alpha_01..alpha_08, fwd_ret_1/5/20/60, industry, size_bin)
"""
import os, sys, time
import numpy as np
import pandas as pd
import tushare as ts

CACHE = "/home/user/Factor_Zoo/.cache"


def log(s):
    print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)


# -------- 1. Load --------
log("loading parquet caches")
income = pd.read_parquet(f"{CACHE}/income.parquet")
bs = pd.read_parquet(f"{CACHE}/balancesheet.parquet")
cf = pd.read_parquet(f"{CACHE}/cashflow.parquet")
daily = pd.read_parquet(f"{CACHE}/daily.parquet")
adj = pd.read_parquet(f"{CACHE}/adj_factor.parquet")
db = pd.read_parquet(f"{CACHE}/daily_basic.parquet")

TOKEN = os.environ["TUSHARE_TOKEN"]
pro = ts.pro_api(TOKEN)
basic = pro.stock_basic(
    exchange="", list_status="L", fields="ts_code,name,industry,list_date"
)
# Also fetch delisted to catch historical exits (optional)
log(f"basic: {len(basic)} rows, industries: {basic['industry'].nunique()}")


# -------- 2. Universe --------
EXCLUDED_INDUSTRIES = {
    "银行", "全国地产", "区域地产", "房产服务",
    "保险", "证券", "多元金融", "期货",
}
basic["list_date"] = pd.to_datetime(basic["list_date"], format="%Y%m%d")
basic["is_financial"] = basic["industry"].isin(EXCLUDED_INDUSTRIES)
stock_meta = basic[["ts_code", "industry", "list_date", "is_financial"]].copy()

# ST filter: use name-based; current ST only (free/pro tier often lacks historical namechange)
# We already used list_status='L', so ST stocks with name prefix *ST/ST are still in
# We'll drop by name pattern
basic["is_st"] = basic["name"].str.contains("ST", na=False)
stock_meta["is_st"] = basic["is_st"]

# -------- 3. Clean fundamentals: merge into wide quarterly table --------
for df in (income, bs, cf):
    df["ann_date"] = pd.to_datetime(df["ann_date"], format="%Y%m%d", errors="coerce")
    df["end_date"] = pd.to_datetime(df["end_date"], format="%Y%m%d", errors="coerce")

# Keep the earliest ann_date per (ts_code, end_date) — already done in fetch step
income_use = income[["ts_code", "ann_date", "end_date", "n_income", "revenue"]]
bs_use = bs[
    [
        "ts_code",
        "ann_date",
        "end_date",
        "total_assets",
        "accounts_receiv",
        "inventories",
        "accounts_pay",
        "total_share",
    ]
]
cf_use = cf[
    ["ts_code", "ann_date", "end_date", "n_cashflow_act", "depr_fa_coga_dpba"]
]

fund = (
    income_use.merge(bs_use, on=["ts_code", "end_date"], suffixes=("_i", "_b"))
    .merge(cf_use, on=["ts_code", "end_date"], suffixes=("", "_c"))
)
# use the latest of the three ann_dates (conservative — wait until all 3 statements are out)
fund["ann_date"] = fund[["ann_date_i", "ann_date_b", "ann_date"]].max(axis=1)
fund = fund.drop(columns=[c for c in fund.columns if c.startswith("ann_date_")])
fund = fund.sort_values(["ts_code", "end_date"]).reset_index(drop=True)
log(f"fund merged: {len(fund)} rows, {fund['ts_code'].nunique()} stocks")


# -------- 4. TTM rollups (trailing 4 quarters per ts_code) --------
def ttm(series: pd.Series) -> pd.Series:
    """trailing 4-quarter sum; requires >=3 of 4 non-NaN"""
    return series.rolling(4, min_periods=3).sum()


def avg4(series: pd.Series) -> pd.Series:
    """trailing 4-quarter mean for stocks (typical for avg TA)"""
    return series.rolling(4, min_periods=3).mean()


fund = fund.sort_values(["ts_code", "end_date"])
g = fund.groupby("ts_code", group_keys=False)
fund["ni_ttm"] = g["n_income"].transform(ttm)
fund["cfo_ttm"] = g["n_cashflow_act"].transform(ttm)
fund["dep_ttm"] = g["depr_fa_coga_dpba"].transform(ttm)
fund["ta_avg"] = g["total_assets"].transform(avg4)
# working-capital accrual parts
fund["wc"] = (
    fund["accounts_receiv"].fillna(0) + fund["inventories"].fillna(0)
    - fund["accounts_pay"].fillna(0)
)
fund["delta_wc"] = g["wc"].transform(lambda s: s.diff(4))  # yoy change
# derived
fund["acc_ttm"] = (fund["ni_ttm"] - fund["cfo_ttm"]) / fund["ta_avg"]
fund["wca_bs"] = (fund["delta_wc"] - fund["dep_ttm"]) / fund["ta_avg"]
fund["cfo_over_absni"] = fund["cfo_ttm"] / (
    fund["ni_ttm"].abs() + 0.01 * fund["ta_avg"]
)
fund["cfo_q"] = fund["n_cashflow_act"] / fund["total_assets"]
fund["ni_q_ta"] = fund["n_income"] / fund["total_assets"]
# 8-quarter earnings vol
fund["ni_vol_8q"] = g["ni_q_ta"].transform(lambda s: s.rolling(8, min_periods=5).std())
# 12-quarter persistence of cfo vs lag4 cfo
fund["cfo_q_lag4"] = g["cfo_q"].transform(lambda s: s.shift(4))
fund["cfo_persist"] = g.apply(
    lambda df: df["cfo_q"].rolling(12, min_periods=6).corr(df["cfo_q_lag4"]),
    include_groups=False,
).reset_index(level=0, drop=True)
# acc yoy
fund["acc_ttm_lag4"] = g["acc_ttm"].transform(lambda s: s.shift(4))
fund["dacc_yoy"] = fund["acc_ttm"] - fund["acc_ttm_lag4"]
# stability weighted
fund["acc_over_nivol"] = fund["acc_ttm"] / (fund["ni_vol_8q"] + 1e-4)
# persist weighted
fund["acc_x_persist"] = fund["acc_ttm"] * fund["cfo_persist"]


# -------- 5. Forward-fill fundamentals to daily panel at ann_date + 1 trade day --------
log("pivoting daily panel (close, adj, mv)")
daily = daily.merge(adj, on=["ts_code", "trade_date"])
daily = daily.merge(db, on=["ts_code", "trade_date"], how="left")
daily["close_adj"] = daily["close"] * daily["adj_factor"]
daily = daily.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)

# Merge on stock meta and filter universe
daily = daily.merge(stock_meta, on="ts_code", how="left")
daily["days_listed"] = (daily["trade_date"] - daily["list_date"]).dt.days
univ_mask = (
    (~daily["is_financial"].fillna(True))
    & (~daily["is_st"].fillna(True))
    & (daily["days_listed"] >= 252)
    & daily["industry"].notna()
)
daily = daily[univ_mask].copy()
log(f"daily panel after universe filter: {len(daily)} rows, {daily['ts_code'].nunique()} stocks")


# per-stock forward-fill of fundamentals starting from ann_date + 1 trading day
log("merging fundamentals to daily via asof on ann_date")
fund_cols = [
    "acc_ttm", "wca_bs", "cfo_over_absni", "dacc_yoy",
    "acc_over_nivol", "acc_x_persist", "total_assets", "end_date",
]
fund_gated = fund.dropna(subset=["ann_date"]).copy()
fund_gated = fund_gated.sort_values(["ann_date", "ts_code"]).reset_index(drop=True)
daily = daily.sort_values(["trade_date", "ts_code"]).reset_index(drop=True)
merged = pd.merge_asof(
    daily,
    fund_gated[["ts_code", "ann_date"] + fund_cols],
    left_on="trade_date",
    right_on="ann_date",
    by="ts_code",
    direction="backward",
    allow_exact_matches=False,
)
# drop rows without any fundamental yet
merged = merged.dropna(subset=["acc_ttm"]).copy()
log(f"after ann_date gating: {len(merged)} rows")


# -------- 6. Cross-sectional ranks per trade_date (and industry-neutral variants) --------
log("computing cross-sectional ranks")


def cs_rank(df, col):
    return df.groupby("trade_date")[col].rank(pct=True) - 0.5


def group_rank(df, col, by_cols):
    g2 = df.groupby(["trade_date"] + by_cols)[col]
    return g2.rank(pct=True) - 0.5


# size bin within industry on each date
log("size bins by industry per date")
merged["log_mv"] = np.log(merged["total_mv"].clip(lower=1))
merged["size_bin"] = (
    merged.groupby(["trade_date", "industry"])["log_mv"].rank(pct=True)
)
merged["size_bin"] = pd.cut(
    merged["size_bin"].fillna(0.5),
    bins=[-0.01, 0.2, 0.4, 0.6, 0.8, 1.01],
    labels=["s1", "s2", "s3", "s4", "s5"],
)

# winsorize raw signals cross-sectionally at [0.01, 0.99]
RAW = ["acc_ttm", "wca_bs", "cfo_over_absni", "dacc_yoy", "acc_over_nivol", "acc_x_persist"]
for c in RAW:
    merged[c + "_wz"] = merged.groupby("trade_date")[c].transform(
        lambda s: s.clip(lower=s.quantile(0.01), upper=s.quantile(0.99))
    )

log("building alphas")
# sign convention: higher alpha == higher expected forward return
merged["alpha_01"] = -cs_rank(merged, "acc_ttm_wz")
merged["alpha_02"] = -cs_rank(merged, "wca_bs_wz")
merged["alpha_03"] = -group_rank(merged, "acc_ttm_wz", ["industry"])
merged["alpha_04"] = cs_rank(merged, "cfo_over_absni_wz")  # already high=good
merged["alpha_05"] = -cs_rank(merged, "dacc_yoy_wz")
merged["alpha_06"] = -cs_rank(merged, "acc_over_nivol_wz")
merged["alpha_07"] = -cs_rank(merged, "acc_x_persist_wz")
merged["alpha_08"] = -group_rank(merged, "acc_ttm_wz", ["industry", "size_bin"])

# -------- 7. Forward returns (T+1 to T+h adj close) --------
log("computing forward returns (delay=1)")
merged = merged.sort_values(["ts_code", "trade_date"])
for h in (1, 5, 20, 60):
    merged[f"fwd_ret_{h}"] = (
        merged.groupby("ts_code")["close_adj"]
        .transform(lambda s: s.shift(-1 - h) / s.shift(-1) - 1)
    )

# -------- 8. Save --------
keep = [
    "ts_code", "trade_date", "industry", "size_bin",
    "alpha_01", "alpha_02", "alpha_03", "alpha_04",
    "alpha_05", "alpha_06", "alpha_07", "alpha_08",
    "fwd_ret_1", "fwd_ret_5", "fwd_ret_20", "fwd_ret_60",
    "total_mv",
]
out = merged[keep].copy()
out.to_parquet(f"{CACHE}/panel.parquet", index=False)
log(f"saved panel: {len(out):,} rows, cols={list(out.columns)}")
log(f"date range: {out['trade_date'].min()} .. {out['trade_date'].max()}")
log(f"stocks: {out['ts_code'].nunique()}  industries: {out['industry'].nunique()}")
