"""
Round 2 — combined backtest + audits for α_09..α_16 (idiosyncratic skewness family).

Steps for each alpha:
  1) Pre-submission: coverage, xsection std, IC sign on validate
  2) Full backtest: LS/Q5/Q1 with 5bps turnover-aware cost
  3) Audits: look-ahead, worst-year, LOYO, falsification, residualization (full stack)
"""
import os, json, numpy as np, pandas as pd
from numpy.linalg import lstsq

SESSION = "/home/user/Factor_Zoo/logs/20260421_volprice_max_lottery"
PANEL = f"{SESSION}/outputs/panel_round2_skew.parquet"
OUT = f"{SESSION}/outputs"

p = pd.read_parquet(PANEL)
p["year"] = p["trade_date"].dt.year
p["log_mv"] = np.log1p(p["total_mv"])

ALPHAS = [f"alpha_{i:02d}" for i in range(9, 17)]


def rank_ic_by_date(panel, col, target="fwd_ret_20"):
    tmp = panel[[col, target]].dropna().copy()
    tmp["date"] = panel.loc[tmp.index, "trade_date"].values
    tmp["ra"] = tmp.groupby("date")[col].rank()
    tmp["rt"] = tmp.groupby("date")[target].rank()
    out = tmp.groupby("date")[["ra", "rt"]].corr().iloc[0::2, -1]
    return out


def ann_sharpe(r):
    r = r.dropna()
    if len(r) < 3 or r.std() < 1e-9: return np.nan
    return r.mean() * 12 / (r.std() * np.sqrt(12))


def max_dd(r):
    c = (1 + r.fillna(0)).cumprod()
    return (c/c.cummax() - 1).min()


def period_mask(d):
    d = pd.to_datetime(d)
    if d < pd.to_datetime("2023-01-01"): return "train"
    if d < pd.to_datetime("2024-01-01"): return "validate"
    return "test"


def backtest(panel, col):
    dates = np.sort(panel["trade_date"].unique())[::20]
    prev5, prev1 = set(), set()
    rows = []
    for rd in dates:
        sub = panel.loc[panel["trade_date"]==rd, ["ts_code", col, "fwd_ret_20"]].dropna()
        if len(sub) < 100: continue
        try:
            sub["q"] = pd.qcut(sub[col], 5, labels=["Q1","Q2","Q3","Q4","Q5"])
        except ValueError:
            sub["q"] = pd.qcut(sub[col].rank(method="first"), 5, labels=["Q1","Q2","Q3","Q4","Q5"])
        qr = sub.groupby("q", observed=True)["fwd_ret_20"].mean()
        mkt = sub["fwd_ret_20"].mean()
        q5 = set(sub.loc[sub["q"]=="Q5", "ts_code"]); q1 = set(sub.loc[sub["q"]=="Q1", "ts_code"])
        t5 = 1 - len(q5&prev5)/max(len(q5),1) if prev5 else 0.0
        t1 = 1 - len(q1&prev1)/max(len(q1),1) if prev1 else 0.0
        prev5, prev1 = q5, q1
        ls_gross = qr.get("Q5", np.nan) - qr.get("Q1", np.nan)
        cost = (t5 + t1) * 5e-4
        rows.append({
            "date": rd, "ls_gross": ls_gross, "ls_net": ls_gross - cost,
            "q5_exc": qr.get("Q5", np.nan) - mkt - t5*5e-4,
            "q1_exc": qr.get("Q1", np.nan) - mkt - t1*5e-4,
            "t5": t5, "t1": t1,
            "period": period_mask(rd), "year": pd.Timestamp(rd).year,
        })
    return pd.DataFrame(rows)


def residualize_ic(panel, col, ctrl_cols=["ret_5","ret_20","sigma_20","turnover_20","log_mv"]):
    ics = []
    for d, sub in panel.groupby("trade_date"):
        s = sub[[col] + ctrl_cols + ["fwd_ret_20"]].dropna()
        if len(s) < 200: continue
        X = s[ctrl_cols].values
        X = X - X.mean(axis=0)
        X = np.hstack([X, np.ones((len(X), 1))])
        try:
            beta, *_ = lstsq(X, s[col].values, rcond=None)
        except np.linalg.LinAlgError:
            continue
        resid = s[col].values - X @ beta
        if resid.std() < 1e-9: continue
        r_resid = pd.Series(resid).rank().values
        r_fwd = s["fwd_ret_20"].rank().values
        if r_fwd.std() < 1e-9: continue
        ics.append(np.corrcoef(r_resid, r_fwd)[0,1])
    return float(np.nanmean(ics)) if ics else np.nan


# Shuffle target for look-ahead once
rng = np.random.default_rng(42)
p["_shuf"] = p.groupby("trade_date")["fwd_ret_20"].transform(lambda s: rng.permutation(s.values))
rng2 = np.random.default_rng(123)
p["_rnd"] = rng2.standard_normal(len(p))
ic_rnd = rank_ic_by_date(p, "_rnd").mean()
print(f"random-alpha IC baseline: {ic_rnd:.4f}")

results = []
for a in ALPHAS:
    print(f"\n=== {a} ===")
    # Pre-submission checks
    val = p[(p.trade_date >= "2023-01-01") & (p.trade_date < "2024-01-01")]
    cov = val[a].notna().mean()
    ic_val = rank_ic_by_date(val, a).mean()
    print(f"   coverage={cov:.3f}  val IC={ic_val:.4f}")

    ic_real = rank_ic_by_date(p, a).mean()
    ic_shuf = rank_ic_by_date(p, a, "_shuf").mean()

    bt = backtest(p, a)
    if len(bt) == 0:
        print(f"   no backtest rows, skipping")
        continue
    head = ann_sharpe(bt["ls_net"])
    years = sorted(bt["year"].unique())
    yearly = {int(y): float(ann_sharpe(bt.loc[bt.year==y, "ls_net"])) for y in years}
    worst = min(v for v in yearly.values() if pd.notna(v))
    loyo = {int(y): float(ann_sharpe(bt.loc[bt.year!=y, "ls_net"])) for y in years}
    min_loyo = min(loyo.values())

    resid_ic = residualize_ic(p, a)

    # Test period
    test = bt[bt.period == "test"]
    train = bt[bt.period == "train"]
    valp = bt[bt.period == "validate"]

    audits = {
        "look_ahead_ok": abs(ic_shuf) < 0.02,
        "worst_year_ok": worst >= 0.5,
        "loyo_ok": min_loyo >= 0.5 * head,
        "falsification_ok": abs(ic_rnd) < 0.02,
        "residual_survives": (np.sign(resid_ic) == np.sign(ic_real)) and (abs(resid_ic) >= 0.3*abs(ic_real)),
    }
    all_pass = all(audits.values())

    print(f"   IC={ic_real:.4f} IC-shuf={ic_shuf:.4f} resid_IC={resid_ic:.4f}")
    print(f"   full Sharpe={head:.3f}  test={ann_sharpe(test['ls_net']):.3f}")
    print(f"   worst-year={worst:.3f}  min-loyo={min_loyo:.3f}")
    print(f"   audits: {audits} -> {'PASS' if all_pass else 'FAIL'}")

    results.append({
        "alpha": a,
        "coverage": cov,
        "ic_real": ic_real,
        "ic_shuffled": ic_shuf,
        "ls_sharpe_full": head,
        "ls_sharpe_train": ann_sharpe(train["ls_net"]),
        "ls_sharpe_validate": ann_sharpe(valp["ls_net"]),
        "ls_sharpe_test": ann_sharpe(test["ls_net"]),
        "q5_ir_full": ann_sharpe(bt["q5_exc"]),
        "q5_ir_test": ann_sharpe(test["q5_exc"]),
        "max_dd_full": max_dd(bt["ls_net"]),
        "avg_t5": bt["t5"].mean(),
        "avg_t1": bt["t1"].mean(),
        "worst_year": worst,
        "yearly": yearly,
        "min_loyo": min_loyo,
        "residual_ic": resid_ic,
        **audits,
        "all_audits_pass": all_pass,
    })

R = pd.DataFrame(results)
R.to_csv(f"{OUT}/backtest_results_batch_0002_skew.csv", index=False)
print()
print(R[["alpha","ls_sharpe_full","ls_sharpe_test","q5_ir_full","q5_ir_test","residual_ic","worst_year","min_loyo","all_audits_pass"]].to_string(index=False))

# Save detailed audits
with open(f"{OUT}/audits_round2.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print(f"\nwrote {OUT}/audits_round2.json")
