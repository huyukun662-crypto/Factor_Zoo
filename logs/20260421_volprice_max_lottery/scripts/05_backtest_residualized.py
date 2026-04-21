"""
Backtest residualized alphas — are they still deployable?
"""
import os, numpy as np, pandas as pd

SESSION = "/home/user/Factor_Zoo/logs/20260421_volprice_max_lottery"
PANEL = f"{SESSION}/outputs/panel_round2.parquet"
OUT = f"{SESSION}/outputs"

p = pd.read_parquet(PANEL)
p = p.sort_values(["trade_date", "ts_code"]).reset_index(drop=True)
dates = np.sort(p["trade_date"].unique())
reb_dates = dates[::20]


def period_mask(d):
    d = pd.to_datetime(d)
    if d < pd.to_datetime("2023-01-01"): return "train"
    if d < pd.to_datetime("2024-01-01"): return "validate"
    return "test"


def ann_sharpe(r):
    r = r.dropna()
    if len(r) < 3 or r.std() < 1e-9: return np.nan
    return r.mean() * 12 / (r.std() * np.sqrt(12))


def max_dd(r):
    c = (1 + r.fillna(0)).cumprod()
    return (c/c.cummax() - 1).min()


# Pick the top candidates by residualization screen
CANDS = [
    "r_08_full",  # abnormal MAX full residualized
    "r_08_volrev",
    "r_03_full",  # 60d MAX full residualized
    "r_03_volrev",
    "r_04_vol",   # vol-scaled, vol-residualized (α_04 already vol-normalized)
    "r_08_vol",
    "r_08_rev",   # abnormal MAX stripped of reversal only
    "r_03_rev",
]

rows = []
for a in CANDS:
    print(f"\n=== {a} ===")
    prev5, prev1 = set(), set()
    br = []
    for rd in reb_dates:
        sub = p.loc[p["trade_date"] == rd, ["ts_code", a, "fwd_ret_20"]].dropna()
        if len(sub) < 100: continue
        try:
            sub["q"] = pd.qcut(sub[a], 5, labels=["Q1","Q2","Q3","Q4","Q5"])
        except ValueError:
            sub["q"] = pd.qcut(sub[a].rank(method="first"), 5, labels=["Q1","Q2","Q3","Q4","Q5"])
        qr = sub.groupby("q", observed=True)["fwd_ret_20"].mean()
        mkt = sub["fwd_ret_20"].mean()
        q5 = set(sub.loc[sub["q"]=="Q5", "ts_code"]); q1 = set(sub.loc[sub["q"]=="Q1", "ts_code"])
        t5 = 1 - len(q5&prev5)/max(len(q5),1) if prev5 else 0.0
        t1 = 1 - len(q1&prev1)/max(len(q1),1) if prev1 else 0.0
        prev5, prev1 = q5, q1
        ls = qr.get("Q5", np.nan) - qr.get("Q1", np.nan)
        cost = (t5 + t1) * 5e-4
        br.append({"date": rd, "ls_gross": ls, "ls_net": ls - cost, "q5_excess_net": qr.get("Q5", np.nan) - mkt - t5*5e-4,
                   "q1_excess_net": qr.get("Q1", np.nan) - mkt - t1*5e-4,
                   "t5": t5, "t1": t1, "period": period_mask(rd)})
    bt = pd.DataFrame(br)
    for per in ["full", "train", "validate", "test"]:
        s = bt if per == "full" else bt[bt.period == per]
        rows.append({
            "alpha": a, "period": per,
            "ls_net_sharpe": ann_sharpe(s["ls_net"]),
            "q5_excess_ir": ann_sharpe(s["q5_excess_net"]),
            "q1_excess_ir": ann_sharpe(s["q1_excess_net"]),
            "ls_max_dd": max_dd(s["ls_net"]),
            "avg_t5": s["t5"].mean(),
            "avg_t1": s["t1"].mean(),
        })

r = pd.DataFrame(rows)
r.to_csv(f"{OUT}/backtest_results_batch_0002.csv", index=False)
print()
print(r[r.period == "full"].to_string(index=False))
print()
print(r[r.period == "test"].to_string(index=False))
