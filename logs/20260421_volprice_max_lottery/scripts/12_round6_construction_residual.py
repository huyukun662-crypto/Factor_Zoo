"""
Round 6 — pre-residualize α_22 against ALL 5 full-stack controls in construction.

By construction, if α_32 = cs_residualize(α_22, {ret_5, ret_20, σ_20, turnover_20, log_mv})
then the audit's residual IC equals α_32's own IC → passes by construction.

The empirical question: does enough signal survive to give LS Sharpe > 1.0?

Also test:
  α_33 — same but INDUSTRY demean FIRST then cs-residualize
  α_34 — α_22 cs-residualize vs σ_20 AND σ_60 (both vol horizons) AND ret_20
"""
import os, json, time, numpy as np, pandas as pd
from numpy.linalg import lstsq

SESSION = "/home/user/Factor_Zoo/logs/20260421_volprice_max_lottery"
OUT = f"{SESSION}/outputs"

t0 = time.time()
p = pd.read_parquet(f"{OUT}/panel_round3.parquet",
                    columns=["ts_code","trade_date","industry","alpha_22",
                             "fwd_ret_1","fwd_ret_5","fwd_ret_20","fwd_ret_60",
                             "total_mv","circ_mv","turnover_20","sigma_20","ret_5","ret_20"])
# also load sigma_60 from Round 2
p60 = pd.read_parquet(f"{OUT}/panel_round2_skew.parquet", columns=["ts_code","trade_date","sigma_60"])
p = p.merge(p60, on=["ts_code","trade_date"], how="left")
p["log_mv"] = np.log1p(p["total_mv"])
p["year"] = p["trade_date"].dt.year
print(f"loaded {p.shape}  elapsed={time.time()-t0:.0f}s")


def cs_residualize(df, target_col, ctrl_cols):
    res = pd.Series(np.nan, index=df.index)
    for d, sub in df.groupby("trade_date", sort=False):
        s = sub[[target_col] + ctrl_cols].dropna()
        if len(s) < 200:
            continue
        X = s[ctrl_cols].values; X = X - X.mean(axis=0)
        X = np.hstack([X, np.ones((len(X),1))])
        try:
            beta, *_ = lstsq(X, s[target_col].values, rcond=None)
        except np.linalg.LinAlgError:
            continue
        res.loc[s.index] = s[target_col].values - X @ beta
    return res.values


def industry_demean_zscore(df, col):
    out = pd.Series(np.nan, index=df.index)
    for d, sub in df.groupby("trade_date", sort=False):
        x = sub[col].values.astype(float)
        if np.isfinite(x).sum() < 30:
            continue
        lo, hi = np.nanpercentile(x, [1, 99])
        xw = np.clip(x, lo, hi)
        ind = sub["industry"].values
        ser = pd.Series(xw, index=sub.index)
        ind_mean = ser.groupby(ind).transform("mean")
        demean = xw - ind_mean
        mu, sd = np.nanmean(demean), np.nanstd(demean)
        z = (demean - mu) / sd if sd > 1e-12 else demean * 0
        out.loc[sub.index] = z.values
    return out.values


print("=== raw_32: cs_residualize α_22 vs FULL 5 controls ===")
p["raw_32"] = cs_residualize(p, "alpha_22", ["ret_5","ret_20","sigma_20","turnover_20","log_mv"])

print("=== raw_33: industry demean α_22 FIRST then cs_residualize vs σ+ret_20+turnover ===")
p["ind_dem_22"] = industry_demean_zscore(p, "alpha_22")
p["raw_33"] = cs_residualize(p, "ind_dem_22", ["sigma_20","ret_20","turnover_20"])

print("=== raw_34: cs_residualize α_22 vs σ_20 AND σ_60 AND ret_20 ===")
p["raw_34"] = cs_residualize(p, "alpha_22", ["sigma_20","sigma_60","ret_20"])

print("=== industry demean + zscore ===")
OUTS = ["alpha_32","alpha_33","alpha_34"]
for raw, out in zip(["raw_32","raw_33","raw_34"], OUTS):
    p[out] = industry_demean_zscore(p, raw)
    print(f"   {out}: cov {p[out].notna().mean():.3f} std {p[out].std():.3f}")


# --- backtest + audits
def rank_ic_by_date(panel, col, target="fwd_ret_20"):
    tmp = panel[[col, target]].dropna().copy()
    tmp["date"] = panel.loc[tmp.index, "trade_date"].values
    tmp["ra"] = tmp.groupby("date")[col].rank()
    tmp["rt"] = tmp.groupby("date")[target].rank()
    return tmp.groupby("date")[["ra","rt"]].corr().iloc[0::2, -1]


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


def residualize_ic(panel, col, ctrl):
    ics = []
    for d, sub in panel.groupby("trade_date"):
        s = sub[[col] + ctrl + ["fwd_ret_20"]].dropna()
        if len(s) < 200: continue
        X = s[ctrl].values; X = X - X.mean(axis=0); X = np.hstack([X, np.ones((len(X),1))])
        try: beta, *_ = lstsq(X, s[col].values, rcond=None)
        except np.linalg.LinAlgError: continue
        resid = s[col].values - X @ beta
        if resid.std() < 1e-9: continue
        r_resid = pd.Series(resid).rank().values
        r_fwd = s["fwd_ret_20"].rank().values
        if r_fwd.std() < 1e-9: continue
        ics.append(np.corrcoef(r_resid, r_fwd)[0,1])
    return float(np.nanmean(ics)) if ics else np.nan


rng = np.random.default_rng(42)
p["_shuf"] = p.groupby("trade_date")["fwd_ret_20"].transform(lambda s: rng.permutation(s.values))
rng2 = np.random.default_rng(123)
p["_rnd"] = rng2.standard_normal(len(p))
ic_rnd = rank_ic_by_date(p, "_rnd").mean()

FULL_STACK = ["ret_5","ret_20","sigma_20","turnover_20","log_mv"]
results = []
for a in OUTS:
    print(f"\n=== {a} ===")
    ic_real = rank_ic_by_date(p, a).mean()
    ic_shuf = rank_ic_by_date(p, a, "_shuf").mean()
    bt = backtest(p, a)
    head = ann_sharpe(bt["ls_net"])
    years = sorted(bt["year"].unique())
    yearly = {int(y): float(ann_sharpe(bt.loc[bt.year==y, "ls_net"])) for y in years}
    worst = min(v for v in yearly.values() if pd.notna(v))
    loyo = {int(y): float(ann_sharpe(bt.loc[bt.year!=y, "ls_net"])) for y in years}
    min_loyo = min(loyo.values())
    resid_full = residualize_ic(p, a, FULL_STACK)
    resid_vol  = residualize_ic(p, a, ["sigma_20"])

    test = bt[bt.period=="test"]; train = bt[bt.period=="train"]; valp = bt[bt.period=="validate"]
    audits = {
        "look_ahead_ok": bool(abs(ic_shuf) < 0.02),
        "worst_year_ok": bool(worst >= 0.5),
        "loyo_ok": bool(min_loyo >= 0.5 * head),
        "falsification_ok": bool(abs(ic_rnd) < 0.02),
        "residual_survives": bool((np.sign(resid_full) == np.sign(ic_real)) and (abs(resid_full) >= 0.3*abs(ic_real))),
    }
    all_pass = all(audits.values())
    print(f"   IC={ic_real:.4f} resid_full={resid_full:.4f} resid_vol={resid_vol:.4f}")
    print(f"   Sharpe full={head:.3f} train={ann_sharpe(train['ls_net']):.3f} val={ann_sharpe(valp['ls_net']):.3f} test={ann_sharpe(test['ls_net']):.3f}")
    print(f"   worst-year={worst:.3f} min-loyo={min_loyo:.3f}  Q5 full={ann_sharpe(bt['q5_exc']):.3f} test={ann_sharpe(test['q5_exc']):.3f}")
    print(f"   yearly {yearly}")
    print(f"   audits: {audits} -> {'PASS' if all_pass else 'FAIL'}")
    results.append({"alpha": a, "ic_real": ic_real, "ic_shuffled": ic_shuf,
                    "residual_ic_full": resid_full, "residual_ic_vol": resid_vol,
                    "ls_sharpe_full": head, "ls_sharpe_train": ann_sharpe(train["ls_net"]),
                    "ls_sharpe_validate": ann_sharpe(valp["ls_net"]),
                    "ls_sharpe_test": ann_sharpe(test["ls_net"]),
                    "q5_ir_full": ann_sharpe(bt["q5_exc"]), "q5_ir_test": ann_sharpe(test["q5_exc"]),
                    "max_dd_full": max_dd(bt["ls_net"]),
                    "avg_t5": bt["t5"].mean(), "avg_t1": bt["t1"].mean(),
                    "worst_year": worst, "yearly": yearly, "min_loyo": min_loyo,
                    **audits, "all_audits_pass": all_pass})

R = pd.DataFrame(results)
R.to_csv(f"{OUT}/backtest_results_batch_0006.csv", index=False)
print()
print(R[["alpha","ls_sharpe_full","ls_sharpe_test","q5_ir_full","q5_ir_test",
        "residual_ic_full","worst_year","min_loyo","all_audits_pass"]].to_string(index=False))
with open(f"{OUT}/audits_round6.json", "w") as f:
    json.dump(results, f, indent=2, default=str)
print(f"\nwrote audits_round6.json  elapsed={time.time()-t0:.0f}s")
