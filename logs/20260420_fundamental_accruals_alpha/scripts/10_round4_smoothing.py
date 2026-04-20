"""
Round 4: Deployment robustness — signal smoothing, turnover control, regime blending.

All 8 variants start from the Round 3 winner `alpha_med_ind` (median-TTM,
industry-neutral Sloan accruals). They differ in post-processing of the signal
to improve after-cost Sharpe by reducing turnover, or by blending regimes.

Measuring turnover explicitly this round: for each variant at each rebalance,
fraction of Q5 or Q1 positions that change from prior rebalance. Cost is applied
at cost_bps * 2 * turnover (both sides of LS, pro-rata).

8 variants
----------
  v1  baseline       = alpha_med_ind                            (reference)
  v2  ema_20         = 20-day EMA of alpha_med_ind               (smooth)
  v3  ema_60         = 60-day EMA of alpha_med_ind               (heavier smooth)
  v4  ema_120        = 120-day EMA (quarterly rhythm)            (heaviest)
  v5  consensus_ind  = 0.5 * ind + 0.5 * ind_x_size               (regime blend)
  v6  sticky_band    = rebalance only if |Δrank| > 0.10           (dead band)
  v7  bi_monthly     = rebalance every 40 days (2x less)          (brute force)
  v8  horizon_blend  = rank(alpha20) + rank(alpha60)              (multi-horizon)

Same universe / period / delay / raw cost as Round 3.
"""
import os, sys, time
import numpy as np
import pandas as pd

CACHE = "/home/user/Factor_Zoo/.cache"
SESSION = "/home/user/Factor_Zoo/logs/20260420_fundamental_accruals_alpha"
OUT = f"{SESSION}/outputs"


def log(s): print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)


# ---- load R3 panel (has alpha_med_ind + alpha_med_indxsize + fwd returns) ----
log("loading panel_round3")
panel = pd.read_parquet(f"{CACHE}/panel_round3.parquet")
log(f"rows {len(panel):,}  stocks {panel.ts_code.nunique()}  dates {panel.trade_date.min().date()} .. {panel.trade_date.max().date()}")


# ---- per-stock EMA of the alpha signal ----
def ema_signal(df, col, span):
    df = df.sort_values(["ts_code", "trade_date"])
    return df.groupby("ts_code")[col].transform(lambda s: s.ewm(span=span, adjust=False).mean())


log("constructing smoothed variants v2-v4")
panel = panel.sort_values(["ts_code","trade_date"])
panel["v2_ema20"]  = ema_signal(panel, "alpha_med_ind", 20)
panel["v3_ema60"]  = ema_signal(panel, "alpha_med_ind", 60)
panel["v4_ema120"] = ema_signal(panel, "alpha_med_ind", 120)

log("v5 consensus_ind = 0.5*ind + 0.5*ind_x_size")
panel["v5_consensus"] = 0.5 * panel["alpha_med_ind"] + 0.5 * panel["alpha_med_indxsize"]

# v6 sticky: computed at portfolio-build time (position inertia), not as signal transform
# v7 bi-monthly: computed by sampling every 40 trade days
# v8 horizon-blend: need a 60-day horizon rank
# we approximate by z-scoring alpha_med_ind within trade_date at horizon 60 is the same
#   as the 20-horizon within-date rank, since the alpha doesn't change by horizon choice.
# Better: blend the alpha_med_ind with a lag-20 version (anticipating decay)
log("v8 horizon_blend = 0.5 * alpha(t) + 0.5 * alpha(t-20)")
panel["v8_horizon_blend"] = 0.5 * panel["alpha_med_ind"] + 0.5 * panel.groupby("ts_code")["alpha_med_ind"].shift(20)

# v1 = baseline reference
panel["v1_baseline"] = panel["alpha_med_ind"]


# ---- monthly-LS with explicit turnover tracking ----
def monthly_ls_with_turnover(df, col, cost_bps_per_side=10.0, step=20):
    """Returns port df + turnover series. Cost applied = cost_bps_per_side/1e4 * 2 * turnover_each_side."""
    dfa = df.dropna(subset=[col, "fwd_ret_20"]).copy()
    dates = np.sort(dfa["trade_date"].unique())
    reb = dates[::step]
    dfa = dfa[dfa["trade_date"].isin(reb)].copy()
    dfa["q"] = dfa.groupby("trade_date")[col].transform(
        lambda s: pd.qcut(s.rank(method="first"), 5, labels=False, duplicates="drop")
    )
    dfa = dfa.dropna(subset=["q"]).copy()
    dfa["q"] = dfa["q"].astype(int)
    # snapshot of Q5 and Q1 members at each rebalance
    q5_sets = {d: set(g["ts_code"]) for d, g in dfa[dfa["q"]==4].groupby("trade_date")}
    q1_sets = {d: set(g["ts_code"]) for d, g in dfa[dfa["q"]==0].groupby("trade_date")}
    # turnover = |A symmetric_diff B| / (|A|+|B|)
    turnover_rows = []
    reb_sorted = sorted(q5_sets.keys())
    for i, d in enumerate(reb_sorted):
        if i == 0:
            t5 = t1 = np.nan
        else:
            prev = reb_sorted[i-1]
            q5_p, q5_c = q5_sets[prev], q5_sets[d]
            q1_p, q1_c = q1_sets[prev], q1_sets[d]
            t5 = len(q5_p ^ q5_c) / max(1, len(q5_p) + len(q5_c))
            t1 = len(q1_p ^ q1_c) / max(1, len(q1_p) + len(q1_c))
        turnover_rows.append(dict(trade_date=d, tov_q5=t5, tov_q1=t1))
    tov = pd.DataFrame(turnover_rows).set_index("trade_date")

    port = dfa.groupby(["trade_date","q"])["fwd_ret_20"].mean().unstack("q")
    port.columns = [f"Q{int(c)+1}" for c in sorted(port.columns)]
    port = port.join(tov, how="left")
    port["LS"] = port["Q5"] - port["Q1"]
    # per-period cost = cost_bps/1e4 * (tov_q5 + tov_q1)   (LS is 2-sided; each side pays on its turnover)
    port["cost"] = cost_bps_per_side/1e4 * (port["tov_q5"].fillna(0) + port["tov_q1"].fillna(0))
    port["LS_net"] = port["LS"] - port["cost"]
    port["MKT_EW"] = port[["Q1","Q2","Q3","Q4","Q5"]].mean(axis=1)
    port["Q5_ex"]  = port["Q5"] - port["MKT_EW"]
    # Q5-only cost = 1-sided
    port["Q5_ex_net"] = port["Q5_ex"] - cost_bps_per_side/1e4 * port["tov_q5"].fillna(0)
    return port.sort_index()


def sticky_monthly_ls(df, col, band=0.10, cost_bps_per_side=10.0, step=20):
    """Rebalance only if |new_percentile_rank - old_percentile_rank| > band for a given stock.
    We simulate by carrying the prior rebalance's Q assignment for stocks whose new rank is
    within `band` of the prior rank (and the stock is still present)."""
    dfa = df.dropna(subset=[col, "fwd_ret_20"]).copy()
    dates = np.sort(dfa["trade_date"].unique())
    reb = dates[::step]
    dfa = dfa[dfa["trade_date"].isin(reb)].copy()
    dfa["rank"] = dfa.groupby("trade_date")[col].rank(pct=True)
    dfa = dfa.sort_values(["trade_date","ts_code"])

    prev_q = {}          # ts_code -> prior q (0..4)
    prev_rank = {}       # ts_code -> prior rank
    port_rows = []
    tov_rows = []
    q5_prev, q1_prev = set(), set()
    for d, sub in dfa.groupby("trade_date"):
        sub = sub.copy()
        # new raw q
        sub["q_raw"] = pd.qcut(sub[col].rank(method="first"), 5, labels=False, duplicates="drop")
        # sticky q: carry prior if |Δrank| <= band AND prior q exists
        def carry(row):
            ts = row["ts_code"]; new_rank = row["rank"]; new_q = row["q_raw"]
            if ts in prev_rank and abs(new_rank - prev_rank[ts]) <= band and ts in prev_q:
                return prev_q[ts]
            return new_q
        sub["q"] = sub.apply(carry, axis=1)
        sub = sub.dropna(subset=["q"]).copy()
        sub["q"] = sub["q"].astype(int)
        # record q5, q1 sets
        q5_now = set(sub[sub["q"]==4]["ts_code"])
        q1_now = set(sub[sub["q"]==0]["ts_code"])
        tov5 = np.nan if not q5_prev else len(q5_prev ^ q5_now)/max(1,len(q5_prev)+len(q5_now))
        tov1 = np.nan if not q1_prev else len(q1_prev ^ q1_now)/max(1,len(q1_prev)+len(q1_now))
        # portfolio returns
        r = sub.groupby("q")["fwd_ret_20"].mean().to_dict()
        port_rows.append(dict(trade_date=d,
            Q1=r.get(0,np.nan), Q2=r.get(1,np.nan), Q3=r.get(2,np.nan),
            Q4=r.get(3,np.nan), Q5=r.get(4,np.nan)))
        tov_rows.append(dict(trade_date=d, tov_q5=tov5, tov_q1=tov1))
        # update state
        prev_q = dict(zip(sub["ts_code"], sub["q"]))
        prev_rank = dict(zip(sub["ts_code"], sub["rank"]))
        q5_prev, q1_prev = q5_now, q1_now

    port = pd.DataFrame(port_rows).set_index("trade_date")
    tov = pd.DataFrame(tov_rows).set_index("trade_date")
    port = port.join(tov)
    port["LS"] = port["Q5"] - port["Q1"]
    port["cost"] = cost_bps_per_side/1e4 * (port["tov_q5"].fillna(0) + port["tov_q1"].fillna(0))
    port["LS_net"] = port["LS"] - port["cost"]
    port["MKT_EW"] = port[["Q1","Q2","Q3","Q4","Q5"]].mean(axis=1)
    port["Q5_ex"] = port["Q5"] - port["MKT_EW"]
    port["Q5_ex_net"] = port["Q5_ex"] - cost_bps_per_side/1e4 * port["tov_q5"].fillna(0)
    return port.sort_index()


def perf(r):
    r = r.dropna()
    if len(r)<2 or r.std()==0: return {}
    mu, sd = r.mean(), r.std()
    cum = (1+r).cumprod()
    return dict(
        n=int(len(r)),
        ann_ret=(1+mu)**12-1,
        ann_vol=sd*np.sqrt(12),
        sharpe=mu/sd*np.sqrt(12),
        max_dd=float((cum/cum.cummax()-1).min()),
        hit=float((r>0).mean()),
    )


def ic_stats(df, col, ret):
    s = df.dropna(subset=[col,ret]).groupby("trade_date").apply(
        lambda x: x[col].corr(x[ret], method="spearman"), include_groups=False
    ).dropna()
    if len(s) < 10: return dict(ic=np.nan, icir=np.nan, tstat=np.nan, n=len(s))
    return dict(ic=float(s.mean()), icir=float(s.mean()/s.std()),
                tstat=float(s.mean()/s.std()*np.sqrt(len(s))), n=int(len(s)))


log("evaluating 8 variants")
VARS = [
    ("v1_baseline",     "alpha_med_ind",      20, "monthly", None),
    ("v2_ema20",        "v2_ema20",           20, "monthly", None),
    ("v3_ema60",        "v3_ema60",           20, "monthly", None),
    ("v4_ema120",       "v4_ema120",          20, "monthly", None),
    ("v5_consensus",    "v5_consensus",       20, "monthly", None),
    ("v6_sticky_10pct", "alpha_med_ind",      20, "sticky",  0.10),
    ("v7_bimonthly",    "alpha_med_ind",      40, "monthly", None),
    ("v8_horizon_blend","v8_horizon_blend",   20, "monthly", None),
]

rows_full, rows_tvt, port_cache = [], [], {}
for name, col, step, mode, band in VARS:
    if mode == "sticky":
        port = sticky_monthly_ls(panel, col, band=band, cost_bps_per_side=10.0, step=step)
    else:
        port = monthly_ls_with_turnover(panel, col, cost_bps_per_side=10.0, step=step)
    port_cache[name] = port

    # IC on full panel where signal exists
    ic20 = ic_stats(panel, col, "fwd_ret_20") if col in panel.columns else dict(ic=np.nan, icir=np.nan, tstat=np.nan)
    ic60 = ic_stats(panel, col, "fwd_ret_60") if col in panel.columns else dict(ic=np.nan, icir=np.nan, tstat=np.nan)

    for label, s in [("LS_net", port["LS_net"]), ("LS_gross", port["LS"]),
                     ("Q5_ex_net", port["Q5_ex_net"]), ("Q5_ex", port["Q5_ex"])]:
        p = perf(s)
        if p:
            rows_full.append(dict(alpha=name, strategy=label, step_days=step,
                ic20=ic20["ic"], icir20=ic20["icir"], ic60=ic60["ic"], icir60=ic60["icir"],
                tov_q5_avg=float(port["tov_q5"].mean(skipna=True)) if "tov_q5" in port else np.nan,
                tov_q1_avg=float(port["tov_q1"].mean(skipna=True)) if "tov_q1" in port else np.nan,
                **p))

    # TVT breakdown
    port = port.copy()
    port["year"] = pd.to_datetime(port.index).year
    for split, y0, y1 in [("Train",2018,2021), ("Validate",2022,2023), ("Test",2024,2025), ("Full",2018,2025)]:
        sub = port[(port["year"]>=y0) & (port["year"]<=y1)]
        p_ls = perf(sub["LS_net"]); p_q5 = perf(sub["Q5_ex_net"])
        rows_tvt.append(dict(alpha=name, split=split, period=f"{y0}-{y1}",
            n=p_ls.get("n",0),
            ls_net_sharpe=p_ls.get("sharpe", np.nan),
            ls_net_ann_ret=p_ls.get("ann_ret", np.nan),
            ls_max_dd=p_ls.get("max_dd", np.nan),
            q5ex_net_ir=p_q5.get("sharpe", np.nan),
            q5ex_net_ann=p_q5.get("ann_ret", np.nan),
            q5ex_max_dd=p_q5.get("max_dd", np.nan),
            tov_q5_avg=float(sub["tov_q5"].mean(skipna=True)),
        ))


full = pd.DataFrame(rows_full).round(4)
tvt = pd.DataFrame(rows_tvt).round(4)
full.to_csv(f"{OUT}/ls_summary_batch_0004.csv", index=False)
tvt.to_csv(f"{OUT}/tvt_split_batch_0004.csv", index=False)

pd.options.display.width = 220
pd.options.display.float_format = "{:.3f}".format

log("\n=== Full window: LS_net by variant  (2018-2025) ===")
v = full[(full["strategy"]=="LS_net")]
log("\n" + v[["alpha","step_days","ic20","icir20","ann_ret","ann_vol","sharpe","max_dd","hit","tov_q5_avg","tov_q1_avg"]].to_string(index=False))

log("\n=== Full window: Q5_ex_net by variant (deployable) ===")
v = full[(full["strategy"]=="Q5_ex_net")]
log("\n" + v[["alpha","step_days","ic20","icir20","ann_ret","ann_vol","sharpe","max_dd","hit","tov_q5_avg"]].to_string(index=False))

log("\n=== TVT split: LS_net_sharpe ===")
log("\n" + tvt.pivot(index="alpha", columns="split", values="ls_net_sharpe").to_string())

log("\n=== TVT split: Q5ex_net_IR ===")
log("\n" + tvt.pivot(index="alpha", columns="split", values="q5ex_net_ir").to_string())

log("\n=== TVT split: avg Q5 turnover per rebalance ===")
log("\n" + tvt.pivot(index="alpha", columns="split", values="tov_q5_avg").to_string())

# save winner's per-rebalance
winner = full.loc[(full["strategy"]=="LS_net")].sort_values("sharpe", ascending=False).iloc[0]["alpha"]
log(f"\nfull-window winner on LS_net Sharpe: {winner}")
winner_q5 = full.loc[(full["strategy"]=="Q5_ex_net")].sort_values("sharpe", ascending=False).iloc[0]["alpha"]
log(f"full-window winner on Q5_ex_net IR:  {winner_q5}")
port_cache[winner].to_csv(f"{OUT}/round4_winner_port_{winner}.csv")
log(f"saved {OUT}/round4_winner_port_{winner}.csv")
