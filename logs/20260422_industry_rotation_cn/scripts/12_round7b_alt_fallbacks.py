"""
Round 7b — explore alternative fallbacks & ensembles to push MaxDD < -6%.

Variants:
  V1 BASE        — A_tuned_v1 cash                         (reference DD -9.3%)
  V2 RED         — A + 红利ETF fallback                     (DD -13.4%, worse)
  V3 GOLD        — A + 黄金ETF (159934) fallback             (anti-cyclic)
  V4 RED+GOLD    — A + 50% 红利 + 50% 黄金 fallback          (diversified safe haven)
  V5 HALF_RED    — A + 50% 红利 + 50% cash fallback          (half dose)
  V6 HALF_GOLD   — A + 50% 黄金 + 50% cash fallback          (half dose)
  V7 ENS_GOLD    — 0.5*A + 0.5*G + 黄金 fallback
  V8 A_vt10      — A + cash + tighter vol target 10%
  V9 A_top5      — A with top_n=5
  V10 MA60_vt10  — A with MA60 gate + 10% vol target
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

RED = "515080.SH"
GOLD = "159934.SZ"

IS_MASK  = ret.index < pd.Timestamp("2024-01-01")
OOS_MASK = ret.index >= pd.Timestamp("2024-01-01")

def zscore_cs(df):
    df = df.where(elig); mu=df.mean(axis=1); sd=df.std(axis=1)
    return df.sub(mu, axis=0).div(sd, axis=0)

def build_A_weights(top_n=4, lam=1.5, mu=0.3, mom_w=4, turn_w=4):
    momX = cum / cum.shift(mom_w) - 1
    turnX = turn.rolling(turn_w, min_periods=2).mean()
    br_s = ((cum > cum.rolling(20, min_periods=8).mean()).where(elig).sum(axis=1) /
            elig.sum(axis=1).replace(0, np.nan))
    br_z = (br_s - br_s.rolling(52, min_periods=20).mean()) / br_s.rolling(52, min_periods=20).std()
    bread_df = pd.DataFrame({c: br_z for c in cols})
    score = zscore_cs(momX) - lam*zscore_cs(turnX) + mu*bread_df
    w_mat = np.zeros(score.shape, dtype=float)
    sv = score.values.astype(float); rv = ret.values.astype(float); em = elig.values.astype(bool)
    for ti in range(sv.shape[0]):
        s = sv[ti]; v = np.isfinite(s) & np.isfinite(rv[ti]) & em[ti]
        if v.sum() < top_n: continue
        s_v = np.where(v, s, -np.inf)
        ix = np.argpartition(-s_v, top_n)[:top_n]
        w_mat[ti, ix] = 1.0/top_n
    return pd.DataFrame(w_mat, index=score.index, columns=cols)

def build_G_weights():
    group_names = sorted(set(uni["group"].dropna()))
    gret = pd.DataFrame(0.0, index=ret.index, columns=group_names)
    for g in group_names:
        codes_g = [c for c in uni[uni["group"]==g]["ts_code"] if c in cols]
        v = elig[codes_g]
        gret[g] = ret[codes_g].where(v).mean(axis=1)
    gcum = (1+gret.fillna(0)).cumprod()
    gmom4 = gcum/gcum.shift(4) - 1
    mom4_etf = cum / cum.shift(4) - 1
    wmat = np.zeros((len(ret), len(cols)), dtype=float)
    for ti in range(len(ret)):
        gs = gmom4.iloc[ti].dropna()
        if len(gs) < 3: continue
        tops = gs.nlargest(3).index.tolist()
        picks = []
        for g in tops:
            codes_g = [c for c in uni[uni["group"]==g]["ts_code"] if c in cols]
            s = mom4_etf.iloc[ti][codes_g].dropna()
            s = s[[c for c in s.index if elig.iloc[ti][c]]]
            if len(s)<1: continue
            picks += s.nlargest(1).index.tolist()
        if not picks: continue
        nw = 1.0/len(picks)
        for c in picks:
            wmat[ti, cols.get_loc(c)] = nw
    return pd.DataFrame(wmat, index=ret.index, columns=cols)

def make_gate(ma=50):
    mc = cum.mean(axis=1)
    return (mc > mc.rolling(ma, min_periods=ma//2).mean()).reindex(ret.index).fillna(False)

def apply_gate_fallback(w_raw, fallback, gate):
    w = w_raw.copy()
    off = ~gate
    w.loc[off] = 0.0
    if fallback == "cash": return w
    red_ok = elig[RED].fillna(False)
    gold_ok = elig[GOLD].fillna(False)
    for t in w.index[off]:
        r_ok = red_ok.loc[t]; g_ok = gold_ok.loc[t]
        if fallback == "red" and r_ok:
            w.at[t, RED] = 1.0
        elif fallback == "gold" and g_ok:
            w.at[t, GOLD] = 1.0
        elif fallback == "red_gold":
            if r_ok and g_ok:
                w.at[t, RED] = 0.5; w.at[t, GOLD] = 0.5
            elif r_ok:
                w.at[t, RED] = 1.0
            elif g_ok:
                w.at[t, GOLD] = 1.0
        elif fallback == "half_red" and r_ok:
            w.at[t, RED] = 0.5
        elif fallback == "half_gold" and g_ok:
            w.at[t, GOLD] = 0.5
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
            "cal":float(cal) if np.isfinite(cal) else np.nan,"n":int(len(r))}

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

w_A_top4 = build_A_weights(top_n=4)
w_A_top5 = build_A_weights(top_n=5)
w_G = build_G_weights()
gate50 = make_gate(50)
gate60 = make_gate(60)

configs = {}
def go(name, w_raw, fallback, gate, vt):
    w = apply_gate_fallback(w_raw, fallback, gate)
    w = apply_vol_target(w, vt, 26)
    pnl, tov = run_bt(w, 5)
    configs[name] = {"pnl": pnl, "tov": tov, "w": w}

go("V1_BASE",       w_A_top4,               "cash",     gate50, 0.15)
go("V2_RED",        w_A_top4,               "red",      gate50, 0.15)
go("V3_GOLD",       w_A_top4,               "gold",     gate50, 0.15)
go("V4_RED_GOLD",   w_A_top4,               "red_gold", gate50, 0.15)
go("V5_HALF_RED",   w_A_top4,               "half_red", gate50, 0.15)
go("V6_HALF_GOLD",  w_A_top4,               "half_gold",gate50, 0.15)
go("V7_ENS_GOLD",   0.5*w_A_top4 + 0.5*w_G, "gold",     gate50, 0.15)
go("V8_A_vt10",     w_A_top4,               "cash",     gate50, 0.10)
go("V9_A_top5",     w_A_top5,               "cash",     gate50, 0.15)
go("V10_MA60_vt10", w_A_top4,               "cash",     gate60, 0.10)

rows = []
for name, b in configs.items():
    pnl, tov = b["pnl"], b["tov"]
    m_is = perf(pnl, IS_MASK); m_oos = perf(pnl, OOS_MASK); m_full = perf(pnl)
    rows.append({"config":name,
                 "full_sh":m_full["sh"],"full_cal":m_full["cal"],"full_dd":m_full["dd"],
                 "full_ann":m_full["ann"],"full_vol":m_full["vol"],
                 "is_sh":m_is["sh"],"is_cal":m_is["cal"],"is_dd":m_is["dd"],
                 "oos_sh":m_oos["sh"],"oos_cal":m_oos["cal"],"oos_dd":m_oos["dd"],
                 "ann_tov":float(tov.mean()*52)})
df = pd.DataFrame(rows).sort_values("full_dd", ascending=False)
say("\n===== 10 configs (sorted by MaxDD, best first) =====")
print(df.to_string(index=False))
df.to_csv(OUT / "round7b_compare.csv", index=False)

say("\n===== Per-year — top 5 by MaxDD =====")
for name in df["config"].head(5).tolist():
    py = per_year(configs[name]["pnl"])
    say(f"\n--- {name} ---")
    print(py[["year","ret","vol","sh","dd","cal","n"]].to_string(index=False))
    py.to_csv(OUT / f"round7b_{name}_peryear.csv", index=False)

say("\n===== Target: Sh≥1.2, Cal≥2.5, MaxDD>-6% =====")
for _, r in df.iterrows():
    ok_dd = r["full_dd"] > -0.06; ok_sh = r["full_sh"] >= 1.2; ok_cal = r["full_cal"] >= 2.5
    print(f"  {r['config']:15s}  Sh={r['full_sh']:.2f}  Cal={r['full_cal']:.2f}  DD={r['full_dd']*100:+.1f}%  "
          f"[Sh {('✓' if ok_sh else '✗')}, Cal {('✓' if ok_cal else '✗')}, DD {('✓' if ok_dd else '✗')}]")

curves = pd.DataFrame({name: (1+b["pnl"].fillna(0)).cumprod() for name,b in configs.items()})
curves.to_csv(OUT / "round7b_equity_curves.csv")
say("[done]")
