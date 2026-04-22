"""
Agent 5 · Evaluator & Recorder
 - Rank 24 specs (3 batches)
 - Per-year performance of top winners
 - Mandatory audits: delay / lookahead / worst-year / best-year-out / placebo
 - Write alpha_ranking.md, round_0001.yml
"""
import os, time
from pathlib import Path
import numpy as np
import pandas as pd

OUT = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs")
say = lambda s: print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)

W = pd.read_parquet(OUT / "industry_weekly.parquet").sort_values(["trade_week","industry_code"])
INDS = sorted(W["industry_code"].unique())
ret = W.pivot(index="trade_week", columns="industry_code", values="ret_w").sort_index()
turn = W.pivot(index="trade_week", columns="industry_code", values="turnover_mv_w").sort_index()
gross = 1.0 + ret.fillna(0)
cum = gross.cumprod()
T, N = ret.shape

# --- helpers (match backtest) ---
def mom_W(W_): return cum / cum.shift(W_) - 1
def turn_avg(W_): return turn.rolling(W_, min_periods=max(2, W_//2)).mean()
def zscore_cs(df):
    mu = df.mean(axis=1); sd = df.std(axis=1)
    return df.sub(mu, axis=0).div(sd, axis=0)
def breadth():
    ma20 = cum.rolling(20, min_periods=8).mean()
    above = (cum > ma20).astype(float).mean(axis=1)
    z = (above - above.rolling(52, min_periods=20).mean()) / above.rolling(52, min_periods=20).std()
    return pd.DataFrame({c: z for c in ret.columns})

def topn_weights(score, n=3, long_only=True):
    cols = score.columns
    w_mat = np.zeros_like(score.values, dtype=float)
    sv = score.values; rv = ret.values
    for t_idx in range(sv.shape[0]):
        s = sv[t_idx]
        v = np.isfinite(s) & np.isfinite(rv[t_idx])
        if v.sum() < n: continue
        s_v = np.where(v, s, -np.inf)
        top_ix = np.argpartition(-s_v, n)[:n]
        w_mat[t_idx, top_ix] = 1.0/n
        if not long_only:
            s_v2 = np.where(v, s, np.inf)
            bot_ix = np.argpartition(s_v2, n)[:n]
            w_mat[t_idx, bot_ix] = -1.0/n
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
        topk_ix = np.argpartition(-m_v, k)[:k]
        c_top = c[topk_ix]
        vc = np.isfinite(c_top)
        if vc.sum() < n: continue
        c_top_v = np.where(vc, c_top, np.inf)
        sel = np.argpartition(c_top_v, n)[:n]
        w_mat[t_idx, topk_ix[sel]] = 1.0/n
    return pd.DataFrame(w_mat, index=mom_score.index, columns=cols)

def run_bt(weights, cost_bps=5):
    w_exec = weights.shift(1)
    pnl_g = (w_exec * ret).sum(axis=1)
    tov = (w_exec.fillna(0).diff().abs().sum(axis=1) / 2.0).fillna(0)
    cost = tov * (cost_bps / 1e4)
    pnl_n = pnl_g - cost
    return pnl_n, tov

def perf(pnl, label=""):
    r = pnl.dropna()
    yrs = len(r)/52.0
    ann = (1+r).prod()**(1/yrs) - 1 if yrs>0 else np.nan
    vol = r.std()*np.sqrt(52); sh = ann/vol if vol>0 else np.nan
    eq = (1+r).cumprod(); dd = (eq/eq.cummax()-1).min()
    return ann, vol, sh, dd

def per_year(pnl):
    r = pnl.dropna()
    r.index = pd.to_datetime(r.index)
    rows = []
    for yr, grp in r.groupby(r.index.year):
        if len(grp) < 10: continue
        ann = (1+grp).prod()**(52/len(grp)) - 1
        vol = grp.std()*np.sqrt(52)
        sh = ann/vol if vol>0 else np.nan
        eq = (1+grp).cumprod(); dd = (eq/eq.cummax()-1).min()
        rows.append({"year": int(yr), "ann_ret": ann, "vol": vol, "sharpe": sh, "max_dd": dd, "n_weeks": len(grp)})
    return pd.DataFrame(rows).sort_values("year")

# ----- Build top spec signals -----
mom = {w_: mom_W(w_) for w_ in [1,2,3,4,8,12]}
t_avg = {w_: turn_avg(w_) for w_ in [2,4,8]}
bread = breadth()

TOP_SPECS = {
    # 3 A winners + 3 B winners
    "A7_lam10_m4_t4_b": ("A", lambda: topn_weights(zscore_cs(mom[4]) - 1.0*zscore_cs(t_avg[4]) + 0.3*bread, 3)),
    "A2_lam10_m4_t4":   ("A", lambda: topn_weights(zscore_cs(mom[4]) - 1.0*zscore_cs(t_avg[4]), 3)),
    "A6_lam10_m4_t8":   ("A", lambda: topn_weights(zscore_cs(mom[4]) - 1.0*zscore_cs(t_avg[8]), 3)),
    "B2_m4_K8_t4":      ("B", lambda: layered_select(mom[4], t_avg[4], 8, 3)),
    "B6_m4_K10_t8":     ("B", lambda: layered_select(mom[4], t_avg[8], 10, 3)),
    "B1_m4_K10_t4":     ("B", lambda: layered_select(mom[4], t_avg[4], 10, 3)),
    # One C best for comparison
    "C1_rev1w":         ("C", lambda: topn_weights(-mom[1], 3)),
}

# ----- Per-year stats -----
say("\n===== PER-YEAR STATS (top candidates) =====")
year_dfs = {}
for name, (fam, fn) in TOP_SPECS.items():
    w = fn()
    pnl, tov = run_bt(w)
    py = per_year(pnl).assign(spec=name, family=fam)
    year_dfs[name] = py
    print(f"\n>>> {name} ({fam})")
    print(py[["year","ann_ret","sharpe","max_dd","n_weeks"]].to_string(index=False))
all_per_year = pd.concat(year_dfs.values())
all_per_year.to_csv(OUT / "per_year_top_specs.csv", index=False)

# ----- Audit: execution delay (sanity: shift weights by +2 instead of +1 should differ a lot) -----
say("\n===== AUDIT 1: execution delay =====")
pick = "A7_lam10_m4_t4_b"
w = TOP_SPECS[pick][1]()
for d in [0,1,2,3]:
    pnl_g = (w.shift(d+1) * ret).sum(axis=1)
    _, _, sh, _ = perf(pnl_g, f"delay={d}")
    print(f"  delay={d}: sharpe={sh:.3f}")

# ----- Audit 2: lookahead randomize next-bar returns -----
say("\n===== AUDIT 2: lookahead (randomize next-bar ret, should collapse) =====")
rng = np.random.default_rng(42)
ret_shuf = ret.copy()
ret_shuf.iloc[:] = rng.permutation(ret.values, axis=0)
w = TOP_SPECS[pick][1]()
pnl_g = (w.shift(1) * ret_shuf).sum(axis=1)
_,_,sh,_ = perf(pnl_g)
print(f"  ret rows shuffled in time: sharpe={sh:.3f} (should be near 0)")

# ----- Audit 3 & 4: worst-year, best-year-out =====
say("\n===== AUDIT 3 & 4 — worst-year ≥ 0.5 ; ex-best-year ≥ 50% =====")
audit_rows = []
for name, (fam, fn) in TOP_SPECS.items():
    w = fn()
    pnl, _ = run_bt(w)
    ann,_,sh_full,dd = perf(pnl)
    py = per_year(pnl)
    worst = py["sharpe"].min()
    # ex-best year
    best_y = py.loc[py["sharpe"].idxmax(), "year"]
    py_ex = py[py["year"] != best_y]
    # recompute full sharpe without best year
    r = pnl.dropna(); r.index = pd.to_datetime(r.index)
    r_no = r[r.index.year != best_y]
    sh_ex = (r_no.mean()*52)/(r_no.std()*np.sqrt(52)) if r_no.std()>0 else np.nan
    pass_wy = worst >= 0.5
    pass_bo = sh_ex >= 0.5 * sh_full
    audit_rows.append({"spec": name, "family": fam, "sharpe_full": sh_full,
                       "worst_year_sharpe": worst, "best_year": int(best_y),
                       "sharpe_ex_best": sh_ex, "pass_worst05": pass_wy,
                       "pass_bestout50pct": pass_bo})
audit_df = pd.DataFrame(audit_rows)
print(audit_df.to_string(index=False))
audit_df.to_csv(OUT / "audit_worst_best.csv", index=False)

# ----- Placebo: randomize SCORES cross-section 100x -----
say("\n===== AUDIT 5: placebo (100 trials, random cross-section of A7 score) =====")
pick_name = "A7_lam10_m4_t4_b"
score_ref = zscore_cs(mom[4]) - 1.0*zscore_cs(t_avg[4]) + 0.3*bread
ref_w = topn_weights(score_ref, 3)
ref_pnl, _ = run_bt(ref_w)
_,_,ref_sh,_ = perf(ref_pnl)
ref_py = per_year(ref_pnl); ref_worst = ref_py["sharpe"].min()
print(f"  reference: sharpe_full={ref_sh:.3f}  worst_year={ref_worst:.3f}")

rng = np.random.default_rng(7)
sh_null, wr_null = [], []
sv = score_ref.values
for i in range(100):
    sv_perm = sv.copy()
    for t_idx in range(sv.shape[0]):
        sv_perm[t_idx] = rng.permutation(sv[t_idx])
    sp = pd.DataFrame(sv_perm, index=score_ref.index, columns=score_ref.columns)
    w = topn_weights(sp, 3)
    pnl, _ = run_bt(w)
    _,_,sh,_ = perf(pnl)
    py = per_year(pnl)
    sh_null.append(sh); wr_null.append(py["sharpe"].min() if len(py) else np.nan)
sh_null = np.array(sh_null); wr_null = np.array([x for x in wr_null if np.isfinite(x)])
p_sh = (sh_null >= ref_sh).mean()
p_wr = (wr_null >= ref_worst).mean()
print(f"  placebo sharpe_full:   null mean={sh_null.mean():.3f}  p(null>=ref)={p_sh:.3f}")
print(f"  placebo worst-year:    null mean={wr_null.mean():.3f}  p(null>=ref)={p_wr:.3f}")

pd.DataFrame({"null_sharpe": sh_null}).to_csv(OUT/"placebo_sharpe.csv", index=False)
pd.DataFrame({"null_worst": wr_null}).to_csv(OUT/"placebo_worst.csv", index=False)

say("[done] Agent 5 audit complete.")
