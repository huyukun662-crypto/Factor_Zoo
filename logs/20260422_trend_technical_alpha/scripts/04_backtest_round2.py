"""
Round 2 backtest + audits — idiosyncratic momentum (alpha_09..alpha_16).
Same pipeline as 02_backtest_audit.py but for residualized alphas.
"""
from __future__ import annotations
import json
import time
import numpy as np
import pandas as pd

ROOT = "/home/user/Factor_Zoo/logs/20260422_trend_technical_alpha"
OUT = f"{ROOT}/outputs"
PANEL = f"{OUT}/panel_trend_round2.parquet"

ALPHAS = [f"alpha_{i:02d}" for i in range(9, 17)]
HORIZONS = [5, 20, 60]
PRIMARY_K = 20
COST_BPS = 5
REBAL = 20
TRAIN_END = pd.Timestamp("2022-12-31")
VALID_END = pd.Timestamp("2023-12-31")


def industry_demean(df, col):
    g = df.groupby(["trade_date", "industry"])[col]
    return df[col] - g.transform("mean")


def rank_ic_by_date(df, alpha, target):
    sub = df[["trade_date", alpha, target]].dropna().copy()
    if sub.empty:
        return pd.Series(dtype=float)
    sub["ra"] = sub.groupby("trade_date")[alpha].rank()
    sub["rt"] = sub.groupby("trade_date")[target].rank()
    return sub.groupby("trade_date").apply(lambda d: d["ra"].corr(d["rt"])).dropna()


def quintile_portfolios(df, alpha, ret_col, rebal_dates):
    rows = []
    prev_q5 = set()
    prev_q1 = set()
    panel = df[["trade_date", "ts_code", alpha, ret_col]].dropna()
    for t in rebal_dates:
        snap = panel[panel["trade_date"] == t]
        if len(snap) < 100:
            continue
        snap = snap.copy()
        snap["q"] = pd.qcut(snap[alpha].rank(method="first"), 5, labels=False, duplicates="drop")
        if snap["q"].isna().all():
            continue
        q5 = snap[snap["q"] == 4]
        q1 = snap[snap["q"] == 0]
        all_ret = snap[ret_col].mean()
        q5_ret = q5[ret_col].mean()
        q1_ret = q1[ret_col].mean()
        ls_ret = q5_ret - q1_ret
        cur_q5 = set(q5["ts_code"])
        cur_q1 = set(q1["ts_code"])
        tov_q5 = 1.0 - len(cur_q5 & prev_q5) / max(len(cur_q5), 1) if prev_q5 else 1.0
        tov_q1 = 1.0 - len(cur_q1 & prev_q1) / max(len(cur_q1), 1) if prev_q1 else 1.0
        prev_q5, prev_q1 = cur_q5, cur_q1
        rows.append(dict(trade_date=t, q5=q5_ret, q1=q1_ret, ls=ls_ret, all=all_ret, tov_q5=tov_q5, tov_q1=tov_q1))
    return pd.DataFrame(rows)


def perf_metrics(returns, periods_per_year=12):
    if len(returns) < 2:
        return {"sharpe": np.nan, "annret": np.nan, "annvol": np.nan, "maxdd": np.nan}
    annret = returns.mean() * periods_per_year
    annvol = returns.std(ddof=0) * np.sqrt(periods_per_year)
    sharpe = annret / annvol if annvol > 0 else np.nan
    eq = (1 + returns).cumprod()
    maxdd = (eq / eq.cummax() - 1).min()
    return {"sharpe": sharpe, "annret": annret, "annvol": annvol, "maxdd": maxdd}


def per_year_sharpe(returns, periods_per_year=12):
    yrs = returns.index.year
    out = {}
    for y in sorted(set(yrs)):
        r = returns[yrs == y]
        if len(r) >= 6:
            out[int(y)] = float((r.mean() * periods_per_year) / (r.std(ddof=0) * np.sqrt(periods_per_year))) if r.std(ddof=0) > 0 else float("nan")
    return out


def main():
    t0 = time.time()
    df = pd.read_parquet(PANEL)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.dropna(subset=["industry"])
    print(f"[r2bt] panel: {df.shape}")

    print("[r2bt] industry-neutralizing idio alphas...")
    for a in ALPHAS:
        df[a + "_n"] = industry_demean(df, a)

    print("[r2bt] rank IC...")
    ic_table = []
    for a in ALPHAS:
        for K in HORIZONS:
            ic = rank_ic_by_date(df, a, f"fwd_ret_{K}")
            ic_n = rank_ic_by_date(df, a + "_n", f"fwd_ret_{K}")
            ic_table.append(dict(
                alpha=a, horizon=K,
                ic_mean=float(ic.mean()), ic_std=float(ic.std()),
                ic_ir=float(ic.mean() / (ic.std() / np.sqrt(len(ic)))) if len(ic) > 1 and ic.std() > 0 else np.nan,
                icn_mean=float(ic_n.mean()),
                icn_ir=float(ic_n.mean() / (ic_n.std() / np.sqrt(len(ic_n)))) if len(ic_n) > 1 and ic_n.std() > 0 else np.nan,
            ))
    ic_df = pd.DataFrame(ic_table)
    ic_df.to_csv(f"{OUT}/rank_ic_round2.csv", index=False)
    print(ic_df.to_string(index=False))

    all_dates = pd.Index(sorted(df["trade_date"].unique()))
    rebal_dates = all_dates[::REBAL]

    summary_rows = []
    for a in ALPHAS:
        res = quintile_portfolios(df, a + "_n", f"fwd_ret_{PRIMARY_K}", rebal_dates)
        if res.empty:
            continue
        res = res.set_index("trade_date").sort_index()
        cost_ls = (res["tov_q5"] + res["tov_q1"]) * (COST_BPS / 1e4)
        cost_q5 = res["tov_q5"] * (COST_BPS / 1e4)
        res["ls_after"] = res["ls"] - cost_ls
        res["q5_excess"] = res["q5"] - res["all"]
        res["q5_excess_after"] = res["q5_excess"] - cost_q5
        full = perf_metrics(res["ls_after"], 12)
        full_q5 = perf_metrics(res["q5_excess_after"], 12)
        py = per_year_sharpe(res["ls_after"], 12)
        py_q5 = per_year_sharpe(res["q5_excess_after"], 12)
        train = res[res.index <= TRAIN_END]
        valid = res[(res.index > TRAIN_END) & (res.index <= VALID_END)]
        test = res[res.index > VALID_END]
        m_train = perf_metrics(train["ls_after"], 12)
        m_valid = perf_metrics(valid["ls_after"], 12)
        m_test = perf_metrics(test["ls_after"], 12)
        m_q5_test = perf_metrics(test["q5_excess_after"], 12)
        worst_year = min(py.values()) if py else np.nan
        if py and len(py) >= 2:
            best_y = max(py, key=lambda k: py[k])
            res_no_best = res.loc[res.index.year != best_y]
            byo = perf_metrics(res_no_best["ls_after"], 12)["sharpe"]
        else:
            byo = np.nan
        summary_rows.append(dict(
            alpha=a,
            ic_primary=float(ic_df[(ic_df.alpha == a) & (ic_df.horizon == PRIMARY_K)]["ic_mean"].iloc[0]),
            icn_primary=float(ic_df[(ic_df.alpha == a) & (ic_df.horizon == PRIMARY_K)]["icn_mean"].iloc[0]),
            ls_sharpe_full=full["sharpe"],
            ls_sharpe_train=m_train["sharpe"],
            ls_sharpe_valid=m_valid["sharpe"],
            ls_sharpe_test=m_test["sharpe"],
            q5_excess_ir_full=full_q5["sharpe"],
            q5_excess_ir_test=m_q5_test["sharpe"],
            ls_maxdd_full=full["maxdd"],
            worst_year=worst_year,
            best_year_out_sharpe=byo,
            byo_pct_of_full=byo / full["sharpe"] if (not pd.isna(byo) and full["sharpe"]) else np.nan,
            avg_tov_q5=float(res["tov_q5"].mean()),
            avg_tov_q1=float(res["tov_q1"].mean()),
            n_periods=len(res),
            per_year=py,
        ))

    summary = pd.DataFrame(summary_rows).drop(columns=["per_year"])
    summary.to_csv(f"{OUT}/backtest_results_batch_0002.csv", index=False)
    print("\n[r2bt] SUMMARY:")
    print(summary.to_string(index=False))

    # Audits json
    audit = {
        "round": 2,
        "mechanism": "idiosyncratic_momentum_cs_residualized",
        "controls": ["log_mv", "sigma_120", "ret_20"],
        "residualization_method": "per-date OLS, walk-forward-safe by construction",
        "summary_signs": {r["alpha"]: int(np.sign(r["ls_sharpe_full"])) for r in summary_rows},
        "primary_horizon": PRIMARY_K,
        "rebal_days": REBAL,
        "cost_bps_per_side": COST_BPS,
        "per_year": {r["alpha"]: r["per_year"] for r in summary_rows},
    }
    with open(f"{OUT}/audits_round2.json", "w") as f:
        json.dump(audit, f, indent=2, default=str)

    print(f"\n[r2bt] done in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
