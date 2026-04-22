"""
Follow-on #1: apply dispersion gate (from trend α_35) to lottery α_17.

Test hypothesis: does the Stivers-Sun dispersion gate transfer across factor
families? α_17 (σ-bucket rank of α_08, idio-MAX) from lottery session has:
  - LS full Sharpe 1.69, test 1.73, Q5 test 1.03
  - Max DD -9.5%
  - Worst year LS = -0.27 (2020, bull year that destroys lottery)
  - Audit verdict: worst_year fail, residualization fail

Prediction (if gate mechanism is family-agnostic): gate should lift 2020
above 0.5 the same way it lifted 2023 for α_29.

Compare ungated α_17 vs gated α_17:
  - per-year LS Sharpe
  - worst year, max DD, full Sharpe
  - placebo-style conclusion
"""
from __future__ import annotations
import json, time
import numpy as np
import pandas as pd

CACHE = "/home/user/Factor_Zoo/.cache"
LOT = "/home/user/Factor_Zoo/logs/20260421_volprice_max_lottery"
OUT_DIR = "/home/user/Factor_Zoo/logs/20260422_trend_technical_alpha/outputs"
FOLLOWUP_OUT = f"{OUT_DIR}/followup_disp_gate_on_lottery_alpha17.json"

PRIMARY_K = 20
COST_BPS = 5
REBAL = 20
TRAIN_END = pd.Timestamp("2022-12-31")
VALID_END = pd.Timestamp("2023-12-31")


def industry_demean(df, col):
    return df[col] - df.groupby(["trade_date", "industry"])[col].transform("mean")


def quintile_portfolios_gated(df, alpha, ret_col, rebal_dates, gate_series):
    rows = []
    prev_q5 = set(); prev_q1 = set(); prev_state = 0
    panel = df[["trade_date","ts_code", alpha, ret_col]].dropna()
    for t in rebal_dates:
        gate = int(gate_series.get(t, 0))
        if gate == 0:
            tov_q5 = 1.0 if prev_state == 1 else 0.0
            tov_q1 = 1.0 if prev_state == 1 else 0.0
            rows.append(dict(trade_date=t, ls=0.0, q5=0.0, q1=0.0, all=0.0,
                             tov_q5=tov_q5, tov_q1=tov_q1, gate=0))
            prev_state = 0; prev_q5 = set(); prev_q1 = set()
            continue
        snap = panel[panel["trade_date"] == t]
        if len(snap) < 100:
            rows.append(dict(trade_date=t, ls=0.0, q5=0.0, q1=0.0, all=0.0,
                             tov_q5=0.0, tov_q1=0.0, gate=0))
            prev_state = 0
            continue
        snap = snap.copy()
        snap["q"] = pd.qcut(snap[alpha].rank(method="first"), 5, labels=False, duplicates="drop")
        if snap["q"].isna().all():
            continue
        q5 = snap[snap["q"] == 4]; q1 = snap[snap["q"] == 0]
        cur_q5 = set(q5["ts_code"]); cur_q1 = set(q1["ts_code"])
        if prev_state == 1 and prev_q5:
            tov_q5 = 1.0 - len(cur_q5 & prev_q5) / max(len(cur_q5), 1)
            tov_q1 = 1.0 - len(cur_q1 & prev_q1) / max(len(cur_q1), 1)
        else:
            tov_q5 = 1.0; tov_q1 = 1.0
        prev_q5, prev_q1 = cur_q5, cur_q1
        prev_state = 1
        rows.append(dict(trade_date=t, q5=q5[ret_col].mean(), q1=q1[ret_col].mean(),
                         ls=q5[ret_col].mean()-q1[ret_col].mean(), all=snap[ret_col].mean(),
                         tov_q5=tov_q5, tov_q1=tov_q1, gate=1))
    return pd.DataFrame(rows)


def perf(r, ppy=12):
    if len(r) < 2:
        return {"sharpe": np.nan, "ann": np.nan, "maxdd": np.nan}
    ann = r.mean() * ppy
    vol = r.std(ddof=0) * np.sqrt(ppy)
    eq = (1+r).cumprod()
    return {"sharpe": ann/vol if vol>0 else 0, "ann": ann,
            "maxdd": float((eq/eq.cummax()-1).min())}


def per_year_active(r):
    yrs = r.index.year
    out = {}
    for y in sorted(set(yrs)):
        rr = r[yrs == y]
        if len(rr) < 6: continue
        v = rr.std(ddof=0)
        if v > 0:
            out[int(y)] = float((rr.mean()*12)/(v*np.sqrt(12)))
        elif abs(rr.mean()) < 1e-9:
            out[int(y)] = 0.0
    return out


def main():
    t0 = time.time()
    print("[fu] load α_17 from lottery panel_round3...")
    lot = pd.read_parquet(f"{LOT}/outputs/panel_round3.parquet",
                          columns=["ts_code","trade_date","industry","alpha_17",
                                   "fwd_ret_20"])
    lot["trade_date"] = pd.to_datetime(lot["trade_date"])
    lot = lot.dropna(subset=["industry"])
    lot["alpha_17_n"] = industry_demean(lot, "alpha_17")
    print(f"  loaded {lot.shape}  {time.time()-t0:.1f}s")

    # Build dispersion gate from daily
    print("[fu] build dispersion gate...")
    daily = pd.read_parquet(f"{CACHE}/daily.parquet").merge(
        pd.read_parquet(f"{CACHE}/adj_factor.parquet"),
        on=["ts_code","trade_date"], how="left"
    )
    daily["adj_factor"] = daily["adj_factor"].fillna(1.0)
    daily["P"] = daily["close"] * daily["adj_factor"]
    daily = daily.sort_values(["ts_code","trade_date"]).reset_index(drop=True)
    daily["ret"] = daily.groupby("ts_code")["P"].transform(lambda s: np.log(s).diff())
    daily["ret_20"] = daily.groupby("ts_code")["ret"].transform(lambda s: s.rolling(20, min_periods=15).sum())
    disp = daily.groupby("trade_date")["ret_20"].std().rename("mkt_disp")
    disp_med = disp.rolling(252, min_periods=180).median()
    gate = (disp > disp_med).astype(int)
    print(f"  gate on-frac = {gate.mean():.3f}  {time.time()-t0:.1f}s")

    all_dates = pd.Index(sorted(lot["trade_date"].unique()))
    rebal_dates = all_dates[::REBAL]

    # Ungated baseline
    print("[fu] backtest UNGATED α_17...")
    gate_always_on = pd.Series(1, index=all_dates)
    res_u = quintile_portfolios_gated(lot, "alpha_17_n", "fwd_ret_20", rebal_dates, gate_always_on)
    res_u = res_u.set_index("trade_date").sort_index()
    res_u["ls_after"] = res_u["ls"] - (res_u["tov_q5"] + res_u["tov_q1"]) * COST_BPS / 1e4
    res_u["q5_excess_after"] = (res_u["q5"] - res_u["all"]) - res_u["tov_q5"] * COST_BPS / 1e4

    # Gated
    print("[fu] backtest GATED α_17 (dispersion gate from α_35)...")
    res_g = quintile_portfolios_gated(lot, "alpha_17_n", "fwd_ret_20", rebal_dates, gate)
    res_g = res_g.set_index("trade_date").sort_index()
    res_g["ls_after"] = res_g["ls"] - (res_g["tov_q5"] + res_g["tov_q1"]) * COST_BPS / 1e4
    res_g["q5_excess_after"] = (res_g["q5"] - res_g["all"]) - res_g["tov_q5"] * COST_BPS / 1e4

    # Metrics
    def summarize(res, name):
        full = perf(res["ls_after"])
        full_q5 = perf(res["q5_excess_after"])
        train = res[res.index <= TRAIN_END]
        test = res[res.index > VALID_END]
        py = per_year_active(res["ls_after"])
        py_q5 = per_year_active(res["q5_excess_after"])
        worst = min(py.values()) if py else np.nan
        worst_q5 = min(py_q5.values()) if py_q5 else np.nan
        return dict(
            name=name,
            ls_full=full["sharpe"], ls_ann=full["ann"], ls_maxdd=full["maxdd"],
            ls_test=perf(test["ls_after"])["sharpe"],
            ls_train=perf(train["ls_after"])["sharpe"],
            q5_full=full_q5["sharpe"], q5_test=perf(test["q5_excess_after"])["sharpe"],
            worst_year_ls=worst, worst_year_q5=worst_q5,
            gate_on_frac=res["gate"].mean(),
            per_year_ls=py, per_year_q5=py_q5,
        )

    u = summarize(res_u, "α_17 UNGATED")
    g = summarize(res_g, "α_17 + dispersion gate")

    print("\n" + "="*80)
    print("COMPARISON: α_17 (lottery) UNGATED vs + dispersion-gate (from α_35)")
    print("="*80)
    fmt = lambda v: f"{v:>7.3f}" if isinstance(v, float) and not np.isnan(v) else f"{str(v):>7}"
    print(f"{'metric':<22} {'UNGATED':>12} {'GATED':>12} {'Δ':>12}")
    for m in ["ls_full","ls_ann","ls_maxdd","ls_train","ls_test","q5_full","q5_test","worst_year_ls","worst_year_q5","gate_on_frac"]:
        du, dg = u[m], g[m]
        delta = dg - du if (isinstance(du,(int,float)) and isinstance(dg,(int,float)) and not (np.isnan(du) or np.isnan(dg))) else np.nan
        print(f"  {m:<20} {fmt(du)} {fmt(dg)} {fmt(delta)}")

    print("\nPer-year LS Sharpe:")
    all_years = sorted(set(list(u["per_year_ls"].keys()) + list(g["per_year_ls"].keys())))
    print(f"{'year':<8} {'UNGATED':>10} {'GATED':>10} {'Δ':>10}")
    for y in all_years:
        du = u["per_year_ls"].get(y, np.nan)
        dg = g["per_year_ls"].get(y, np.nan)
        dd = dg - du if not (np.isnan(du) or np.isnan(dg)) else np.nan
        print(f"  {y:<6} {du:>10.3f} {dg:>10.3f} {dd:>10.3f}")

    # Write summary json
    import json as _json
    out = {
        "experiment": "follow_on_1_dispersion_gate_on_lottery_alpha_17",
        "hypothesis": "Stivers-Sun dispersion gate is family-agnostic: should lift α_17 worst-year (2020 = -0.27) above 0.5 same as it did for trend α_29 (2023 = 0.04 → 0.63).",
        "alpha_tested": "α_17 = σ-bucket rank of α_08 (σ-decoupled MAX / idio-MAX), from lottery session logs/20260421_volprice_max_lottery",
        "gate": "1{cross_sectional_std(ret_20) > rolling_252d_median}",
        "UNGATED": u,
        "GATED": g,
    }
    with open(FOLLOWUP_OUT, "w") as f:
        _json.dump(out, f, indent=2, default=str)
    print(f"\n[fu] wrote {FOLLOWUP_OUT}")
    print(f"[fu] done {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
