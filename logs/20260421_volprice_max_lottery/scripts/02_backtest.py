"""
Backtest Operator — 8 alphas × full/train/validate/test × monthly rebalance × 5 bps cost

Approach:
  - For each rebalance date t (every 20 trading days),
    1) form quintile portfolios by alpha value (industry-demean already in panel)
    2) equal-weight within quantile
    3) hold for 20 trading days → next forward return (fwd_ret_20 at t)
    4) compute turnover vs previous rebalance's Q5 / Q1 composition
    5) net cost: turnover × 2 × 5 bps (one-side × two sides for LS; for Q5 long-only, turnover × 5 bps)
  - Aggregate: annualized Sharpe = mean(R) * 12 / std(R) * sqrt(12); use monthly frequency (12 periods/yr).
  - IC: spearman(alpha_t, fwd_ret_k_t) per trade_date, mean and ir over [full/train/validate/test]
"""
import os, json, numpy as np, pandas as pd
from scipy.stats import spearmanr

SESSION = "/home/user/Factor_Zoo/logs/20260421_volprice_max_lottery"
PANEL = f"{SESSION}/outputs/panel_volprice.parquet"
OUT_DIR = f"{SESSION}/outputs"

p = pd.read_parquet(PANEL)
p = p.sort_values(["trade_date", "ts_code"]).reset_index(drop=True)
dates = np.sort(p["trade_date"].unique())

# Pick rebalance dates: every 20 trading days
reb_dates = dates[::20]
print(f"Total dates: {len(dates)}, rebalance dates: {len(reb_dates)}")

ALPHAS = [f"alpha_{i:02d}" for i in range(1, 9)]


def period_mask(d):
    d = pd.to_datetime(d)
    if d < pd.to_datetime("2023-01-01"):
        return "train"
    elif d < pd.to_datetime("2024-01-01"):
        return "validate"
    else:
        return "test"


def ann_sharpe(ret_series, periods_per_year=12):
    r = ret_series.dropna()
    if len(r) < 3 or r.std() < 1e-9:
        return np.nan
    return r.mean() * periods_per_year / (r.std() * np.sqrt(periods_per_year))


def max_dd(ret_series):
    cum = (1 + ret_series.fillna(0)).cumprod()
    dd = cum / cum.cummax() - 1
    return dd.min()


all_results = []

for a in ALPHAS:
    print(f"\n=== {a} ===")
    # per-date Q5/Q1 portfolios
    rows = []
    prev_q5, prev_q1 = set(), set()
    for rd in reb_dates:
        sub = p.loc[p["trade_date"] == rd, ["ts_code", a, "fwd_ret_20"]].dropna()
        if len(sub) < 100:
            continue
        # quintile on alpha (already industry-demeaned z-score)
        try:
            sub["q"] = pd.qcut(sub[a], 5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"])
        except ValueError:
            # duplicate edges — fall back to rank-based bin
            sub["q"] = pd.qcut(sub[a].rank(method="first"), 5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"])
        q_ret = sub.groupby("q", observed=True)["fwd_ret_20"].mean()
        mkt = sub["fwd_ret_20"].mean()
        q5, q1 = set(sub.loc[sub["q"] == "Q5", "ts_code"]), set(sub.loc[sub["q"] == "Q1", "ts_code"])
        # turnover: fraction of names replaced on long side; symmetric on short
        t_q5 = 1 - len(q5 & prev_q5) / max(len(q5), 1) if prev_q5 else 0.0
        t_q1 = 1 - len(q1 & prev_q1) / max(len(q1), 1) if prev_q1 else 0.0
        prev_q5, prev_q1 = q5, q1
        rows.append({
            "date": rd,
            "Q1": q_ret.get("Q1", np.nan),
            "Q2": q_ret.get("Q2", np.nan),
            "Q3": q_ret.get("Q3", np.nan),
            "Q4": q_ret.get("Q4", np.nan),
            "Q5": q_ret.get("Q5", np.nan),
            "mkt": mkt,
            "t_q5": t_q5,
            "t_q1": t_q1,
        })
    bt = pd.DataFrame(rows).dropna(subset=["Q5", "Q1"])
    # LS gross = Q5 - Q1
    bt["ls_gross"] = bt["Q5"] - bt["Q1"]
    # turnover-aware net: cost per rebalance = (t_q5 + t_q1) * 5 bps (sum of both legs)
    bt["ls_cost"] = (bt["t_q5"] + bt["t_q1"]) * 5e-4
    bt["ls_net"] = bt["ls_gross"] - bt["ls_cost"]
    bt["q5_excess"] = bt["Q5"] - bt["mkt"]
    bt["q5_cost"] = bt["t_q5"] * 5e-4
    bt["q5_excess_net"] = bt["q5_excess"] - bt["q5_cost"]
    bt["q1_excess"] = bt["Q1"] - bt["mkt"]
    bt["q1_cost"] = bt["t_q1"] * 5e-4
    bt["q1_excess_net"] = bt["q1_excess"] - bt["q1_cost"]
    bt["period"] = bt["date"].map(period_mask)

    bt.to_csv(f"{OUT_DIR}/rebalances_{a}.csv", index=False)

    # IC daily
    # Compute daily IC for ICIR
    def daily_ic(sub, target):
        s = sub[[a, target]].dropna()
        if len(s) < 100:
            return np.nan
        return spearmanr(s[a], s[target]).correlation
    ic_by_date = p.groupby("trade_date").apply(
        lambda g: daily_ic(g, "fwd_ret_20"), include_groups=False
    )
    ic_by_date.index = pd.to_datetime(ic_by_date.index)

    def period_ic(period_name):
        if period_name == "full":
            return ic_by_date
        elif period_name == "train":
            return ic_by_date[ic_by_date.index < "2023-01-01"]
        elif period_name == "validate":
            return ic_by_date[(ic_by_date.index >= "2023-01-01") & (ic_by_date.index < "2024-01-01")]
        elif period_name == "test":
            return ic_by_date[ic_by_date.index >= "2024-01-01"]

    periods = ["full", "train", "validate", "test"]
    for per in periods:
        if per == "full":
            sub = bt
        else:
            sub = bt[bt.period == per]
        ic = period_ic(per)
        all_results.append({
            "alpha": a,
            "period": per,
            "n_rebalances": len(sub),
            "ls_gross_sharpe": ann_sharpe(sub["ls_gross"]),
            "ls_net_sharpe": ann_sharpe(sub["ls_net"]),
            "q5_excess_ir": ann_sharpe(sub["q5_excess_net"]),
            "q1_excess_ir": ann_sharpe(sub["q1_excess_net"]),
            "ls_net_max_dd": max_dd(sub["ls_net"]),
            "q5_max_dd": max_dd(sub["q5_excess_net"]),
            "avg_t_q5": sub["t_q5"].mean(),
            "avg_t_q1": sub["t_q1"].mean(),
            "ls_cost_bps_avg": sub["ls_cost"].mean() * 1e4,
            "ic_mean": ic.mean(),
            "ic_ir": ic.mean() / ic.std() * np.sqrt(252) if ic.std() > 0 else np.nan,
        })
    print(f"   full LS net Sharpe: {all_results[-4]['ls_net_sharpe']:.3f}")

res = pd.DataFrame(all_results)
res.to_csv(f"{OUT_DIR}/backtest_results_batch_0001.csv", index=False)
print()
print(res[res.period == "full"].to_string(index=False))
print()
print(res[res.period == "test"].to_string(index=False))
