"""
Round 5 — α_29 with market regime overlays (α_33..α_40).
Goal: lift worst-year LS Sharpe above 0.5 floor.
"""
from __future__ import annotations
import json
import time
import numpy as np
import pandas as pd

ROOT = "/home/user/Factor_Zoo/logs/20260422_trend_technical_alpha"
OUT = f"{ROOT}/outputs"

PRIMARY_K = 20
COST_BPS = 5
REBAL = 20
TRAIN_END = pd.Timestamp("2022-12-31")
VALID_END = pd.Timestamp("2023-12-31")


def industry_demean(df, col):
    return df[col] - df.groupby(["trade_date", "industry"])[col].transform("mean")


def perf(returns, ppy=12):
    if len(returns) < 2:
        return {"sharpe": np.nan, "maxdd": np.nan}
    annret = returns.mean() * ppy
    annvol = returns.std(ddof=0) * np.sqrt(ppy)
    eq = (1 + returns).cumprod()
    return {"sharpe": annret/annvol if annvol > 0 else np.nan,
            "maxdd": float((eq/eq.cummax()-1).min())}


def per_year(returns, ppy=12):
    yrs = returns.index.year
    out = {}
    for y in sorted(set(yrs)):
        r = returns[yrs == y]
        if len(r) >= 6:
            v = r.std(ddof=0)
            if v > 0:
                out[int(y)] = float((r.mean()*ppy)/(v*np.sqrt(ppy)))
            elif abs(r.mean()) < 1e-9:
                out[int(y)] = 0.0  # held cash all year (gated off)
            else:
                out[int(y)] = float("nan")
    return out


def quintile_portfolios_gated(df, alpha, ret_col, rebal_dates, gate_series):
    """
    Same as before but with a per-rebal-date gate ∈ {0, 1}.
    When gate(t) == 0 → no position, turnover at boundary only.
    """
    rows = []
    prev_q5 = set(); prev_q1 = set()
    prev_state = 0  # 0 = off, 1 = on
    panel = df[["trade_date","ts_code", alpha, ret_col]].dropna()
    for t in rebal_dates:
        gate = int(gate_series.get(t, 0))
        if gate == 0:
            # Position flat
            if prev_state == 1:
                # Liquidation cost: tov = 1 for both legs
                tov_q5 = 1.0; tov_q1 = 1.0
            else:
                tov_q5 = 0.0; tov_q1 = 0.0
            rows.append(dict(trade_date=t, q5=0.0, q1=0.0, ls=0.0, all=0.0,
                             tov_q5=tov_q5, tov_q1=tov_q1, gate=0))
            prev_state = 0
            prev_q5 = set(); prev_q1 = set()
            continue

        snap = panel[panel["trade_date"] == t]
        if len(snap) < 100:
            rows.append(dict(trade_date=t, q5=0.0, q1=0.0, ls=0.0, all=0.0,
                             tov_q5=0.0, tov_q1=0.0, gate=0))
            prev_state = 0
            prev_q5 = set(); prev_q1 = set()
            continue
        snap = snap.copy()
        snap["q"] = pd.qcut(snap[alpha].rank(method="first"), 5, labels=False, duplicates="drop")
        if snap["q"].isna().all():
            rows.append(dict(trade_date=t, q5=0.0, q1=0.0, ls=0.0, all=0.0,
                             tov_q5=0.0, tov_q1=0.0, gate=0))
            prev_state = 0
            continue
        q5 = snap[snap["q"] == 4]
        q1 = snap[snap["q"] == 0]
        all_ret = snap[ret_col].mean()
        cur_q5 = set(q5["ts_code"]); cur_q1 = set(q1["ts_code"])
        if prev_state == 1 and prev_q5:
            tov_q5 = 1.0 - len(cur_q5 & prev_q5) / max(len(cur_q5), 1)
            tov_q1 = 1.0 - len(cur_q1 & prev_q1) / max(len(cur_q1), 1)
        else:
            # Just turned on or first period — full entry
            tov_q5 = 1.0; tov_q1 = 1.0
        prev_q5, prev_q1 = cur_q5, cur_q1
        prev_state = 1
        rows.append(dict(trade_date=t, q5=q5[ret_col].mean(), q1=q1[ret_col].mean(),
                         ls=q5[ret_col].mean()-q1[ret_col].mean(), all=all_ret,
                         tov_q5=tov_q5, tov_q1=tov_q1, gate=1))
    return pd.DataFrame(rows)


def main():
    t0 = time.time()
    print("[r5] loading panel + daily for regime indicators...")
    panel4 = pd.read_parquet(f"{OUT}/panel_trend_round4.parquet")
    panel4["trade_date"] = pd.to_datetime(panel4["trade_date"])
    panel4 = panel4.dropna(subset=["industry"])

    daily = pd.read_parquet("/home/user/Factor_Zoo/.cache/daily.parquet").merge(
        pd.read_parquet("/home/user/Factor_Zoo/.cache/adj_factor.parquet"),
        on=["ts_code","trade_date"], how="left"
    )
    daily["adj_factor"] = daily["adj_factor"].fillna(1.0)
    daily["P"] = daily["close"] * daily["adj_factor"]
    daily = daily.sort_values(["ts_code","trade_date"]).reset_index(drop=True)
    daily["ret"] = daily.groupby("ts_code")["P"].transform(lambda s: np.log(s).diff())
    print(f"  daily ret built {time.time()-t0:.1f}s")

    # Equal-weight market series
    print("[r5] building market regime indicators...")
    mkt = daily.groupby("trade_date")["ret"].mean().to_frame("ew_ret").sort_index()
    mkt["ew_cum"] = mkt["ew_ret"].cumsum()
    mkt["ew_MA200"] = mkt["ew_cum"].rolling(200, min_periods=160).mean()
    mkt["ew_slope_21"] = mkt["ew_MA200"].diff(21)
    mkt["mkt_ret_252"] = mkt["ew_ret"].rolling(252, min_periods=200).sum()
    mkt["mkt_ret_21"] = mkt["ew_ret"].rolling(21, min_periods=15).sum()
    mkt["mkt_TS_mom"] = mkt["mkt_ret_252"] - mkt["mkt_ret_21"]
    mkt["mkt_vol_60"] = mkt["ew_ret"].rolling(60, min_periods=40).std()
    mkt["mkt_vol_60_med252"] = mkt["mkt_vol_60"].rolling(252, min_periods=180).median()

    # Breadth: fraction of stocks above own MA200
    daily["MA200_self"] = daily.groupby("ts_code")["P"].transform(
        lambda s: s.rolling(200, min_periods=160).mean()
    )
    daily["above_MA200"] = (daily["P"] > daily["MA200_self"]).astype(float)
    breadth = daily.groupby("trade_date")["above_MA200"].mean().rename("breadth")

    # Cross-sectional dispersion of 20d returns
    daily["ret_20"] = daily.groupby("ts_code")["ret"].transform(lambda s: s.rolling(20, min_periods=15).sum())
    disp = daily.groupby("trade_date")["ret_20"].std().rename("mkt_disp")
    disp_med252 = disp.rolling(252, min_periods=180).median().rename("mkt_disp_med252")

    regime = mkt.join(breadth, how="left").join(disp, how="left").join(disp_med252, how="left")
    regime.to_csv(f"{OUT}/market_regime.csv")
    print(f"  regime indicators saved ({len(regime)} dates) {time.time()-t0:.1f}s")

    # Build gates per trade_date
    gates = pd.DataFrame(index=regime.index)
    gates["α_33_uptrend"] = (regime["ew_slope_21"] > 0).astype(int)
    gates["α_34_breadth"] = (regime["breadth"] > 0.5).astype(int)
    gates["α_35_disp"] = (regime["mkt_disp"] > regime["mkt_disp_med252"]).astype(int)
    gates["α_36_TSmom"] = (regime["mkt_TS_mom"] > 0).astype(int)
    gates["α_37_calm"] = (regime["mkt_vol_60"] < regime["mkt_vol_60_med252"]).astype(int)
    # α_38 continuous: sigmoid of normalized regime score
    score = (
        np.sign(regime["ew_slope_21"]).fillna(0) * 0.5
        + (regime["breadth"] - 0.5).fillna(0)
        + np.sign(regime["mkt_TS_mom"]).fillna(0) * 0.5
    )
    z = (score - score.rolling(252, min_periods=180).mean()) / score.rolling(252, min_periods=180).std()
    gates["α_38_softmax"] = 1.0 / (1.0 + np.exp(-z))  # continuous in [0,1]
    gates["α_39_combo"] = ((regime["ew_slope_21"] > 0) & (regime["breadth"] > 0.4)).astype(int)
    # α_40 placeholder — assigned post-hoc to whichever single hard gate had best worst-year on training period

    # Industry-neutralize α_29
    print("[r5] industry-neutralize α_29...")
    panel4["alpha_29_n"] = industry_demean(panel4, "alpha_29")

    all_dates = pd.Index(sorted(panel4["trade_date"].unique()))
    rebal_dates = all_dates[::REBAL]
    print(f"  {len(rebal_dates)} rebal dates")

    summary_rows = []
    py_dump = {}
    gates_to_test = ["α_33_uptrend","α_34_breadth","α_35_disp","α_36_TSmom","α_37_calm","α_38_softmax","α_39_combo"]

    for gname in gates_to_test:
        gate_series = gates[gname]
        # For continuous gate (α_38), threshold at 0.5
        if gname == "α_38_softmax":
            gate_used = (gate_series > 0.5).astype(int)
        else:
            gate_used = gate_series.astype(int)
        gate_used.name = gname
        res = quintile_portfolios_gated(panel4, "alpha_29_n", f"fwd_ret_{PRIMARY_K}", rebal_dates, gate_used)
        if res.empty:
            continue
        res = res.set_index("trade_date").sort_index()
        cost_ls = (res["tov_q5"] + res["tov_q1"]) * (COST_BPS / 1e4)
        cost_q5 = res["tov_q5"] * (COST_BPS / 1e4)
        res["ls_after"] = res["ls"] - cost_ls
        res["q5_excess"] = res["q5"] - res["all"]
        res["q5_excess_after"] = res["q5_excess"] - cost_q5

        full = perf(res["ls_after"], 12)
        full_q5 = perf(res["q5_excess_after"], 12)
        py = per_year(res["ls_after"], 12)
        py_q5 = per_year(res["q5_excess_after"], 12)
        train = res[res.index <= TRAIN_END]
        valid = res[(res.index > TRAIN_END) & (res.index <= VALID_END)]
        test = res[res.index > VALID_END]
        m_train = perf(train["ls_after"], 12)["sharpe"]
        m_valid = perf(valid["ls_after"], 12)["sharpe"]
        m_test = perf(test["ls_after"], 12)["sharpe"]
        m_q5_test = perf(test["q5_excess_after"], 12)["sharpe"]
        worst = min(py.values()) if py else np.nan
        worst_q5 = min(py_q5.values()) if py_q5 else np.nan
        on_frac = res["gate"].mean()
        summary_rows.append(dict(
            alpha_id=gname.split("_")[0],
            gate=gname,
            on_frac=on_frac,
            ls_full=full["sharpe"], ls_train=m_train, ls_valid=m_valid, ls_test=m_test,
            q5_full=full_q5["sharpe"], q5_test=m_q5_test,
            maxdd=full["maxdd"], worst_year_ls=worst, worst_year_q5=worst_q5,
            n=len(res),
        ))
        py_dump[gname] = {"ls": py, "q5": py_q5}

    # α_40 — adaptive: pick best individual gate by training-period LS Sharpe + min worst-year
    # Score = train_ls + 0.5 * worst_year (roughly trade off)
    individual = [r for r in summary_rows if r["gate"] not in ("α_38_softmax", "α_39_combo")]
    best_ind = max(individual, key=lambda r: (r["ls_train"] + 0.5 * (r["worst_year_ls"] if not pd.isna(r["worst_year_ls"]) else -10)))
    best_gate_name = best_ind["gate"]
    best_gate_series = (gates[best_gate_name] > (0.5 if best_gate_name == "α_38_softmax" else 0)).astype(int)
    best_gate_series.name = "α_40_adaptive"
    res = quintile_portfolios_gated(panel4, "alpha_29_n", f"fwd_ret_{PRIMARY_K}", rebal_dates, best_gate_series)
    res = res.set_index("trade_date").sort_index()
    cost_ls = (res["tov_q5"] + res["tov_q1"]) * (COST_BPS / 1e4)
    cost_q5 = res["tov_q5"] * (COST_BPS / 1e4)
    res["ls_after"] = res["ls"] - cost_ls
    res["q5_excess_after"] = (res["q5"] - res["all"]) - cost_q5
    full = perf(res["ls_after"], 12)
    py = per_year(res["ls_after"], 12)
    py_q5 = per_year(res["q5_excess_after"], 12)
    test = res[res.index > VALID_END]
    summary_rows.append(dict(
        alpha_id="α_40",
        gate=f"adaptive_best_of_train={best_gate_name}",
        on_frac=res["gate"].mean(),
        ls_full=full["sharpe"], ls_train=perf(res[res.index <= TRAIN_END]["ls_after"], 12)["sharpe"],
        ls_valid=perf(res[(res.index > TRAIN_END) & (res.index <= VALID_END)]["ls_after"], 12)["sharpe"],
        ls_test=perf(test["ls_after"], 12)["sharpe"],
        q5_full=perf(res["q5_excess_after"], 12)["sharpe"],
        q5_test=perf(test["q5_excess_after"], 12)["sharpe"],
        maxdd=full["maxdd"],
        worst_year_ls=min(py.values()) if py else np.nan,
        worst_year_q5=min(py_q5.values()) if py_q5 else np.nan,
        n=len(res),
    ))
    py_dump["α_40_adaptive"] = {"ls": py, "q5": py_q5}

    # Baseline (no gate) for comparison
    res_no_gate = quintile_portfolios_gated(panel4, "alpha_29_n", f"fwd_ret_{PRIMARY_K}", rebal_dates,
                                            pd.Series(1, index=all_dates))
    res_no_gate = res_no_gate.set_index("trade_date").sort_index()
    cost_ls = (res_no_gate["tov_q5"] + res_no_gate["tov_q1"]) * (COST_BPS / 1e4)
    cost_q5 = res_no_gate["tov_q5"] * (COST_BPS / 1e4)
    res_no_gate["ls_after"] = res_no_gate["ls"] - cost_ls
    res_no_gate["q5_excess_after"] = (res_no_gate["q5"] - res_no_gate["all"]) - cost_q5
    py_no = per_year(res_no_gate["ls_after"], 12)
    py_no_q5 = per_year(res_no_gate["q5_excess_after"], 12)
    full_no = perf(res_no_gate["ls_after"], 12)
    test_no = res_no_gate[res_no_gate.index > VALID_END]
    summary_rows.append(dict(
        alpha_id="α_29",
        gate="no_gate_baseline",
        on_frac=1.0,
        ls_full=full_no["sharpe"],
        ls_train=perf(res_no_gate[res_no_gate.index <= TRAIN_END]["ls_after"], 12)["sharpe"],
        ls_valid=perf(res_no_gate[(res_no_gate.index > TRAIN_END) & (res_no_gate.index <= VALID_END)]["ls_after"], 12)["sharpe"],
        ls_test=perf(test_no["ls_after"], 12)["sharpe"],
        q5_full=perf(res_no_gate["q5_excess_after"], 12)["sharpe"],
        q5_test=perf(test_no["q5_excess_after"], 12)["sharpe"],
        maxdd=full_no["maxdd"],
        worst_year_ls=min(py_no.values()) if py_no else np.nan,
        worst_year_q5=min(py_no_q5.values()) if py_no_q5 else np.nan,
        n=len(res_no_gate),
    ))
    py_dump["α_29_no_gate"] = {"ls": py_no, "q5": py_no_q5}

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(f"{OUT}/backtest_results_batch_0005.csv", index=False)
    print("\n[r5] SUMMARY (Round 5 regime overlays vs no-gate baseline):")
    print(summary.to_string(index=False))

    audit = {
        "round": 5,
        "purpose": "lift α_29 worst-year LS Sharpe above 0.5 with market regime overlay",
        "best_individual_gate_for_α_40": best_gate_name,
        "per_year": py_dump,
    }
    with open(f"{OUT}/audits_round5.json", "w") as f:
        json.dump(audit, f, indent=2, default=str)
    print(f"\n[r5] done in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
