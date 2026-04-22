"""
Final placebo + audit block for the recommended winner B6_m4_K10_t8.
Produces:
  - outputs/final_b6_metrics.json (headline + per-year + audit + placebo)
  - outputs/final_b6_equity.csv
"""
import numpy as np, pandas as pd, time, json
from pathlib import Path

OUT = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs")
say = lambda s: print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)

W = pd.read_parquet(OUT / "industry_weekly.parquet").sort_values(["trade_week","industry_code"])
ret = W.pivot(index="trade_week", columns="industry_code", values="ret_w").sort_index()
turn = W.pivot(index="trade_week", columns="industry_code", values="turnover_mv_w").sort_index()
gross = 1.0 + ret.fillna(0); cum = gross.cumprod()
INDS = ret.columns.tolist()

def mom_W(W_): return cum / cum.shift(W_) - 1
def turn_avg(W_): return turn.rolling(W_, min_periods=max(2, W_//2)).mean()

def topn_weights(score, n=3):
    cols = score.columns
    w_mat = np.zeros_like(score.values, dtype=float)
    sv = score.values; rv = ret.values
    for t_idx in range(sv.shape[0]):
        s = sv[t_idx]; v = np.isfinite(s) & np.isfinite(rv[t_idx])
        if v.sum() < n: continue
        s_v = np.where(v, s, -np.inf)
        ix = np.argpartition(-s_v, n)[:n]
        w_mat[t_idx, ix] = 1.0/n
    return pd.DataFrame(w_mat, index=score.index, columns=cols)

def layered_select(mom_score, crowd_score, k=10, n=3):
    cols = mom_score.columns
    w_mat = np.zeros_like(mom_score.values, dtype=float)
    mv = mom_score.values
    cv = crowd_score.reindex(index=mom_score.index, columns=cols).values
    for t_idx in range(mv.shape[0]):
        m = mv[t_idx]; c = cv[t_idx]
        vm = np.isfinite(m)
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
    tov = (w_exec.fillna(0).diff().abs().sum(axis=1) / 2.0).fillna(0)
    cost = tov * (cost_bps / 1e4)
    return pnl_g - cost, tov

def perf(pnl):
    r = pnl.dropna(); yrs=len(r)/52.0
    ann = (1+r).prod()**(1/yrs)-1 if yrs>0 else np.nan
    vol = r.std()*np.sqrt(52); sh = ann/vol if vol>0 else np.nan
    eq = (1+r).cumprod(); dd = (eq/eq.cummax()-1).min()
    return {"ann_ret":float(ann),"vol":float(vol),"sharpe":float(sh),"max_dd":float(dd)}

def per_year(pnl):
    r = pnl.dropna(); r.index = pd.to_datetime(r.index); out=[]
    for yr, grp in r.groupby(r.index.year):
        if len(grp)<10: continue
        ann = (1+grp).prod()**(52/len(grp))-1; vol = grp.std()*np.sqrt(52)
        sh = ann/vol if vol>0 else np.nan
        eq=(1+grp).cumprod(); dd=(eq/eq.cummax()-1).min()
        out.append({"year":int(yr),"ann_ret":float(ann),"sharpe":float(sh),"max_dd":float(dd),"n":int(len(grp))})
    return out

# ---- B6: mom_4w layered top-10, within top-10 pick lowest turn_8w top-3 ----
mom4 = mom_W(4); t8 = turn_avg(8)
w = layered_select(mom4, t8, 10, 3)
pnl, tov = run_bt(w, cost_bps=5)
py = per_year(pnl)

# IC = Spearman between weekly score and next-week industry return
# use negative crowding as tie-breaker, mom as primary; for IC just use mom_4w as primary signal
from scipy.stats import spearmanr
ic_list = []
for t_idx in range(len(mom4)-1):
    s = mom4.iloc[t_idx].values
    r_next = ret.iloc[t_idx+1].values
    m = np.isfinite(s) & np.isfinite(r_next)
    if m.sum() < 10: continue
    rho, _ = spearmanr(s[m], r_next[m])
    ic_list.append(rho)
ic = np.mean(ic_list); icir = ic / (np.std(ic_list) + 1e-12)

# Per-year IC
ic_by_year = {}
idx = mom4.index[:-1]
for t_idx in range(len(idx)):
    yr = pd.Timestamp(idx[t_idx]).year
    ic_by_year.setdefault(yr, []).append(ic_list[t_idx] if t_idx < len(ic_list) else np.nan)
ic_year_out = {str(k): {"ic": float(np.nanmean(v)), "icir": float(np.nanmean(v) / (np.nanstd(v)+1e-12)), "n": int(len(v))}
               for k, v in ic_by_year.items()}

# ---- Placebo 200 trials (score permutation) ----
say("placebo 200 trials on B6…")
rng = np.random.default_rng(11)
sv_ref = mom4.values  # primary signal
null_sh = []; null_worst = []
for i in range(200):
    sv_perm = sv_ref.copy()
    for t_idx in range(sv_perm.shape[0]):
        row = sv_perm[t_idx].copy()
        m = np.isfinite(row)
        if m.sum() >= 2:
            row[m] = rng.permutation(row[m])
            sv_perm[t_idx] = row
    sp = pd.DataFrame(sv_perm, index=mom4.index, columns=mom4.columns)
    w_perm = layered_select(sp, t8, 10, 3)
    pnl_p, _ = run_bt(w_perm)
    null_sh.append(perf(pnl_p)["sharpe"])
    py_p = per_year(pnl_p)
    if py_p:
        null_worst.append(min([r["sharpe"] for r in py_p]))
null_sh = np.array(null_sh); null_worst = np.array(null_worst)
p_sh = float((null_sh >= perf(pnl)["sharpe"]).mean())
worst_ref = min([r["sharpe"] for r in py])
p_worst = float((null_worst >= worst_ref).mean())
say(f"  ref sharpe={perf(pnl)['sharpe']:.3f}  null mean={null_sh.mean():.3f}  p_sh={p_sh:.3f}")
say(f"  ref worst={worst_ref:.3f}  null mean={null_worst.mean():.3f}  p_worst={p_worst:.3f}")

# ---- Delay audit ----
say("delay audit…")
delay_sh = {}
for d in [0,1,2,3,4]:
    pnl_d = (w.shift(d+1) * ret).sum(axis=1) - (w.shift(d+1).fillna(0).diff().abs().sum(axis=1)/2 * 5e-4).fillna(0)
    delay_sh[d] = perf(pnl_d)["sharpe"]
print(" ", delay_sh)

# ---- Lookahead (cross-section permutation) ----
say("lookahead audit…")
ret_shuf = ret.copy().values.copy()
rng2 = np.random.default_rng(42)
for t_idx in range(ret_shuf.shape[0]):
    row = ret_shuf[t_idx].copy(); m = np.isfinite(row)
    if m.sum() >= 2:
        row[m] = rng2.permutation(row[m]); ret_shuf[t_idx] = row
rs = pd.DataFrame(ret_shuf, index=ret.index, columns=ret.columns)
pnl_la = (w.shift(1) * rs).sum(axis=1) - (tov * 5e-4)
la_sh = perf(pnl_la)["sharpe"]
# Bench for reference
valid = ret.notna()
bench = valid.div(valid.sum(axis=1), axis=0).fillna(0)
pnl_bench = (bench.shift(1) * ret).sum(axis=1)
bench_sh = perf(pnl_bench)["sharpe"]

# ---- Annual holdings composition (most frequent picks) ----
# count weeks each industry is held
held = (w > 0).sum(axis=0).sort_values(ascending=False)
name_map = W.drop_duplicates("industry_code").set_index("industry_code")["industry_name"].to_dict()
held_named = [{"code": k, "name": name_map.get(k, "?"), "weeks_held": int(v), "pct_weeks": float(v/len(w))}
              for k, v in held.items()]

metrics = {
    "spec": "B6_m4_K10_t8_top3",
    "formula": "Step1: rank by mom_4w, keep top-10. Step2: within top-10, rank by -turn_8w, long-only equal-weight top-3.",
    "sample": f"{str(ret.index.min())} → {str(ret.index.max())}",
    "n_weeks": int(ret.shape[0]),
    "headline": perf(pnl),
    "per_year": py,
    "ic": {"full_mean_ic": float(ic), "icir": float(icir), "per_year": ic_year_out},
    "audit": {
        "delay_sharpe": delay_sh,
        "lookahead_shuf_sharpe": float(la_sh),
        "bench_sharpe": float(bench_sh),
        "lookahead_pass": bool(abs(la_sh - bench_sh) < 0.15),
        "worst_year_pass_05": bool(worst_ref >= 0.5),
        "best_year_out": {
            "best_year": int(max(py, key=lambda r: r['sharpe'])['year']) if py else None,
            "sharpe_ex_best": float(
                ((pnl[pnl.index.year != max(py, key=lambda r: r['sharpe'])['year']]).mean()*52) /
                ((pnl[pnl.index.year != max(py, key=lambda r: r['sharpe'])['year']]).std()*np.sqrt(52))
                if py else np.nan
            ) if py else None,
        },
    },
    "placebo": {
        "n_trials": 200,
        "null_mean_sharpe": float(null_sh.mean()),
        "p_sharpe": p_sh,
        "null_mean_worst": float(null_worst.mean()),
        "p_worst_year": p_worst,
    },
    "holdings_top20": held_named[:20],
    "turnover_annual_oneway": float(tov.mean()*52),
    "cost_bps_per_side": 5,
}
with open(OUT/"final_b6_metrics.json", "w") as f:
    json.dump(metrics, f, indent=2, ensure_ascii=False)

# equity curve
eq = (1+pnl.dropna()).cumprod()
eq.index.name = "trade_week"
eq.to_frame("equity_B6").to_csv(OUT/"final_b6_equity.csv")
pnl.dropna().to_frame("pnl_net_B6").to_csv(OUT/"final_b6_pnl.csv")

say("[done]")
