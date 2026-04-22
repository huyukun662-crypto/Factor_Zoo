"""
Follow-on #1b: INVERSE dispersion gate on lottery α_17.

Preliminary result (09_followup): dispersion gate transfers PARTIALLY to
lottery α_17 — worst-year slightly improves but full Sharpe is halved.

Hypothesis: lottery premium is concentrated in LOW-dispersion regimes
(opposite of momentum). Invert the gate: trade α_17 only when
cross-sectional dispersion is BELOW its 252d rolling median.

Compare:
  α_17 ungated
  α_17 × 1{disp > med252}    (momentum-style gate — tested in 09)
  α_17 × 1{disp < med252}    (inverse gate — this script)
"""
from __future__ import annotations
import json, time
import numpy as np
import pandas as pd

CACHE = "/home/user/Factor_Zoo/.cache"
LOT = "/home/user/Factor_Zoo/logs/20260421_volprice_max_lottery"
OUT_DIR = "/home/user/Factor_Zoo/logs/20260422_trend_technical_alpha/outputs"
FOLLOWUP_OUT = f"{OUT_DIR}/followup_inverse_disp_gate_on_lottery_alpha17.json"

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
        if snap["q"].isna().all(): continue
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
    if len(r) < 2: return {"sharpe": np.nan, "ann": np.nan, "maxdd": np.nan}
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
    lot = pd.read_parquet(f"{LOT}/outputs/panel_round3.parquet",
                          columns=["ts_code","trade_date","industry","alpha_17","fwd_ret_20"])
    lot["trade_date"] = pd.to_datetime(lot["trade_date"])
    lot = lot.dropna(subset=["industry"])
    lot["alpha_17_n"] = industry_demean(lot, "alpha_17")

    daily = pd.read_parquet(f"{CACHE}/daily.parquet").merge(
        pd.read_parquet(f"{CACHE}/adj_factor.parquet"),
        on=["ts_code","trade_date"], how="left"
    )
    daily["adj_factor"] = daily["adj_factor"].fillna(1.0)
    daily["P"] = daily["close"] * daily["adj_factor"]
    daily = daily.sort_values(["ts_code","trade_date"]).reset_index(drop=True)
    daily["ret"] = daily.groupby("ts_code")["P"].transform(lambda s: np.log(s).diff())
    daily["ret_20"] = daily.groupby("ts_code")["ret"].transform(lambda s: s.rolling(20, min_periods=15).sum())
    disp = daily.groupby("trade_date")["ret_20"].std()
    disp_med = disp.rolling(252, min_periods=180).median()

    gate_mom  = (disp > disp_med).astype(int)   # momentum-style gate
    gate_inv  = (disp < disp_med).astype(int).where(~disp_med.isna(), 0)  # inverse — for lottery
    gate_always = pd.Series(1, index=disp.index)
    print(f"gate_mom on-frac = {gate_mom.mean():.3f}, gate_inv on-frac = {gate_inv.mean():.3f}")

    all_dates = pd.Index(sorted(lot["trade_date"].unique()))
    rebal_dates = all_dates[::REBAL]

    def run(gate, name):
        res = quintile_portfolios_gated(lot, "alpha_17_n", "fwd_ret_20", rebal_dates, gate)
        res = res.set_index("trade_date").sort_index()
        res["ls_after"] = res["ls"] - (res["tov_q5"] + res["tov_q1"]) * COST_BPS / 1e4
        res["q5_excess_after"] = (res["q5"] - res["all"]) - res["tov_q5"] * COST_BPS / 1e4
        full = perf(res["ls_after"])
        full_q5 = perf(res["q5_excess_after"])
        test = res[res.index > VALID_END]
        py = per_year_active(res["ls_after"])
        py_q5 = per_year_active(res["q5_excess_after"])
        return dict(
            name=name,
            ls_full=full["sharpe"], ls_ann=full["ann"], ls_maxdd=full["maxdd"],
            ls_test=perf(test["ls_after"])["sharpe"],
            q5_full=full_q5["sharpe"], q5_test=perf(test["q5_excess_after"])["sharpe"],
            worst_year_ls=min(py.values()) if py else np.nan,
            worst_year_q5=min(py_q5.values()) if py_q5 else np.nan,
            gate_on_frac=res["gate"].mean(),
            per_year_ls=py, per_year_q5=py_q5,
        )

    u = run(gate_always, "UNGATED")
    m = run(gate_mom, "+ dispersion gate (momentum-style, gate>med)")
    i = run(gate_inv, "+ INVERSE dispersion gate (gate<med, lottery-style)")

    print("\n" + "="*90)
    print("α_17 (lottery) three variants:")
    print("="*90)
    fmt = lambda v: f"{v:>8.3f}" if isinstance(v, float) and not np.isnan(v) else f"{str(v):>8}"
    print(f"{'metric':<22} {'UNGATED':>10} {'MOM-GATE':>12} {'INV-GATE':>12}")
    for mname in ["ls_full","ls_ann","ls_maxdd","ls_test","q5_full","q5_test","worst_year_ls","worst_year_q5","gate_on_frac"]:
        print(f"  {mname:<20} {fmt(u[mname])} {fmt(m[mname])} {fmt(i[mname])}")

    print("\nPer-year LS Sharpe:")
    all_years = sorted(set(list(u["per_year_ls"].keys()) + list(m["per_year_ls"].keys()) + list(i["per_year_ls"].keys())))
    print(f"{'year':<8} {'UNGATED':>10} {'MOM-GATE':>12} {'INV-GATE':>12}")
    for y in all_years:
        du = u["per_year_ls"].get(y, np.nan)
        dm = m["per_year_ls"].get(y, np.nan)
        di = i["per_year_ls"].get(y, np.nan)
        f = lambda v: f"{v:>10.3f}" if isinstance(v, float) and not np.isnan(v) else f"{'cash':>10}"
        print(f"  {y:<6} {f(du)} {f(dm):>12} {f(di):>12}")

    out = {
        "experiment": "follow_on_1b_inverse_disp_gate_on_lottery_alpha_17",
        "hypothesis": "lottery premium concentrates in LOW-dispersion regimes (opposite of momentum). Inverse dispersion gate should rescue α_17.",
        "conclusion_if_inverse_beats_mom": "dispersion gate mechanism is NOT family-agnostic; it is specifically momentum-regime; lottery needs inverse form.",
        "UNGATED": u, "MOM_GATE": m, "INVERSE_GATE": i,
    }
    with open(FOLLOWUP_OUT, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\n[fu-1b] wrote {FOLLOWUP_OUT}")
    print(f"[fu-1b] done {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
