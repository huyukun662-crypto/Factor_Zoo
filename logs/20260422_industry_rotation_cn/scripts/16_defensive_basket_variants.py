"""
Round 8 — defensive basket fallbacks for V7.

Strategy: when gate is OFF (market in downtrend), replace 100% gold fallback
with a DEFENSIVE BASKET. Test multiple compositions.

Defensive assets available:
  Existing in 34-ETF universe (main strategy universe):
    - 黄金ETF    159934.SZ (2015+)
    - 石油ETF    561360.SH (2023+, too short)
  New assets fetched to .cache/fund_daily_defensive.parquet:
    - 铜ETF     159981.SZ (2020+)
    - 白银LOF    161226.SZ (2015+)
    - 恒生ETF    159920.SZ (2015+) — HK tracker
    - 纳指ETF    159941.SZ (2015+) — US tech tracker
  Additional oil via LOF (need separate fetch):
    - 华宝油气   162411.SZ (2015+)

Variants tested:
  V7_baseline       : 100% gold (reference, the current V7)
  V7_metals         : eq-wt (gold, silver, copper if eligible)
  V7_global         : eq-wt (gold, silver, HK, US)
  V7_full_defense   : eq-wt (gold, silver, copper, HK, US, oil)
  V7_weighted       : 40% gold + 20% silver + 20% US + 20% HK (fixed;
                       fallback if some unavail: redistribute)
  V7_rp             : inverse-vol weighted among eligible defensives
                       (26w trailing vol, normalized)
  V7_gold_half_safe : 50% gold + 50% (eq-wt US+HK+silver)
"""
import json, os, time
from pathlib import Path
import numpy as np, pandas as pd
import tushare as ts

CACHE = Path("/home/user/Factor_Zoo/.cache")
OUT = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs")
say = lambda s: print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)

# -------- 0. ensure 162411 is fetched --------
secret = Path("/home/user/Factor_Zoo/.secrets/tushare.env")
if not os.environ.get("TUSHARE_TOKEN") and secret.exists():
    for line in secret.read_text().splitlines():
        if line.startswith("TUSHARE_TOKEN="):
            os.environ["TUSHARE_TOKEN"] = line.split("=",1)[1].strip()
OIL_FD = CACHE / "fund_daily_oil_lof.parquet"
if not OIL_FD.exists():
    pro = ts.pro_api(os.environ["TUSHARE_TOKEN"])
    rows_d, rows_a = [], []
    for code in ["162411.SZ"]:
        d = pro.fund_daily(ts_code=code, start_date="20150101", end_date="20260422")
        rows_d.append(d)
        a = pro.fund_adj(ts_code=code, start_date="20150101", end_date="20260422")
        rows_a.append(a)
    fd = pd.concat(rows_d, ignore_index=True); fd["trade_date"] = pd.to_datetime(fd["trade_date"])
    fa = pd.concat(rows_a, ignore_index=True); fa["trade_date"] = pd.to_datetime(fa["trade_date"])
    pd.merge(fd, fa, on=["ts_code","trade_date"], how="left").to_parquet(OIL_FD)
    say(f"fetched 162411 华宝油气")

# -------- 1. Load main ETF panel --------
W_main = pd.read_parquet(OUT / "etf_weekly.parquet")
uni = pd.read_csv(OUT / "etf_universe.csv")
code2name = dict(zip(uni["ts_code"], uni["name"]))

W_main["trade_week"] = pd.to_datetime(W_main["trade_week"])
W_main = W_main[W_main["trade_week"] >= "2019-01-01"].sort_values(["trade_week","ts_code"]).reset_index(drop=True)
ret_main = W_main.pivot(index="trade_week", columns="ts_code", values="ret_w").sort_index()
turn_main = W_main.pivot(index="trade_week", columns="ts_code", values="turnover_w").sort_index()
gross_main = 1 + ret_main.fillna(0); cum_main = gross_main.cumprod()
age_main = ret_main.notna().cumsum(); elig_main = age_main >= 12
main_cols = ret_main.columns
all_dates = ret_main.index

# -------- 2. Load defensive panel + oil --------
W_def = pd.read_parquet(OUT / "defensive_weekly.parquet")
W_def["trade_week"] = pd.to_datetime(W_def["trade_week"])

# Add oil (162411) as weekly
oil_daily = pd.read_parquet(OIL_FD)
oil_daily["close_adj"] = oil_daily["close"] * oil_daily["adj_factor"].fillna(1.0)
oil_daily = oil_daily.sort_values(["ts_code","trade_date"])
oil_daily["ret"] = oil_daily.groupby("ts_code")["close_adj"].pct_change()
oil_daily["year_week"] = oil_daily["trade_date"].dt.strftime("%G-%V")
oil_daily["gross"] = 1 + oil_daily["ret"].fillna(0)
oil_daily["cum"] = oil_daily.groupby("ts_code")["gross"].cumprod()
oil_w = (oil_daily.groupby(["ts_code","year_week"], sort=False)
         .agg(trade_week=("trade_date","last"), cum_w=("cum","last"))
         .reset_index().sort_values(["ts_code","trade_week"]))
oil_w["ret_w"] = oil_w.groupby("ts_code")["cum_w"].pct_change()
oil_w = oil_w.dropna(subset=["ret_w"])
W_def2 = pd.concat([W_def[["ts_code","trade_week","ret_w"]], oil_w[["ts_code","trade_week","ret_w"]]],
                   ignore_index=True)

# Defensive wide
ret_def = W_def2.pivot(index="trade_week", columns="ts_code", values="ret_w")
ret_def = ret_def.reindex(all_dates)

# Map defensive asset tags
DEF_NAMES = {
    "159934.SZ":"黄金",   # already in main universe but listed here for convenience
    "161226.SZ":"白银",
    "159981.SZ":"铜",
    "159920.SZ":"港股(恒生)",
    "159941.SZ":"美科技(纳指)",
    "162411.SZ":"海外油气",
}

# Combine defensive ret with main-universe gold (since gold is in main universe too)
# For consistency, pull gold ret from main panel
if "159934.SZ" in ret_main.columns and "159934.SZ" not in ret_def.columns:
    ret_def["159934.SZ"] = ret_main["159934.SZ"]

# Eligibility per defensive: ≥12 weeks of history
age_def = ret_def.notna().cumsum()
elig_def = age_def >= 12

say(f"\n===== Defensive asset coverage =====")
for c in DEF_NAMES:
    if c not in ret_def.columns:
        say(f"  {DEF_NAMES[c]:18s} MISSING"); continue
    n = ret_def[c].notna().sum()
    first_elig = elig_def.index[elig_def[c]].min() if elig_def[c].any() else None
    say(f"  {DEF_NAMES[c]:18s} ({c})  n={n}  first eligible={first_elig.date() if first_elig else 'N/A'}")

# -------- 3. Build main strategy legs (A + G ensemble) --------
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
    wm = np.zeros(score.shape)
    sv = score.values.astype(float); rv = ret_main.values.astype(float); em = elig_main.values.astype(bool)
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

# -------- 4. Basket fallback constructors --------
def eligible_from_list(t, assets):
    return [a for a in assets if a in elig_def.columns and elig_def.loc[t, a]]

BASKETS = {
    "V7_gold":         ["159934.SZ"],                                   # baseline
    "V7_metals":       ["159934.SZ", "161226.SZ", "159981.SZ"],         # gold+silver+copper
    "V7_global":       ["159934.SZ", "161226.SZ", "159920.SZ", "159941.SZ"],  # +HK+US
    "V7_full_def":     ["159934.SZ", "161226.SZ", "159981.SZ", "159920.SZ", "159941.SZ", "162411.SZ"],
    "V7_gold_half":    ["159934.SZ", "161226.SZ", "159920.SZ", "159941.SZ"],  # gold 50% + eq-rest 50%
}

def build_defensive_weights(basket_name, t_idx, w_off_scalar=1.0):
    """Return a dict {code: weight} that sums to w_off_scalar for defensive holdings at time t."""
    t = all_dates[t_idx]
    if basket_name == "V7_gold":
        if elig_def.loc[t, "159934.SZ"]:
            return {"159934.SZ": w_off_scalar}
        return {}
    if basket_name == "V7_metals":
        elig_members = eligible_from_list(t, ["159934.SZ","161226.SZ","159981.SZ"])
        if not elig_members: return {}
        wt = w_off_scalar / len(elig_members)
        return {c: wt for c in elig_members}
    if basket_name == "V7_global":
        elig_members = eligible_from_list(t, ["159934.SZ","161226.SZ","159920.SZ","159941.SZ"])
        if not elig_members: return {}
        wt = w_off_scalar / len(elig_members)
        return {c: wt for c in elig_members}
    if basket_name == "V7_full_def":
        elig_members = eligible_from_list(t, ["159934.SZ","161226.SZ","159981.SZ","159920.SZ","159941.SZ","162411.SZ"])
        if not elig_members: return {}
        wt = w_off_scalar / len(elig_members)
        return {c: wt for c in elig_members}
    if basket_name == "V7_gold_half":
        # 50% gold (if eligible), 50% spread among {silver, HK, US} eligible
        if not elig_def.loc[t, "159934.SZ"]:
            # gold not elig → use full_def
            return build_defensive_weights("V7_full_def", t_idx, w_off_scalar)
        others = eligible_from_list(t, ["161226.SZ","159920.SZ","159941.SZ"])
        out = {"159934.SZ": 0.5 * w_off_scalar}
        if others:
            wt = 0.5 * w_off_scalar / len(others)
            for c in others: out[c] = wt
        else:
            # no others → full gold
            out["159934.SZ"] = w_off_scalar
        return out
    return {}

# -------- 5. Build and backtest each variant --------
def apply_vol_target(pnl_series_raw, target=0.15, lookback=26):
    rv = pnl_series_raw.rolling(lookback, min_periods=8).std()*np.sqrt(52)
    return (target / rv).clip(upper=1.0).fillna(0)

def run_variant(basket_name, cost_bps=5):
    """Build weight matrix across both main ETFs and defensive assets."""
    # Combine columns: all main + defensive (union)
    all_codes = sorted(set(main_cols) | set(ret_def.columns))
    # Build ret_all (combined)
    ret_all = pd.DataFrame(index=all_dates, columns=all_codes, dtype=float)
    for c in main_cols:
        ret_all[c] = ret_main[c]
    for c in ret_def.columns:
        if c not in main_cols:  # if in main, main ret takes precedence
            ret_all[c] = ret_def[c]
        elif c == "159934.SZ":
            pass  # gold already in main
    ret_all = ret_all.astype(float)
    ret_vals = ret_all.values

    w_mat = np.zeros((len(all_dates), len(all_codes)))
    col_idx = {c:i for i,c in enumerate(all_codes)}

    # Step A: when gate ON, put ensemble weights
    # Step B: when gate OFF, put basket weights
    for ti in range(len(all_dates)):
        if gate.iloc[ti]:
            for c in main_cols:
                w = w_ens.iloc[ti][c]
                if w > 0: w_mat[ti, col_idx[c]] = w
        else:
            basket = build_defensive_weights(basket_name, ti, 1.0)
            for c, wt in basket.items():
                if c in col_idx: w_mat[ti, col_idx[c]] = wt

    w_df = pd.DataFrame(w_mat, index=all_dates, columns=all_codes)

    # Vol target using raw (pre-scaled) pnl
    pnl_raw = (w_df.shift(1) * ret_all).sum(axis=1)
    scale = apply_vol_target(pnl_raw, 0.15, 26)
    w_final = w_df.mul(scale.reindex(w_df.index), axis=0)

    # realized pnl + cost
    w_exec = w_final.shift(1)
    pnl_g = (w_exec * ret_all).sum(axis=1)
    tov = (w_exec.fillna(0).diff().abs().sum(axis=1)/2).fillna(0)
    pnl_net = pnl_g - tov*(cost_bps/1e4)
    return pnl_net, tov, w_final, scale

def perf(pnl, mask=None):
    r = pnl.dropna() if mask is None else pnl[mask].dropna()
    if len(r) < 10: return None
    yrs = len(r)/52.0
    ann = (1+r).prod()**(1/yrs)-1 if yrs>0 else np.nan
    vol = r.std()*np.sqrt(52); sh = ann/vol if vol>0 else np.nan
    eq = (1+r).cumprod(); peak = eq.cummax()
    dd = (eq/peak-1).min()
    # Sortino
    down = r[r<0]
    dv = down.std()*np.sqrt(52) if len(down)>0 else np.nan
    sortino = ann/dv if dv and dv>0 else np.nan
    cal = ann/abs(dd) if dd<0 else np.nan
    return {"ann":float(ann),"vol":float(vol),"sharpe":float(sh),"sortino":float(sortino) if np.isfinite(sortino) else np.nan,
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

results = {}
summary = []
say(f"\n===== Running {len(BASKETS)} variants =====")
for name in BASKETS.keys():
    pnl, tov, w_final, scale = run_variant(name)
    m_is = perf(pnl, IS_MASK); m_oos = perf(pnl, OOS_MASK); m_full = perf(pnl)
    results[name] = {"pnl":pnl, "tov":tov, "w_final":w_final, "scale":scale,
                     "m_is":m_is, "m_oos":m_oos, "m_full":m_full,
                     "per_year": per_year(pnl)}
    summary.append({
        "basket": name,
        "is_sh":m_is["sharpe"],"is_cal":m_is["calmar"],"is_dd":m_is["max_dd"],
        "oos_sh":m_oos["sharpe"],"oos_cal":m_oos["calmar"],"oos_dd":m_oos["max_dd"],
        "full_sh":m_full["sharpe"],"full_sortino":m_full["sortino"],
        "full_cal":m_full["calmar"],"full_dd":m_full["max_dd"],"full_ann":m_full["ann"],"full_vol":m_full["vol"],
        "ann_tov":float(tov.mean()*52),
    })
    say(f"  {name:15s}  Full Sh={m_full['sharpe']:.2f}  Cal={m_full['calmar']:.2f}  DD={m_full['max_dd']*100:+.2f}%  AnnRet={m_full['ann']*100:+.1f}%")

df = pd.DataFrame(summary).sort_values("full_cal", ascending=False)
say(f"\n===== Summary (sorted by full_calmar) =====")
print(df.to_string(index=False))
df.to_csv(OUT / "round8_basket_compare.csv", index=False)

# per-year for all variants
say(f"\n===== Per-year comparison =====")
for name in BASKETS.keys():
    py = results[name]["per_year"]
    say(f"\n--- {name} ---")
    print(py[["year","ret","sh","dd","cal","n"]].to_string(index=False))
    py.to_csv(OUT / f"round8_{name}_peryear.csv", index=False)

# Key: what each basket does in 2022 and 2020 (bear years)
say(f"\n===== Stress-year comparison: 2020 (COVID Q1) & 2022 (bear) =====")
stress = {"year": [2020, 2022]}
for name in BASKETS.keys():
    py = results[name]["per_year"]
    for year in [2020, 2022]:
        row = py[py["year"]==year]
        stress.setdefault(f"{name}_ret", []).append(float(row["ret"].iloc[0]) if len(row) else np.nan)
        stress.setdefault(f"{name}_dd", []).append(float(row["dd"].iloc[0]) if len(row) else np.nan)
s_df = pd.DataFrame(stress)
print(s_df.to_string(index=False))
s_df.to_csv(OUT / "round8_stress_years.csv", index=False)

# Save equity curves
curves = pd.DataFrame({name: (1+r["pnl"].fillna(0)).cumprod() for name, r in results.items()})
curves.to_csv(OUT / "round8_equity_curves.csv")

# Save full JSON bundle
bundle = {
    "baskets": BASKETS,
    "defensive_codes": DEF_NAMES,
    "variants": {
        name: {
            "is": results[name]["m_is"], "oos": results[name]["m_oos"], "full": results[name]["m_full"],
            "per_year": results[name]["per_year"].to_dict("records"),
            "ann_turnover": float(results[name]["tov"].mean()*52),
        } for name in BASKETS.keys()
    }
}
with open(OUT / "round8_basket_stats.json", "w") as f:
    json.dump(bundle, f, indent=2, ensure_ascii=False)

say("[done]")
