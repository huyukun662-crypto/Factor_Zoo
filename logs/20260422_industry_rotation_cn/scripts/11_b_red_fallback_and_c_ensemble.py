"""
Round 7 — evaluate (b) 红利 fallback and (c) A_tuned_v1 + G_top3 ensemble.

Four configs compared side by side on the 34-ETF universe:
  1. BASE        : A_tuned_v1 (cash fallback when gate off)
  2. B_ONLY      : A_tuned_v1 + 红利 fallback (515080 when gate off)
  3. C_ONLY      : Ensemble 50/50 (A_tuned_v1 + G_top3), cash fallback
  4. B_PLUS_C    : Ensemble 50/50 + 红利 fallback

Shared convention:
  - IS  = 2019-2023, OOS = 2024-2026
  - delay=1, weekly rebalance, cost 5 bps/side
  - gate = mkt_cum > 50w MA
  - vol target 15% annual (scale-down only, applied AFTER combine)

Targets:
  - Maintain Full Sharpe ≥ 1.2
  - MaxDD < -6% (user target)
  - Calmar ≥ 2.5 (stretch)
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
cols = ret.columns

RED_CODE = "515080.SH"          # 红利ETF
assert RED_CODE in cols, f"{RED_CODE} not in panel"

IS_MASK  = ret.index < pd.Timestamp("2024-01-01")
OOS_MASK = ret.index >= pd.Timestamp("2024-01-01")

def zscore_cs(df):
    df = df.where(elig); mu=df.mean(axis=1); sd=df.std(axis=1)
    return df.sub(mu, axis=0).div(sd, axis=0)

# ---------- A_tuned_v1 raw weights (before gate) ----------
def build_A_weights():
    mom4 = cum / cum.shift(4) - 1
    turn4 = turn.rolling(4, min_periods=2).mean()
    br_s = ((cum > cum.rolling(20, min_periods=8).mean()).where(elig).sum(axis=1) /
            elig.sum(axis=1).replace(0, np.nan))
    br_z = (br_s - br_s.rolling(52, min_periods=20).mean()) / br_s.rolling(52, min_periods=20).std()
    bread_df = pd.DataFrame({c: br_z for c in cols})
    score = zscore_cs(mom4) - 1.5*zscore_cs(turn4) + 0.3*bread_df
    w_mat = np.zeros(score.shape, dtype=float)
    sv = score.values.astype(float); rv = ret.values.astype(float); em = elig.values.astype(bool)
    for t_idx in range(sv.shape[0]):
        s = sv[t_idx]; v = np.isfinite(s) & np.isfinite(rv[t_idx]) & em[t_idx]
        if v.sum() < 4: continue
        s_v = np.where(v, s, -np.inf)
        ix = np.argpartition(-s_v, 4)[:4]
        w_mat[t_idx, ix] = 0.25
    return pd.DataFrame(w_mat, index=score.index, columns=cols)

# ---------- G_top3 rotator raw weights ----------
def build_G_weights():
    group_names = sorted(set(uni["group"].dropna()))
    group_ret = pd.DataFrame(0.0, index=ret.index, columns=group_names)
    for g in group_names:
        codes_g = [c for c in uni[uni["group"]==g]["ts_code"] if c in cols]
        v = elig[codes_g]
        group_ret[g] = ret[codes_g].where(v).mean(axis=1)
    g_gross = 1 + group_ret.fillna(0); g_cum = g_gross.cumprod()
    g_mom4 = g_cum / g_cum.shift(4) - 1
    mom4_etf = cum / cum.shift(4) - 1

    w_mat = np.zeros((len(ret), len(cols)), dtype=float)
    for t_idx in range(len(ret)):
        gs = g_mom4.iloc[t_idx].dropna()
        if len(gs) < 3: continue
        top_groups = gs.nlargest(3).index.tolist()
        picks = []
        for g in top_groups:
            codes_g = [c for c in uni[uni["group"]==g]["ts_code"] if c in cols]
            s = mom4_etf.iloc[t_idx][codes_g].dropna()
            s = s[[c for c in s.index if elig.iloc[t_idx][c]]]
            if len(s) < 1: continue
            picks += s.nlargest(1).index.tolist()
        if not picks: continue
        nw = 1.0 / len(picks)
        for c in picks:
            w_mat[t_idx, cols.get_loc(c)] = nw
    return pd.DataFrame(w_mat, index=ret.index, columns=cols)

w_A = build_A_weights()
w_G = build_G_weights()
say(f"Built A weights: sum_check mean = {w_A.sum(axis=1).replace(0, np.nan).dropna().mean():.3f}")
say(f"Built G weights: sum_check mean = {w_G.sum(axis=1).replace(0, np.nan).dropna().mean():.3f}")

# ---------- Gate & fallback & vol target ----------
mc = cum.mean(axis=1)
gate = (mc > mc.rolling(50, min_periods=25).mean())  # Series
gate_on = gate.reindex(ret.index).fillna(False)

def apply_gate_fallback(w_raw, fallback="cash"):
    """When gate off: cash → 0 weights; 红利 → 100% on RED_CODE (if eligible)."""
    w = w_raw.copy()
    off = ~gate_on
    if fallback == "cash":
        w.loc[off] = 0.0
    elif fallback == "red":
        # when off and red is eligible, set 100% on red; else cash
        red_ok = elig[RED_CODE].fillna(False)
        w.loc[off] = 0.0
        for t in w.index[off & red_ok]:
            w.at[t, RED_CODE] = 1.0
    else:
        raise ValueError(fallback)
    return w

def apply_vol_target(w, target=0.15, lookback=26):
    pnl_raw = (w.shift(1) * ret).sum(axis=1)
    rv = pnl_raw.rolling(lookback, min_periods=8).std()*np.sqrt(52)
    sc = (target / rv).clip(upper=1.0).fillna(0)
    return w.mul(sc.reindex(w.index), axis=0)

def run_bt(w, cost_bps=5):
    w_exec = w.shift(1)
    pnl_g = (w_exec * ret).sum(axis=1)
    tov = (w_exec.fillna(0).diff().abs().sum(axis=1)/2).fillna(0)
    return pnl_g - tov*(cost_bps/1e4), tov

def perf(pnl, mask=None):
    r = pnl.dropna() if mask is None else pnl[mask].dropna()
    if len(r) < 10: return None
    yrs = len(r)/52.0
    ann = (1+r).prod()**(1/yrs)-1 if yrs>0 else np.nan
    vol = r.std()*np.sqrt(52); sh = ann/vol if vol>0 else np.nan
    eq = (1+r).cumprod(); dd = (eq/eq.cummax()-1).min()
    cal = ann/abs(dd) if dd<0 else np.nan
    return {"ann":float(ann),"vol":float(vol),"sh":float(sh),"dd":float(dd),
            "cal":float(cal) if np.isfinite(cal) else np.nan, "n":int(len(r))}

def per_year(pnl):
    r = pnl.dropna(); r.index = pd.to_datetime(r.index); rows=[]
    for yr, grp in r.groupby(r.index.year):
        if len(grp)<10: continue
        ann = (1+grp).prod()**(52/len(grp))-1
        vol = grp.std()*np.sqrt(52)
        sh = ann/vol if vol>0 else np.nan
        eq=(1+grp).cumprod(); dd=(eq/eq.cummax()-1).min()
        cal = ann/abs(dd) if dd<0 else np.nan
        rows.append({"year":int(yr),"ret":float(ann),"vol":float(vol),"sh":float(sh),"dd":float(dd),
                     "cal":float(cal) if np.isfinite(cal) else np.nan,"n":int(len(grp))})
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)

# ---------- Build 4 configs ----------
configs = {}

# 1. BASE — A_tuned_v1 with cash
w = apply_gate_fallback(w_A, "cash")
w = apply_vol_target(w, 0.15, 26)
pnl, tov = run_bt(w, 5)
configs["BASE_A_cash"] = {"pnl":pnl, "tov":tov, "w":w}

# 2. B_ONLY — A_tuned_v1 with 红利 fallback
w = apply_gate_fallback(w_A, "red")
w = apply_vol_target(w, 0.15, 26)
pnl, tov = run_bt(w, 5)
configs["B_A_red"] = {"pnl":pnl, "tov":tov, "w":w}

# 3. C_ONLY — Ensemble 50/50 with cash fallback
w_ens = 0.5*w_A + 0.5*w_G
w = apply_gate_fallback(w_ens, "cash")
w = apply_vol_target(w, 0.15, 26)
pnl, tov = run_bt(w, 5)
configs["C_ens_cash"] = {"pnl":pnl, "tov":tov, "w":w}

# 4. B_PLUS_C — Ensemble + 红利 fallback
w_ens = 0.5*w_A + 0.5*w_G
w = apply_gate_fallback(w_ens, "red")
w = apply_vol_target(w, 0.15, 26)
pnl, tov = run_bt(w, 5)
configs["BC_ens_red"] = {"pnl":pnl, "tov":tov, "w":w}

# ---------- Report ----------
say("\n===== 4-way comparison =====")
rows = []
for name, bundle in configs.items():
    pnl, tov = bundle["pnl"], bundle["tov"]
    m_is = perf(pnl, IS_MASK); m_oos = perf(pnl, OOS_MASK); m_full = perf(pnl)
    rows.append({
        "config": name,
        "is_sh": m_is["sh"],   "is_cal": m_is["cal"],   "is_dd": m_is["dd"],   "is_ann": m_is["ann"],
        "oos_sh": m_oos["sh"], "oos_cal": m_oos["cal"], "oos_dd": m_oos["dd"], "oos_ann": m_oos["ann"],
        "full_sh": m_full["sh"], "full_cal": m_full["cal"], "full_dd": m_full["dd"], "full_ann": m_full["ann"],
        "full_vol": m_full["vol"],
        "ann_tov": float(tov.mean()*52),
    })
df = pd.DataFrame(rows)
print(df.to_string(index=False))
df.to_csv(OUT / "round7_compare.csv", index=False)

# per-year for each
say("\n===== Per-year =====")
for name, bundle in configs.items():
    py = per_year(bundle["pnl"])
    py["config"] = name
    say(f"\n--- {name} ---")
    print(py[["year","ret","vol","sh","dd","cal","n"]].to_string(index=False))
    py.to_csv(OUT / f"round7_{name}_peryear.csv", index=False)

# ---------- Holdings (for best) ----------
say("\n===== Top holdings (BC_ens_red) =====")
w_best = configs["BC_ens_red"]["w"]
held = (w_best > 0).sum(axis=0).sort_values(ascending=False)
hn = pd.DataFrame({"ts_code": held.index,
                   "etf_name":[code2name.get(c,"?") for c in held.index],
                   "group":[code2group.get(c,"?") for c in held.index],
                   "weeks_held": held.values,
                   "pct_weeks": [v/len(w_best) for v in held.values]}).head(20)
print(hn.to_string(index=False))
hn.to_csv(OUT / "round7_BC_ens_red_holdings.csv", index=False)

# ---------- Save each equity curve ----------
curves = pd.DataFrame({name: (1+b["pnl"].fillna(0)).cumprod() for name,b in configs.items()})
curves.to_csv(OUT / "round7_equity_curves.csv")

# Summary targets
say("\n===== Target check =====")
for _, r in df.iterrows():
    tag = r["config"]
    ok_dd = r["full_dd"] > -0.06
    ok_sh = r["full_sh"] >= 1.2
    ok_cal = r["full_cal"] >= 2.5
    print(f"  {tag:14s}  Sh={r['full_sh']:.2f}  Cal={r['full_cal']:.2f}  DD={r['full_dd']*100:+.1f}%  "
          f"[Sh≥1.2 {('✓' if ok_sh else '✗')}, Cal≥2.5 {('✓' if ok_cal else '✗')}, DD>-6% {('✓' if ok_dd else '✗')}]")

say("[done]")
