"""
Round 2 batch_0002: 8 enhancement variants of alpha_03 (industry-neutral Sloan CFS).

All 8 variants share the same mechanism (accruals-based earnings quality, short high-accruals).
They differ in: winsorization, normalization style, TTM window, ensemble weighting, or
attribution-lever choice. The baseline alpha_03 is carried as variant 1 for comparison.
"""
import os, sys, time
import numpy as np
import pandas as pd

CACHE = "/home/user/Factor_Zoo/.cache"
SESSION = "/home/user/Factor_Zoo/logs/20260420_fundamental_accruals_alpha"
OUT = f"{SESSION}/outputs"


def log(s):
    print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)


# ---- load panel (has alpha_01..alpha_08 and fwd returns already) ----
log("loading existing panel")
panel = pd.read_parquet(f"{CACHE}/panel.parquet")
log(f"panel rows: {len(panel):,}")

# Also need the raw quarterly fundamentals for new constructions (8q TTM, etc.)
income = pd.read_parquet(f"{CACHE}/income.parquet")
bs = pd.read_parquet(f"{CACHE}/balancesheet.parquet")
cf = pd.read_parquet(f"{CACHE}/cashflow.parquet")
for d in (income, bs, cf):
    d["ann_date"] = pd.to_datetime(d["ann_date"], format="%Y%m%d", errors="coerce")
    d["end_date"] = pd.to_datetime(d["end_date"], format="%Y%m%d", errors="coerce")


# Rebuild the fund table with richer fields
log("rebuilding fund table with extended rollups")
f = (
    income[["ts_code", "ann_date", "end_date", "n_income"]]
    .merge(bs[["ts_code", "end_date", "total_assets"]], on=["ts_code", "end_date"])
    .merge(cf[["ts_code", "end_date", "n_cashflow_act"]], on=["ts_code", "end_date"])
    .sort_values(["ts_code", "end_date"])
)
g = f.groupby("ts_code", group_keys=False)
f["ni_ttm_4q"] = g["n_income"].transform(lambda s: s.rolling(4, min_periods=3).sum())
f["cfo_ttm_4q"] = g["n_cashflow_act"].transform(lambda s: s.rolling(4, min_periods=3).sum())
f["ta_avg_4q"] = g["total_assets"].transform(lambda s: s.rolling(4, min_periods=3).mean())
f["ni_ttm_8q"] = g["n_income"].transform(lambda s: s.rolling(8, min_periods=6).mean() * 4)
f["cfo_ttm_8q"] = g["n_cashflow_act"].transform(lambda s: s.rolling(8, min_periods=6).mean() * 4)
f["ta_avg_8q"] = g["total_assets"].transform(lambda s: s.rolling(8, min_periods=6).mean())
# median-TTM: robust to a single restatement
f["ni_med_4q"] = g["n_income"].transform(lambda s: s.rolling(4, min_periods=3).median() * 4)
f["cfo_med_4q"] = g["n_cashflow_act"].transform(lambda s: s.rolling(4, min_periods=3).median() * 4)

f["acc_4q"] = (f["ni_ttm_4q"] - f["cfo_ttm_4q"]) / f["ta_avg_4q"]
f["acc_8q"] = (f["ni_ttm_8q"] - f["cfo_ttm_8q"]) / f["ta_avg_8q"]
f["acc_med_4q"] = (f["ni_med_4q"] - f["cfo_med_4q"]) / f["ta_avg_4q"]

# scale by revenue (alternative denom)
inc_rev = income[["ts_code", "end_date", "revenue"]].drop_duplicates(["ts_code", "end_date"])
f = f.merge(inc_rev, on=["ts_code", "end_date"], how="left")
g = f.groupby("ts_code", group_keys=False)  # regroup after merge
f["rev_ttm_4q"] = g["revenue"].transform(lambda s: s.rolling(4, min_periods=3).sum())
f["acc_rev_4q"] = (f["ni_ttm_4q"] - f["cfo_ttm_4q"]) / f["rev_ttm_4q"].abs().clip(lower=1e6)

# earnings vol (quarterly NI/TA)
f["ni_q_ta"] = f["n_income"] / f["total_assets"]
f["ni_vol_8q"] = g["ni_q_ta"].transform(lambda s: s.rolling(8, min_periods=5).std())

# ann_date used = max of the three statements' ann_dates (same as Round 1)
f["ann_date_max"] = g["ann_date"].transform(lambda s: s)  # keep income ann_date (proxy)


# ---- build daily-level variants via merge_asof on ann_date ----
log("merge_asof new fund fields to panel dates")
f_gated = f.dropna(subset=["ann_date"]).copy()
f_gated = f_gated.sort_values(["ann_date", "ts_code"]).reset_index(drop=True)

panel = panel.sort_values(["trade_date", "ts_code"]).reset_index(drop=True)

NEW = ["acc_4q", "acc_8q", "acc_med_4q", "acc_rev_4q", "ni_vol_8q"]
panel = pd.merge_asof(
    panel,
    f_gated[["ts_code", "ann_date"] + NEW],
    left_on="trade_date",
    right_on="ann_date",
    by="ts_code",
    direction="backward",
    allow_exact_matches=False,
)


# ---- construct 8 variants (all industry-neutral by default) ----
log("constructing 8 Round-2 variants")

def cs_rank(df, col):
    return df.groupby("trade_date")[col].rank(pct=True) - 0.5

def group_rank(df, col, by):
    return df.groupby(["trade_date"] + by)[col].rank(pct=True) - 0.5

def cs_zscore(df, col):
    g2 = df.groupby("trade_date")[col]
    return (df[col] - g2.transform("mean")) / g2.transform("std").replace(0, 1)

def group_zscore(df, col, by):
    g2 = df.groupby(["trade_date"] + by)[col]
    return (df[col] - g2.transform("mean")) / g2.transform("std").replace(0, 1)


# v1: baseline alpha_03 (carry-over)
panel["alpha_v1"] = panel["alpha_03"]

# v2: tighter winsorize [0.05, 0.95]
panel["acc_4q_w05"] = panel.groupby("trade_date")["acc_4q"].transform(
    lambda s: s.clip(lower=s.quantile(0.05), upper=s.quantile(0.95))
)
panel["alpha_v2"] = -group_rank(panel, "acc_4q_w05", ["industry"])

# v3: industry-zscore (preserve magnitude info, not just rank)
panel["acc_4q_wz"] = panel.groupby("trade_date")["acc_4q"].transform(
    lambda s: s.clip(lower=s.quantile(0.01), upper=s.quantile(0.99))
)
panel["alpha_v3"] = -group_zscore(panel, "acc_4q_wz", ["industry"])

# v4: 8-quarter TTM (smoother)
panel["acc_8q_w"] = panel.groupby("trade_date")["acc_8q"].transform(
    lambda s: s.clip(lower=s.quantile(0.01), upper=s.quantile(0.99))
)
panel["alpha_v4"] = -group_rank(panel, "acc_8q_w", ["industry"])

# v5: median-TTM (robust to single-quarter restatement)
panel["acc_med_w"] = panel.groupby("trade_date")["acc_med_4q"].transform(
    lambda s: s.clip(lower=s.quantile(0.01), upper=s.quantile(0.99))
)
panel["alpha_v5"] = -group_rank(panel, "acc_med_w", ["industry"])

# v6: revenue-scaled accruals (alternative denom)
panel["acc_rev_w"] = panel.groupby("trade_date")["acc_rev_4q"].transform(
    lambda s: s.clip(lower=s.quantile(0.01), upper=s.quantile(0.99))
)
panel["alpha_v6"] = -group_rank(panel, "acc_rev_w", ["industry"])

# v7: stability-weighted industry-neutral (combines alpha_03 + alpha_06 idea, with industry filter)
panel["acc_stab"] = panel["acc_4q"] / (panel["ni_vol_8q"] + 1e-4)
panel["acc_stab_w"] = panel.groupby("trade_date")["acc_stab"].transform(
    lambda s: s.clip(lower=s.quantile(0.01), upper=s.quantile(0.99))
)
panel["alpha_v7"] = -group_rank(panel, "acc_stab_w", ["industry"])

# v8: ensemble of v1 (industry-neutral) and v7 (stability-weighted industry-neutral), 50-50
panel["alpha_v8"] = 0.5 * panel["alpha_v1"] + 0.5 * panel["alpha_v7"]


VARIANTS = [f"alpha_v{i}" for i in range(1, 9)]
log(f"variant non-null counts:")
for v in VARIANTS:
    log(f"  {v}: {panel[v].notna().sum():,}")


# ---- evaluate (IC + LS + audits) ----
def ic_summary(df, col, ret_col):
    ic = df.dropna(subset=[col, ret_col]).groupby("trade_date").apply(
        lambda x: x[col].corr(x[ret_col], method="spearman"),
        include_groups=False,
    ).dropna()
    if len(ic) < 10:
        return dict(ic_mean=np.nan, icir=np.nan, tstat=np.nan, n=len(ic))
    return dict(
        ic_mean=float(ic.mean()),
        icir=float(ic.mean() / ic.std()),
        tstat=float(ic.mean() / ic.std() * np.sqrt(len(ic))),
        n=int(len(ic)),
    )


log("IC table R2")
ic_rows = []
for v in VARIANTS:
    for h in (5, 20, 60):
        r = ic_summary(panel, v, f"fwd_ret_{h}")
        r.update(alpha=v, horizon=h)
        ic_rows.append(r)
ic_tbl = pd.DataFrame(ic_rows)[["alpha", "horizon", "ic_mean", "icir", "tstat", "n"]]
ic_tbl.to_csv(f"{OUT}/ic_table_batch_0002.csv", index=False)
log("\n" + ic_tbl.pivot(index="alpha", columns="horizon", values="ic_mean").round(4).to_string())
log("ICIR\n" + ic_tbl.pivot(index="alpha", columns="horizon", values="icir").round(3).to_string())


def monthly_ls(df, alpha_col, cost_bps=10.0):
    dfa = df.dropna(subset=[alpha_col, "fwd_ret_20"]).copy()
    all_dates = np.sort(dfa["trade_date"].unique())
    reb_dates = all_dates[::20]
    dfa = dfa[dfa["trade_date"].isin(reb_dates)].copy()
    dfa["q"] = dfa.groupby("trade_date")[alpha_col].transform(
        lambda s: pd.qcut(s.rank(method="first"), 5, labels=False, duplicates="drop")
    )
    dfa = dfa.dropna(subset=["q"])
    port = dfa.groupby(["trade_date", "q"])["fwd_ret_20"].mean().unstack("q")
    port.columns = [f"Q{int(c)+1}" for c in sorted(port.columns)]
    port["LS"] = port["Q5"] - port["Q1"]
    port["LS_net"] = port["LS"] - 2 * cost_bps / 1e4
    return port


def sharpe_annual(r):
    if len(r) < 4:
        return np.nan
    return float(r.mean() / r.std() * np.sqrt(12)) if r.std() > 0 else np.nan


log("LS + annual R2")
sum_rows = []
ann_rows = []
audit_rows = []
for v in VARIANTS:
    port = monthly_ls(panel, v)
    port["year"] = pd.to_datetime(port.index).year
    s_gross = sharpe_annual(port["LS"])
    s_net = sharpe_annual(port["LS_net"])
    # exclude partial 2025 from worst-year
    annual = port[port["year"] != 2025].groupby("year")["LS"].apply(
        lambda r: sharpe_annual(r) if len(r) >= 6 else np.nan
    ).dropna()
    worst = annual.min() if len(annual) else np.nan
    best = annual.max() if len(annual) else np.nan
    # best-year-out
    if len(annual) >= 2:
        best_year = annual.idxmax()
        port_no_best = port[port["year"] != best_year]
        s_no_best = sharpe_annual(port_no_best["LS"])
    else:
        s_no_best = np.nan
    kept = s_no_best / s_gross if s_gross and s_gross > 0 else np.nan
    cumret = (1 + port["LS"]).cumprod()
    dd = float((cumret / cumret.cummax() - 1).min())
    sum_rows.append(dict(
        alpha=v,
        ls_sharpe_gross=s_gross,
        ls_sharpe_net_10bps=s_net,
        worst_year_sharpe=worst,
        best_year_sharpe=best,
        no_best_year_sharpe=s_no_best,
        pct_kept_no_best=kept,
        max_dd_ls=dd,
        n_rebalances=int(len(port)),
    ))
    for y, ss in annual.items():
        ann_rows.append(dict(alpha=v, year=int(y), ls_sharpe=float(ss)))
    audit_rows.append(dict(
        alpha=v,
        worst_year_floor_pass=bool((worst or -1) >= 0.5),
        best_year_out_pass=bool(kept is not np.nan and (kept or 0) >= 0.5),
    ))

summary = pd.DataFrame(sum_rows)
annual_tbl = pd.DataFrame(ann_rows)
audit_tbl = pd.DataFrame(audit_rows)
summary.to_csv(f"{OUT}/ls_summary_batch_0002.csv", index=False)
annual_tbl.to_csv(f"{OUT}/ls_annual_batch_0002.csv", index=False)
audit_tbl.to_csv(f"{OUT}/audit_batch_0002.csv", index=False)

log("\n=== Summary ===")
pd.options.display.width = 200
pd.options.display.float_format = "{:.3f}".format
log("\n" + summary.to_string(index=False))
log("\n=== Annual ===")
log("\n" + annual_tbl.pivot(index="alpha", columns="year", values="ls_sharpe").round(2).to_string())
log("\n=== Audit ===")
log("\n" + audit_tbl.to_string(index=False))


# ---- save panel with R2 variants for reference (not to git) ----
keep_cols = ["ts_code", "trade_date", "industry", "fwd_ret_20"] + VARIANTS
panel[keep_cols].to_parquet(f"{CACHE}/panel_round2.parquet", index=False)
log("wrote panel_round2.parquet (cache, not in git)")
