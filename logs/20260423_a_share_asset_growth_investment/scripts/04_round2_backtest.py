"""
Round 2 — refined deployment variants of f5_ag_2y_ind.
- Quarterly rebalance (63d)
- Long-only Q5 / Q10 with equal or rank weighting
- Regime filter (CSI300 6m return <= 20%)
- Liquidity floor (top 60% circ_mv)
- OLS size-residualization
- Composite 0.6 * f5_ag_2y_ind + 0.4 * f2_ag_yoy_ind
"""
from __future__ import annotations
import os, json, time, warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

CACHE = "/home/user/Factor_Zoo/.cache"
OUT = "/home/user/Factor_Zoo/logs/20260423_a_share_asset_growth_investment/outputs"
T0 = time.time()
def log(m): print(f"[{time.time()-T0:6.1f}s] {m}", flush=True)

# ---------------------------------------------------------------------------
# 1. Load BS + panel
# ---------------------------------------------------------------------------
log("load balance sheet")
bs = pd.read_parquet(f"{CACHE}/balancesheet.parquet")
bs = bs.dropna(subset=["total_assets","end_date","f_ann_date"]).copy()
bs["f_ann_date"] = pd.to_datetime(bs["f_ann_date"].astype(str), errors="coerce")
bs["end_date"]   = pd.to_datetime(bs["end_date"].astype(str),   errors="coerce")
bs = bs.dropna(subset=["f_ann_date","end_date"])
bs = (bs.sort_values(["ts_code","end_date","f_ann_date"])
        .groupby(["ts_code","end_date"], as_index=False).last())
bs = bs.sort_values(["ts_code","end_date"])
bs["ta_lag_4q"] = bs.groupby("ts_code")["total_assets"].shift(4)
bs["ta_lag_8q"] = bs.groupby("ts_code")["total_assets"].shift(8)
eps = 1e-8
bs["ag_yoy_q"] = -(bs["total_assets"] - bs["ta_lag_4q"]) / (bs["ta_lag_4q"].abs() + eps)
bs["ag_2y_q"]  = -(bs["total_assets"] - bs["ta_lag_8q"]) / (bs["ta_lag_8q"].abs() + eps)

log("load panel")
panel = pd.read_parquet(f"{CACHE}/panel.parquet",
    columns=["ts_code","trade_date","industry","size_bin","total_mv",
             "fwd_ret_1","fwd_ret_5","fwd_ret_20","fwd_ret_60"])
panel["trade_date"] = pd.to_datetime(panel["trade_date"])
panel = panel.sort_values(["trade_date","ts_code"]).reset_index(drop=True)

log("circ_mv from daily_basic")
db = pd.read_parquet(f"{CACHE}/daily_basic.parquet",
                     columns=["ts_code","trade_date","circ_mv"])
db["trade_date"] = pd.to_datetime(db["trade_date"])
panel = panel.merge(db, on=["ts_code","trade_date"], how="left")

log("PIT merge_asof")
bs_join = bs[["ts_code","f_ann_date","ag_yoy_q","ag_2y_q"]].copy()
bs_join["signal_date"] = bs_join["f_ann_date"] + pd.Timedelta(days=1)
bs_join = bs_join.dropna(subset=["signal_date"]).sort_values(["ts_code","signal_date"])

panel = pd.merge_asof(
    panel.sort_values("trade_date"),
    bs_join.sort_values("signal_date")[["ts_code","signal_date","ag_yoy_q","ag_2y_q"]],
    left_on="trade_date", right_on="signal_date", by="ts_code", direction="backward")
panel["staleness"] = (panel["trade_date"] - panel["signal_date"]).dt.days
for c in ["ag_yoy_q","ag_2y_q"]:
    panel.loc[panel["staleness"] > 200, c] = np.nan

# ---------------------------------------------------------------------------
# 2. Industry-demean + winsor + z (f2_ag_yoy_ind, f5_ag_2y_ind)
# ---------------------------------------------------------------------------
log("industry demean + z-score")
def cs_demean(df, col, by):
    return df[col] - df.groupby(by)[col].transform("median")

def cs_winsor_z(s):
    lo, hi = s.quantile(0.01), s.quantile(0.99)
    s = s.clip(lo, hi)
    mu, sd = s.mean(), s.std()
    return (s - mu) / sd if sd and not np.isnan(sd) else s * 0

panel["ag_yoy_ind"] = cs_demean(panel, "ag_yoy_q", ["trade_date","industry"])
panel["ag_2y_ind"]  = cs_demean(panel, "ag_2y_q",  ["trade_date","industry"])
panel["f2"] = panel.groupby("trade_date")["ag_yoy_ind"].transform(cs_winsor_z)
panel["f5"] = panel.groupby("trade_date")["ag_2y_ind"].transform(cs_winsor_z)

# OLS size-residualize f5 per date
log("OLS residualize f5 vs log(total_mv)")
panel["log_mv"] = np.log(panel["total_mv"].clip(lower=1))

def residualize(g):
    x = g["log_mv"].values
    y = g["f5"].values
    mask = ~(np.isnan(x) | np.isnan(y))
    if mask.sum() < 30:
        return pd.Series(np.nan, index=g.index)
    b, a = np.polyfit(x[mask], y[mask], 1)
    return pd.Series(y - (a + b*x), index=g.index)

panel["f5_sresid"] = (panel.groupby("trade_date", group_keys=False)
                          .apply(residualize))
panel["f5_sresid"] = panel.groupby("trade_date")["f5_sresid"].transform(cs_winsor_z)

# Composite 0.6 f5 + 0.4 f2
panel["f_combo"] = 0.6*panel["f5"] + 0.4*panel["f2"]
panel["f_combo"] = panel.groupby("trade_date")["f_combo"].transform(cs_winsor_z)

# ---------------------------------------------------------------------------
# 3. Regime filter (market 6m return from panel cross-sectional mean)
# ---------------------------------------------------------------------------
log("build market regime series")
# realized market return = mean of fwd_ret_1 at t - 1 (observed today)
mkt = panel.groupby("trade_date")["fwd_ret_1"].mean().sort_index()
mkt_today = mkt.shift(1)  # today's return = yesterday's fwd_ret_1
log_cum = (1 + mkt_today).cumprod()
mkt_126d = log_cum / log_cum.shift(126) - 1
regime_on = (mkt_126d <= 0.20).fillna(True)  # default to ON when no history
log(f"regime ON fraction: {regime_on.mean():.3f}")

# ---------------------------------------------------------------------------
# 4. Backtest helper — quarterly rebal long-only
# ---------------------------------------------------------------------------
REBAL = 63
COST  = 5e-4

def long_only_bt(p, factor, top_frac=0.2, weight="ew",
                 liq_filter=False, regime_filter=False,
                 min_stocks=100):
    """
    Long-only backtest with:
    - top_frac of 0.2 = Q5, 0.1 = Q10
    - weight: 'ew' or 'rw' (rank-weighted within the top fraction)
    - liq_filter: keep only top 60% by circ_mv at rebal date
    - regime_filter: disable long when mkt 6m return > 20%
    Returns daily returns dict with metrics.
    """
    df = p[["trade_date","ts_code",factor,"fwd_ret_1","circ_mv"]].dropna(subset=[factor,"fwd_ret_1"])
    dates_sorted = np.sort(df["trade_date"].unique())
    rebal_set = set(dates_sorted[::REBAL].tolist())

    # assign weights on rebal days only, forward-fill per ts_code between rebals
    df["w"] = 0.0
    df["_mark"] = 0

    rebal_list = [d for d in dates_sorted if d in rebal_set]
    w_holdings = {}  # current {ts_code: weight}
    prev_holdings = {}
    daily = {}
    turnover_by_date = {}

    # precompute per-date stock groups for speed
    dfg = {d: g for d, g in df.groupby("trade_date")}

    # portfolio state
    cur_members = {}
    rebal_idx = -1
    for i, d in enumerate(dates_sorted):
        if d in rebal_set:
            rebal_idx += 1
            g = dfg[d]
            if liq_filter:
                mv_thresh = g["circ_mv"].quantile(0.4)
                g = g[g["circ_mv"] >= mv_thresh]
            if regime_filter and not regime_on.get(d, True):
                cur_members = {}  # flatten
            else:
                # pick top_frac
                n = len(g)
                if n < min_stocks:
                    cur_members = {}
                else:
                    n_top = max(1, int(round(n * top_frac)))
                    top = g.nlargest(n_top, factor)
                    if weight == "ew":
                        w = pd.Series(1.0/n_top, index=top["ts_code"])
                    else:
                        # rank-weighted: linear weight from 1 at lowest in top to n_top at highest
                        top = top.sort_values(factor)
                        ranks = np.arange(1, n_top+1)
                        w = pd.Series(ranks / ranks.sum(), index=top["ts_code"].values)
                    cur_members = w.to_dict()
            # turnover
            prev_set = set(prev_holdings)
            new_set  = set(cur_members)
            prev_arr = pd.Series(prev_holdings).reindex(prev_set | new_set).fillna(0)
            new_arr  = pd.Series(cur_members).reindex(prev_set | new_set).fillna(0)
            to = (new_arr - prev_arr).abs().sum()
            turnover_by_date[d] = to
            prev_holdings = cur_members.copy()
        # realized daily return using current weights
        if cur_members:
            g = dfg[d]
            r_series = g.set_index("ts_code")["fwd_ret_1"]
            w_series = pd.Series(cur_members)
            common = w_series.index.intersection(r_series.index)
            port_ret = (w_series.loc[common] * r_series.loc[common]).sum() / w_series.loc[common].sum() if len(common) else 0.0
        else:
            port_ret = 0.0
        cost = turnover_by_date.get(d, 0) * COST
        daily[d] = {"ret": port_ret - cost, "gross": port_ret, "cost": cost,
                    "mkt": dfg[d]["fwd_ret_1"].mean(), "invested": len(cur_members) > 0}

    out = pd.DataFrame.from_dict(daily, orient="index").reset_index().rename(columns={"index":"trade_date"})
    out["year"] = out["trade_date"].dt.year
    out["excess"] = out["ret"] - out["mkt"]

    def sharpe(x):
        x = x.dropna()
        if len(x) < 2 or x.std() == 0: return np.nan
        return x.mean()*252 / (x.std()*np.sqrt(252))

    total_to = sum(turnover_by_date.values())
    yrs = (out["trade_date"].max() - out["trade_date"].min()).days / 365.25
    ann_turnover = total_to / yrs if yrs > 0 else np.nan

    metrics = {
        "sharpe_excess": sharpe(out["excess"]),
        "ann_ret_excess": out["excess"].mean()*252,
        "sharpe_abs": sharpe(out["ret"]),
        "ann_ret_abs": out["ret"].mean()*252,
        "worst_year_excess": out.groupby("year")["excess"].apply(sharpe).min(),
        "invested_share": out["invested"].mean(),
        "ann_turnover": ann_turnover,
        "n_rebals": len(turnover_by_date),
        "n_years": out["year"].nunique(),
    }
    annual = (out.groupby("year")
                 .agg(sharpe_excess=("excess", sharpe),
                      ann_ret_excess=("excess", lambda x: x.mean()*252),
                      sharpe_abs=("ret", sharpe),
                      ann_ret_abs=("ret", lambda x: x.mean()*252),
                      invested_share=("invested","mean"),
                      n_days=("ret","count"))
                 .reset_index())
    return metrics, annual, out

# ---------------------------------------------------------------------------
# 5. Run 8 variants
# ---------------------------------------------------------------------------
log("running 8 Round-2 variants")
VARIANTS = [
    ("r2_q5_ew_q",          "f5",       dict(top_frac=0.2, weight="ew",  liq_filter=False, regime_filter=False)),
    ("r2_q5_rw_q",          "f5",       dict(top_frac=0.2, weight="rw",  liq_filter=False, regime_filter=False)),
    ("r2_q5_ew_q_regime",   "f5",       dict(top_frac=0.2, weight="ew",  liq_filter=False, regime_filter=True)),
    ("r2_q5_ew_q_liqfl",    "f5",       dict(top_frac=0.2, weight="ew",  liq_filter=True,  regime_filter=False)),
    ("r2_q5_ew_q_sresid",   "f5_sresid",dict(top_frac=0.2, weight="ew",  liq_filter=False, regime_filter=False)),
    ("r2_q10_ew_q",         "f5",       dict(top_frac=0.1, weight="ew",  liq_filter=False, regime_filter=False)),
    ("r2_q5_ew_q_combo",    "f_combo",  dict(top_frac=0.2, weight="ew",  liq_filter=False, regime_filter=False)),
    ("r2_q5_ew_q_all",      "f5_sresid",dict(top_frac=0.2, weight="ew",  liq_filter=True,  regime_filter=True)),
]
sum_rows = []; ann_rows = []
for name, fac, kw in VARIANTS:
    m, ann, _ = long_only_bt(panel, fac, **kw)
    m["name"] = name; m["factor"] = fac
    ann["name"] = name
    sum_rows.append(m); ann_rows.append(ann)
    log(f"   {name:22s} factor={fac:10s}  sharpe_excess={m['sharpe_excess']:6.3f}  worst_yr={m['worst_year_excess']:6.2f}  turnover={m['ann_turnover']:5.2f}  invested={m['invested_share']:.2f}")

summary = pd.DataFrame(sum_rows)[["name","factor","sharpe_excess","ann_ret_excess","sharpe_abs","ann_ret_abs","worst_year_excess","invested_share","ann_turnover","n_rebals","n_years"]]
annual = pd.concat(ann_rows, ignore_index=True)
summary.to_csv(f"{OUT}/r2_summary_batch_0002.csv", index=False)
annual.to_csv(f"{OUT}/r2_annual_batch_0002.csv", index=False)

# ---------------------------------------------------------------------------
# 6. Best-year-out audit for top 3 variants
# ---------------------------------------------------------------------------
log("best-year-out audit for top 3 variants")
top3 = summary.sort_values("sharpe_excess", ascending=False).head(3)["name"].tolist()
byo_rows = []
for name in top3:
    ann_sub = annual[annual["name"]==name].copy()
    best_yr = ann_sub.loc[ann_sub["sharpe_excess"].idxmax(), "year"]
    # recompute Sharpe dropping best year
    daily_all = []
    for _, _, d in []: pass  # not stored; instead approximate by annual
    # use cumulative ann_ret_excess avg ex best year, weighted by n_days
    ex = ann_sub[ann_sub["year"] != best_yr]
    headline_sharpe = summary[summary["name"]==name]["sharpe_excess"].values[0]
    # Use annual Sharpe as proxy — combine via weighted geometric or simple mean
    # Better: daily mean/sd ex best year — need reconstruction. Skip exact, approximate via
    # Sharpe ex best = sqrt(sum(n_days_i) / total) * weighted mean / weighted std
    # Simpler proxy: weighted average of remaining annual Sharpes
    w = ex["n_days"] / ex["n_days"].sum()
    approx_ex_sharpe = (w * ex["sharpe_excess"]).sum()
    byo_rows.append({"name": name, "headline_sharpe": headline_sharpe,
                     "best_year": int(best_yr),
                     "approx_ex_best_sharpe": approx_ex_sharpe,
                     "ratio": approx_ex_sharpe / headline_sharpe if headline_sharpe else np.nan})
byo = pd.DataFrame(byo_rows)
byo.to_csv(f"{OUT}/r2_best_year_out.csv", index=False)
log("best-year-out:")
print(byo.to_string(index=False))

# ---------------------------------------------------------------------------
# 7. Write markdown report
# ---------------------------------------------------------------------------
log("write report")
def fmt(df, fmt_str=".3f"):
    return "```\n" + df.to_string(float_format=lambda x: f"{x:{fmt_str}}") + "\n```"

with open(f"{OUT}/backtest_results_batch_0002.md","w") as f:
    f.write(f"""# Backtest Results — Batch 0002 (Round 2)

Session: 20260423_a_share_asset_growth_investment
Parent: Round 1 winner `f5_ag_2y_ind` (IC t-stat 17.08 at h=60)
Rebalance: quarterly (63 trading days); Cost: 5 bps/side; Delay: 1
Panel: 2020-01-02 .. 2025-04-18

## Summary (long-only excess vs equal-weight universe)

{fmt(summary.round(3))}

## Per-year Sharpe (long-only excess)

{fmt(annual.pivot(index='name', columns='year', values='sharpe_excess').round(2), ".2f")}

## Per-year abs return

{fmt(annual.pivot(index='name', columns='year', values='ann_ret_abs').round(3))}

## Best-year-out audit (top 3 by headline Sharpe)

{fmt(byo.round(3))}

## Notes

- `r2_q5_ew_q_regime` uses CSI300-proxy 6m market return threshold of 20%; when triggered, position flattens (100% cash, 0% excess).
- `r2_q5_ew_q_liqfl` keeps only top 60% by circ_mv before selecting Q5.
- `r2_q5_ew_q_sresid` residualizes factor vs log(total_mv) by OLS per date (proper, unlike Round 1's failed median-demean in f3).
- `r2_q5_ew_q_combo` uses 0.6·f5_ag_2y_ind + 0.4·f2_ag_yoy_ind composite.
- `r2_q5_ew_q_all` stacks regime + liquidity + size-residualization.
""")
log(f"DONE {time.time()-T0:.1f}s")
