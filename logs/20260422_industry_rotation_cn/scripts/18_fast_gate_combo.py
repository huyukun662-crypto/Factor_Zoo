"""
Round 10 — fast breadth gate to catch COVID-style V-crashes.

Current MA50 gate is slow (6-12m lag) and missed 2020 Q1 COVID (strategy was
fully invested during the -15% 4-week crash). Goal: add a FAST gate that
triggers risk-off faster.

Fast gate candidates (all operate on weekly ETF data):

  FG1  %above_MA10   : share of eligible ETFs above 10-week MA, <0.30 → off
  FG2  %above_MA20   : share above 20-week MA, <0.25 → off
  FG3  mkt_rev_2w    : market 2-week return < -5% → off (stay off for 4 weeks)
  FG4  vol_expansion : rolling 4w vol > 2× rolling 26w vol → off (stay off 6w)
  FG5  mkt_dd_4w     : rolling 4-week drawdown from 4w peak < -8% → off (stay off 6w)

Combination logic:
  risk_on[t] = slow_gate[t] AND fast_gate[t]   (both must be bullish)
  risk_off   = NOT risk_on                      (fallback activates)

Applied to V7_gold and V7_gb_70_30.

Report:
  - 2020 year DD (COVID test)
  - 2022 year DD (bear test)
  - full Sharpe / Calmar / MaxDD
  - fast-gate activation rate (false-positive rate during bull 2019/2021/2025)
"""
import os, time, json
from pathlib import Path
import numpy as np, pandas as pd

OUT = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs")
say = lambda s: print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)

# ------- Load main panel + defensive -------
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
CACHE = Path("/home/user/Factor_Zoo/.cache")
bonds = pd.read_parquet(CACHE / "fund_daily_bonds.parquet").merge(
    pd.read_parquet(CACHE / "fund_adj_bonds.parquet"), on=["ts_code","trade_date"], how="left")
bonds["close_adj"] = bonds["close"] * bonds["adj_factor"].fillna(1.0)
bonds = bonds.sort_values(["ts_code","trade_date"]).reset_index(drop=True)
bonds["ret"] = bonds.groupby("ts_code")["close_adj"].pct_change()
bonds["year_week"] = bonds["trade_date"].dt.strftime("%G-%V")
bonds["gross"] = 1 + bonds["ret"].fillna(0)
bonds["cum"] = bonds.groupby("ts_code")["gross"].cumprod()
bw = (bonds.groupby(["ts_code","year_week"], sort=False)
      .agg(trade_week=("trade_date","last"), cum_w=("cum","last"))
      .reset_index().sort_values(["ts_code","trade_week"]))
bw["ret_w"] = bw.groupby("ts_code")["cum_w"].pct_change()
bw = bw.dropna(subset=["ret_w"])

all_def = pd.concat([W_def[["ts_code","trade_week","ret_w"]], bw[["ts_code","trade_week","ret_w"]]], ignore_index=True)
ret_def = all_def.pivot(index="trade_week", columns="ts_code", values="ret_w").reindex(all_dates)
if "159934.SZ" in ret_main.columns: ret_def["159934.SZ"] = ret_main["159934.SZ"]
elig_def = ret_def.notna().cumsum() >= 12

# ------- Slow gate (MA50) -------
mc = cum_main.mean(axis=1)
slow_gate = (mc > mc.rolling(50, min_periods=25).mean()).reindex(all_dates).fillna(False)

# ------- Fast gate constructors -------
def fg_breadth_ma(ma_win, thresh):
    """%eligible ETFs above own ma_win MA < thresh → off."""
    above_ma = (cum_main > cum_main.rolling(ma_win, min_periods=max(4,ma_win//2)).mean()).where(elig_main)
    n_elig = elig_main.sum(axis=1).replace(0, np.nan)
    br = above_ma.sum(axis=1) / n_elig
    return (br >= thresh).reindex(all_dates).fillna(True)  # True = on (bullish)

def fg_mkt_rev(lookback, thresh, stay_off_weeks=4):
    """Market 2w return < thresh → off for next stay_off_weeks weeks."""
    mkt_ret = cum_main.mean(axis=1).pct_change(lookback).reindex(all_dates)
    triggered = (mkt_ret < thresh).fillna(False)
    # apply stickiness: once triggered, stay off for stay_off_weeks
    off = pd.Series(False, index=all_dates)
    off_countdown = 0
    for i, t in enumerate(all_dates):
        if triggered.iloc[i]:
            off_countdown = stay_off_weeks
        if off_countdown > 0:
            off.iloc[i] = True
            off_countdown -= 1
    return ~off  # True = on

def fg_vol_expansion(short_w=4, long_w=26, ratio_thresh=2.0, stay_off_weeks=6):
    """Vol expansion regime: short_vol > ratio_thresh * long_vol → off."""
    mkt = cum_main.mean(axis=1).pct_change().reindex(all_dates)
    vol_s = mkt.rolling(short_w, min_periods=2).std()
    vol_l = mkt.rolling(long_w, min_periods=8).std()
    triggered = (vol_s > ratio_thresh * vol_l).fillna(False)
    off = pd.Series(False, index=all_dates)
    cd = 0
    for i in range(len(all_dates)):
        if triggered.iloc[i]: cd = stay_off_weeks
        if cd > 0: off.iloc[i] = True; cd -= 1
    return ~off

def fg_mkt_dd(lookback=4, thresh=-0.08, stay_off_weeks=6):
    """Market DD over rolling lookback > thresh (more negative) → off."""
    mkt_level = cum_main.mean(axis=1).reindex(all_dates)
    roll_peak = mkt_level.rolling(lookback).max()
    dd = mkt_level / roll_peak - 1
    triggered = (dd < thresh).fillna(False)
    off = pd.Series(False, index=all_dates)
    cd = 0
    for i in range(len(all_dates)):
        if triggered.iloc[i]: cd = stay_off_weeks
        if cd > 0: off.iloc[i] = True; cd -= 1
    return ~off

FAST_GATES = {
    "FG1_br10_30":   fg_breadth_ma(10, 0.30),
    "FG2_br20_25":   fg_breadth_ma(20, 0.25),
    "FG3_rev2w_m5":  fg_mkt_rev(2, -0.05, 4),
    "FG4_vol_ex":    fg_vol_expansion(4, 26, 2.0, 6),
    "FG5_mktdd_m8":  fg_mkt_dd(4, -0.08, 6),
}

# ------- Strategy builders -------
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

# ------- Run variant with combined gate and fallback -------
BASKETS = {
    "V7gold": {"159934.SZ": 1.0},
    "V7gb7030": {"159934.SZ": 0.7, "511010.SH": 0.3},
}

def apply_vol_target(pnl_raw, target=0.15, lookback=26):
    rv = pnl_raw.rolling(lookback, min_periods=8).std()*np.sqrt(52)
    return (target / rv).clip(upper=1.0).fillna(0)

def run(basket_spec, fast_gate_series):
    """fast_gate_series: True=on (bullish). Combined: risk_on = slow AND fast."""
    on = (slow_gate & fast_gate_series.reindex(all_dates).fillna(True))
    off = ~on
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
            # apply basket (normalize if some assets not eligible)
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
    pnl_net = pnl_g - tov*(5e-4)
    return pnl_net, tov, w_final, on

def perf(pnl, mask=None):
    r = pnl.dropna() if mask is None else pnl[mask].dropna()
    if len(r) < 10: return None
    yrs = len(r)/52.0
    ann = (1+r).prod()**(1/yrs)-1 if yrs>0 else np.nan
    vol = r.std()*np.sqrt(52); sh = ann/vol if vol>0 else np.nan
    eq = (1+r).cumprod(); dd = (eq/eq.cummax()-1).min()
    cal = ann/abs(dd) if dd<0 else np.nan
    return {"ann":float(ann),"vol":float(vol),"sharpe":float(sh),"max_dd":float(dd),
            "calmar":float(cal) if np.isfinite(cal) else np.nan,"n":int(len(r))}

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

# ---- Gate-only baseline (no fast gate) ----
results = {}
say(f"\n===== Baseline (slow gate only, no fast gate) =====")
fast_no = pd.Series(True, index=all_dates)  # always on
for bname, bspec in BASKETS.items():
    pnl, tov, w_final, on = run(bspec, fast_no)
    m = perf(pnl); py = per_year(pnl)
    dd2020 = py[py["year"]==2020]["dd"].iloc[0] if (py["year"]==2020).any() else np.nan
    dd2022 = py[py["year"]==2022]["dd"].iloc[0] if (py["year"]==2022).any() else np.nan
    results[f"{bname}_noFG"] = {"pnl":pnl, "tov":tov, "on":on, "perf":m, "per_year":py}
    say(f"  {bname}_noFG: Sh {m['sharpe']:.2f}  Cal {m['calmar']:.2f}  DD {m['max_dd']*100:+.2f}%  2020_DD {dd2020*100:+.2f}%  2022_DD {dd2022*100:+.2f}%  OnRate {on.mean()*100:.1f}%")

# ---- Each fast gate × each basket ----
say(f"\n===== Fast-gate × basket combinations =====")
for fg_name, fg_series in FAST_GATES.items():
    for bname, bspec in BASKETS.items():
        pnl, tov, w_final, on = run(bspec, fg_series)
        m = perf(pnl); m_is = perf(pnl, IS_MASK); m_oos = perf(pnl, OOS_MASK)
        py = per_year(pnl)
        dd2020 = py[py["year"]==2020]["dd"].iloc[0] if (py["year"]==2020).any() else np.nan
        dd2022 = py[py["year"]==2022]["dd"].iloc[0] if (py["year"]==2022).any() else np.nan
        key = f"{bname}_{fg_name}"
        results[key] = {"pnl":pnl, "tov":tov, "on":on, "perf":m, "is":m_is, "oos":m_oos,
                        "per_year":py, "fg_name": fg_name, "bname": bname}
        fg_on_rate = fg_series.mean()
        combined_on_rate = on.mean()
        say(f"  {key:24s}  Sh {m['sharpe']:.2f}  Cal {m['calmar']:.2f}  DD {m['max_dd']*100:+.2f}%  "
            f"2020 {dd2020*100:+.2f}%  2022 {dd2022*100:+.2f}%  FG_on {fg_on_rate*100:.1f}%  combined_on {combined_on_rate*100:.1f}%")

# Summary table
rows = []
for k, r in results.items():
    if "perf" not in r: continue
    py = r["per_year"]
    dd2020 = py[py["year"]==2020]["dd"].iloc[0] if (py["year"]==2020).any() else np.nan
    dd2022 = py[py["year"]==2022]["dd"].iloc[0] if (py["year"]==2022).any() else np.nan
    rows.append({
        "combo": k,
        "full_sh": r["perf"]["sharpe"], "full_cal": r["perf"]["calmar"],
        "full_dd": r["perf"]["max_dd"], "full_ann": r["perf"]["ann"],
        "dd_2020": dd2020, "dd_2022": dd2022,
        "combined_on_rate": r["on"].mean(),
    })
df = pd.DataFrame(rows).sort_values("full_dd", ascending=False)
say(f"\n===== Sorted by full_dd (least severe first) =====")
print(df.to_string(index=False))
df.to_csv(OUT / "round10_fastgate_compare.csv", index=False)

# Top 5 per-year
top_by_cal = df.sort_values("full_cal", ascending=False).head(5)
say(f"\n===== Per-year for top 5 by Calmar =====")
for k in top_by_cal["combo"]:
    py = results[k]["per_year"]
    say(f"\n--- {k} ---")
    print(py[["year","ret","sh","dd","cal"]].to_string(index=False))
    py.to_csv(OUT / f"round10_{k}_peryear.csv", index=False)

# Save equity
curves = pd.DataFrame({k: (1+r["pnl"].fillna(0)).cumprod() for k,r in results.items()})
curves.to_csv(OUT / "round10_equity_curves.csv")

# Full bundle
bundle = {
    "fast_gate_definitions": {
        "FG1_br10_30": "share of eligible ETFs above 10-week MA, <0.30 → off",
        "FG2_br20_25": "share of eligible ETFs above 20-week MA, <0.25 → off",
        "FG3_rev2w_m5": "market 2-week return < -5% → off for next 4 weeks",
        "FG4_vol_ex": "rolling 4w vol > 2× rolling 26w vol → off for 6 weeks",
        "FG5_mktdd_m8": "market 4-week drawdown < -8% → off for 6 weeks",
    },
    "combination_logic": "risk_on = slow_ma50 AND fast_gate",
    "results": {
        k: {"full":r["perf"],"is":r.get("is"),"oos":r.get("oos"),
            "per_year":r["per_year"].to_dict("records"),
            "on_rate":float(r["on"].mean())}
        for k, r in results.items()
    }
}
with open(OUT / "round10_fastgate_stats.json","w") as f:
    json.dump(bundle, f, indent=2, ensure_ascii=False)

say("[done]")
