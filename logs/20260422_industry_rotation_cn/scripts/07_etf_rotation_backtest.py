"""
Run industry-rotation strategy on the 34-ETF tradable universe.

Design:
 - Staggered join: each ETF enters cross-section only after ≥ 12 weeks of history
 - Sample: 2019-01 → 2026-04 (~378 weeks)
 - Rerun B6 (layered) and A7 (penalized) on ETF universe
 - Compare to SW L1 baseline
 - Extra: 9-group rotator using user's GROUPS taxonomy

Outputs:
  - outputs/etf_backtest_summary.csv
  - outputs/etf_b6_metrics.json
  - outputs/etf_per_year.csv
"""
import json, time
from pathlib import Path
import numpy as np, pandas as pd

OUT = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs")
say = lambda s: print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)

W = pd.read_parquet(OUT / "etf_weekly.parquet")
uni = pd.read_csv(OUT / "etf_universe.csv")
name2code = dict(zip(uni["name"], uni["ts_code"]))
code2name = dict(zip(uni["ts_code"], uni["name"]))
code2group = dict(zip(uni["ts_code"], uni["group"]))

# Start 2019-01
W["trade_week"] = pd.to_datetime(W["trade_week"])
W = W[W["trade_week"] >= "2019-01-01"].sort_values(["trade_week","ts_code"]).reset_index(drop=True)
CODES = sorted(W["ts_code"].unique())
say(f"ETFs in sample: {len(CODES)}, weeks {W['trade_week'].nunique()} ({W['trade_week'].min().date()} → {W['trade_week'].max().date()})")

# Pivot to wide
ret = W.pivot(index="trade_week", columns="ts_code", values="ret_w").sort_index()
turn = W.pivot(index="trade_week", columns="ts_code", values="turnover_w").sort_index()  # amount weekly avg
gross = 1.0 + ret.fillna(0)
cum = gross.cumprod()

# Compute listing-age mask: ETF is eligible only after 12 weeks of history
age = ret.notna().cumsum()  # weeks seen so far per ETF
eligible = age >= 12          # boolean T×N

say(f"average eligible ETFs per week (mid-sample):  {eligible.iloc[len(eligible)//2].sum()}")
say(f"eligible ETFs at start:  {eligible.iloc[10].sum()}")
say(f"eligible ETFs at end:    {eligible.iloc[-1].sum()}")

def mom_W(W_): return cum / cum.shift(W_) - 1
def turn_avg(W_): return turn.rolling(W_, min_periods=max(2, W_//2)).mean()
def zscore_cs(df):
    df = df.where(eligible)
    mu = df.mean(axis=1); sd = df.std(axis=1)
    return df.sub(mu, axis=0).div(sd, axis=0)
def breadth_series():
    ma20 = cum.rolling(20, min_periods=8).mean().where(eligible)
    n_e = eligible.sum(axis=1).replace(0, np.nan)
    return (cum > ma20).where(eligible).sum(axis=1) / n_e
def breadth_df():
    b = breadth_series()
    z = (b - b.rolling(52, min_periods=20).mean()) / b.rolling(52, min_periods=20).std()
    return pd.DataFrame({c: z for c in ret.columns})

def topn_weights(score, n=3):
    score = score.reindex(columns=ret.columns).astype(float)
    cols = score.columns
    w_mat = np.zeros(score.shape, dtype=float)
    sv = score.values.astype(float); rv = ret.values.astype(float); em = eligible.values.astype(bool)
    for t_idx in range(sv.shape[0]):
        s = sv[t_idx]
        v = np.isfinite(s) & np.isfinite(rv[t_idx]) & em[t_idx]
        if v.sum() < n: continue
        s_v = np.where(v, s, -np.inf)
        ix = np.argpartition(-s_v, n)[:n]
        w_mat[t_idx, ix] = 1.0/n
    return pd.DataFrame(w_mat, index=score.index, columns=cols)

def layered_select(mom_score, crowd_score, k=10, n=3):
    mom_score = mom_score.reindex(columns=ret.columns).astype(float)
    cols = mom_score.columns
    w_mat = np.zeros(mom_score.shape, dtype=float)
    mv = mom_score.values.astype(float)
    cv = crowd_score.reindex(index=mom_score.index, columns=cols).values.astype(float)
    em = eligible.values.astype(bool)
    for t_idx in range(mv.shape[0]):
        m = mv[t_idx]; c = cv[t_idx]; e = em[t_idx]
        vm = np.isfinite(m) & e
        if vm.sum() < k: continue
        m_v = np.where(vm, m, -np.inf)
        topk = np.argpartition(-m_v, k)[:k]
        c_top = c[topk]; vc = np.isfinite(c_top)
        if vc.sum() < n: continue
        c_top_v = np.where(vc, c_top, np.inf)
        sel = np.argpartition(c_top_v, n)[:n]
        w_mat[t_idx, topk[sel]] = 1.0/n
    return pd.DataFrame(w_mat, index=mom_score.index, columns=cols)

def run_bt(weights, cost_bps=5):
    w_exec = weights.shift(1)
    pnl_g = (w_exec * ret).sum(axis=1)
    tov = (w_exec.fillna(0).diff().abs().sum(axis=1)/2).fillna(0)
    cost = tov * (cost_bps/1e4)
    return pnl_g - cost, tov

def perf(pnl):
    r = pnl.dropna(); yrs = len(r)/52.0
    ann = (1+r).prod()**(1/yrs)-1 if yrs>0 else np.nan
    vol = r.std()*np.sqrt(52); sh = ann/vol if vol>0 else np.nan
    eq = (1+r).cumprod(); dd = (eq/eq.cummax()-1).min()
    return {"ann_ret":float(ann),"vol":float(vol),"sharpe":float(sh),"max_dd":float(dd)}

def per_year(pnl):
    r = pnl.dropna(); r.index = pd.to_datetime(r.index); rows=[]
    for yr, grp in r.groupby(r.index.year):
        if len(grp)<10: continue
        ann = (1+grp).prod()**(52/len(grp))-1; vol = grp.std()*np.sqrt(52)
        sh = ann/vol if vol>0 else np.nan
        eq=(1+grp).cumprod(); dd=(eq/eq.cummax()-1).min()
        rows.append({"year":int(yr),"ann_ret":float(ann),"sharpe":float(sh),"max_dd":float(dd),"n":int(len(grp))})
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)

# ---- Pre-compute signals ----
mom = {w_: mom_W(w_) for w_ in [1,2,4,8,12]}
t_avg = {w_: turn_avg(w_) for w_ in [2,4,8]}
bread = breadth_df()

# ---- Run 5 specs (re-run A/B winners + group rotator) ----
rows = []; eq_curves = {}

SPECS = [
    # A-family winners
    ("A7_lam10_m4_t4_b", lambda: topn_weights(zscore_cs(mom[4]) - 1.0*zscore_cs(t_avg[4]) + 0.3*bread, 3)),
    ("A2_lam10_m4_t4",   lambda: topn_weights(zscore_cs(mom[4]) - 1.0*zscore_cs(t_avg[4]), 3)),
    # B-family winners
    ("B6_m4_K10_t8",     lambda: layered_select(mom[4], t_avg[8], 10, 3)),
    ("B2_m4_K8_t4",      lambda: layered_select(mom[4], t_avg[4], 8, 3)),
    ("B1_m4_K10_t4",     lambda: layered_select(mom[4], t_avg[4], 10, 3)),
    # Pure momentum baseline (A8)
    ("A8_pure_m4",       lambda: topn_weights(zscore_cs(mom[4]), 3)),
    # C reversal control
    ("C1_rev1w",         lambda: topn_weights(-mom[1], 3)),
    # 9-group rotator (below, added later)
]

for name, fn in SPECS:
    w = fn()
    pnl, tov = run_bt(w)
    p = perf(pnl); py = per_year(pnl)
    worst = py["sharpe"].min() if len(py) else np.nan
    best_y = int(py.loc[py["sharpe"].idxmax(), "year"]) if len(py) else None
    r = pnl.dropna(); r.index = pd.to_datetime(r.index)
    r_no = r[r.index.year != best_y] if best_y else r
    sh_ex = (r_no.mean()*52)/(r_no.std()*np.sqrt(52)) if r_no.std()>0 else np.nan
    rows.append({**p, "spec":name, "worst_year":float(worst), "sharpe_ex_best":float(sh_ex),
                 "ann_tov":float(tov.mean()*52)})
    eq_curves[name] = (1+pnl.fillna(0)).cumprod()

# ---- 9-group rotator ----
say("[group rotator] computing group-level momentum…")
# For each week, compute group-level mom = weighted avg of eligible ETFs in group
group_ret = pd.DataFrame(index=ret.index, columns=list(set(uni["group"])))
for g in group_ret.columns:
    codes_g = uni[uni["group"]==g]["ts_code"].tolist()
    codes_g = [c for c in codes_g if c in ret.columns]
    valid = eligible[codes_g]
    n = valid.sum(axis=1).replace(0, np.nan)
    group_ret[g] = ret[codes_g].where(valid).mean(axis=1)
g_gross = 1+group_ret.fillna(0); g_cum = g_gross.cumprod()
g_mom4 = g_cum / g_cum.shift(4) - 1
# For each t: rank groups, pick top-3 groups; within each, pick 1 ETF with highest 4w mom
def group_rotator(top_g=3, per_g=1):
    cols = ret.columns
    w = pd.DataFrame(0.0, index=ret.index, columns=cols)
    for t_idx in range(len(ret)):
        t = ret.index[t_idx]
        gscores = g_mom4.iloc[t_idx].dropna()
        if len(gscores) < top_g: continue
        top_groups = gscores.nlargest(top_g).index.tolist()
        picks = []
        for g in top_groups:
            codes_g = [c for c in uni[uni["group"]==g]["ts_code"] if c in cols]
            # within group, pick by 4w mom, with eligibility
            s = mom[4].iloc[t_idx][codes_g].dropna()
            s = s[[c for c in s.index if eligible.iloc[t_idx][c]]]
            if len(s) < per_g: continue
            picks += s.nlargest(per_g).index.tolist()
        if not picks: continue
        nw = 1.0 / len(picks)
        for c in picks:
            w.iat[t_idx, w.columns.get_loc(c)] = nw
    return w

for (name, top_g, per_g) in [("G_top3_1each", 3, 1), ("G_top2_1each", 2, 1), ("G_top3_mom_within", 3, 1)]:
    w = group_rotator(top_g, per_g)
    pnl, tov = run_bt(w)
    p = perf(pnl); py = per_year(pnl)
    worst = py["sharpe"].min() if len(py) else np.nan
    best_y = int(py.loc[py["sharpe"].idxmax(), "year"]) if len(py) else None
    r = pnl.dropna(); r.index = pd.to_datetime(r.index)
    r_no = r[r.index.year != best_y] if best_y else r
    sh_ex = (r_no.mean()*52)/(r_no.std()*np.sqrt(52)) if r_no.std()>0 else np.nan
    rows.append({**p, "spec":name, "worst_year":float(worst), "sharpe_ex_best":float(sh_ex),
                 "ann_tov":float(tov.mean()*52)})
    eq_curves[name] = (1+pnl.fillna(0)).cumprod()

# ---- Bench (equal-weight all eligible ETFs) ----
# use inverse of eligible count for normalized weights
w_bench = eligible.astype(float).div(eligible.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
pnl_b, tov_b = run_bt(w_bench)
p_b = perf(pnl_b); py_b = per_year(pnl_b)
rows.append({**p_b, "spec":"ETF_EQW_BENCH", "worst_year":float(py_b["sharpe"].min() if len(py_b) else np.nan),
             "sharpe_ex_best": np.nan, "ann_tov":float(tov_b.mean()*52)})

df = pd.DataFrame(rows).sort_values("sharpe", ascending=False)
say("\n===== ETF UNIVERSE BACKTEST =====")
print(df[["spec","ann_ret","sharpe","max_dd","worst_year","sharpe_ex_best","ann_tov"]].to_string(index=False))
df.to_csv(OUT / "etf_backtest_summary.csv", index=False)

# ---- Per-year stats for top 3 specs ----
all_py = []
for name, fn in SPECS[:3] + [("G_top3_1each", lambda: group_rotator(3,1))]:
    w = fn()
    pnl, _ = run_bt(w)
    py = per_year(pnl); py["spec"] = name
    all_py.append(py)
say("\n===== PER-YEAR (top specs) =====")
py_df = pd.concat(all_py, ignore_index=True)
print(py_df.to_string(index=False))
py_df.to_csv(OUT / "etf_per_year_top.csv", index=False)

# ---- Top holdings (for winner) ----
winner_name, winner_fn = SPECS[2]  # B6
w = winner_fn()
held = (w > 0).sum(axis=0).sort_values(ascending=False)
held_named = pd.DataFrame({
    "ts_code": held.index,
    "etf_name": [code2name.get(c, "?") for c in held.index],
    "group": [code2group.get(c, "?") for c in held.index],
    "weeks_held": held.values,
    "pct_weeks": [v/len(w) for v in held.values],
}).sort_values("weeks_held", ascending=False).head(25)
say("\n===== TOP HOLDINGS (B6 on ETF universe) =====")
print(held_named.to_string(index=False))
held_named.to_csv(OUT/"etf_b6_holdings.csv", index=False)

# equity curves
curves = pd.concat([v.rename(k) for k,v in eq_curves.items()], axis=1)
curves.index.name = "trade_week"
curves.to_csv(OUT / "etf_equity_curves.csv")

say("[done]")
