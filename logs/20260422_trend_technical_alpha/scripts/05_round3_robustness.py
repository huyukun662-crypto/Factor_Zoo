"""
Round 3 build + backtest — robustness variants of idio momentum.
α_17..α_24 as defined in expressions_batch_0003.md.
"""
from __future__ import annotations
import json
import time
import numpy as np
import pandas as pd

ROOT = "/home/user/Factor_Zoo/logs/20260422_trend_technical_alpha"
OUT = f"{ROOT}/outputs"

ALPHAS = [f"alpha_{i:02d}" for i in range(17, 25)]
PRIMARY_K = 20
COST_BPS = 5
REBAL = 20
TRAIN_END = pd.Timestamp("2022-12-31")
VALID_END = pd.Timestamp("2023-12-31")


def cs_residualize(df, target, controls):
    out = pd.Series(np.nan, index=df.index, dtype=np.float64)
    sub = df[["trade_date", target] + controls].copy()
    for d, idx in sub.groupby("trade_date").indices.items():
        rows = sub.loc[idx]
        m = rows[[target] + controls].dropna()
        if len(m) < 50:
            continue
        y = m[target].values
        X = np.column_stack([np.ones(len(m))] + [m[c].values for c in controls])
        try:
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
            yhat = X @ beta
            out.loc[m.index] = y - yhat
        except np.linalg.LinAlgError:
            continue
    return out


def industry_demean(df, col):
    return df[col] - df.groupby(["trade_date", "industry"])[col].transform("mean")


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
    print("[r3] loading round-2 panel + raw daily for new windows...")
    df = pd.read_parquet(f"{OUT}/panel_trend_round2.parquet")
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)

    daily = pd.read_parquet("/home/user/Factor_Zoo/.cache/daily.parquet").merge(
        pd.read_parquet("/home/user/Factor_Zoo/.cache/adj_factor.parquet"),
        on=["ts_code", "trade_date"], how="left"
    )
    daily["adj_factor"] = daily["adj_factor"].fillna(1.0)
    daily["P"] = daily["close"] * daily["adj_factor"]
    daily = daily.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)
    daily["ret"] = daily.groupby("ts_code")["P"].transform(lambda s: np.log(s).diff())
    print(f"  daily ret built  {time.time()-t0:.1f}s")

    g = daily.groupby("ts_code")["ret"]
    daily["cum_252"] = g.transform(lambda s: s.rolling(252, min_periods=200).sum())
    daily["cum_504"] = g.transform(lambda s: s.rolling(504, min_periods=350).sum())
    daily["cum_189"] = g.transform(lambda s: s.rolling(189, min_periods=140).sum())
    daily["cum_126"] = g.transform(lambda s: s.rolling(126, min_periods=90).sum())
    daily["cum_42"] = g.transform(lambda s: s.rolling(42, min_periods=30).sum())
    daily["cum_21"] = g.transform(lambda s: s.rolling(21, min_periods=15).sum())
    daily["sigma_60"] = g.transform(lambda s: s.rolling(60, min_periods=40).std(ddof=0))
    print(f"  rolling sums built  {time.time()-t0:.1f}s")

    # ret_42 control for α_19
    daily["ret_42"] = daily["cum_42"]

    df = df.merge(
        daily[["ts_code", "trade_date", "cum_252", "cum_504", "cum_189", "cum_126", "cum_42", "cum_21", "ret_42"]],
        on=["ts_code", "trade_date"], how="left"
    )

    # Raw composite signals
    df["raw_19"] = df["cum_252"] - df["cum_42"]   # 12-2 momentum
    df["raw_20"] = df["cum_504"] - df["cum_21"]   # 24-1 momentum
    df["raw_23"] = df["cum_126"] - df["cum_21"]   # 6-1 momentum
    df["raw_24"] = df["cum_189"] - df["cum_21"]   # 9-1 momentum

    # ---- α_17: α_15 large-cap filter (apply at evaluation, not construction) ----
    # We materialize α_15 here and compute a flag column for size-filter.
    df["mv_med"] = df.groupby("trade_date")["total_mv"].transform("median")
    df["large_cap"] = (df["total_mv"] >= df["mv_med"]).astype(int)
    df["alpha_17"] = np.where(df["large_cap"] == 1, df["alpha_15"], np.nan)

    # ---- α_18: industry-relative idio_12_1 ----
    print("[r3] alpha_18 (industry-relative)...")
    # ret_252_ind = ret_252 (= cum_252) - industry_mean(cum_252)
    df["ret_252_ind"] = df["cum_252"] - df.groupby(["trade_date", "industry"])["cum_252"].transform("mean")
    df["ret_20_ind"] = df["ret_20"] - df.groupby(["trade_date", "industry"])["ret_20"].transform("mean")
    df["raw_18"] = df["ret_252_ind"] - df["ret_20_ind"]
    df["alpha_18"] = cs_residualize(df, "raw_18", ["log_mv", "sigma_120", "ret_20"])

    # ---- α_19: 12-2 momentum idio ----
    print("[r3] alpha_19 (12-2 idio)...")
    df["alpha_19"] = cs_residualize(df, "raw_19", ["log_mv", "sigma_120", "ret_42"])

    # ---- α_20: 24-1 idio ----
    print("[r3] alpha_20 (24-1 idio)...")
    df["alpha_20"] = cs_residualize(df, "raw_20", ["log_mv", "sigma_120", "ret_20"])

    # ---- α_21: z-mean of α_12 + α_15 ----
    print("[r3] alpha_21 (combo 12+15)...")
    z12 = df.groupby("trade_date")["alpha_12"].transform(lambda s: (s - s.mean()) / s.std(ddof=0))
    z15 = df.groupby("trade_date")["alpha_15"].transform(lambda s: (s - s.mean()) / s.std(ddof=0))
    df["alpha_21"] = (z12 + z15) / 2.0

    # ---- α_22: z-mean α_11 + α_12 + α_15 ----
    print("[r3] alpha_22 (combo 11+12+15)...")
    z11 = df.groupby("trade_date")["alpha_11"].transform(lambda s: (s - s.mean()) / s.std(ddof=0))
    df["alpha_22"] = (z11 + z12 + z15) / 3.0

    # ---- α_23: 6-1 idio ----
    print("[r3] alpha_23 (6-1 idio)...")
    df["alpha_23"] = cs_residualize(df, "raw_23", ["log_mv", "sigma_120", "ret_20"])

    # ---- α_24: 9-1 idio ----
    print("[r3] alpha_24 (9-1 idio)...")
    df["alpha_24"] = cs_residualize(df, "raw_24", ["log_mv", "sigma_120", "ret_20"])

    # Save
    keep_cols = ["ts_code", "trade_date", "industry", "total_mv"] + ALPHAS + [f"fwd_ret_{K}" for K in [1,5,20,60]]
    panel3 = df[keep_cols].copy()
    panel3.to_parquet(f"{OUT}/panel_trend_round3.parquet", index=False)
    print(f"[r3] panel3 saved  {time.time()-t0:.1f}s")

    # Industry neutralize
    print("[r3] industry-neutralizing...")
    df_n = panel3.dropna(subset=["industry"]).copy()
    for a in ALPHAS:
        df_n[a + "_n"] = industry_demean(df_n, a)

    # Rank IC
    print("[r3] rank IC primary horizon...")
    ic_rows = []
    for a in ALPHAS:
        ic = rank_ic_by_date(df_n, a, f"fwd_ret_{PRIMARY_K}")
        ic_n = rank_ic_by_date(df_n, a + "_n", f"fwd_ret_{PRIMARY_K}")
        ic_rows.append(dict(
            alpha=a,
            ic_mean=float(ic.mean()),
            ic_ir=float(ic.mean() / (ic.std() / np.sqrt(len(ic)))) if len(ic) > 1 and ic.std() > 0 else np.nan,
            icn_mean=float(ic_n.mean()),
            icn_ir=float(ic_n.mean() / (ic_n.std() / np.sqrt(len(ic_n)))) if len(ic_n) > 1 and ic_n.std() > 0 else np.nan,
        ))
    ic_df = pd.DataFrame(ic_rows)
    print(ic_df.to_string(index=False))

    # Backtest
    all_dates = pd.Index(sorted(df_n["trade_date"].unique()))
    rebal_dates = all_dates[::REBAL]
    summary_rows = []
    for a in ALPHAS:
        res = quintile_portfolios(df_n, a + "_n", f"fwd_ret_{PRIMARY_K}", rebal_dates)
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
        ic_row = ic_df[ic_df.alpha == a].iloc[0]
        summary_rows.append(dict(
            alpha=a,
            ic_primary=float(ic_row["ic_mean"]),
            icn_primary=float(ic_row["icn_mean"]),
            ic_ir=float(ic_row["icn_ir"]),
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
    summary.to_csv(f"{OUT}/backtest_results_batch_0003.csv", index=False)
    print("\n[r3] SUMMARY:")
    print(summary.to_string(index=False))

    audit = {
        "round": 3,
        "mechanism": "idio_momentum_robustness_variants",
        "summary_signs": {r["alpha"]: int(np.sign(r["ls_sharpe_full"])) for r in summary_rows},
        "per_year": {r["alpha"]: r["per_year"] for r in summary_rows},
    }
    with open(f"{OUT}/audits_round3.json", "w") as f:
        json.dump(audit, f, indent=2, default=str)
    print(f"\n[r3] done in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
