"""
Round 7c — full-sample comprehensive statistics for V3 and V7.

V3 = A_tuned_v1 (top-4 penalized) + 黄金ETF fallback + 15% vol target
V7 = Ensemble (0.5*A + 0.5*G_top3) + 黄金ETF fallback + 15% vol target

Outputs:
  v3_v7_full_stats.json
  v3_v7_monthly.csv
  v3_v7_drawdowns.csv
  v3_v7_holdings_weighted.csv
  v3_v7_full_stats.md
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

def build_A_weights():
    mom4 = cum / cum.shift(4) - 1
    turn4 = turn.rolling(4, min_periods=2).mean()
    br_s = ((cum > cum.rolling(20, min_periods=8).mean()).where(elig).sum(axis=1) /
            elig.sum(axis=1).replace(0, np.nan))
    br_z = (br_s - br_s.rolling(52, min_periods=20).mean()) / br_s.rolling(52, min_periods=20).std()
    bread_df = pd.DataFrame({c: br_z for c in cols})
    score = zscore_cs(mom4) - 1.5*zscore_cs(turn4) + 0.3*bread_df
    wm = np.zeros(score.shape, dtype=float)
    sv = score.values.astype(float); rv = ret.values.astype(float); em = elig.values.astype(bool)
    for ti in range(sv.shape[0]):
        s = sv[ti]; v = np.isfinite(s) & np.isfinite(rv[ti]) & em[ti]
        if v.sum() < 4: continue
        s_v = np.where(v, s, -np.inf)
        ix = np.argpartition(-s_v, 4)[:4]
        wm[ti, ix] = 0.25
    return pd.DataFrame(wm, index=score.index, columns=cols)

def build_G_weights():
    gnames = sorted(set(uni["group"].dropna()))
    gret = pd.DataFrame(0.0, index=ret.index, columns=gnames)
    for g in gnames:
        codes_g = [c for c in uni[uni["group"]==g]["ts_code"] if c in cols]
        v = elig[codes_g]
        gret[g] = ret[codes_g].where(v).mean(axis=1)
    gcum = (1+gret.fillna(0)).cumprod()
    gmom4 = gcum/gcum.shift(4) - 1
    mom4_etf = cum / cum.shift(4) - 1
    wm = np.zeros((len(ret), len(cols)), dtype=float)
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
            wm[ti, cols.get_loc(c)] = nw
    return pd.DataFrame(wm, index=ret.index, columns=cols)

def make_gate(ma=50):
    mc = cum.mean(axis=1)
    return (mc > mc.rolling(ma, min_periods=ma//2).mean()).reindex(ret.index).fillna(False)

def apply_gate_gold(w_raw, gate):
    w = w_raw.copy()
    off = ~gate
    w.loc[off] = 0.0
    gold_ok = elig[GOLD].fillna(False)
    for t in w.index[off & gold_ok]:
        w.at[t, GOLD] = 1.0
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
    return pnl_g - tov*(cost_bps/1e4), tov, w_exec

# ---- Build V3 and V7 ----
w_A = build_A_weights()
w_G = build_G_weights()
gate50 = make_gate(50)

w_v3 = apply_gate_gold(w_A, gate50)
w_v3 = apply_vol_target(w_v3, 0.15, 26)
pnl_v3, tov_v3, wexec_v3 = run_bt(w_v3, 5)

w_v7 = apply_gate_gold(0.5*w_A + 0.5*w_G, gate50)
w_v7 = apply_vol_target(w_v7, 0.15, 26)
pnl_v7, tov_v7, wexec_v7 = run_bt(w_v7, 5)

# ---- Metrics utilities ----
def full_stats(pnl, mask=None, label=""):
    r = pnl.dropna() if mask is None else pnl[mask].dropna()
    if len(r) < 10:
        return None
    yrs = len(r)/52.0
    # returns
    ann_ret = (1+r).prod()**(1/yrs)-1
    vol = r.std()*np.sqrt(52)
    sh = ann_ret / vol if vol>0 else np.nan
    # drawdown
    eq = (1+r).cumprod()
    peak = eq.cummax()
    dd_series = eq/peak - 1
    dd = dd_series.min()
    # DD recovery
    trough_idx = dd_series.idxmin()
    # Find peak before trough
    peak_before_trough = peak.loc[:trough_idx].iloc[-1]
    peak_date = peak.loc[:trough_idx].idxmax()
    # Find recovery
    after = eq.loc[trough_idx:]
    recovered = after[after >= peak_before_trough]
    if len(recovered) > 0:
        recovery_date = recovered.index[0]
        dd_duration_weeks = (recovery_date - peak_date).days / 7
    else:
        recovery_date = None
        dd_duration_weeks = (r.index[-1] - peak_date).days / 7
    # Calmar
    calmar = ann_ret / abs(dd) if dd < 0 else np.nan
    # Monthly stats
    r_m = r.copy()
    r_m.index = pd.to_datetime(r_m.index)
    monthly = r_m.resample("ME").apply(lambda s: (1+s).prod()-1 if len(s)>0 else 0)
    monthly = monthly[monthly != 0]
    # Distribution
    win_rate_w = (r > 0).mean()
    win_rate_m = (monthly > 0).mean() if len(monthly)>0 else np.nan
    best_week = r.max(); worst_week = r.min()
    best_month = monthly.max() if len(monthly)>0 else np.nan
    worst_month = monthly.min() if len(monthly)>0 else np.nan
    skew = r.skew(); kurt = r.kurt()
    var_95 = r.quantile(0.05); cvar_95 = r[r <= var_95].mean()
    # Sortino
    downside = r[r < 0]
    down_vol = downside.std()*np.sqrt(52) if len(downside)>0 else np.nan
    sortino = ann_ret / down_vol if down_vol>0 else np.nan
    # Rolling 12m sharpe (52-week)
    roll_sh = r.rolling(52).apply(lambda s: (s.mean()*52)/(s.std()*np.sqrt(52)) if s.std()>0 else np.nan)
    min_roll_sh = roll_sh.min(); max_roll_sh = roll_sh.max()
    # Up/down capture (vs equal-weight ETF bench)
    bench_pnl = ret.mean(axis=1).reindex(pnl.index)
    b_r = bench_pnl[r.index]
    up_b = b_r > 0; dn_b = b_r < 0
    up_cap = r[up_b].mean() / b_r[up_b].mean() if up_b.any() else np.nan
    dn_cap = r[dn_b].mean() / b_r[dn_b].mean() if dn_b.any() else np.nan
    return {
        "n_weeks": int(len(r)),
        "years": float(yrs),
        "ann_ret": float(ann_ret),
        "vol": float(vol),
        "sharpe": float(sh),
        "sortino": float(sortino) if np.isfinite(sortino) else None,
        "max_dd": float(dd),
        "max_dd_depth_pct": float(dd*100),
        "dd_peak_date": str(peak_date.date()),
        "dd_trough_date": str(trough_idx.date()),
        "dd_recovery_date": str(recovery_date.date()) if recovery_date is not None else "not yet",
        "dd_duration_weeks": float(dd_duration_weeks),
        "calmar": float(calmar),
        "win_rate_weekly": float(win_rate_w),
        "win_rate_monthly": float(win_rate_m) if np.isfinite(win_rate_m) else None,
        "best_week": float(best_week),
        "worst_week": float(worst_week),
        "best_month": float(best_month) if np.isfinite(best_month) else None,
        "worst_month": float(worst_month) if np.isfinite(worst_month) else None,
        "weekly_skew": float(skew),
        "weekly_kurt_excess": float(kurt),
        "var_95_weekly": float(var_95),
        "cvar_95_weekly": float(cvar_95),
        "roll_sh_12m_min": float(min_roll_sh) if np.isfinite(min_roll_sh) else None,
        "roll_sh_12m_max": float(max_roll_sh) if np.isfinite(max_roll_sh) else None,
        "up_capture_vs_bench": float(up_cap) if np.isfinite(up_cap) else None,
        "down_capture_vs_bench": float(dn_cap) if np.isfinite(dn_cap) else None,
    }

def per_year(pnl):
    r = pnl.dropna(); r.index = pd.to_datetime(r.index); rows=[]
    for yr, grp in r.groupby(r.index.year):
        if len(grp)<10: continue
        ann = (1+grp).prod()**(52/len(grp))-1
        vol_y = grp.std()*np.sqrt(52)
        sh = ann/vol_y if vol_y>0 else np.nan
        eq=(1+grp).cumprod(); dd=(eq/eq.cummax()-1).min()
        cal = ann/abs(dd) if dd<0 else np.nan
        wr = (grp > 0).mean()
        rows.append({"year":int(yr),"ret":float(ann),"vol":float(vol_y),"sh":float(sh),
                     "dd":float(dd),"cal":float(cal) if np.isfinite(cal) else np.nan,
                     "win_rate":float(wr),"n":int(len(grp))})
    return pd.DataFrame(rows).sort_values("year").reset_index(drop=True)

def drawdown_table(pnl, top_k=5):
    """Top-k drawdowns by depth."""
    r = pnl.dropna(); r.index = pd.to_datetime(r.index)
    eq = (1+r).cumprod()
    peak = eq.cummax()
    dd = eq/peak - 1
    # Identify drawdown episodes: dd series that starts at 0, goes negative, returns to 0
    in_dd = dd < -0.001
    episodes = []
    start = None; min_dd = 0; min_idx = None; last = None
    for ti, (t, v) in enumerate(dd.items()):
        if v < -0.001:
            if start is None:
                start = t
                min_dd = v; min_idx = t
            else:
                if v < min_dd:
                    min_dd = v; min_idx = t
            last = t
        else:
            if start is not None:
                # episode complete at t (recovered)
                episodes.append({"peak_date": str(dd.index[dd.index.get_loc(start)-1].date()) if dd.index.get_loc(start) > 0 else str(start.date()),
                                 "trough_date": str(min_idx.date()),
                                 "recovery_date": str(t.date()),
                                 "depth_pct": float(min_dd*100),
                                 "duration_weeks": int((t - start).days / 7 + 1)})
                start = None; min_dd = 0; min_idx = None
    # Open episode
    if start is not None:
        episodes.append({"peak_date": str(dd.index[dd.index.get_loc(start)-1].date()) if dd.index.get_loc(start) > 0 else str(start.date()),
                         "trough_date": str(min_idx.date()),
                         "recovery_date": "not yet",
                         "depth_pct": float(min_dd*100),
                         "duration_weeks": int((last - start).days / 7 + 1)})
    df = pd.DataFrame(episodes).sort_values("depth_pct").head(top_k).reset_index(drop=True)
    return df

def weighted_holdings(w_exec, top_k=25):
    """Sum weights across time → dollar-time exposure."""
    total = w_exec.fillna(0).sum(axis=0)
    years = len(w_exec)/52.0
    avg = total / len(w_exec)
    rows = []
    for code in total.index:
        if total[code] == 0: continue
        weeks = (w_exec[code] > 0).sum()
        rows.append({
            "ts_code": code,
            "etf_name": code2name.get(code, "?"),
            "group": code2group.get(code, "?"),
            "avg_weight": float(avg[code]),
            "weeks_held": int(weeks),
            "pct_weeks": float(weeks/len(w_exec)),
            "dollar_time_yrs": float(total[code]/52.0),
        })
    return pd.DataFrame(rows).sort_values("avg_weight", ascending=False).head(top_k).reset_index(drop=True)

def gate_gold_stats(wexec, gate):
    """Report gate + gold-fallback stats."""
    gate_on = gate.reindex(wexec.index).fillna(False)
    total_weeks = len(wexec)
    # weeks with 100% gold = single-asset gold holding
    gold_col = wexec[GOLD].fillna(0)
    gold_dominant = (gold_col > 0.5).sum()
    # weeks all weights 0 (cash)
    w_sum = wexec.fillna(0).sum(axis=1)
    cash_weeks = ((w_sum < 0.01) & ~gate_on).sum()
    return {
        "gate_on_weeks": int(gate_on.sum()),
        "gate_on_pct": float(gate_on.mean()),
        "gate_off_weeks": int((~gate_on).sum()),
        "gold_dominant_weeks": int(gold_dominant),
        "gold_dominant_pct": float(gold_dominant/total_weeks),
        "cash_weeks": int(cash_weeks),
    }

# ---- Compute stats ----
say("Computing full stats for V3 and V7…")
v3_full = full_stats(pnl_v3)
v3_is = full_stats(pnl_v3, IS_MASK)
v3_oos = full_stats(pnl_v3, OOS_MASK)
v7_full = full_stats(pnl_v7)
v7_is = full_stats(pnl_v7, IS_MASK)
v7_oos = full_stats(pnl_v7, OOS_MASK)

v3_py = per_year(pnl_v3); v7_py = per_year(pnl_v7)
v3_dd = drawdown_table(pnl_v3, 5); v7_dd = drawdown_table(pnl_v7, 5)
v3_h = weighted_holdings(wexec_v3, 25); v7_h = weighted_holdings(wexec_v7, 25)
v3_gate = gate_gold_stats(wexec_v3, gate50)
v7_gate = gate_gold_stats(wexec_v7, gate50)

# Save per-year csvs
v3_py.to_csv(OUT / "round7c_v3_peryear.csv", index=False)
v7_py.to_csv(OUT / "round7c_v7_peryear.csv", index=False)
v3_dd.to_csv(OUT / "round7c_v3_drawdowns.csv", index=False)
v7_dd.to_csv(OUT / "round7c_v7_drawdowns.csv", index=False)
v3_h.to_csv(OUT / "round7c_v3_holdings.csv", index=False)
v7_h.to_csv(OUT / "round7c_v7_holdings.csv", index=False)

# Monthly returns series
pnl_v3_m = pnl_v3.copy(); pnl_v3_m.index = pd.to_datetime(pnl_v3_m.index)
pnl_v7_m = pnl_v7.copy(); pnl_v7_m.index = pd.to_datetime(pnl_v7_m.index)
v3_m = pnl_v3_m.resample("ME").apply(lambda s: (1+s).prod()-1 if len(s)>0 else np.nan)
v7_m = pnl_v7_m.resample("ME").apply(lambda s: (1+s).prod()-1 if len(s)>0 else np.nan)
pd.DataFrame({"V3":v3_m, "V7":v7_m}).to_csv(OUT / "round7c_v3v7_monthly.csv")

# Print summary
def prints(label, s):
    say(f"\n====== {label} ======")
    for k, v in s.items():
        if isinstance(v, float):
            if "pct" in k or "rate" in k or "capture" in k:
                say(f"  {k:30s}: {v*100:+7.2f}%" if "pct" not in k or "depth" in k else f"  {k:30s}: {v:+7.2f}%")
            elif "sharpe" in k or "sortino" in k or "calmar" in k or "skew" in k or "kurt" in k:
                say(f"  {k:30s}: {v:+.3f}")
            elif "ret" in k or "vol" in k or "dd" in k or "var" in k or "cvar" in k or "week" in k or "month" in k:
                if "weeks" in k or "duration" in k:
                    say(f"  {k:30s}: {v:.1f}")
                else:
                    say(f"  {k:30s}: {v*100:+7.2f}%")
            else:
                say(f"  {k:30s}: {v}")
        else:
            say(f"  {k:30s}: {v}")

prints("V3 FULL (2019-01 → 2026-04)", v3_full)
prints("V3 IS",   v3_is)
prints("V3 OOS",  v3_oos)
prints("V7 FULL (2019-01 → 2026-04)", v7_full)
prints("V7 IS",   v7_is)
prints("V7 OOS",  v7_oos)

say("\n===== V3 per-year =====")
print(v3_py.to_string(index=False))
say("\n===== V7 per-year =====")
print(v7_py.to_string(index=False))

say("\n===== V3 top-5 drawdowns =====")
print(v3_dd.to_string(index=False))
say("\n===== V7 top-5 drawdowns =====")
print(v7_dd.to_string(index=False))

say("\n===== V3 gate/gold =====")
print(v3_gate)
say("\n===== V7 gate/gold =====")
print(v7_gate)

say("\n===== V3 holdings by avg weight =====")
print(v3_h.head(20).to_string(index=False))
say("\n===== V7 holdings by avg weight =====")
print(v7_h.head(20).to_string(index=False))

# Full JSON bundle
bundle = {
    "v3": {
        "spec": "A_tuned_v1 (top-4 penalized) + 黄金ETF fallback + MA50 gate + 15% vol target",
        "config": {"mom_w":4,"turn_w":4,"lambda":1.5,"mu":0.3,"top_n":4,
                   "gate":"mkt_cum > 50w MA","fallback":"100% 黄金ETF when gate off",
                   "vol_target":0.15,"rebalance_w":1,"delay":1,"cost_bps":5},
        "full": v3_full, "is": v3_is, "oos": v3_oos,
        "per_year": v3_py.to_dict("records"),
        "top_drawdowns": v3_dd.to_dict("records"),
        "gate_gold": v3_gate,
        "top_holdings": v3_h.to_dict("records"),
        "turnover_annual_oneway": float(tov_v3.mean()*52),
    },
    "v7": {
        "spec": "Ensemble 0.5*A_tuned_v1 + 0.5*G_top3 + 黄金ETF fallback + MA50 gate + 15% vol target",
        "config": {"spec_A":"(mom_4w,turn_4w,λ=1.5,μ=0.3,top_n=4)",
                   "spec_G":"top-3 groups → top-1 ETF per group (by group 4w mom)",
                   "weight":"0.5/0.5 equal blend",
                   "gate":"mkt_cum > 50w MA","fallback":"100% 黄金ETF when gate off",
                   "vol_target":0.15,"rebalance_w":1,"delay":1,"cost_bps":5},
        "full": v7_full, "is": v7_is, "oos": v7_oos,
        "per_year": v7_py.to_dict("records"),
        "top_drawdowns": v7_dd.to_dict("records"),
        "gate_gold": v7_gate,
        "top_holdings": v7_h.to_dict("records"),
        "turnover_annual_oneway": float(tov_v7.mean()*52),
    }
}
with open(OUT / "round7c_v3_v7_full_stats.json", "w") as f:
    json.dump(bundle, f, indent=2, ensure_ascii=False)

# Save PnL series
pnl_v3.to_frame("pnl_v3").to_csv(OUT / "round7c_v3_pnl.csv")
pnl_v7.to_frame("pnl_v7").to_csv(OUT / "round7c_v7_pnl.csv")

say("\n[done] full stats written")
