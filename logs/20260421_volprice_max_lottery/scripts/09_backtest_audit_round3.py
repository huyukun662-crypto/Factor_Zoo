"""
Round 3 — combined backtest + audits for α_17..α_24 (σ-decoupled iterations).
"""
import os, json, numpy as np, pandas as pd
from numpy.linalg import lstsq

SESSION = "/home/user/Factor_Zoo/logs/20260421_volprice_max_lottery"
PANEL = f"{SESSION}/outputs/panel_round3.parquet"
OUT = f"{SESSION}/outputs"

p = pd.read_parquet(PANEL)
p["year"] = p["trade_date"].dt.year
p["log_mv"] = np.log1p(p["total_mv"])

ALPHAS = [f"alpha_{i}" for i in [17,18,19,20,21,22,23,24]]


def rank_ic_by_date(panel, col, target="fwd_ret_20"):
    tmp = panel[[col, target]].dropna().copy()
    tmp["date"] = panel.loc[tmp.index, "trade_date"].values
    tmp["ra"] = tmp.groupby("date")[col].rank()
    tmp["rt"] = tmp.groupby("date")[target].rank()
    out = tmp.groupby("date")[["ra","rt"]].corr().iloc[0::2, -1]
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
        cost = (t5+t1) * 5e-4
        rows.append({"date": rd, "ls_gross": ls_gross, "ls_net": ls_gross-cost,
                     "q5_exc": qr.get("Q5", np.nan) - mkt - t5*5e-4,
                     "q1_exc": qr.get("Q1", np.nan) - mkt - t1*5e-4,
                     "t5": t5, "t1": t1,
                     "period": period_mask(rd), "year": pd.Timestamp(rd).year})
    return pd.DataFrame(rows)


def residualize_ic(panel, col, ctrl_cols=["ret_5","ret_20","sigma_20","turnover_20","log_mv"]):
    ics = []
    for d, sub in panel.groupby("trade_date"):
        s = sub[[col] + ctrl_cols + ["fwd_ret_20"]].dropna()
        if len(s) < 200: continue
        X = s[ctrl_cols].values
        X = X - X.mean(axis=0)
        X = np.hstack([X, np.ones((len(X),1))])
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


def residualize_ic_vol_only(panel, col):
    return residualize_ic(panel, col, ctrl_cols=["sigma_20"])


def residualize_ic_volrev(panel, col):
    return residualize_ic(panel, col, ctrl_cols=["sigma_20","ret_20"])


# Shuffle + random baselines
rng = np.random.default_rng(42)
p["_shuf"] = p.groupby("trade_date")["fwd_ret_20"].transform(lambda s: rng.permutation(s.values))
rng2 = np.random.default_rng(123)
p["_rnd"] = rng2.standard_normal(len(p))
ic_rnd = rank_ic_by_date(p, "_rnd").mean()
print(f"random-alpha IC baseline: {ic_rnd:.4f}")

results = []
for a in ALPHAS:
    print(f"\n=== {a} ===")
    val = p[(p.trade_date >= "2023-01-01") & (p.trade_date < "2024-01-01")]
    cov = val[a].notna().mean()
    ic_real = rank_ic_by_date(p, a).mean()
    ic_shuf = rank_ic_by_date(p, a, "_shuf").mean()

    bt = backtest(p, a)
    head = ann_sharpe(bt["ls_net"])
    years = sorted(bt["year"].unique())
    yearly = {int(y): float(ann_sharpe(bt.loc[bt.year==y, "ls_net"])) for y in years}
    worst = min(v for v in yearly.values() if pd.notna(v))
    loyo = {int(y): float(ann_sharpe(bt.loc[bt.year!=y, "ls_net"])) for y in years}
    min_loyo = min(loyo.values())

    resid_full = residualize_ic(p, a)
    resid_vol  = residualize_ic_vol_only(p, a)
    resid_vr   = residualize_ic_volrev(p, a)

    test = bt[bt.period == "test"]
    train = bt[bt.period == "train"]
    valp  = bt[bt.period == "validate"]

    audits = {
        "look_ahead_ok": bool(abs(ic_shuf) < 0.02),
        "worst_year_ok": bool(worst >= 0.5),
        "loyo_ok": bool(min_loyo >= 0.5 * head),
        "falsification_ok": bool(abs(ic_rnd) < 0.02),
        "residual_survives": bool((np.sign(resid_full) == np.sign(ic_real)) and (abs(resid_full) >= 0.3*abs(ic_real))),
    }
    all_pass = all(audits.values())

    print(f"   cov={cov:.3f}  IC={ic_real:.4f}  IC-shuf={ic_shuf:.4f}")
    print(f"   residual_IC  full={resid_full:.4f}  vs_vol={resid_vol:.4f}  vs_volrev={resid_vr:.4f}")
    print(f"   Sharpe  full={head:.3f}  train={ann_sharpe(train['ls_net']):.3f}  val={ann_sharpe(valp['ls_net']):.3f}  test={ann_sharpe(test['ls_net']):.3f}")
    print(f"   worst-year={worst:.3f}  min-loyo={min_loyo:.3f}")
    print(f"   audits: {audits} -> {'PASS' if all_pass else 'FAIL'}")

    results.append({
        "alpha": a, "coverage": cov,
        "ic_real": ic_real, "ic_shuffled": ic_shuf,
        "residual_ic_full": resid_full,
        "residual_ic_vol": resid_vol,
        "residual_ic_volrev": resid_vr,
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
        **audits,
        "all_audits_pass": all_pass,
    })

R = pd.DataFrame(results)
R.to_csv(f"{OUT}/backtest_results_batch_0003.csv", index=False)
print()
print(R[["alpha","ls_sharpe_full","ls_sharpe_test","q5_ir_full","q5_ir_test","residual_ic_full","residual_ic_vol","worst_year","min_loyo","all_audits_pass"]].to_string(index=False))

with open(f"{OUT}/audits_round3.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print(f"\nwrote {OUT}/audits_round3.json")
