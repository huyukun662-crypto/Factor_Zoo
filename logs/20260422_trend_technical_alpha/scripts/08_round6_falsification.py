"""
Round 6 — falsification of α_35 (dispersion-gated α_29).
1) Spec sensitivity: dispersion threshold and lookback variants.
2) Placebo: 100 random gates with same on-fraction → distribution test.
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


def per_year(returns, ppy=12, ignore_cash=False):
    yrs = returns.index.year
    out = {}
    for y in sorted(set(yrs)):
        r = returns[yrs == y]
        if len(r) >= 6:
            v = r.std(ddof=0)
            if v > 0:
                out[int(y)] = float((r.mean()*ppy)/(v*np.sqrt(ppy)))
            elif abs(r.mean()) < 1e-9:
                if not ignore_cash:
                    out[int(y)] = 0.0
            else:
                out[int(y)] = float("nan")
    return out


def quintile_portfolios_gated(df, alpha, ret_col, rebal_dates, gate_series):
    rows = []
    prev_q5 = set(); prev_q1 = set()
    prev_state = 0
    panel = df[["trade_date","ts_code", alpha, ret_col]].dropna()
    for t in rebal_dates:
        gate = int(gate_series.get(t, 0))
        if gate == 0:
            tov_q5 = 1.0 if prev_state == 1 else 0.0
            tov_q1 = 1.0 if prev_state == 1 else 0.0
            rows.append(dict(trade_date=t, ls=0.0, q5=0.0, q1=0.0, all=0.0,
                             tov_q5=tov_q5, tov_q1=tov_q1, gate=0))
            prev_state = 0
            prev_q5 = set(); prev_q1 = set()
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
        q5 = snap[snap["q"] == 4]
        q1 = snap[snap["q"] == 0]
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


def evaluate(panel, gate_series, rebal_dates):
    res = quintile_portfolios_gated(panel, "alpha_29_n", f"fwd_ret_{PRIMARY_K}", rebal_dates, gate_series)
    res = res.set_index("trade_date").sort_index()
    cost_ls = (res["tov_q5"] + res["tov_q1"]) * (COST_BPS / 1e4)
    cost_q5 = res["tov_q5"] * (COST_BPS / 1e4)
    res["ls_after"] = res["ls"] - cost_ls
    res["q5_excess_after"] = (res["q5"] - res["all"]) - cost_q5
    full = perf(res["ls_after"], 12)
    py = per_year(res["ls_after"], 12)
    py_active = per_year(res["ls_after"], 12, ignore_cash=True)
    test = res[res.index > VALID_END]
    return dict(
        ls_full=full["sharpe"],
        ls_train=perf(res[res.index <= TRAIN_END]["ls_after"], 12)["sharpe"],
        ls_valid=perf(res[(res.index > TRAIN_END) & (res.index <= VALID_END)]["ls_after"], 12)["sharpe"],
        ls_test=perf(test["ls_after"], 12)["sharpe"],
        q5_test=perf(test["q5_excess_after"], 12)["sharpe"],
        maxdd=full["maxdd"],
        worst_year_all=min(py.values()) if py else np.nan,
        worst_year_active=min(py_active.values()) if py_active else np.nan,
        on_frac=res["gate"].mean(),
        per_year=py,
    )


def main():
    t0 = time.time()
    panel4 = pd.read_parquet(f"{OUT}/panel_trend_round4.parquet")
    panel4["trade_date"] = pd.to_datetime(panel4["trade_date"])
    panel4 = panel4.dropna(subset=["industry"])
    panel4["alpha_29_n"] = industry_demean(panel4, "alpha_29")

    daily = pd.read_parquet("/home/user/Factor_Zoo/.cache/daily.parquet").merge(
        pd.read_parquet("/home/user/Factor_Zoo/.cache/adj_factor.parquet"),
        on=["ts_code","trade_date"], how="left"
    )
    daily["adj_factor"] = daily["adj_factor"].fillna(1.0)
    daily["P"] = daily["close"] * daily["adj_factor"]
    daily = daily.sort_values(["ts_code","trade_date"]).reset_index(drop=True)
    daily["ret"] = daily.groupby("ts_code")["P"].transform(lambda s: np.log(s).diff())
    daily["ret_20"] = daily.groupby("ts_code")["ret"].transform(lambda s: s.rolling(20, min_periods=15).sum())
    disp = daily.groupby("trade_date")["ret_20"].std().rename("mkt_disp")
    print(f"  disp series built {time.time()-t0:.1f}s")

    all_dates = pd.Index(sorted(panel4["trade_date"].unique()))
    rebal_dates = all_dates[::REBAL]

    # ---- Spec sensitivity variants ----
    print("\n[r6] SPEC SENSITIVITY of dispersion gate:")
    spec_rows = []
    spec_configs = [
        ("baseline_252d_med",  disp.rolling(252, min_periods=180).median(), 0.5),
        ("60d_med",            disp.rolling(60,  min_periods=40).median(),  0.5),
        ("126d_med",           disp.rolling(126, min_periods=80).median(),  0.5),
        ("504d_med",           disp.rolling(504, min_periods=300).median(), 0.5),
        ("252d_p40",           disp.rolling(252, min_periods=180).quantile(0.40), 0.5),
        ("252d_p60",           disp.rolling(252, min_periods=180).quantile(0.60), 0.5),
        ("252d_p70",           disp.rolling(252, min_periods=180).quantile(0.70), 0.5),
    ]
    for name, threshold, _ in spec_configs:
        gate = (disp > threshold).astype(int)
        res = evaluate(panel4, gate, rebal_dates)
        spec_rows.append(dict(spec=name, **{k: v for k, v in res.items() if k != "per_year"}))
    spec_df = pd.DataFrame(spec_rows)
    print(spec_df.to_string(index=False))
    spec_df.to_csv(f"{OUT}/round6_spec_sensitivity.csv", index=False)

    # ---- Placebo test: random gates with same on-fraction as baseline (~0.43) ----
    print("\n[r6] PLACEBO: 100 random gates, on_fraction matched to baseline (0.43)...")
    np.random.seed(20260422)
    n_trials = 100
    placebo_rows = []
    for trial in range(n_trials):
        # Random gate per rebal_date
        on_mask = np.random.rand(len(all_dates)) < 0.43
        rand_gate = pd.Series(on_mask.astype(int), index=all_dates)
        res = evaluate(panel4, rand_gate, rebal_dates)
        placebo_rows.append(dict(trial=trial, **{k: v for k, v in res.items() if k != "per_year"}))
    placebo_df = pd.DataFrame(placebo_rows)
    placebo_df.to_csv(f"{OUT}/round6_placebo_random_gates.csv", index=False)

    # Compute baseline (α_35) metrics
    base_gate = (disp > disp.rolling(252, min_periods=180).median()).astype(int)
    base_res = evaluate(panel4, base_gate, rebal_dates)

    pct = lambda v, col: (placebo_df[col] >= v).mean()
    placebo_summary = pd.DataFrame([{
        "metric": col,
        "α_35_value": base_res[col],
        "placebo_mean": placebo_df[col].mean(),
        "placebo_p95": placebo_df[col].quantile(0.95),
        "placebo_p99": placebo_df[col].quantile(0.99),
        "placebo_max": placebo_df[col].max(),
        "p_value_one_sided": pct(base_res[col], col),
    } for col in ["ls_full", "ls_test", "q5_test", "worst_year_active"]])
    print("\n[r6] PLACEBO DISTRIBUTION vs α_35:")
    print(placebo_summary.to_string(index=False))
    placebo_summary.to_csv(f"{OUT}/round6_placebo_summary.csv", index=False)

    audit = {
        "round": 6,
        "purpose": "spec_sensitivity_+_placebo_falsification_for_α_35_dispersion_gate",
        "α_35_baseline_metrics": base_res,
        "spec_variants_summary": spec_df.to_dict(orient="records"),
        "placebo_n_trials": n_trials,
        "placebo_summary": placebo_summary.to_dict(orient="records"),
    }
    with open(f"{OUT}/audits_round6.json", "w") as f:
        json.dump(audit, f, indent=2, default=str)
    print(f"\n[r6] done in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
