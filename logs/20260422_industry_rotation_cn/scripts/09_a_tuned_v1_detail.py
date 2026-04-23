"""
Detailed IS/OOS analysis + audit on the tuned winner.

Winning config (A_tuned_v1):
  mom_w=4, turn_w=4, lambda=1.5, mu=0.3, top_n=4
  gate = cum-mean > 50w MA   (cash when off)
  vol_target = 0.15 annual   (scale-down only, no leverage)
  rebalance_w = 1            (weekly)
  delay = 1, cost = 5 bps/side
"""
import json, time
from pathlib import Path
import numpy as np, pandas as pd

OUT = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs")
say = lambda s: print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)

W = pd.read_parquet(OUT / "etf_weekly.parquet")
uni = pd.read_csv(OUT / "etf_universe.csv")
code2name = dict(zip(uni["ts_code"], uni["name"]))
code2group = dict(zip(uni["ts_code"], uni["group"]))

W["trade_week"] = pd.to_datetime(W["trade_week"])
W = W[W["trade_week"] >= "2019-01-01"].sort_values(["trade_week","ts_code"]).reset_index(drop=True)
ret = W.pivot(index="trade_week", columns="ts_code", values="ret_w").sort_index()
turn = W.pivot(index="trade_week", columns="ts_code", values="turnover_w").sort_index()
gross = 1 + ret.fillna(0); cum = gross.cumprod()
age = ret.notna().cumsum(); elig = age >= 12

SPLIT = pd.Timestamp("2024-01-01")
IS_MASK = ret.index < SPLIT
OOS_MASK = ret.index >= SPLIT

def zscore_cs(df):
    df = df.where(elig); mu=df.mean(axis=1); sd=df.std(axis=1)
    return df.sub(mu, axis=0).div(sd, axis=0)

mom4 = cum / cum.shift(4) - 1
turn4 = turn.rolling(4, min_periods=2).mean()
br_s = ((cum > cum.rolling(20, min_periods=8).mean()).where(elig).sum(axis=1) /
        elig.sum(axis=1).replace(0, np.nan))
br_z = (br_s - br_s.rolling(52, min_periods=20).mean()) / br_s.rolling(52, min_periods=20).std()
bread_df = pd.DataFrame({c: br_z for c in ret.columns})

mkt_cum = cum.mean(axis=1)
gate = (mkt_cum > mkt_cum.rolling(50, min_periods=25).mean())

# ---- Signal and weights ----
score = zscore_cs(mom4) - 1.5*zscore_cs(turn4) + 0.3*bread_df
cols = ret.columns
w_mat = np.zeros(score.shape, dtype=float)
sv = score.values.astype(float); rv = ret.values.astype(float); em = elig.values.astype(bool)
for t_idx in range(sv.shape[0]):
    s = sv[t_idx]; v = np.isfinite(s) & np.isfinite(rv[t_idx]) & em[t_idx]
    if v.sum() < 4: continue
    s_v = np.where(v, s, -np.inf)
    ix = np.argpartition(-s_v, 4)[:4]
    w_mat[t_idx, ix] = 0.25
w_base = pd.DataFrame(w_mat, index=score.index, columns=cols)

# apply gate (cash when off)
off = ~gate.reindex(w_base.index).fillna(False)
w_gated = w_base.copy(); w_gated.loc[off] = 0.0

# apply vol target 15%
def run_bt(weights, cost_bps=5):
    w_exec = weights.shift(1)
    pnl_g = (w_exec * ret).sum(axis=1)
    tov = (w_exec.fillna(0).diff().abs().sum(axis=1)/2).fillna(0)
    cost = tov * (cost_bps/1e4)
    return pnl_g - cost, tov

pnl_raw = (w_gated.shift(1) * ret).sum(axis=1)
rv_26w = pnl_raw.rolling(26, min_periods=8).std() * np.sqrt(52)
scale = (0.15 / rv_26w).clip(upper=1.0).fillna(0.0)
w_final = w_gated.mul(scale.reindex(w_gated.index), axis=0)

pnl_net, tov_ser = run_bt(w_final)

def perf(pnl, mask=None):
    r = pnl.dropna() if mask is None else pnl[mask].dropna()
    if len(r) < 10: return None
    yrs = len(r)/52.0
    ann = (1+r).prod()**(1/yrs)-1 if yrs>0 else np.nan
    vol = r.std()*np.sqrt(52); sh = ann/vol if vol>0 else np.nan
    eq = (1+r).cumprod(); dd = (eq/eq.cummax()-1).min()
    calmar = ann / abs(dd) if dd < 0 else np.nan
    return {"ann_ret":float(ann),"vol":float(vol),"sharpe":float(sh),
            "max_dd":float(dd),"calmar":float(calmar) if np.isfinite(calmar) else np.nan,
            "n_weeks":int(len(r))}

def per_year(pnl):
    r = pnl.dropna(); r.index = pd.to_datetime(r.index); rows=[]
    for yr, grp in r.groupby(r.index.year):
        if len(grp)<10: continue
        ann = (1+grp).prod()**(52/len(grp))-1
        vol = grp.std()*np.sqrt(52)
        sh = ann/vol if vol>0 else np.nan
        eq=(1+grp).cumprod(); dd=(eq/eq.cummax()-1).min()
        calmar = ann/abs(dd) if dd<0 else np.nan
        rows.append({"year":int(yr),"ann_ret":float(ann),"vol":float(vol),"sharpe":float(sh),
                     "max_dd":float(dd),"calmar":float(calmar) if np.isfinite(calmar) else np.nan,"n":int(len(grp))})
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)

# ---- Performance ----
p_is = perf(pnl_net, IS_MASK); p_oos = perf(pnl_net, OOS_MASK); p_full = perf(pnl_net)
py_df = per_year(pnl_net)
say(f"\n===== A_tuned_v1 =====")
say(f"IS   (2019-01 → 2023-12): {p_is}")
say(f"OOS  (2024-01 → 2026-04): {p_oos}")
say(f"FULL (2019-01 → 2026-04): {p_full}")
say(f"\nPer-year:")
print(py_df.to_string(index=False))

# ---- Audit: placebo 200 trials on score permutation ----
say("\n===== Placebo (200 trials, score permutation, IS only) =====")
rng = np.random.default_rng(13)
null_is_sh, null_is_cal = [], []
for _ in range(200):
    sv_p = sv.copy()
    for t_idx in range(sv_p.shape[0]):
        row = sv_p[t_idx].copy(); m = np.isfinite(row)
        if m.sum() >= 2:
            row[m] = rng.permutation(row[m]); sv_p[t_idx] = row
    w_perm = np.zeros_like(w_mat)
    for t_idx in range(sv_p.shape[0]):
        s = sv_p[t_idx]; v = np.isfinite(s) & np.isfinite(rv[t_idx]) & em[t_idx]
        if v.sum() < 4: continue
        s_v = np.where(v, s, -np.inf)
        ix = np.argpartition(-s_v, 4)[:4]
        w_perm[t_idx, ix] = 0.25
    wp = pd.DataFrame(w_perm, index=score.index, columns=cols)
    wp.loc[off] = 0.0
    pnl_pr = (wp.shift(1) * ret).sum(axis=1)
    rv26 = pnl_pr.rolling(26, min_periods=8).std()*np.sqrt(52)
    sc = (0.15 / rv26).clip(upper=1.0).fillna(0)
    wp2 = wp.mul(sc.reindex(wp.index), axis=0)
    pnl_p = (wp2.shift(1)*ret).sum(axis=1) - (wp2.shift(1).fillna(0).diff().abs().sum(axis=1)/2 * 5e-4).fillna(0)
    m = perf(pnl_p, IS_MASK)
    if m is None: continue
    null_is_sh.append(m["sharpe"]); null_is_cal.append(m["calmar"] if np.isfinite(m["calmar"]) else 0)
null_is_sh = np.array(null_is_sh); null_is_cal = np.array(null_is_cal)
p_sh = float((null_is_sh >= p_is["sharpe"]).mean())
p_cal = float((null_is_cal >= p_is["calmar"]).mean())
say(f"  IS ref sharpe={p_is['sharpe']:.3f}  null mean={null_is_sh.mean():.3f}  p={p_sh:.3f}")
say(f"  IS ref calmar={p_is['calmar']:.3f}  null mean={null_is_cal.mean():.3f}  p={p_cal:.3f}")

# ---- Top holdings ----
held = (w_final > 0).sum(axis=0).sort_values(ascending=False)
held_named = pd.DataFrame({
    "ts_code": held.index,
    "etf_name": [code2name.get(c, "?") for c in held.index],
    "group": [code2group.get(c, "?") for c in held.index],
    "weeks_held": held.values,
    "pct_weeks": [v/len(w_final) for v in held.values],
}).sort_values("weeks_held", ascending=False).head(15)
say(f"\n===== Top 15 holdings (full sample, A_tuned_v1) =====")
print(held_named.to_string(index=False))
held_named.to_csv(OUT / "a_tuned_v1_holdings.csv", index=False)

# Gate activation rate
gate_on_is = gate[IS_MASK].mean()
gate_on_oos = gate[OOS_MASK].mean()
say(f"\nGate on-rate IS: {gate_on_is*100:.1f}%  OOS: {gate_on_oos*100:.1f}%")
scale_mean_is = scale[IS_MASK].mean()
scale_mean_oos = scale[OOS_MASK].mean()
say(f"Vol-target scale mean IS: {scale_mean_is:.2f}  OOS: {scale_mean_oos:.2f}")
say(f"Ann turnover (IS): {tov_ser[IS_MASK].mean()*52:.1f}  (OOS): {tov_ser[OOS_MASK].mean()*52:.1f}")

# ---- save metrics bundle ----
out = {
    "spec": "A_tuned_v1",
    "config": {
        "family":"A_penalized", "mom_w":4, "turn_w":4, "lambda":1.5, "mu":0.3,
        "top_n":4, "gate":"mkt_cum > 50w MA", "vol_target_ann":0.15,
        "rebalance_w":1, "delay":1, "cost_bps":5,
    },
    "is_period":  {"start":"2019-01-04", "end":"2023-12-31", **(p_is or {})},
    "oos_period": {"start":"2024-01-01", "end":"2026-04-22", **(p_oos or {})},
    "full_period": p_full,
    "per_year": py_df.to_dict(orient="records"),
    "gate_on_rate": {"is":float(gate_on_is), "oos":float(gate_on_oos)},
    "vol_scale_mean": {"is":float(scale_mean_is), "oos":float(scale_mean_oos)},
    "placebo_is": {"n":int(len(null_is_sh)), "null_mean_sharpe":float(null_is_sh.mean()),
                   "p_sharpe":p_sh, "null_mean_calmar":float(null_is_cal.mean()), "p_calmar":p_cal},
    "top_holdings": held_named.to_dict(orient="records"),
    "targets": {"is_sharpe_ge_14": p_is["sharpe"]>=1.4,
                "is_calmar_ge_20": p_is["calmar"]>=2.0,
                "oos_sharpe_ge_14": p_oos["sharpe"]>=1.4,
                "oos_calmar_ge_20": p_oos["calmar"]>=2.0,
                "full_sharpe_ge_14": p_full["sharpe"]>=1.4,
                "full_calmar_ge_20": p_full["calmar"]>=2.0},
    "turnover_annual": {"is":float(tov_ser[IS_MASK].mean()*52), "oos":float(tov_ser[OOS_MASK].mean()*52)},
}
with open(OUT/"a_tuned_v1_metrics.json","w") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)

py_df.to_csv(OUT/"a_tuned_v1_per_year.csv", index=False)
pnl_net.to_frame("pnl_net").to_csv(OUT/"a_tuned_v1_pnl.csv")
(1+pnl_net.fillna(0)).cumprod().to_frame("equity").to_csv(OUT/"a_tuned_v1_equity.csv")
say("[done]")
