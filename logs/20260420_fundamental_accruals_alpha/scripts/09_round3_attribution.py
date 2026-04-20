"""
Round 3: attribution decomposition on full 2018-2025 window.

2 x 4 factorial on the accruals mechanism:
    TTM type:      {sum_4q, median_4q}
    Neutralization:{none, size, industry, industry_x_size}
-> 8 alphas in one batch (Rule of 8 + one mechanism preserved).

Sign: all flipped so higher = higher expected return.
Window: 2018-01-02 .. 2025-04-18 (extended from Round 2's 2020-2025).
"""
import os, sys, time
import numpy as np
import pandas as pd
import tushare as ts

CACHE = "/home/user/Factor_Zoo/.cache"
SESSION = "/home/user/Factor_Zoo/logs/20260420_fundamental_accruals_alpha"
OUT = f"{SESSION}/outputs"


def log(s):
    print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)


log("loading caches")
income = pd.read_parquet(f"{CACHE}/income.parquet")
bs = pd.read_parquet(f"{CACHE}/balancesheet.parquet")
cf = pd.read_parquet(f"{CACHE}/cashflow.parquet")
daily = pd.read_parquet(f"{CACHE}/daily.parquet")
adj = pd.read_parquet(f"{CACHE}/adj_factor.parquet")
db = pd.read_parquet(f"{CACHE}/daily_basic.parquet")
pro = ts.pro_api(os.environ["TUSHARE_TOKEN"])
basic = pro.stock_basic(exchange="", list_status="L", fields="ts_code,name,industry,list_date")
log(f"daily rows: {len(daily):,}  date range {daily.trade_date.min()} .. {daily.trade_date.max()}")

# ---- universe filter ----
EXCLUDED = {"银行", "全国地产", "区域地产", "房产服务", "保险", "证券", "多元金融", "期货"}
basic["list_date"] = pd.to_datetime(basic["list_date"], format="%Y%m%d")
basic["is_financial"] = basic["industry"].isin(EXCLUDED)
basic["is_st"] = basic["name"].str.contains("ST", na=False)
meta = basic[["ts_code","industry","list_date","is_financial","is_st"]]

# ---- fundamentals rebuild ----
log("rebuilding fund with both sum-TTM and median-TTM")
for d in (income, bs, cf):
    d["ann_date"] = pd.to_datetime(d["ann_date"], format="%Y%m%d", errors="coerce")
    d["end_date"] = pd.to_datetime(d["end_date"], format="%Y%m%d", errors="coerce")
f = (
    income[["ts_code","ann_date","end_date","n_income"]]
    .merge(bs[["ts_code","end_date","total_assets"]], on=["ts_code","end_date"])
    .merge(cf[["ts_code","end_date","n_cashflow_act"]], on=["ts_code","end_date"])
    .sort_values(["ts_code","end_date"])
)
g = f.groupby("ts_code", group_keys=False)
f["ni_sum"]  = g["n_income"].transform(lambda s: s.rolling(4, min_periods=3).sum())
f["cfo_sum"] = g["n_cashflow_act"].transform(lambda s: s.rolling(4, min_periods=3).sum())
f["ni_med"]  = g["n_income"].transform(lambda s: s.rolling(4, min_periods=3).median() * 4)
f["cfo_med"] = g["n_cashflow_act"].transform(lambda s: s.rolling(4, min_periods=3).median() * 4)
f["ta_avg"]  = g["total_assets"].transform(lambda s: s.rolling(4, min_periods=3).mean())
f["acc_sum"] = (f["ni_sum"]  - f["cfo_sum"])  / f["ta_avg"]
f["acc_med"] = (f["ni_med"]  - f["cfo_med"])  / f["ta_avg"]

# ---- daily panel + classic merges ----
log("building daily panel with adj, mv, meta")
daily = daily.merge(adj,  on=["ts_code","trade_date"])
daily = daily.merge(db,   on=["ts_code","trade_date"], how="left")
daily["close_adj"] = daily["close"] * daily["adj_factor"]
daily = daily.merge(meta, on="ts_code", how="left")
daily["days_listed"] = (daily["trade_date"] - daily["list_date"]).dt.days
daily = daily[
    (~daily["is_financial"].fillna(True))
    & (~daily["is_st"].fillna(True))
    & (daily["days_listed"] >= 252)
    & daily["industry"].notna()
].copy()
daily = daily.sort_values(["trade_date","ts_code"]).reset_index(drop=True)
log(f"universe-filtered daily rows: {len(daily):,}  stocks: {daily.ts_code.nunique()}")

# forward returns
daily = daily.sort_values(["ts_code","trade_date"])
for h in (20, 60):
    daily[f"fwd_ret_{h}"] = daily.groupby("ts_code")["close_adj"].transform(
        lambda s: s.shift(-1-h) / s.shift(-1) - 1
    )

# ann_date merge
log("merge_asof fund to daily via ann_date")
f_gated = f.dropna(subset=["ann_date"]).sort_values(["ann_date","ts_code"]).reset_index(drop=True)
daily = daily.sort_values(["trade_date","ts_code"]).reset_index(drop=True)
panel = pd.merge_asof(
    daily,
    f_gated[["ts_code","ann_date","acc_sum","acc_med"]],
    left_on="trade_date", right_on="ann_date", by="ts_code",
    direction="backward", allow_exact_matches=False,
)
panel = panel.dropna(subset=["acc_sum","acc_med"]).copy()
log(f"post-gating rows: {len(panel):,}")

# size bins within industry per date
log("size_bin + winsorize")
panel["log_mv"] = np.log(panel["total_mv"].clip(lower=1))
panel["size_bin"] = (
    panel.groupby(["trade_date","industry"])["log_mv"].rank(pct=True)
).fillna(0.5)
panel["size_bin"] = pd.cut(panel["size_bin"], bins=[-0.01,0.2,0.4,0.6,0.8,1.01], labels=["s1","s2","s3","s4","s5"])
panel["size5_global"] = panel.groupby("trade_date")["log_mv"].rank(pct=True)
panel["size5_global"] = pd.cut(panel["size5_global"], bins=[-0.01,0.2,0.4,0.6,0.8,1.01], labels=["s1","s2","s3","s4","s5"])

for col in ("acc_sum","acc_med"):
    panel[col+"_wz"] = panel.groupby("trade_date")[col].transform(
        lambda s: s.clip(lower=s.quantile(0.01), upper=s.quantile(0.99))
    )

# ---- 8 attribution variants ----
log("building 8 attribution variants (2 TTM x 4 neutralization)")
def cs_rank(df, col):
    return df.groupby("trade_date")[col].rank(pct=True) - 0.5
def grp_rank(df, col, by):
    return df.groupby(["trade_date"] + list(by))[col].rank(pct=True) - 0.5

# sum-TTM  (R1 alpha_03 family)
panel["alpha_sum_none"]    = -cs_rank(panel, "acc_sum_wz")
panel["alpha_sum_size"]    = -grp_rank(panel, "acc_sum_wz", ["size5_global"])
panel["alpha_sum_ind"]     = -grp_rank(panel, "acc_sum_wz", ["industry"])
panel["alpha_sum_indxsize"]= -grp_rank(panel, "acc_sum_wz", ["industry","size_bin"])
# median-TTM  (R2 alpha_v5 family)
panel["alpha_med_none"]    = -cs_rank(panel, "acc_med_wz")
panel["alpha_med_size"]    = -grp_rank(panel, "acc_med_wz", ["size5_global"])
panel["alpha_med_ind"]     = -grp_rank(panel, "acc_med_wz", ["industry"])           # = new alpha_v5 on extended window
panel["alpha_med_indxsize"]= -grp_rank(panel, "acc_med_wz", ["industry","size_bin"])

VARIANTS = [c for c in panel.columns if c.startswith("alpha_")]
log(f"variants: {VARIANTS}")

# ---- metrics ----
def ic_summary(df, col, ret_col):
    s = df.dropna(subset=[col, ret_col]).groupby("trade_date").apply(
        lambda x: x[col].corr(x[ret_col], method="spearman"),
        include_groups=False,
    ).dropna()
    if len(s) < 10:
        return dict(ic_mean=np.nan, icir=np.nan, tstat=np.nan, n=len(s))
    return dict(ic_mean=float(s.mean()), icir=float(s.mean()/s.std()),
                tstat=float(s.mean()/s.std()*np.sqrt(len(s))), n=int(len(s)))


def monthly_ls(df, col, cost_bps=10.0):
    dfa = df.dropna(subset=[col, "fwd_ret_20"]).copy()
    dates = np.sort(dfa["trade_date"].unique())
    reb = dates[::20]
    dfa = dfa[dfa["trade_date"].isin(reb)].copy()
    dfa["q"] = dfa.groupby("trade_date")[col].transform(
        lambda s: pd.qcut(s.rank(method="first"), 5, labels=False, duplicates="drop")
    )
    dfa = dfa.dropna(subset=["q"])
    port = dfa.groupby(["trade_date","q"])["fwd_ret_20"].mean().unstack("q")
    port.columns = [f"Q{int(c)+1}" for c in sorted(port.columns)]
    port["LS"] = port["Q5"] - port["Q1"]
    port["LS_net"] = port["LS"] - 2 * cost_bps / 1e4
    port["MKT_EW"] = port[["Q1","Q2","Q3","Q4","Q5"]].mean(axis=1)
    port["Q5ex"] = port["Q5"] - port["MKT_EW"]
    return port


def sharpe_m(r):
    r = r.dropna()
    if len(r) < 4 or r.std() == 0:
        return np.nan
    return float(r.mean()/r.std()*np.sqrt(12))


log("IC + LS + Q5ex tables")
ic_rows, sum_rows, ann_rows = [], [], []
for v in VARIANTS:
    for h in (20, 60):
        r = ic_summary(panel, v, f"fwd_ret_{h}")
        r.update(alpha=v, horizon=h)
        ic_rows.append(r)
    port = monthly_ls(panel, v)
    port["year"] = pd.to_datetime(port.index).year
    # exclude partial 2025
    annual = port[port["year"] != 2025].groupby("year").agg(
        LS_mean=("LS","mean"), LS_std=("LS","std"),
        Q5ex_mean=("Q5ex","mean"), Q5ex_std=("Q5ex","std"),
        n=("LS","size"),
    )
    annual["LS_sharpe"]   = annual["LS_mean"]/annual["LS_std"]*np.sqrt(12)
    annual["Q5ex_ir"]     = annual["Q5ex_mean"]/annual["Q5ex_std"]*np.sqrt(12)
    annual["LS_ann_ret"]  = (1 + annual["LS_mean"])**12 - 1
    annual["Q5ex_ann"]    = (1 + annual["Q5ex_mean"])**12 - 1
    worst = annual["LS_sharpe"].min()
    best  = annual["LS_sharpe"].max()
    cum   = (1 + port["LS"]).cumprod()
    dd    = float((cum/cum.cummax() - 1).min())
    s_gross_all = sharpe_m(port["LS"])
    s_net_all   = sharpe_m(port["LS_net"])
    q5ex_ir_all = sharpe_m(port["Q5ex"])
    # no-best-year
    if len(annual) >= 2:
        best_year = annual["LS_sharpe"].idxmax()
        s_no_best = sharpe_m(port[port["year"] != best_year]["LS"])
    else:
        s_no_best = np.nan
    sum_rows.append(dict(
        alpha=v,
        ls_sharpe_gross=s_gross_all,
        ls_sharpe_net=s_net_all,
        ls_ann_ret_gross=(1 + port["LS"].mean())**12 - 1,
        ls_ann_vol=port["LS"].std()*np.sqrt(12),
        q5ex_ir=q5ex_ir_all,
        q5ex_ann=(1 + port["Q5ex"].mean())**12 - 1,
        worst_year_sharpe=float(worst) if pd.notna(worst) else np.nan,
        best_year_sharpe=float(best) if pd.notna(best) else np.nan,
        no_best_year_sharpe=s_no_best,
        pct_kept_no_best=(s_no_best/s_gross_all) if (s_gross_all and s_gross_all>0) else np.nan,
        max_dd=dd,
        n_rebalances=int(len(port)),
    ))
    for y, row in annual.iterrows():
        ann_rows.append(dict(alpha=v, year=int(y), **row.round(4).to_dict()))

ic_tbl = pd.DataFrame(ic_rows)
ls_sum = pd.DataFrame(sum_rows)
ann_tbl = pd.DataFrame(ann_rows)
ic_tbl.to_csv(f"{OUT}/ic_table_batch_0003.csv", index=False)
ls_sum.to_csv(f"{OUT}/ls_summary_batch_0003.csv", index=False)
ann_tbl.to_csv(f"{OUT}/ls_annual_batch_0003.csv", index=False)

pd.options.display.width = 220
pd.options.display.float_format = "{:.3f}".format
log("\n=== IC (pivot) ===\n" + ic_tbl.pivot(index="alpha", columns="horizon", values="ic_mean").round(4).to_string())
log("\n=== ICIR (pivot) ===\n" + ic_tbl.pivot(index="alpha", columns="horizon", values="icir").round(3).to_string())
log("\n=== LS summary ===\n" + ls_sum.to_string(index=False))
log("\n=== Annual LS Sharpe ===\n" + ann_tbl.pivot(index="alpha", columns="year", values="LS_sharpe").round(2).to_string())
log("\n=== Annual Q5 excess IR ===\n" + ann_tbl.pivot(index="alpha", columns="year", values="Q5ex_ir").round(2).to_string())

# look-ahead numeric audit on the winner (median+ind) on the extended window
log("\nshuffle test on alpha_med_ind (extended window)")
rng = np.random.default_rng(0)
panel["fwd_shuf"] = panel.groupby("trade_date")["fwd_ret_20"].transform(
    lambda s: pd.Series(rng.permutation(s.values), index=s.index)
)
clean = ic_summary(panel, "alpha_med_ind", "fwd_ret_20")
shuf  = ic_summary(panel, "alpha_med_ind", "fwd_shuf")
log(f"alpha_med_ind clean IC={clean['ic_mean']:.4f}  shuffled IC={shuf['ic_mean']:.6f}  ratio={clean['ic_mean']/shuf['ic_mean'] if shuf['ic_mean'] else 999:.0f}x")

# save panel for optional re-use
panel_out = panel[["ts_code","trade_date","industry","size_bin","size5_global","fwd_ret_20","fwd_ret_60"] + VARIANTS]
panel_out.to_parquet(f"{CACHE}/panel_round3.parquet", index=False)
log(f"wrote panel_round3 (rows {len(panel_out):,})")
