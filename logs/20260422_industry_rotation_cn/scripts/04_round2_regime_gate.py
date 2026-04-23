"""
Round 2: add market-regime gate to rescue 2018/2022 worst-year.

Hypothesis: top winners (A7, B6) have strong 2019-2026 performance but fail
worst-year 0.5 floor purely because of 2018 bear market (when all 31 industries
tanked together). A breadth-based regime gate that switches to cash when market
breadth collapses should lift 2018 sharpe ≥ 0.5 while keeping 95% of the alpha.

Also: fix lookahead audit to permute returns CROSS-SECTION at each time
(not rows across time).
"""
import numpy as np, pandas as pd, time
from pathlib import Path

OUT = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs")
say = lambda s: print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)

W = pd.read_parquet(OUT / "industry_weekly.parquet").sort_values(["trade_week","industry_code"])
ret = W.pivot(index="trade_week", columns="industry_code", values="ret_w").sort_index()
turn = W.pivot(index="trade_week", columns="industry_code", values="turnover_mv_w").sort_index()
gross = 1.0 + ret.fillna(0)
cum = gross.cumprod()

def mom_W(W_): return cum / cum.shift(W_) - 1
def turn_avg(W_): return turn.rolling(W_, min_periods=max(2, W_//2)).mean()
def zscore_cs(df):
    mu = df.mean(axis=1); sd = df.std(axis=1)
    return df.sub(mu, axis=0).div(sd, axis=0)
def breadth_series():
    ma20 = cum.rolling(20, min_periods=8).mean()
    return (cum > ma20).astype(float).mean(axis=1)  # 0..1 series

def topn_weights(score, n=3):
    cols = score.columns
    w_mat = np.zeros_like(score.values, dtype=float)
    sv = score.values; rv = ret.values
    for t_idx in range(sv.shape[0]):
        s = sv[t_idx]; v = np.isfinite(s) & np.isfinite(rv[t_idx])
        if v.sum() < n: continue
        s_v = np.where(v, s, -np.inf)
        top_ix = np.argpartition(-s_v, n)[:n]
        w_mat[t_idx, top_ix] = 1.0/n
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

def apply_gate(weights, gate_mask, fallback="cash", bench_w=None):
    """gate_mask: bool series T. True = risk-on (hold alpha), False = risk-off (fallback)."""
    w = weights.copy()
    off = ~gate_mask.reindex(w.index).fillna(False)
    if fallback == "cash":
        w.loc[off] = 0.0
    elif fallback == "bench":
        # equal-weight 31 industries where ret is valid
        valid = ret.notna()
        bench = valid.div(valid.sum(axis=1), axis=0).fillna(0)
        w.loc[off] = bench.loc[off].values
    return w

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
    return {"ann_ret":ann, "vol":vol, "sharpe":sh, "max_dd":dd}

def per_year(pnl):
    r = pnl.dropna(); r.index = pd.to_datetime(r.index)
    rows=[]
    for yr, grp in r.groupby(r.index.year):
        if len(grp)<10: continue
        ann = (1+grp).prod()**(52/len(grp))-1
        vol = grp.std()*np.sqrt(52)
        sh = ann/vol if vol>0 else np.nan
        eq = (1+grp).cumprod(); dd = (eq/eq.cummax()-1).min()
        rows.append({"year":int(yr),"ann_ret":ann,"sharpe":sh,"max_dd":dd,"n":len(grp)})
    return pd.DataFrame(rows).sort_values("year")

# ---- Build base signals ----
mom = {w_: mom_W(w_) for w_ in [1,2,3,4,8,12]}
t_avg = {w_: turn_avg(w_) for w_ in [2,4,8]}
BR = breadth_series()

# breadth z-score DataFrame for A7
bz_mat = (BR - BR.rolling(52, min_periods=20).mean()) / BR.rolling(52, min_periods=20).std()
breadth_df = pd.DataFrame({c: bz_mat for c in ret.columns})

BASE_SPECS = {
    "A7_base": lambda: topn_weights(zscore_cs(mom[4]) - 1.0*zscore_cs(t_avg[4]) + 0.3*breadth_df, 3),
    "A2_base": lambda: topn_weights(zscore_cs(mom[4]) - 1.0*zscore_cs(t_avg[4]), 3),
    "B6_base": lambda: layered_select(mom[4], t_avg[8], 10, 3),
    "B2_base": lambda: layered_select(mom[4], t_avg[4], 8, 3),
}

# ---- Define gates ----
# 1. breadth absolute: %above_ma20 > threshold
# 2. breadth z (centered): z > threshold
# 3. slow moving average of cum (50w)
def mkt_ma50():
    mkt_cum = cum.mean(axis=1)
    ma = mkt_cum.rolling(50, min_periods=20).mean()
    return mkt_cum > ma

GATES = {
    "breadth_gt30":  (BR > 0.30),
    "breadth_gt40":  (BR > 0.40),
    "breadth_gt50":  (BR > 0.50),
    "breadth_z_gt0": (bz_mat > 0),
    "mkt_above_ma50": mkt_ma50(),
    "none": pd.Series(True, index=ret.index),
}

# ---- Grid: base × gate × fallback ----
rows = []
for base_name, make_w in BASE_SPECS.items():
    base_w = make_w()
    for gate_name, gate_mask in GATES.items():
        for fb in ["cash", "bench"]:
            w_g = apply_gate(base_w, gate_mask, fallback=fb)
            pnl, tov = run_bt(w_g)
            p = perf(pnl)
            py = per_year(pnl)
            worst = py["sharpe"].min() if len(py) else np.nan
            y2018 = py[py["year"]==2018]["sharpe"].iloc[0] if (py["year"]==2018).any() else np.nan
            # ex-best
            best_y = int(py.loc[py["sharpe"].idxmax(), "year"]) if len(py) else None
            r = pnl.dropna(); r.index = pd.to_datetime(r.index)
            r_no = r[r.index.year != best_y]
            sh_ex = (r_no.mean()*52)/(r_no.std()*np.sqrt(52)) if r_no.std()>0 else np.nan
            rows.append({
                "base": base_name, "gate": gate_name, "fallback": fb,
                "sharpe": p["sharpe"], "ann_ret": p["ann_ret"], "max_dd": p["max_dd"],
                "worst_year": worst, "sharpe_2018": y2018,
                "sharpe_ex_best": sh_ex,
                "pass_worst05": worst >= 0.5,
                "pass_bestout50": sh_ex >= 0.5 * p["sharpe"],
                "ann_tov": tov.mean()*52,
            })
df = pd.DataFrame(rows).sort_values("sharpe", ascending=False)
df.to_csv(OUT/"round2_gate_grid.csv", index=False)
say("\n===== Round 2 — base × gate × fallback =====")
print(df.to_string(index=False))

say("\n===== Passers (worst_year>=0.5 AND bestout>=50% AND sharpe>=1.0) =====")
passers = df[(df["pass_worst05"]) & (df["pass_bestout50"]) & (df["sharpe"]>=1.0)]
print(passers.to_string(index=False))
passers.to_csv(OUT/"round2_passers.csv", index=False)

# ---- Corrected lookahead audit: cross-section permutation per time ----
say("\n===== Lookahead audit (corrected: permute CROSS-SECTION) =====")
rng = np.random.default_rng(42)
base_w = BASE_SPECS["A7_base"]()
ret_shuf = ret.copy().values.copy()
for t_idx in range(ret_shuf.shape[0]):
    row = ret_shuf[t_idx].copy()
    m = np.isfinite(row)
    if m.sum() >= 2:
        row[m] = rng.permutation(row[m])
        ret_shuf[t_idx] = row
ret_shuf = pd.DataFrame(ret_shuf, index=ret.index, columns=ret.columns)
# recompute pnl
w_exec = base_w.shift(1)
pnl_g = (w_exec * ret_shuf).sum(axis=1)
_,_,sh_shuf,_ = perf(pnl_g).values() if hasattr(perf(pnl_g), 'values') else (None,None,perf(pnl_g)["sharpe"],None)
print(f"  cross-section shuffled ret: sharpe={perf(pnl_g)['sharpe']:.3f} (should ≈ 0)")

say("[done] round 2 complete")
