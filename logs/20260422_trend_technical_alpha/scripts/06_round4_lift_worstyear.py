"""
Round 4 — variants of α_19 (12-2 idio momentum) attempting to lift worst-year (2023) above 0.5.
α_25..α_32.
"""
from __future__ import annotations
import json
import time
import numpy as np
import pandas as pd

ROOT = "/home/user/Factor_Zoo/logs/20260422_trend_technical_alpha"
OUT = f"{ROOT}/outputs"

ALPHAS = [f"alpha_{i:02d}" for i in range(25, 33)]
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
            out.loc[m.index] = y - X @ beta
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
    prev_q5 = set(); prev_q1 = set()
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
        cur_q5 = set(q5["ts_code"]); cur_q1 = set(q1["ts_code"])
        tov_q5 = 1.0 - len(cur_q5 & prev_q5) / max(len(cur_q5), 1) if prev_q5 else 1.0
        tov_q1 = 1.0 - len(cur_q1 & prev_q1) / max(len(cur_q1), 1) if prev_q1 else 1.0
        prev_q5, prev_q1 = cur_q5, cur_q1
        rows.append(dict(trade_date=t, q5=q5[ret_col].mean(), q1=q1[ret_col].mean(),
                         ls=q5[ret_col].mean()-q1[ret_col].mean(), all=all_ret,
                         tov_q5=tov_q5, tov_q1=tov_q1))
    return pd.DataFrame(rows)


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
            out[int(y)] = float((r.mean()*ppy)/(v*np.sqrt(ppy))) if v > 0 else float("nan")
    return out


def main():
    t0 = time.time()
    df3 = pd.read_parquet(f"{OUT}/panel_trend_round3.parquet")
    df3["trade_date"] = pd.to_datetime(df3["trade_date"])

    df2 = pd.read_parquet(f"{OUT}/panel_trend_round2.parquet")[
        ["ts_code","trade_date","alpha_19" if False else "log_mv","sigma_120","ret_20"]
    ].rename(columns={})
    # fix selection
    df2 = pd.read_parquet(f"{OUT}/panel_trend_round2.parquet")[
        ["ts_code","trade_date","log_mv","sigma_120","ret_20","alpha_19" if False else "alpha_15"]
    ]
    df2["trade_date"] = pd.to_datetime(df2["trade_date"])

    daily = pd.read_parquet("/home/user/Factor_Zoo/.cache/daily.parquet").merge(
        pd.read_parquet("/home/user/Factor_Zoo/.cache/adj_factor.parquet"),
        on=["ts_code","trade_date"], how="left"
    )
    daily["adj_factor"] = daily["adj_factor"].fillna(1.0)
    daily["P"] = daily["close"] * daily["adj_factor"]
    daily = daily.sort_values(["ts_code","trade_date"]).reset_index(drop=True)
    daily["ret"] = daily.groupby("ts_code")["P"].transform(lambda s: np.log(s).diff())
    g = daily.groupby("ts_code")["ret"]
    daily["cum_252"] = g.transform(lambda s: s.rolling(252, min_periods=200).sum())
    daily["cum_42"] = g.transform(lambda s: s.rolling(42, min_periods=30).sum())
    daily["cum_63"] = g.transform(lambda s: s.rolling(63, min_periods=45).sum())
    daily["cum_378"] = g.transform(lambda s: s.rolling(378, min_periods=280).sum())
    daily["cum_21"] = g.transform(lambda s: s.rolling(21, min_periods=15).sum())
    daily["sigma_60"] = g.transform(lambda s: s.rolling(60, min_periods=40).std(ddof=0))
    daily["ret_42"] = daily["cum_42"]
    daily["raw_19"] = daily["cum_252"] - daily["cum_42"]
    daily["raw_29"] = daily["cum_252"] - daily["cum_63"]   # 12-3
    daily["raw_30"] = daily["cum_378"] - daily["cum_21"]   # 18-1
    print(f"  rolling sums {time.time()-t0:.1f}s")

    df = df3[["ts_code","trade_date","industry","total_mv","alpha_19","alpha_21",
              "fwd_ret_5","fwd_ret_20","fwd_ret_60"]].merge(
        df2[["ts_code","trade_date","log_mv","sigma_120","ret_20"]],
        on=["ts_code","trade_date"], how="left"
    ).merge(
        daily[["ts_code","trade_date","sigma_60","ret_42","raw_19","raw_29","raw_30"]],
        on=["ts_code","trade_date"], how="left"
    )

    # ---- α_25: α_19 large-cap (mv ≥ median per date) ----
    df["mv_med"] = df.groupby("trade_date")["total_mv"].transform("median")
    df["alpha_25"] = np.where(df["total_mv"] >= df["mv_med"], df["alpha_19"], np.nan)

    # ---- α_26: α_19 large-cap top-30% (mv ≥ 70th pctile per date) ----
    df["mv_70"] = df.groupby("trade_date")["total_mv"].transform(lambda s: s.quantile(0.70))
    df["alpha_26"] = np.where(df["total_mv"] >= df["mv_70"], df["alpha_19"], np.nan)

    # ---- α_27: industry-relative 12-2 momentum, then idio ----
    print("[r4] alpha_27 (industry-relative 12-2 idio)...")
    df["raw_19_ind"] = df["raw_19"] - df.groupby(["trade_date","industry"])["raw_19"].transform("mean")
    df["alpha_27"] = cs_residualize(df, "raw_19_ind", ["log_mv","sigma_120","ret_42"])

    # ---- α_28: α_19 with σ_60 control instead of σ_120 ----
    print("[r4] alpha_28 (12-2 with σ_60 control)...")
    df["alpha_28"] = cs_residualize(df, "raw_19", ["log_mv","sigma_60","ret_42"])

    # ---- α_29: 12-3 idio momentum ----
    print("[r4] alpha_29 (12-3 idio)...")
    df["alpha_29"] = cs_residualize(df, "raw_29", ["log_mv","sigma_120","ret_20"])

    # ---- α_30: 18-1 idio momentum ----
    print("[r4] alpha_30 (18-1 idio)...")
    df["alpha_30"] = cs_residualize(df, "raw_30", ["log_mv","sigma_120","ret_20"])

    # ---- α_31: combo 50/50 α_19 + α_21 ----
    z19 = df.groupby("trade_date")["alpha_19"].transform(lambda s: (s - s.mean()) / s.std(ddof=0))
    z21 = df.groupby("trade_date")["alpha_21"].transform(lambda s: (s - s.mean()) / s.std(ddof=0))
    df["alpha_31"] = (z19 + z21) / 2.0

    # ---- α_32: industry-relative + double residual ----
    print("[r4] alpha_32 (double residual)...")
    df["alpha_32"] = cs_residualize(df, "raw_19_ind", ["log_mv","sigma_60","ret_20","ret_42"])

    # Save
    keep = ["ts_code","trade_date","industry","total_mv"] + ALPHAS + ["fwd_ret_5","fwd_ret_20","fwd_ret_60"]
    panel4 = df[keep].copy()
    panel4.to_parquet(f"{OUT}/panel_trend_round4.parquet", index=False)
    print(f"  panel saved {time.time()-t0:.1f}s")

    df_n = panel4.dropna(subset=["industry"]).copy()
    for a in ALPHAS:
        df_n[a + "_n"] = industry_demean(df_n, a)

    # Rank IC
    print("[r4] rank IC...")
    ic_rows = []
    for a in ALPHAS:
        ic_n = rank_ic_by_date(df_n, a + "_n", f"fwd_ret_{PRIMARY_K}")
        ic_rows.append(dict(
            alpha=a,
            icn_mean=float(ic_n.mean()),
            icn_ir=float(ic_n.mean()/(ic_n.std()/np.sqrt(len(ic_n)))) if len(ic_n) > 1 and ic_n.std() > 0 else np.nan,
        ))
    print(pd.DataFrame(ic_rows).to_string(index=False))

    # Backtest
    all_dates = pd.Index(sorted(df_n["trade_date"].unique()))
    rebal_dates = all_dates[::REBAL]
    rows = []
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
        rows.append(dict(alpha=a,
            ls_full=full["sharpe"], ls_train=m_train, ls_valid=m_valid, ls_test=m_test,
            q5_full=full_q5["sharpe"], q5_test=m_q5_test,
            maxdd=full["maxdd"], worst_year=worst, worst_year_q5=worst_q5,
            tov_q5=res["tov_q5"].mean(), tov_q1=res["tov_q1"].mean(), n=len(res),
            per_year=py, per_year_q5=py_q5))

    summary = pd.DataFrame(rows).drop(columns=["per_year","per_year_q5"])
    summary.to_csv(f"{OUT}/backtest_results_batch_0004.csv", index=False)
    print("\n[r4] SUMMARY:")
    print(summary.to_string(index=False))

    # Per-year detail
    audit = {
        "round": 4,
        "purpose": "lift worst-year above 0.5 floor for α_19 family",
        "per_year_ls": {r["alpha"]: r["per_year"] for r in rows},
        "per_year_q5": {r["alpha"]: r["per_year_q5"] for r in rows},
    }
    with open(f"{OUT}/audits_round4.json", "w") as f:
        json.dump(audit, f, indent=2, default=str)
    print(f"\n[r4] done {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
