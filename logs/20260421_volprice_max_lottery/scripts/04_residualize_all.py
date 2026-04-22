"""
Round-2 residualization screen.

For each of the 8 alphas, build a residualized version by regressing out
{ret_5, ret_20, sigma_20, turnover_20, log_mv} per date and store `resid_NN`
as a new column. Compute IC and rank on full/test.

Also test lighter residualization stacks:
  - vs {sigma_20} only  (is MAX = vol?)
  - vs {ret_20} only    (is MAX = reversal?)
  - vs {sigma_20, ret_20} (both)
"""
import os, numpy as np, pandas as pd, json
from numpy.linalg import lstsq

SESSION = "/home/user/Factor_Zoo/logs/20260421_volprice_max_lottery"
PANEL = f"{SESSION}/outputs/panel_volprice.parquet"
OUT = f"{SESSION}/outputs"

p = pd.read_parquet(PANEL)
p["log_mv"] = np.log1p(p["total_mv"])


def cs_demean_and_zscore(df, col):
    g = df.groupby("trade_date")[col]
    return ((df[col] - g.transform("mean")) / g.transform("std")).fillna(0)


def residualize_per_date(panel, alpha_col, ctrl_cols, out_col):
    panel[out_col] = np.nan
    for d, sub in panel.groupby("trade_date"):
        s = sub[[alpha_col] + ctrl_cols].dropna()
        if len(s) < 200:
            continue
        X = s[ctrl_cols].values
        X = X - X.mean(axis=0)
        X = np.hstack([X, np.ones((len(X), 1))])
        y = s[alpha_col].values
        try:
            beta, *_ = lstsq(X, y, rcond=None)
        except np.linalg.LinAlgError:
            continue
        panel.loc[s.index, out_col] = y - X @ beta
    # cross-section z-score
    g = panel.groupby("trade_date")[out_col]
    mu = g.transform("mean"); sd = g.transform("std")
    panel[out_col] = ((panel[out_col] - mu) / sd).where(sd > 1e-9, 0)
    return panel


def rank_ic_by_date(panel, alpha_col, target="fwd_ret_20"):
    tmp = panel[[alpha_col, target]].dropna().copy()
    tmp["date"] = panel.loc[tmp.index, "trade_date"].values
    tmp["ra"] = tmp.groupby("date")[alpha_col].rank()
    tmp["rt"] = tmp.groupby("date")[target].rank()
    out = tmp.groupby("date")[["ra", "rt"]].corr().iloc[0::2, -1]
    return out.values


ALPHAS = [f"alpha_{i:02d}" for i in range(1, 9)]
STACKS = {
    "full":   ["ret_5","ret_20","sigma_20","turnover_20","log_mv"],
    "vol":    ["sigma_20"],
    "rev":    ["ret_20"],
    "volrev": ["sigma_20","ret_20"],
}

rows = []
for a in ALPHAS:
    for stack_name, ctrl in STACKS.items():
        col = f"r_{a[-2:]}_{stack_name}"
        print(f"residualizing {a} / {stack_name} ...")
        residualize_per_date(p, a, ctrl, col)
        ic_full = rank_ic_by_date(p, col)
        ic_full_mean = np.nanmean(ic_full)
        ic_full_ir = ic_full_mean / np.nanstd(ic_full) * np.sqrt(252) if np.nanstd(ic_full) > 0 else np.nan
        # test subset
        test_mask = (p["trade_date"] >= "2024-01-01") & (p["trade_date"] <= "2025-04-18")
        pt = p.loc[test_mask]
        ic_test = rank_ic_by_date(pt, col)
        ic_test_mean = np.nanmean(ic_test)
        rows.append({
            "alpha": a, "stack": stack_name, "ic_full": ic_full_mean, "ic_ir_full": ic_full_ir,
            "ic_test": ic_test_mean
        })

r = pd.DataFrame(rows)
r.to_csv(f"{OUT}/residualization_screen.csv", index=False)
print()
print(r.pivot(index="alpha", columns="stack", values="ic_full").round(4))
print()
print("TEST window IC:")
print(r.pivot(index="alpha", columns="stack", values="ic_test").round(4))
# Persist the residualized alphas we care about
p.to_parquet(f"{OUT}/panel_round2.parquet", index=False)
print(f"\nwrote panel_round2.parquet with residualized alphas")
