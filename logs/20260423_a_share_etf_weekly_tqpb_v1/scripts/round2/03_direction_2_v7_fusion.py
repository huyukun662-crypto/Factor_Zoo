#!/usr/bin/env python3
"""Round 2 Direction 2: signal-level fusion into V7's Leg A.

Replaces V7's  `0.3 * breadth[t]` with `0.15 * breadth[t] + 0.15 * z_cs(breakout_vol_conf[i,t])`.
Re-runs the full V7 pipeline (Leg A + Leg G + gate + vol target) and compares.

Uses V7's weekly panel (cum_w, turnover_w, ret_w) to match V7's semantics exactly,
then computes z_cs(breakout_vol_conf) on the same weekly grid from daily data.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path("/home/user/Factor_Zoo/logs/20260423_a_share_etf_weekly_tqpb_v1/outputs/round2")
OUT.mkdir(parents=True, exist_ok=True)
V7_ROOT = Path("/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs")

GOLD = "159934.SZ"


# ---------------- load V7's data ----------------
W = pd.read_parquet(V7_ROOT / "etf_weekly.parquet")
uni = pd.read_csv(V7_ROOT / "etf_universe.csv")
W["trade_week"] = pd.to_datetime(W["trade_week"])
W = W[W["trade_week"] >= "2019-01-01"].sort_values(["trade_week", "ts_code"]).reset_index(drop=True)

ret = W.pivot(index="trade_week", columns="ts_code", values="ret_w").sort_index()
turn = W.pivot(index="trade_week", columns="ts_code", values="turnover_w").sort_index()
cum = (1 + ret.fillna(0)).cumprod()
age = ret.notna().cumsum()
elig = age >= 12
cols = ret.columns


def zscore_cs(df):
    df = df.where(elig); mu = df.mean(axis=1); sd = df.std(axis=1)
    return df.sub(mu, axis=0).div(sd, axis=0)


# ---------------- breadth (shared across ETFs, scalar per week) ----------------
br_s = ((cum > cum.rolling(20, min_periods=8).mean()).where(elig).sum(axis=1) /
        elig.sum(axis=1).replace(0, np.nan))
br_z = (br_s - br_s.rolling(52, min_periods=20).mean()) / br_s.rolling(52, min_periods=20).std()


# ---------------- breakout signal on weekly grid ----------------
# Use the daily panel for the 34 ETFs, compute breakout_vol_conf daily, then sample Fridays.
D = pd.read_parquet(V7_ROOT / "etf_daily.parquet").rename(columns={"trade_date": "date"})
D["date"] = pd.to_datetime(D["date"])
D = D[(D["date"] >= "2019-01-01") & (D["date"] <= "2026-04-22")].copy()
D = D.sort_values(["ts_code", "date"]).reset_index(drop=True)
D["log_close"] = np.log(D["close_adj"])
D["log_ret_1"] = D.groupby("ts_code")["log_close"].diff()
g = D.groupby("ts_code", group_keys=False)
D["std_20d"] = g["log_ret_1"].transform(lambda s: s.rolling(20, min_periods=10).std())
# Correct past-20 max (exclude today) for breakout semantics
D["max_high_20_prior"] = g["close_adj"].transform(lambda s: s.shift(1).rolling(20, min_periods=10).max())
D["vol_5"] = g["vol"].transform(lambda s: s.rolling(5, min_periods=3).mean())
D["vol_20"] = g["vol"].transform(lambda s: s.rolling(20, min_periods=10).mean())
breakout_flag = ((D["close_adj"] > D["max_high_20_prior"]) &
                 (D["vol_5"] / D["vol_20"].replace(0, np.nan) > 1.2)).astype(float)
brk_raw = (D["close_adj"] - D["max_high_20_prior"]) / D["std_20d"].replace(0, np.nan)
D["brk"] = brk_raw.clip(lower=0) * breakout_flag

# sample to weekly: take per-week MAX of brk per ETF (captures the biggest breakout event in the week)
D["iso_year"] = D["date"].dt.isocalendar().year
D["iso_week"] = D["date"].dt.isocalendar().week
D["last_dow"] = D["date"].dt.dayofweek
# trade_week key used in V7: map to last trading day of iso-week
brk_weekly = (D.groupby(["ts_code", "iso_year", "iso_week"])
                .agg(brk_max=("brk", "max"), last_date=("date", "max"))
                .reset_index())
# align to V7's trade_week (use the last date of the week, converted)
brk_weekly["trade_week"] = pd.to_datetime(brk_weekly["last_date"])
# pivot to ETF x week
brk_w = (brk_weekly.pivot(index="trade_week", columns="ts_code", values="brk_max")
         .reindex(ret.index))
# a few weeks may not align exactly — forward-fill at most one week to absorb timestamp drift
brk_w = brk_w.sort_index().ffill(limit=1).fillna(0.0)
# restrict to same columns as ret
brk_w = brk_w.reindex(columns=cols).fillna(0.0)

# cross-sectional z-score of breakout per week (on eligible only)
brk_z = zscore_cs(brk_w).fillna(0.0)


# ---------------- V7 original build ----------------
def build_A_weights_original():
    mom4 = cum / cum.shift(4) - 1
    turn4 = turn.rolling(4, min_periods=2).mean()
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


def build_A_weights_fused(w_br: float = 0.15, w_br_from_breadth: float = 0.15):
    """Fused Leg A: score = z(mom4) - 1.5*z(turn4) + w_br_from_breadth*breadth + w_br*z(breakout)"""
    mom4 = cum / cum.shift(4) - 1
    turn4 = turn.rolling(4, min_periods=2).mean()
    bread_df = pd.DataFrame({c: br_z for c in cols})
    score = zscore_cs(mom4) - 1.5*zscore_cs(turn4) + w_br_from_breadth*bread_df + w_br*brk_z
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
    for gr in gnames:
        codes_g = [c for c in uni[uni["group"] == gr]["ts_code"] if c in cols]
        v = elig[codes_g]
        gret[gr] = ret[codes_g].where(v).mean(axis=1)
    gcum = (1+gret.fillna(0)).cumprod()
    gmom4 = gcum/gcum.shift(4) - 1
    mom4_etf = cum / cum.shift(4) - 1
    wm = np.zeros((len(ret), len(cols)), dtype=float)
    for ti in range(len(ret)):
        gs = gmom4.iloc[ti].dropna()
        if len(gs) < 3: continue
        tops = gs.nlargest(3).index.tolist()
        picks = []
        for gr in tops:
            codes_g = [c for c in uni[uni["group"] == gr]["ts_code"] if c in cols]
            s = mom4_etf.iloc[ti][codes_g].dropna()
            s = s[[c for c in s.index if elig.iloc[ti][c]]]
            if len(s) < 1: continue
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
    gold_ok = elig[GOLD].fillna(False) if GOLD in elig.columns else None
    if gold_ok is not None:
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


def metrics(pnl):
    r = pnl.dropna()
    cum_r = r.cumsum(); dd = cum_r - cum_r.cummax()
    vol = r.std()*np.sqrt(52); mean = r.mean()*52
    return {"sharpe": float(mean/vol) if vol > 0 else 0.0,
            "annret": float(np.exp(mean) - 1) if abs(mean) < 5 else float("nan"),
            "vol": float(vol), "maxdd": float(dd.min()), "n": int(len(r))}


def per_year(pnl):
    p = pnl.to_frame("pnl"); p["year"] = p.index.year
    rows = []
    for y, g in p.groupby("year"):
        m = metrics(g["pnl"])
        rows.append({"year": int(y), "n_weeks": len(g), "sharpe": m["sharpe"],
                     "annret": m["annret"], "vol": m["vol"], "maxdd": m["maxdd"]})
    return pd.DataFrame(rows)


# ---------------- Main ----------------
w_A_orig = build_A_weights_original()
w_G = build_G_weights()
gate50 = make_gate(50)

# V7 ORIGINAL (sanity — should match round7c_v7_pnl.csv closely)
w_v7_orig = apply_vol_target(apply_gate_gold(0.5*w_A_orig + 0.5*w_G, gate50), 0.15, 26)
pnl_v7_orig, _, _ = run_bt(w_v7_orig, 5)

# V7 FUSED: replace 0.3*breadth with 0.15*breadth + 0.15*z(breakout)
w_A_f15 = build_A_weights_fused(w_br=0.15, w_br_from_breadth=0.15)
w_v7_f15 = apply_vol_target(apply_gate_gold(0.5*w_A_f15 + 0.5*w_G, gate50), 0.15, 26)
pnl_v7_f15, _, _ = run_bt(w_v7_f15, 5)

# also try other fusion weights
results_variants = {}
for (wb, wbrk, tag) in [(0.3, 0.0, "v7_orig"), (0.15, 0.15, "fused_15_15"),
                        (0.2, 0.10, "fused_20_10"), (0.1, 0.20, "fused_10_20"),
                        (0.0, 0.30, "fused_00_30"), (0.25, 0.10, "fused_25_10"),
                        (0.15, 0.30, "fused_15_30")]:
    wA = build_A_weights_original() if (wb == 0.3 and wbrk == 0.0) else build_A_weights_fused(w_br=wbrk, w_br_from_breadth=wb)
    w_v7v = apply_vol_target(apply_gate_gold(0.5*wA + 0.5*w_G, gate50), 0.15, 26)
    pnl_v7v, _, _ = run_bt(w_v7v, 5)
    m = metrics(pnl_v7v)
    py_sh_2022 = per_year(pnl_v7v).query("year == 2022")["sharpe"].values
    py_sh_2026 = per_year(pnl_v7v).query("year == 2026")["sharpe"].values
    results_variants[tag] = {
        "weights": {"breadth": wb, "breakout_z": wbrk},
        "sharpe_full": m["sharpe"], "annret_full": m["annret"],
        "vol": m["vol"], "maxdd": m["maxdd"], "n_weeks": m["n"],
        "sh_2022": float(py_sh_2022[0]) if len(py_sh_2022) else None,
        "sh_2026_ytd": float(py_sh_2026[0]) if len(py_sh_2026) else None,
    }

# detailed compare: original vs fused_15_15
orig_m = metrics(pnl_v7_orig); f15_m = metrics(pnl_v7_f15)
orig_py = per_year(pnl_v7_orig); f15_py = per_year(pnl_v7_f15)
py_compare = orig_py.merge(f15_py, on="year", suffixes=("_orig", "_fused"))
py_compare["delta_sharpe"] = py_compare["sharpe_fused"] - py_compare["sharpe_orig"]

out = {
    "v7_baseline_from_reproduction": orig_m,
    "v7_fused_15_15": f15_m,
    "fused_vs_orig_delta_sharpe": f15_m["sharpe"] - orig_m["sharpe"],
    "fused_vs_orig_delta_maxdd": f15_m["maxdd"] - orig_m["maxdd"],
    "variants_sweep": results_variants,
    "per_year_compare": py_compare.to_dict("records"),
    "n_weeks_reproduced": int(len(pnl_v7_orig)),
}

print(f"V7 reproduced baseline: Sharpe {orig_m['sharpe']:.3f}, MaxDD {orig_m['maxdd']:.3f}")
print(f"V7 fused 15+15:         Sharpe {f15_m['sharpe']:.3f}, MaxDD {f15_m['maxdd']:.3f}")
print(f"  Δ Sharpe: {out['fused_vs_orig_delta_sharpe']:+.3f}, Δ MaxDD: {out['fused_vs_orig_delta_maxdd']:+.3f}")
print("\nVariant sweep:")
for tag, v in results_variants.items():
    print(f"  {tag}: breadth={v['weights']['breadth']}, brk_z={v['weights']['breakout_z']} "
          f"→ Sh {v['sharpe_full']:.3f}, MaxDD {v['maxdd']:.3f}, "
          f"Sh_2022 {v['sh_2022']:.2f}" if v['sh_2022'] is not None else "")
print("\nPer-year compare (orig vs fused 15+15):")
print(py_compare[["year", "n_weeks_orig", "sharpe_orig", "sharpe_fused", "delta_sharpe"]].to_string(index=False))

(OUT / "d2_signal_fusion_results.json").write_text(json.dumps(out, indent=2, default=str))
py_compare.to_csv(OUT / "d2_per_year_compare.csv", index=False)
# save PnL series for audit
pd.DataFrame({"trade_week": pnl_v7_orig.index, "pnl_v7_orig": pnl_v7_orig.values,
              "pnl_v7_fused_15_15": pnl_v7_f15.values}).to_csv(OUT / "d2_v7_pnl_series.csv", index=False)
print(f"\nwrote: {OUT/'d2_signal_fusion_results.json'}")
