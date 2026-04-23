"""
Round 10b — tune FG4 (vol expansion) parameters to find Pareto improvement.

Current FG4: short_w=4, long_w=26, ratio=2.0, stay_off=6
→ catches COVID but introduces false positives elsewhere (Full DD -10.1%)

Tune 4 axes:
  short_w:    [2, 3, 4]
  ratio:      [2.0, 2.5, 3.0, 3.5]
  stay_off:   [2, 3, 4, 6]
  (long_w fixed at 26)

Applied to V7_gold and V7_gb7030. Find configs with Full DD < baseline
AND 2020 DD < baseline.
"""
import time, itertools, json
from pathlib import Path
import numpy as np, pandas as pd

OUT = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs")
say = lambda s: print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)

W_main = pd.read_parquet(OUT / "etf_weekly.parquet")
uni = pd.read_csv(OUT / "etf_universe.csv")
W_main["trade_week"] = pd.to_datetime(W_main["trade_week"])
W_main = W_main[W_main["trade_week"] >= "2019-01-01"].sort_values(["trade_week","ts_code"]).reset_index(drop=True)
ret_main = W_main.pivot(index="trade_week", columns="ts_code", values="ret_w").sort_index()
turn_main = W_main.pivot(index="trade_week", columns="ts_code", values="turnover_w").sort_index()
gross_main = 1 + ret_main.fillna(0); cum_main = gross_main.cumprod()
age_main = ret_main.notna().cumsum(); elig_main = age_main >= 12
main_cols = ret_main.columns; all_dates = ret_main.index

W_def = pd.read_parquet(OUT / "defensive_weekly.parquet")
W_def["trade_week"] = pd.to_datetime(W_def["trade_week"])
CACHE = Path("/home/user/Factor_Zoo/.cache")
bonds = pd.read_parquet(CACHE / "fund_daily_bonds.parquet").merge(
    pd.read_parquet(CACHE / "fund_adj_bonds.parquet"), on=["ts_code","trade_date"], how="left")
bonds["close_adj"] = bonds["close"] * bonds["adj_factor"].fillna(1.0)
bonds = bonds.sort_values(["ts_code","trade_date"]).reset_index(drop=True)
bonds["ret"] = bonds.groupby("ts_code")["close_adj"].pct_change()
bonds["year_week"] = bonds["trade_date"].dt.strftime("%G-%V")
bonds["gross"] = 1 + bonds["ret"].fillna(0); bonds["cum"] = bonds.groupby("ts_code")["gross"].cumprod()
bw = (bonds.groupby(["ts_code","year_week"], sort=False)
      .agg(trade_week=("trade_date","last"), cum_w=("cum","last")).reset_index().sort_values(["ts_code","trade_week"]))
bw["ret_w"] = bw.groupby("ts_code")["cum_w"].pct_change(); bw = bw.dropna(subset=["ret_w"])

all_def = pd.concat([W_def[["ts_code","trade_week","ret_w"]], bw[["ts_code","trade_week","ret_w"]]], ignore_index=True)
ret_def = all_def.pivot(index="trade_week", columns="ts_code", values="ret_w").reindex(all_dates)
if "159934.SZ" in ret_main.columns: ret_def["159934.SZ"] = ret_main["159934.SZ"]
elig_def = ret_def.notna().cumsum() >= 12

mc = cum_main.mean(axis=1)
slow_gate = (mc > mc.rolling(50, min_periods=25).mean()).reindex(all_dates).fillna(False)
mkt_ret = mc.pct_change()

def fg_vol(short_w, ratio, stay_off, long_w=26):
    vs = mkt_ret.rolling(short_w, min_periods=2).std()
    vl = mkt_ret.rolling(long_w, min_periods=8).std()
    triggered = (vs > ratio * vl).fillna(False)
    off = pd.Series(False, index=all_dates); cd = 0
    for i in range(len(all_dates)):
        if triggered.iloc[i]: cd = stay_off
        if cd > 0: off.iloc[i] = True; cd -= 1
    return ~off

# ---- strategy ----
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
    score = (zscore_cs(mom4) - 1.5*zscore_cs(turn4) + 0.3*bread_df).reindex(columns=main_cols).astype(float)
    wm = np.zeros(score.shape); sv = score.values.astype(float); rv = ret_main.values.astype(float); em = elig_main.values.astype(bool)
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
    gcum = (1+gret.fillna(0)).cumprod(); gmom4 = gcum/gcum.shift(4) - 1
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

w_A = build_A(); w_G = build_G(); w_ens = 0.5*w_A + 0.5*w_G

BASKETS = {
    "V7gold": {"159934.SZ": 1.0},
    "V7gb7030": {"159934.SZ": 0.7, "511010.SH": 0.3},
}

def apply_vol_target(pnl_raw, target=0.15, lookback=26):
    rv = pnl_raw.rolling(lookback, min_periods=8).std()*np.sqrt(52)
    return (target / rv).clip(upper=1.0).fillna(0)

def run(basket_spec, fast_gate):
    on = (slow_gate & fast_gate.reindex(all_dates).fillna(True))
    all_codes = sorted(set(main_cols) | set(ret_def.columns))
    ret_all = pd.DataFrame(index=all_dates, columns=all_codes, dtype=float)
    for c in main_cols: ret_all[c] = ret_main[c]
    for c in ret_def.columns:
        if c not in main_cols: ret_all[c] = ret_def[c]
    ret_all = ret_all.astype(float)
    w_mat = np.zeros((len(all_dates), len(all_codes)))
    col_idx = {c:i for i,c in enumerate(all_codes)}
    for ti in range(len(all_dates)):
        if on.iloc[ti]:
            for c in main_cols:
                w = w_ens.iloc[ti][c]
                if w > 0: w_mat[ti, col_idx[c]] = w
        else:
            elig_row = {c: elig_def.loc[all_dates[ti], c] for c in basket_spec if c in elig_def.columns}
            ok = {c: basket_spec[c] for c in basket_spec if elig_row.get(c, False)}
            if ok:
                tot = sum(ok.values())
                for c, wt in ok.items():
                    if c in col_idx: w_mat[ti, col_idx[c]] = wt/tot
    w_df = pd.DataFrame(w_mat, index=all_dates, columns=all_codes)
    pnl_raw = (w_df.shift(1) * ret_all).sum(axis=1)
    scale = apply_vol_target(pnl_raw, 0.15, 26)
    w_final = w_df.mul(scale.reindex(w_df.index), axis=0)
    w_exec = w_final.shift(1)
    pnl_g = (w_exec * ret_all).sum(axis=1)
    tov = (w_exec.fillna(0).diff().abs().sum(axis=1)/2).fillna(0)
    return pnl_g - tov*(5e-4), tov, on

def perf_all(pnl):
    r = pnl.dropna(); yrs = len(r)/52.0
    ann = (1+r).prod()**(1/yrs)-1 if yrs>0 else np.nan
    vol = r.std()*np.sqrt(52); sh = ann/vol if vol>0 else np.nan
    eq = (1+r).cumprod(); dd = (eq/eq.cummax()-1).min()
    cal = ann/abs(dd) if dd<0 else np.nan
    # per year dds
    r.index = pd.to_datetime(r.index)
    per_year_dd = {}
    for yr, grp in r.groupby(r.index.year):
        if len(grp)<10: continue
        eq_y = (1+grp).cumprod(); dd_y = (eq_y/eq_y.cummax()-1).min()
        per_year_dd[int(yr)] = float(dd_y)
    return {"sh":float(sh),"cal":float(cal) if np.isfinite(cal) else np.nan,
            "dd":float(dd),"ann":float(ann),
            "dd_2020":per_year_dd.get(2020, np.nan),
            "dd_2022":per_year_dd.get(2022, np.nan)}

# ---- Grid ----
rows = []
for short_w in [2, 3, 4]:
    for ratio in [2.0, 2.5, 3.0, 3.5]:
        for stay_off in [2, 3, 4, 6]:
            fg = fg_vol(short_w, ratio, stay_off)
            fg_on_rate = fg.mean()
            for bname, bspec in BASKETS.items():
                pnl, tov, on = run(bspec, fg)
                p = perf_all(pnl)
                rows.append({
                    "basket": bname, "short_w":short_w, "ratio":ratio, "stay_off":stay_off,
                    "fg_on_rate": float(fg_on_rate),
                    "combined_on_rate": float(on.mean()),
                    "full_sh": p["sh"], "full_cal": p["cal"], "full_dd": p["dd"],
                    "dd_2020": p["dd_2020"], "dd_2022": p["dd_2022"],
                    "full_ann": p["ann"],
                    "ann_tov": float(tov.mean()*52),
                })
df = pd.DataFrame(rows)
df.to_csv(OUT / "round10b_fg4_tune.csv", index=False)

# Pareto: Full DD <= baseline AND 2020 DD < baseline
BASE = {"V7gold": {"full_dd":-0.0889,"dd_2020":-0.0889,"dd_2022":-0.0828,"sh":1.91},
        "V7gb7030": {"full_dd":-0.0889,"dd_2020":-0.0889,"dd_2022":-0.0569,"sh":1.81}}

say(f"===== Pareto improvements (Full DD ≤ baseline AND 2020 DD < baseline AND Sh ≥ baseline - 0.1) =====")
for bname in BASKETS:
    sub = df[df["basket"]==bname]
    base = BASE[bname]
    pareto = sub[(sub["full_dd"] >= base["full_dd"] - 1e-4) &
                 (sub["dd_2020"] > base["dd_2020"] + 1e-4) &
                 (sub["full_sh"] >= base["sh"] - 0.1)].sort_values("full_sh", ascending=False)
    say(f"\n--- {bname} (baseline Sh={base['sh']:.2f}, DD={base['full_dd']*100:.1f}%, 2020 DD={base['dd_2020']*100:.1f}%) ---")
    if len(pareto)==0:
        say("  (none)")
    else:
        print(pareto[["short_w","ratio","stay_off","fg_on_rate","full_sh","full_cal","full_dd","dd_2020","dd_2022","full_ann"]].to_string(index=False))

# Also show: best 2020 DD on each basket
say(f"\n===== Best by 2020 DD (regardless of other metrics) =====")
for bname in BASKETS:
    sub = df[df["basket"]==bname].nsmallest(5, "dd_2020")  # most negative first? we want least negative
    sub = df[df["basket"]==bname].sort_values("dd_2020", ascending=False).head(8)  # least severe DD first
    say(f"\n--- {bname} ---")
    print(sub[["short_w","ratio","stay_off","full_sh","full_cal","full_dd","dd_2020","dd_2022","full_ann"]].to_string(index=False))

# Full top 10 by full_sh with dd_2020 improved
say(f"\n===== Top 10 by Full Sharpe, must have dd_2020 > -8.89% =====")
for bname in BASKETS:
    sub = df[(df["basket"]==bname) & (df["dd_2020"] > -0.085)].nlargest(10, "full_sh")
    say(f"\n--- {bname} ---")
    print(sub[["short_w","ratio","stay_off","fg_on_rate","full_sh","full_cal","full_dd","dd_2020","dd_2022","full_ann"]].to_string(index=False))

say("[done]")
