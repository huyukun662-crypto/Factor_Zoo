"""
Head-to-head detailed comparison: V7_gold vs V7_gb7030_FG4(4,2.5,6).
Focus on Sortino and downside-risk metrics.
"""
import time
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
      .agg(trade_week=("trade_date","last"), cum_w=("cum","last"))
      .reset_index().sort_values(["ts_code","trade_week"]))
bw["ret_w"] = bw.groupby("ts_code")["cum_w"].pct_change(); bw = bw.dropna(subset=["ret_w"])
all_def = pd.concat([W_def[["ts_code","trade_week","ret_w"]], bw[["ts_code","trade_week","ret_w"]]], ignore_index=True)
ret_def = all_def.pivot(index="trade_week", columns="ts_code", values="ret_w").reindex(all_dates)
if "159934.SZ" in ret_main.columns: ret_def["159934.SZ"] = ret_main["159934.SZ"]
elig_def = ret_def.notna().cumsum() >= 12

# signals
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

mc = cum_main.mean(axis=1)
slow_gate = (mc > mc.rolling(50, min_periods=25).mean()).reindex(all_dates).fillna(False)

def fg_vol(short_w, ratio, stay_off, long_w=26):
    mkt_ret = mc.pct_change()
    vs = mkt_ret.rolling(short_w, min_periods=2).std()
    vl = mkt_ret.rolling(long_w, min_periods=8).std()
    triggered = (vs > ratio * vl).fillna(False)
    off = pd.Series(False, index=all_dates); cd = 0
    for i in range(len(all_dates)):
        if triggered.iloc[i]: cd = stay_off
        if cd > 0: off.iloc[i] = True; cd -= 1
    return ~off

fast_none = pd.Series(True, index=all_dates)
fast_fg4 = fg_vol(4, 2.5, 6)

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
    rv26 = pnl_raw.rolling(26, min_periods=8).std()*np.sqrt(52)
    scale = (0.15 / rv26).clip(upper=1.0).fillna(0)
    w_final = w_df.mul(scale.reindex(w_df.index), axis=0)
    w_exec = w_final.shift(1)
    pnl_g = (w_exec * ret_all).sum(axis=1)
    tov = (w_exec.fillna(0).diff().abs().sum(axis=1)/2).fillna(0)
    return pnl_g - tov*(5e-4), tov

def compute_sortino_bundle(pnl, label):
    r = pnl.dropna()
    yrs = len(r)/52.0
    ann = (1+r).prod()**(1/yrs)-1
    vol = r.std()*np.sqrt(52)
    sharpe = ann / vol if vol>0 else np.nan
    # Downside (MAR=0)
    down = r[r < 0]
    down_vol = down.std()*np.sqrt(52) if len(down) > 0 else np.nan
    sortino = ann / down_vol if down_vol and down_vol > 0 else np.nan
    # Sortino MAR=risk-free~2% annual (China 10y avg)
    mar_w = 0.02 / 52
    down_mar = r[r < mar_w] - mar_w
    down_mar_vol = np.sqrt((down_mar**2).mean()) * np.sqrt(52) if len(down_mar)>0 else np.nan
    sortino_mar = (ann - 0.02) / down_mar_vol if down_mar_vol and down_mar_vol > 0 else np.nan
    # semideviation (proper)
    semi_dev = np.sqrt(np.mean(np.minimum(r - 0, 0)**2)) * np.sqrt(52)
    sortino_semi = ann / semi_dev if semi_dev > 0 else np.nan
    # Other risk metrics
    eq = (1+r).cumprod(); dd = (eq/eq.cummax()-1).min()
    calmar = ann / abs(dd) if dd < 0 else np.nan
    # Ulcer / Pain index
    dd_series = eq/eq.cummax() - 1
    ulcer = np.sqrt(np.mean(dd_series**2))
    martin = ann / ulcer if ulcer > 0 else np.nan
    # Downside stats
    worst_week = r.min()
    neg_weeks = (r < 0).sum()
    neg_share = (r < 0).mean()
    mean_neg = r[r<0].mean()
    # VaR/CVaR
    var95 = r.quantile(0.05); cvar95 = r[r<=var95].mean()
    var99 = r.quantile(0.01); cvar99 = r[r<=var99].mean()
    # Skew / kurt
    skew = r.skew(); kurt = r.kurt()
    # per year sortino
    r_t = r.copy(); r_t.index = pd.to_datetime(r_t.index); py_sortino = {}
    for yr, grp in r_t.groupby(r_t.index.year):
        if len(grp) < 10: continue
        annr = (1+grp).prod()**(52/len(grp))-1
        dn = grp[grp<0]
        dv = dn.std()*np.sqrt(52) if len(dn)>0 else np.nan
        py_sortino[int(yr)] = float(annr/dv) if dv and dv>0 else np.nan

    return {
        "label": label, "n_weeks": int(len(r)), "years": float(yrs),
        "ann_ret": float(ann), "vol": float(vol), "sharpe": float(sharpe),
        "downside_vol_MAR0": float(down_vol) if down_vol and np.isfinite(down_vol) else None,
        "sortino_MAR0": float(sortino) if sortino and np.isfinite(sortino) else None,
        "sortino_MAR2pct": float(sortino_mar) if sortino_mar and np.isfinite(sortino_mar) else None,
        "sortino_semidev": float(sortino_semi) if sortino_semi and np.isfinite(sortino_semi) else None,
        "max_dd": float(dd), "calmar": float(calmar) if np.isfinite(calmar) else None,
        "ulcer_index": float(ulcer),
        "martin_ratio": float(martin) if np.isfinite(martin) else None,
        "neg_weeks": int(neg_weeks), "pct_neg_weeks": float(neg_share),
        "mean_neg_week_ret": float(mean_neg) if np.isfinite(mean_neg) else None,
        "worst_week": float(worst_week),
        "var95_weekly": float(var95), "cvar95_weekly": float(cvar95),
        "var99_weekly": float(var99), "cvar99_weekly": float(cvar99),
        "skew": float(skew), "kurt_excess": float(kurt),
        "sortino_by_year": py_sortino,
    }

# Run both
pnl_gold, tov_gold = run({"159934.SZ": 1.0}, fast_none)
pnl_gb, tov_gb = run({"159934.SZ": 0.7, "511010.SH": 0.3}, fast_fg4)

b_gold = compute_sortino_bundle(pnl_gold, "V7_gold")
b_gb = compute_sortino_bundle(pnl_gb, "V7_gb7030_FG4(4,2.5,6)")

# Pretty print side-by-side
def fmt(v, pct=False, dec=3):
    if v is None or (isinstance(v, float) and not np.isfinite(v)): return "N/A"
    if pct: return f"{v*100:+.2f}%"
    return f"{v:+.{dec}f}"

say("\n" + "="*78)
say(f"{'METRIC':<32}{'V7_gold':>22}{'V7_gb7030 + FG4':>22}")
say("="*78)
rows = [
    ("n_weeks",                    b_gold["n_weeks"],          b_gb["n_weeks"],          "int"),
    ("ann_ret",                    b_gold["ann_ret"],          b_gb["ann_ret"],          "pct"),
    ("vol (total)",                b_gold["vol"],              b_gb["vol"],              "pct"),
    ("Sharpe",                     b_gold["sharpe"],           b_gb["sharpe"],           "float"),
    ("Sortino (MAR=0, downvol)",   b_gold["sortino_MAR0"],     b_gb["sortino_MAR0"],     "float"),
    ("Sortino (MAR=2% annual)",    b_gold["sortino_MAR2pct"],  b_gb["sortino_MAR2pct"],  "float"),
    ("Sortino (semi-deviation)",   b_gold["sortino_semidev"],  b_gb["sortino_semidev"],  "float"),
    ("Downside vol (MAR=0)",       b_gold["downside_vol_MAR0"],b_gb["downside_vol_MAR0"],"pct"),
    ("Max Drawdown",               b_gold["max_dd"],           b_gb["max_dd"],           "pct"),
    ("Calmar",                     b_gold["calmar"],           b_gb["calmar"],           "float"),
    ("Ulcer index (√mean(DD²))",   b_gold["ulcer_index"],      b_gb["ulcer_index"],      "pct"),
    ("Martin ratio (ann_ret/UI)",  b_gold["martin_ratio"],     b_gb["martin_ratio"],     "float"),
    ("% negative weeks",           b_gold["pct_neg_weeks"],    b_gb["pct_neg_weeks"],    "pct"),
    ("mean negative-week ret",     b_gold["mean_neg_week_ret"],b_gb["mean_neg_week_ret"],"pct"),
    ("worst weekly return",        b_gold["worst_week"],       b_gb["worst_week"],       "pct"),
    ("VaR 95% (weekly)",           b_gold["var95_weekly"],     b_gb["var95_weekly"],     "pct"),
    ("CVaR 95% (weekly)",          b_gold["cvar95_weekly"],    b_gb["cvar95_weekly"],    "pct"),
    ("VaR 99% (weekly)",           b_gold["var99_weekly"],     b_gb["var99_weekly"],     "pct"),
    ("CVaR 99% (weekly)",          b_gold["cvar99_weekly"],    b_gb["cvar99_weekly"],    "pct"),
    ("skewness",                   b_gold["skew"],             b_gb["skew"],             "float"),
    ("excess kurtosis",            b_gold["kurt_excess"],      b_gb["kurt_excess"],      "float"),
]
for name, v1, v2, kind in rows:
    if kind == "int":
        s1, s2 = f"{v1:>15d}", f"{v2:>15d}"
    elif kind == "pct":
        s1, s2 = f"{fmt(v1, pct=True):>15s}", f"{fmt(v2, pct=True):>15s}"
    else:
        s1, s2 = f"{fmt(v1):>15s}", f"{fmt(v2):>15s}"
    say(f"{name:<32}{s1:>22}{s2:>22}")

say("\n===== Sortino by year =====")
years = sorted(set(list(b_gold['sortino_by_year'].keys()) + list(b_gb['sortino_by_year'].keys())))
say(f"{'year':<8}{'V7_gold':>14}{'V7_gb7030_FG4':>18}{'Δ':>10}")
for yr in years:
    v1 = b_gold['sortino_by_year'].get(yr)
    v2 = b_gb['sortino_by_year'].get(yr)
    delta = (v2 - v1) if (v1 is not None and v2 is not None and np.isfinite(v1) and np.isfinite(v2)) else None
    s1 = f"{v1:+.3f}" if v1 is not None else "N/A"
    s2 = f"{v2:+.3f}" if v2 is not None else "N/A"
    sd = f"{delta:+.3f}" if delta is not None else ""
    say(f"{yr:<8}{s1:>14}{s2:>18}{sd:>10}")

# Save
import json
with open(OUT / "round10c_v7gold_vs_v7gb7030fg4_sortino.json", "w") as f:
    json.dump({"V7_gold": b_gold, "V7_gb7030_FG4": b_gb}, f, indent=2, ensure_ascii=False)
say("\n[done]")
