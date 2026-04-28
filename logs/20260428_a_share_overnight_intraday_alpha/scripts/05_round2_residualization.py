"""
Round 2: residualization screen.

For each PROMOTE-candidate (alpha_01 .. alpha_04), residualize against four
control stacks and re-backtest LS Q5-Q1 monthly. The standard rejects
factors that are vehicles for classic exposures (resid Sharpe < 50% of raw).

Stacks:
  full     : log_mv + sigma_20 + ret_5 + ret_20 + turnover_20
  vol_only : sigma_20
  rev_only : ret_5 + ret_20
  vol_rev  : sigma_20 + ret_5 + ret_20

Reads:  outputs/panel_alphas.parquet, outputs/ls_summary_batch_0001.csv
Writes: outputs/round2_residualization_screen.csv
"""
from __future__ import annotations
import time
from pathlib import Path
import numpy as np
import pandas as pd

SESSION = Path("/home/user/Factor_Zoo/logs/20260428_a_share_overnight_intraday_alpha")
OUT = SESSION / "outputs"
ALPHAS = ["alpha_01", "alpha_02", "alpha_03", "alpha_04"]
REB_DAYS = 20
ann = np.sqrt(252 / REB_DAYS)

t0 = time.time()
ap = pd.read_parquet(OUT / "panel_alphas.parquet")
ap["trade_date"] = ap["trade_date"].astype(str)
ls_sum = pd.read_csv(OUT / "ls_summary_batch_0001.csv").set_index("alpha")

stacks = {
    "full":     ["log_mv", "sigma_20", "ret_5", "ret_20", "turnover_20"],
    "vol_only": ["sigma_20"],
    "rev_only": ["ret_5", "ret_20"],
    "vol_rev":  ["sigma_20", "ret_5", "ret_20"],
}


def cs_zscore(s):
    mu, sd = s.mean(), s.std()
    return (s - mu) / sd if sd and not np.isnan(sd) else s * 0.0


for c in {x for s in stacks.values() for x in s}:
    ap[c + "_z"] = ap.groupby("trade_date")[c].transform(cs_zscore)

rows = []
for a in ALPHAS:
    raw_sh = float(ls_sum.loc[a, "ls_gross_sharpe"])
    for stack_name, ctrls in stacks.items():
        ctrl_z = [c + "_z" for c in ctrls]
        cols = ["trade_date", "ts_code", a, "fwd_ret_20"] + ctrl_z
        base = ap[cols].dropna(subset=[a] + ctrl_z).copy()
        base[f"{a}_resid"] = np.nan
        for d, g in base.groupby("trade_date", sort=False):
            if len(g) < 50:
                continue
            y = g[a].values
            X = np.column_stack([np.ones(len(g))] + [g[c].values for c in ctrl_z])
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
            base.loc[g.index, f"{a}_resid"] = y - X @ beta
        base[f"{a}_resid"] = base.groupby("trade_date")[f"{a}_resid"].transform(cs_zscore)

        dates = sorted(base["trade_date"].unique())
        rebs = dates[::REB_DAYS]
        rs = []
        for d in rebs:
            sub = base[base["trade_date"] == d].dropna(subset=[f"{a}_resid", "fwd_ret_20"])
            if len(sub) < 200:
                continue
            sub = sub.sort_values(f"{a}_resid")
            q = len(sub) // 5
            ls = sub.iloc[-q:]["fwd_ret_20"].mean() - sub.iloc[:q]["fwd_ret_20"].mean()
            rs.append(ls)
        if len(rs) < 5:
            continue
        rs = np.array(rs)
        sh = rs.mean() / rs.std() * ann if rs.std() > 0 else np.nan
        pct = 100.0 * sh / raw_sh if raw_sh else np.nan
        rows.append({"alpha": a, "stack": stack_name, "raw_gross_sh": raw_sh,
                     "resid_gross_sh": float(sh),
                     "pct_retained": float(pct),
                     "pass_50": bool(pct >= 50.0)})
        print(f"  {a} / {stack_name}: raw={raw_sh:.3f}  resid={sh:.3f}  pct={pct:.1f}%  pass={pct>=50}",
              flush=True)

df = pd.DataFrame(rows)
df.to_csv(OUT / "round2_residualization_screen.csv", index=False)
# pivot for readability
piv = df.pivot(index="alpha", columns="stack", values="pct_retained").round(1)
print("\n=== Round 2 — % of raw Sharpe retained ===")
print(piv.to_string())
print(f"\nDONE  elapsed={time.time()-t0:.1f}s")
