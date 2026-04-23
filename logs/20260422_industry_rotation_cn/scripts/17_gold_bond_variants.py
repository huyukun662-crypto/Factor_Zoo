"""
Round 9 — gold + bond-ETF fallback combinations for V7.

Bond ETFs tested:
  511010.SH  国泰上证5年期国债ETF       (2015+, full sample)
  511260.SH  华安十年期国债ETF           (2017+, covers full model sample)

Variants:
  V7_gold          : 100% gold                           (baseline)
  V7_bond5         : 100% 511010 (5y bond)
  V7_bond10        : 100% 511260 (10y bond)
  V7_gb_70_30      : 70% gold + 30% 5y bond
  V7_gb_50_50      : 50% gold + 50% 5y bond
  V7_gb_30_70      : 30% gold + 70% 5y bond
  V7_gb10_50_50    : 50% gold + 50% 10y bond
  V7_rp_g_b5       : risk-parity (inverse 26w vol) between gold and 5y bond
  V7_gold_bond_40_40_silver_20 : 40% gold + 40% bond + 20% 白银 (true 3-way hedge)

Targets: improve Calmar > 3.22, reduce MaxDD < -8.89%, esp. cut 2022 DD.
"""
import os, time, json
from pathlib import Path
import numpy as np, pandas as pd
import tushare as ts

CACHE = Path("/home/user/Factor_Zoo/.cache")
OUT = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs")
say = lambda s: print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)

secret = Path("/home/user/Factor_Zoo/.secrets/tushare.env")
if not os.environ.get("TUSHARE_TOKEN"):
    for line in secret.read_text().splitlines():
        if line.startswith("TUSHARE_TOKEN="):
            os.environ["TUSHARE_TOKEN"] = line.split("=",1)[1].strip()
pro = ts.pro_api(os.environ["TUSHARE_TOKEN"])

# ------------- 1. Fetch bond ETFs -------------
BOND_PATH = CACHE / "fund_daily_bonds.parquet"
BOND_ADJ = CACHE / "fund_adj_bonds.parquet"
BOND_CODES = ["511010.SH", "511260.SH"]
if not BOND_PATH.exists():
    d_rows, a_rows = [], []
    for code in BOND_CODES:
        for _ in range(3):
            try:
                d = pro.fund_daily(ts_code=code, start_date="20150101", end_date="20260422"); break
            except: time.sleep(2)
        else: d = pd.DataFrame()
        d_rows.append(d)
        for _ in range(3):
            try:
                a = pro.fund_adj(ts_code=code, start_date="20150101", end_date="20260422"); break
            except: time.sleep(2)
        else: a = pd.DataFrame()
        a_rows.append(a)
    fd = pd.concat(d_rows); fd["trade_date"] = pd.to_datetime(fd["trade_date"]); fd.to_parquet(BOND_PATH)
    fa = pd.concat(a_rows); fa["trade_date"] = pd.to_datetime(fa["trade_date"]); fa.to_parquet(BOND_ADJ)
    say("fetched bond ETFs")

fd = pd.read_parquet(BOND_PATH).merge(pd.read_parquet(BOND_ADJ), on=["ts_code","trade_date"], how="left")
fd["close_adj"] = fd["close"] * fd["adj_factor"].fillna(1.0)
fd = fd.sort_values(["ts_code","trade_date"]).reset_index(drop=True)
fd["ret"] = fd.groupby("ts_code")["close_adj"].pct_change()
say(f"bond daily: {len(fd):,} rows")

# Weekly
fd["year_week"] = fd["trade_date"].dt.strftime("%G-%V")
fd["gross"] = 1 + fd["ret"].fillna(0)
fd["cum"] = fd.groupby("ts_code")["gross"].cumprod()
bw = (fd.groupby(["ts_code","year_week"], sort=False)
      .agg(trade_week=("trade_date","last"), cum_w=("cum","last"))
      .reset_index().sort_values(["ts_code","trade_week"]))
bw["ret_w"] = bw.groupby("ts_code")["cum_w"].pct_change()
bw = bw.dropna(subset=["ret_w"])

# ------------- 2. Load main panel + defensive panel -------------
W_main = pd.read_parquet(OUT / "etf_weekly.parquet")
uni = pd.read_csv(OUT / "etf_universe.csv")
W_main["trade_week"] = pd.to_datetime(W_main["trade_week"])
W_main = W_main[W_main["trade_week"] >= "2019-01-01"].sort_values(["trade_week","ts_code"]).reset_index(drop=True)
ret_main = W_main.pivot(index="trade_week", columns="ts_code", values="ret_w").sort_index()
turn_main = W_main.pivot(index="trade_week", columns="ts_code", values="turnover_w").sort_index()
gross_main = 1 + ret_main.fillna(0); cum_main = gross_main.cumprod()
age_main = ret_main.notna().cumsum(); elig_main = age_main >= 12
main_cols = ret_main.columns
all_dates = ret_main.index

W_def = pd.read_parquet(OUT / "defensive_weekly.parquet")
W_def["trade_week"] = pd.to_datetime(W_def["trade_week"])

# Combine defensive + bond + gold(from main)
def_parts = [W_def[["ts_code","trade_week","ret_w"]], bw[["ts_code","trade_week","ret_w"]]]
all_def = pd.concat(def_parts, ignore_index=True)
ret_def = all_def.pivot(index="trade_week", columns="ts_code", values="ret_w").reindex(all_dates)
if "159934.SZ" in ret_main.columns:
    ret_def["159934.SZ"] = ret_main["159934.SZ"]

age_def = ret_def.notna().cumsum(); elig_def = age_def >= 12

say(f"\n===== Defensive + bond coverage =====")
names = {"159934.SZ":"黄金","161226.SZ":"白银","159981.SZ":"铜",
         "159920.SZ":"港股","159941.SZ":"纳指","162411.SZ":"油气",
         "511010.SH":"5y 国债","511260.SH":"10y 国债"}
for c, n in names.items():
    if c not in ret_def.columns:
        say(f"  {n:10s} MISSING"); continue
    first = elig_def.index[elig_def[c]].min() if elig_def[c].any() else None
    say(f"  {n:10s} ({c})  n={ret_def[c].notna().sum()}  first elig={first.date() if first is not None else 'N/A'}")

# ------------- 3. Stress-year correlation diagnostic -------------
say(f"\n===== 2022 year returns (stress test: Fed-hike + A-share bear) =====")
for c, n in names.items():
    if c not in ret_def.columns: continue
    r2022 = ret_def[c][ret_def.index.year==2022]
    if len(r2022) >= 30:
        ann = (1+r2022.dropna()).prod() - 1
        dd = ((1+r2022.fillna(0)).cumprod() / (1+r2022.fillna(0)).cumprod().cummax() - 1).min()
        say(f"  {n:10s}  2022 total return = {ann*100:+6.2f}%   DD = {dd*100:+5.2f}%")

# ------------- 4. Build main strategy (A + G ensemble) -------------
def zscore_cs(df):
    df = df.where(elig_main); m=df.mean(axis=1); s=df.std(axis=1)
    return df.sub(m, axis=0).div(s, axis=0)

mom4 = cum_main / cum_main.shift(4) - 1
turn4 = turn_main.rolling(4, min_periods=2).mean()
br_s = ((cum_main > cum_main.rolling(20, min_periods=8).mean()).where(elig_main).sum(axis=1) /
        elig_main.sum(axis=1).replace(0, np.nan))
br_z = (br_s - br_s.rolling(52, min_periods=20).mean()) / br_s.rolling(52, min_periods=20).std()
bread_df = pd.DataFrame({c: br_z for c in main_cols})

def build_A():
    score = zscore_cs(mom4) - 1.5*zscore_cs(turn4) + 0.3*bread_df
    score = score.reindex(columns=main_cols).astype(float)
    wm = np.zeros(score.shape); sv = score.values.astype(float)
    rv = ret_main.values.astype(float); em = elig_main.values.astype(bool)
    for ti in range(sv.shape[0]):
        s = sv[ti]; v = np.isfinite(s) & np.isfinite(rv[ti]) & em[ti]
        if v.sum() < 4: continue
        s_v = np.where(v, s, -np.inf); ix = np.argpartition(-s_v, 4)[:4]
        wm[ti, ix] = 0.25
    return pd.DataFrame(wm, index=score.index, columns=main_cols)

def build_G():
    gnames = sorted(set(uni["group"].dropna()))
    gret = pd.DataFrame(0.0, index=ret_main.index, columns=gnames)
    for g in gnames:
        codes_g = [c for c in uni[uni["group"]==g]["ts_code"] if c in main_cols]
        v = elig_main[codes_g]
        gret[g] = ret_main[codes_g].where(v).mean(axis=1)
    gcum = (1+gret.fillna(0)).cumprod()
    gmom4 = gcum/gcum.shift(4) - 1
    wm = np.zeros((len(ret_main), len(main_cols)))
    for ti in range(len(ret_main)):
        gs = gmom4.iloc[ti].dropna()
        if len(gs) < 3: continue
        tops = gs.nlargest(3).index.tolist()
        picks = []
        for g in tops:
            codes_g = [c for c in uni[uni["group"]==g]["ts_code"] if c in main_cols]
            s = mom4.iloc[ti][codes_g].dropna()
            s = s[[c for c in s.index if elig_main.iloc[ti][c]]]
            if len(s)<1: continue
            picks += s.nlargest(1).index.tolist()
        if not picks: continue
        nw = 1/len(picks)
        for c in picks: wm[ti, main_cols.get_loc(c)] = nw
    return pd.DataFrame(wm, index=ret_main.index, columns=main_cols)

w_A = build_A()
w_G = build_G()
w_ens = 0.5*w_A + 0.5*w_G
mc = cum_main.mean(axis=1)
gate = (mc > mc.rolling(50, min_periods=25).mean()).reindex(all_dates).fillna(False)

# ------------- 5. Basket fallback builder -------------
def eligible_subset(t, assets):
    return [a for a in assets if a in elig_def.columns and elig_def.loc[t, a]]

# Risk-parity helper
def rp_weights(t_idx, assets):
    """Inverse 26w vol weights, among eligible assets at t."""
    t = all_dates[t_idx]
    elig_members = eligible_subset(t, assets)
    if not elig_members: return {}
    if t_idx < 26: return {c: 1.0/len(elig_members) for c in elig_members}
    vols = {}
    for c in elig_members:
        r = ret_def[c].iloc[max(0, t_idx-26):t_idx].dropna()
        if len(r) < 8: vols[c] = np.nan; continue
        vols[c] = r.std() * np.sqrt(52)
    ok = {c: v for c, v in vols.items() if np.isfinite(v) and v > 1e-6}
    if not ok: return {c: 1.0/len(elig_members) for c in elig_members}
    inv = {c: 1.0/v for c, v in ok.items()}
    total = sum(inv.values())
    return {c: inv[c]/total for c in inv}

BASKETS = {
    "V7_gold":         ("fixed", {"159934.SZ": 1.0}),
    "V7_bond5":        ("fixed", {"511010.SH": 1.0}),
    "V7_bond10":       ("fixed", {"511260.SH": 1.0}),
    "V7_gb_70_30":     ("fixed", {"159934.SZ": 0.7, "511010.SH": 0.3}),
    "V7_gb_50_50":     ("fixed", {"159934.SZ": 0.5, "511010.SH": 0.5}),
    "V7_gb_30_70":     ("fixed", {"159934.SZ": 0.3, "511010.SH": 0.7}),
    "V7_gb10_50_50":   ("fixed", {"159934.SZ": 0.5, "511260.SH": 0.5}),
    "V7_rp_g_b5":      ("rp", ["159934.SZ", "511010.SH"]),
    "V7_rp_g_b10":     ("rp", ["159934.SZ", "511260.SH"]),
    "V7_g_b5_silver":  ("fixed", {"159934.SZ":0.4, "511010.SH":0.4, "161226.SZ":0.2}),
}

def build_defensive_weights(name, t_idx):
    kind, spec = BASKETS[name]
    t = all_dates[t_idx]
    if kind == "fixed":
        # normalize by eligibility at t (redistribute if some unavailable)
        ok = {c: w for c, w in spec.items() if c in elig_def.columns and elig_def.loc[t, c]}
        if not ok: return {}
        tot = sum(ok.values())
        return {c: w/tot for c, w in ok.items()}
    elif kind == "rp":
        return rp_weights(t_idx, spec)
    return {}

# ------------- 6. Run each variant -------------
def apply_vol_target(pnl_raw, target=0.15, lookback=26):
    rv = pnl_raw.rolling(lookback, min_periods=8).std()*np.sqrt(52)
    return (target / rv).clip(upper=1.0).fillna(0)

def run_variant(name, cost_bps=5):
    all_codes = sorted(set(main_cols) | set(ret_def.columns))
    ret_all = pd.DataFrame(index=all_dates, columns=all_codes, dtype=float)
    for c in main_cols: ret_all[c] = ret_main[c]
    for c in ret_def.columns:
        if c not in main_cols: ret_all[c] = ret_def[c]
    ret_all = ret_all.astype(float)

    w_mat = np.zeros((len(all_dates), len(all_codes)))
    col_idx = {c:i for i,c in enumerate(all_codes)}

    for ti in range(len(all_dates)):
        if gate.iloc[ti]:
            for c in main_cols:
                w = w_ens.iloc[ti][c]
                if w > 0: w_mat[ti, col_idx[c]] = w
        else:
            basket = build_defensive_weights(name, ti)
            for c, wt in basket.items():
                if c in col_idx: w_mat[ti, col_idx[c]] = wt

    w_df = pd.DataFrame(w_mat, index=all_dates, columns=all_codes)
    pnl_raw = (w_df.shift(1) * ret_all).sum(axis=1)
    scale = apply_vol_target(pnl_raw, 0.15, 26)
    w_final = w_df.mul(scale.reindex(w_df.index), axis=0)
    w_exec = w_final.shift(1)
    pnl_g = (w_exec * ret_all).sum(axis=1)
    tov = (w_exec.fillna(0).diff().abs().sum(axis=1)/2).fillna(0)
    pnl_net = pnl_g - tov*(cost_bps/1e4)
    return pnl_net, tov, w_final

def perf(pnl, mask=None):
    r = pnl.dropna() if mask is None else pnl[mask].dropna()
    if len(r) < 10: return None
    yrs = len(r)/52.0
    ann = (1+r).prod()**(1/yrs)-1 if yrs>0 else np.nan
    vol = r.std()*np.sqrt(52); sh = ann/vol if vol>0 else np.nan
    eq = (1+r).cumprod(); dd = (eq/eq.cummax()-1).min()
    down = r[r<0]
    dv = down.std()*np.sqrt(52) if len(down)>0 else np.nan
    sortino = ann/dv if dv and dv>0 else np.nan
    cal = ann/abs(dd) if dd<0 else np.nan
    return {"ann":float(ann),"vol":float(vol),"sharpe":float(sh),
            "sortino":float(sortino) if np.isfinite(sortino) else np.nan,
            "max_dd":float(dd),"calmar":float(cal) if np.isfinite(cal) else np.nan,"n":int(len(r))}

def per_year(pnl):
    r = pnl.dropna(); r.index = pd.to_datetime(r.index); rows=[]
    for yr, grp in r.groupby(r.index.year):
        if len(grp)<10: continue
        ann = (1+grp).prod()**(52/len(grp))-1
        vol = grp.std()*np.sqrt(52); sh = ann/vol if vol>0 else np.nan
        eq=(1+grp).cumprod(); dd=(eq/eq.cummax()-1).min()
        cal = ann/abs(dd) if dd<0 else np.nan
        rows.append({"year":int(yr),"ret":float(ann),"sh":float(sh),"dd":float(dd),"cal":float(cal) if np.isfinite(cal) else np.nan,"n":int(len(grp))})
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)

IS_MASK = all_dates < pd.Timestamp("2024-01-01")
OOS_MASK = all_dates >= pd.Timestamp("2024-01-01")

results = {}; summary = []
say(f"\n===== Running {len(BASKETS)} variants =====")
for name in BASKETS.keys():
    pnl, tov, w_final = run_variant(name)
    m_is = perf(pnl, IS_MASK); m_oos = perf(pnl, OOS_MASK); m_full = perf(pnl)
    results[name] = {"pnl":pnl, "tov":tov, "m_full":m_full, "m_is":m_is, "m_oos":m_oos,
                     "per_year": per_year(pnl)}
    summary.append({
        "basket": name,
        "full_sh":m_full["sharpe"], "full_sortino":m_full["sortino"],
        "full_cal":m_full["calmar"], "full_dd":m_full["max_dd"], "full_ann":m_full["ann"],
        "is_sh":m_is["sharpe"], "is_cal":m_is["calmar"], "is_dd":m_is["max_dd"],
        "oos_sh":m_oos["sharpe"], "oos_cal":m_oos["calmar"], "oos_dd":m_oos["max_dd"],
        "ann_tov":float(tov.mean()*52),
    })
    say(f"  {name:18s}  Full Sh={m_full['sharpe']:.2f}  Cal={m_full['calmar']:.2f}  "
        f"DD={m_full['max_dd']*100:+.2f}%  AnnRet={m_full['ann']*100:+.1f}%")

df = pd.DataFrame(summary).sort_values("full_cal", ascending=False)
say(f"\n===== Summary (sorted by Calmar desc) =====")
print(df.to_string(index=False))
df.to_csv(OUT / "round9_goldbond_compare.csv", index=False)

# Per-year for top 5
say(f"\n===== Per-year (top 5 by Calmar) =====")
top5 = df.head(5)["basket"].tolist()
for name in top5:
    py = results[name]["per_year"]
    say(f"\n--- {name} ---")
    print(py[["year","ret","sh","dd","cal","n"]].to_string(index=False))
    py.to_csv(OUT / f"round9_{name}_peryear.csv", index=False)

# 2022 stress
say(f"\n===== 2022 stress comparison =====")
r22_rows = []
for name in BASKETS.keys():
    py = results[name]["per_year"]
    row = py[py["year"]==2022]
    if len(row)==0: continue
    r22_rows.append({
        "basket": name,
        "2022_ret": float(row["ret"].iloc[0]),
        "2022_sh":  float(row["sh"].iloc[0]),
        "2022_dd":  float(row["dd"].iloc[0]),
    })
r22 = pd.DataFrame(r22_rows)
print(r22.to_string(index=False))
r22.to_csv(OUT / "round9_2022_stress.csv", index=False)

# save equity
curves = pd.DataFrame({name: (1+r["pnl"].fillna(0)).cumprod() for name,r in results.items()})
curves.to_csv(OUT / "round9_equity_curves.csv")

# full bundle
bundle = {
    "baskets": {k:{"kind":v[0],"spec":v[1]} for k,v in BASKETS.items()},
    "variants": {
        name: {
            "is":results[name]["m_is"],"oos":results[name]["m_oos"],"full":results[name]["m_full"],
            "per_year": results[name]["per_year"].to_dict("records"),
            "ann_tov": float(results[name]["tov"].mean()*52),
        } for name in BASKETS.keys()
    }
}
with open(OUT / "round9_goldbond_stats.json","w") as f:
    json.dump(bundle, f, indent=2, ensure_ascii=False)

say("\n[done]")
