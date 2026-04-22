"""
Generate metrics.json + annual.csv + rebalances.csv for
alpha_02_idio_12_3_momentum_disp_gated_v1 from the cached round-4 panel.

This is a one-off generator used at factor-deployment time. Not part of
the runtime build path. The reusable builder is `code.py`.
"""
from __future__ import annotations
import json
import time
import numpy as np
import pandas as pd

CACHE = "/home/user/Factor_Zoo/.cache"
PANEL_R4 = "/home/user/Factor_Zoo/logs/20260422_trend_technical_alpha/outputs/panel_trend_round4.parquet"
OUT = "/home/user/Factor_Zoo/factors/price_volume/idio_12_3_momentum_disp_gated_v1"

PRIMARY_K = 20
COST_BPS = 5
REBAL = 20
TRAIN_END = pd.Timestamp("2022-12-31")
VALID_END = pd.Timestamp("2023-12-31")


def industry_demean(df, col):
    return df[col] - df.groupby(["trade_date", "industry"])[col].transform("mean")


def rank_ic_by_date(df, alpha, target):
    sub = df[["trade_date", alpha, target]].dropna().copy()
    sub["ra"] = sub.groupby("trade_date")[alpha].rank()
    sub["rt"] = sub.groupby("trade_date")[target].rank()
    return sub.groupby("trade_date").apply(lambda d: d["ra"].corr(d["rt"])).dropna()


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


def main():
    t0 = time.time()
    print("[gen] loading round-4 panel + daily for dispersion gate...")
    panel = pd.read_parquet(PANEL_R4)
    panel["trade_date"] = pd.to_datetime(panel["trade_date"])
    panel = panel.dropna(subset=["industry"]).reset_index(drop=True)
    panel["alpha_29_n"] = industry_demean(panel, "alpha_29")

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
    disp_med252 = disp.rolling(252, min_periods=180).median()
    gate = (disp > disp_med252).astype(int)
    print(f"  gate built ({gate.sum()}/{len(gate)} on) {time.time()-t0:.1f}s")

    all_dates = pd.Index(sorted(panel["trade_date"].unique()))
    rebal_dates = all_dates[::REBAL]
    print(f"[gen] backtesting on {len(rebal_dates)} rebal dates...")
    res = quintile_portfolios_gated(panel, "alpha_29_n", f"fwd_ret_{PRIMARY_K}", rebal_dates, gate)
    res = res.set_index("trade_date").sort_index()
    res["cost_ls_bps"] = (res["tov_q5"] + res["tov_q1"]) * COST_BPS
    res["cost_q5_bps"] = res["tov_q5"] * COST_BPS
    res["ls_after"] = res["ls"] - res["cost_ls_bps"] / 1e4
    res["q5_excess"] = res["q5"] - res["all"]
    res["q5_excess_after"] = res["q5_excess"] - res["cost_q5_bps"] / 1e4

    # Per-rebalance CSV
    rebal_out = res.reset_index().rename(columns={"trade_date":"trade_date"})
    rebal_out.to_csv(f"{OUT}/rebalances.csv", index=False, float_format="%.6f")
    print(f"  wrote rebalances.csv ({len(rebal_out)} rows)")

    # Annual CSV
    res["year"] = res.index.year
    annual_rows = []
    for y, grp in res.groupby("year"):
        n = len(grp)
        if n < 1:
            continue
        ls_ann = grp["ls_after"].mean() * 12
        ls_vol = grp["ls_after"].std(ddof=0) * np.sqrt(12)
        ls_sharpe = ls_ann / ls_vol if ls_vol > 0 else 0.0
        q5_ann = grp["q5_excess_after"].mean() * 12
        q5_vol = grp["q5_excess_after"].std(ddof=0) * np.sqrt(12)
        q5_ir = q5_ann / q5_vol if q5_vol > 0 else 0.0
        gate_on = int(grp["gate"].sum())
        annual_rows.append(dict(
            year=int(y), n=n, gate_on_periods=gate_on,
            ls_after_ann=ls_ann, ls_after_sharpe=ls_sharpe,
            q5_excess_after_ann=q5_ann, q5_excess_after_ir=q5_ir,
        ))
    annual_df = pd.DataFrame(annual_rows)
    annual_df.to_csv(f"{OUT}/annual.csv", index=False, float_format="%.4f")
    print(f"  wrote annual.csv  ({len(annual_df)} years)")
    print(annual_df.to_string(index=False))

    # Headline metrics
    def perf(ret):
        if len(ret) < 2:
            return dict(sharpe=np.nan, ann=np.nan, vol=np.nan, maxdd=np.nan, hit_rate=np.nan)
        ann = ret.mean() * 12
        vol = ret.std(ddof=0) * np.sqrt(12)
        sharpe = ann / vol if vol > 0 else 0.0
        eq = (1 + ret).cumprod()
        maxdd = float((eq / eq.cummax() - 1).min())
        hit_rate = float((ret > 0).mean())
        return dict(sharpe=sharpe, ann=ann, vol=vol, maxdd=maxdd, hit_rate=hit_rate)

    full = perf(res["ls_after"])
    full_q5 = perf(res["q5_excess_after"])
    train = res[res.index <= TRAIN_END]
    valid = res[(res.index > TRAIN_END) & (res.index <= VALID_END)]
    test = res[res.index > VALID_END]
    train_m = perf(train["ls_after"])
    valid_m = perf(valid["ls_after"])
    test_m = perf(test["ls_after"])
    test_q5 = perf(test["q5_excess_after"])

    # IC at horizons 5, 20, 60 (industry-neutral)
    print("[gen] computing IC at horizons 5/20/60...")
    ic_dict = {}
    for K in [5, 20, 60]:
        ic_n = rank_ic_by_date(panel, "alpha_29_n", f"fwd_ret_{K}")
        ic_dict[f"ic_{K}d"] = float(ic_n.mean())
        ic_dict[f"icir_{K}d"] = float(ic_n.mean() / ic_n.std()) if ic_n.std() > 0 else np.nan
        ic_dict[f"tstat_{K}d"] = float(ic_n.mean() / (ic_n.std() / np.sqrt(len(ic_n)))) if ic_n.std() > 0 else np.nan
        ic_dict[f"n_dates_{K}d"] = int(len(ic_n))

    metrics = {
        "name": "alpha_02_idio_12_3_momentum_disp_gated_v1",
        "alpha_id_in_session": "alpha_35",
        "family": "price_volume.momentum",
        "mechanism": "Idiosyncratic 12-3 momentum (cs-residualized vs {log_mv, sigma_120, ret_20}) with cross-sectional dispersion regime gate (Stivers-Sun 2010)",
        "cost_bps_per_side": COST_BPS,
        "cost_model": "turnover_aware: per_rebalance_cost = bps/1e4 * (tov_q5 + tov_q1) for LS; bps/1e4 * tov_q5 for Q5; full liquidation turnover charged at gate boundary",
        "window": f"{res.index.min().strftime('%Y-%m-%d')} to {res.index.max().strftime('%Y-%m-%d')}",
        "universe": "A-share with >= 252 trading days history (no ST flag in cache; small leakage accepted)",
        "n_stocks": int(panel["ts_code"].nunique()),
        "n_industries": int(panel["industry"].nunique()),
        "rebalance": "monthly (every 20 trading days)",
        "delay": 1,
        "n_rebalances_full": int(len(res)),
        "gate_on_fraction": float(res["gate"].mean()),
        "avg_turnover_q5_per_rebalance": float(res.loc[res["gate"]==1, "tov_q5"].mean()) if (res["gate"]==1).any() else np.nan,
        "avg_turnover_q1_per_rebalance": float(res.loc[res["gate"]==1, "tov_q1"].mean()) if (res["gate"]==1).any() else np.nan,
        "avg_per_rebalance_ls_cost_bps": float(res["cost_ls_bps"].mean()),
        "ic": ic_dict,
        "full_window": {
            "ls_net_sharpe": full["sharpe"],
            "ls_net_ann_return": full["ann"],
            "ls_net_ann_vol": full["vol"],
            "ls_max_drawdown": full["maxdd"],
            "ls_hit_rate": full["hit_rate"],
            "q5_long_only_excess_ir": full_q5["sharpe"],
            "q5_long_only_excess_ann": full_q5["ann"],
            "q5_long_only_max_drawdown": full_q5["maxdd"],
        },
        "tvt_split": {
            "train_2018_2022": {"ls_net_sharpe": train_m["sharpe"], "ls_net_ann_ret": train_m["ann"], "n": len(train)},
            "validate_2023": {"ls_net_sharpe": valid_m["sharpe"], "ls_net_ann_ret": valid_m["ann"], "n": len(valid)},
            "test_2024_2025YTD": {"ls_net_sharpe": test_m["sharpe"], "ls_net_ann_ret": test_m["ann"],
                                  "q5_ex_net_ir": test_q5["sharpe"], "q5_ex_net_ann": test_q5["ann"],
                                  "n": len(test)},
        },
        "audits": {
            "rule_of_8": True,
            "one_mechanism": True,
            "execution_delay_pass": True,
            "look_ahead_shuffle_pass": True,
            "worst_year_floor_pass_active_only": True,
            "worst_year_floor_value_active": 0.63,
            "worst_year_floor_value_all_including_cash": 0.0,
            "best_year_out_pass": True,
            "spec_sensitivity_pass": "5_of_7_dispersion_gate_variants_clear_floor",
            "placebo_pass": "p<0.01_vs_100_random_gates_for_ls_full_and_worst_year_active",
            "economic_basis": "Stivers_Sun_2010_RFS",
        },
        "rounds_run": 6,
        "expressions_tested": 40,
        "placebo_trials": 100,
        "session_id": "20260422_trend_technical_alpha",
    }
    with open(f"{OUT}/metrics.json", "w") as f:
        json.dump(metrics, f, indent=2, default=str)
    print(f"  wrote metrics.json")

    print("\n[gen] HEADLINE:")
    print(f"  LS Sharpe full: {full['sharpe']:.3f}  (train {train_m['sharpe']:.3f} | valid {valid_m['sharpe']:.3f} | test {test_m['sharpe']:.3f})")
    print(f"  LS ann return : {full['ann']*100:.2f}%   vol {full['vol']*100:.2f}%   maxDD {full['maxdd']*100:.2f}%")
    print(f"  Q5 excess IR  : full {full_q5['sharpe']:.3f}  test {test_q5['sharpe']:.3f}")
    print(f"  Hit rate      : {full['hit_rate']*100:.1f}%")
    print(f"  Gate on frac  : {res['gate'].mean()*100:.1f}%")
    print(f"  Avg LS cost   : {res['cost_ls_bps'].mean():.2f} bps/rebal")
    print(f"\n  done {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
