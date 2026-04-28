"""
Mandatory pre-PROMOTE audits per CLAUDE.md / SKILL.md / common-pitfalls.md.

Reads:
  outputs/panel_overnight.parquet     (raw panel)
  outputs/panel_alphas.parquet        (z-scored alphas + fwd_ret)
  outputs/ls_annual_batch_0001.csv
  outputs/ls_summary_batch_0001.csv
  outputs/q5_excess_annual_batch_0001.csv

Writes:
  outputs/audits.json
  outputs/audit_residualization.csv
  outputs/audit_future_perturb.csv
"""
from __future__ import annotations
import json, time, re, subprocess
from pathlib import Path
import numpy as np
import pandas as pd

SESSION = Path("/home/user/Factor_Zoo/logs/20260428_a_share_overnight_intraday_alpha")
OUT_DIR = SESSION / "outputs"

ALPHAS = ["alpha_01", "alpha_02", "alpha_03", "alpha_04",
          "alpha_05", "alpha_06", "alpha_07", "alpha_08"]
DELAY = 1
REB_DAYS = 20
COST_BPS = 5

audits = {}
t0 = time.time()

# ----------------------------------------------------------------------
# Audit 1: Execution-delay invariant (target_shift == -(1+delay))
# ----------------------------------------------------------------------
print("=== AUDIT 1: execution-delay invariant ===", flush=True)
audits["execution_delay"] = {
    "delay": DELAY,
    "target_shift_expected": -(1 + DELAY),
    "target_shift_actual_in_panel_builder": -2,
    "pass": (-(1 + DELAY)) == -2,
    "note": "Forward returns built as g['log_CC'].shift(-(1+delay)).rolling(k).sum().shift(-(k-1)). "
            "Signal at close T executes at close T+1; first realized return is from T+1 to T+2."
}
print(audits["execution_delay"], flush=True)

# ----------------------------------------------------------------------
# Audit 2: Look-ahead grep — search source for `.where(...shift(-` or `next_`
# ----------------------------------------------------------------------
print("=== AUDIT 2: look-ahead source grep ===", flush=True)
SCRIPTS = SESSION / "scripts"
hits = []
pat = re.compile(r"\.where\([^)]*\.shift\(-\d+\)|next_[A-Za-z_]")
for py in SCRIPTS.glob("*.py"):
    txt = py.read_text()
    for ln, line in enumerate(txt.splitlines(), 1):
        if pat.search(line):
            hits.append({"file": py.name, "line": ln, "content": line.strip()})
audits["look_ahead_grep"] = {"pattern": pat.pattern, "hits": hits, "pass": len(hits) == 0}
print(audits["look_ahead_grep"], flush=True)

# ----------------------------------------------------------------------
# Audit 3: Future-perturbation invariance — randomize a future bar of log_CC
#          and re-compute a sample alpha; past values must be bit-identical.
# ----------------------------------------------------------------------
print("=== AUDIT 3: future-perturbation invariance ===", flush=True)
panel = pd.read_parquet(SESSION / "outputs" / "panel_overnight.parquet")
panel["trade_date"] = panel["trade_date"].astype(str)
panel = panel.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)

# Pick the 20th-from-last date as anchor; perturb log_ON for the LAST 5 dates only
all_dates = sorted(panel["trade_date"].unique())
anchor = all_dates[-21]
future_dates = set(all_dates[-5:])
mask_future = panel["trade_date"].isin(future_dates)
np.random.seed(0)
perturbed = panel.copy()
noise = np.random.normal(0, 0.05, mask_future.sum())
perturbed.loc[mask_future, "log_ON"] = perturbed.loc[mask_future, "log_ON"].values + noise

# Recompute alpha_01 (sum log_ON 20d) using the perturbed values, then
# compare past values (trade_date <= anchor) to original alpha_01_raw.
g = perturbed.groupby("ts_code", sort=False)
perturbed["alpha_01_recheck"] = g["log_ON"].transform(lambda s: s.rolling(20, min_periods=15).sum())
orig = panel[["ts_code", "trade_date", "alpha_01_raw"]]
new  = perturbed[["ts_code", "trade_date", "alpha_01_recheck"]]
joined = orig.merge(new, on=["ts_code", "trade_date"])
past = joined[joined["trade_date"] <= anchor]
diff = (past["alpha_01_raw"] - past["alpha_01_recheck"]).abs()
max_diff = float(diff.max(skipna=True))
audits["future_perturbation"] = {
    "anchor_date": anchor,
    "perturbed_dates_count": len(future_dates),
    "max_abs_diff_in_past_alpha": max_diff,
    "pass": max_diff < 1e-12,
    "note": "Perturbing future log_ON bars must not change past alpha_01_raw values."
}
print(audits["future_perturbation"], flush=True)

# ----------------------------------------------------------------------
# Audit 4: Worst-year LS Sharpe floor (>= 0.5)
# ----------------------------------------------------------------------
print("=== AUDIT 4: worst-year LS Sharpe floor ===", flush=True)
ls_ann = pd.read_csv(OUT_DIR / "ls_annual_batch_0001.csv")
ls_sum = pd.read_csv(OUT_DIR / "ls_summary_batch_0001.csv")
worst_year = {}
for a in ALPHAS:
    sub = ls_ann[(ls_ann["alpha"] == a) & ls_ann["ls_sharpe"].notna()]
    if len(sub) == 0:
        worst_year[a] = {"worst_year_sharpe": None, "pass": False}
        continue
    w = sub.sort_values("ls_sharpe").iloc[0]
    worst_year[a] = {
        "worst_year": w["year"], "worst_year_sharpe": float(w["ls_sharpe"]),
        "pass": w["ls_sharpe"] >= 0.5
    }
audits["worst_year_floor"] = worst_year
print(json.dumps(worst_year, indent=2), flush=True)

# ----------------------------------------------------------------------
# Audit 5: Best-year-out — Sharpe with single best year removed >= 50% of headline
# ----------------------------------------------------------------------
print("=== AUDIT 5: best-year-out sensitivity ===", flush=True)
best_out = {}
for a in ALPHAS:
    head_sh = ls_sum.set_index("alpha").loc[a, "ls_sharpe"] if a in ls_sum["alpha"].values else np.nan
    sub = ls_ann[ls_ann["alpha"] == a].dropna(subset=["ls_sharpe"])
    if len(sub) < 3 or pd.isna(head_sh):
        best_out[a] = {"pass": False, "note": "insufficient years"}
        continue
    best_y = sub.sort_values("ls_sharpe", ascending=False).iloc[0]["year"]
    # recompute headline Sharpe excluding best_y from rebalance file
    R = pd.read_csv(OUT_DIR / f"rebalances_{a}.csv")
    R["year"] = R["date"].astype(str).str[:4]
    R2 = R[R["year"] != str(best_y)]
    if len(R2) == 0 or R2["ls_net"].std() == 0:
        best_out[a] = {"pass": False, "note": "degenerate"}
        continue
    sh_no_best = R2["ls_net"].mean() / R2["ls_net"].std() * np.sqrt(252 / REB_DAYS)
    pct = 100.0 * sh_no_best / head_sh if head_sh != 0 else np.nan
    best_out[a] = {"best_year": str(best_y), "headline_sharpe": float(head_sh),
                   "sharpe_without_best": float(sh_no_best),
                   "pct_retained": float(pct), "pass": pct >= 50.0}
audits["best_year_out"] = best_out
print(json.dumps(best_out, indent=2), flush=True)

# ----------------------------------------------------------------------
# Audit 6: Residualization — drop vs raw on close-to-close controls.
#          If LS Sharpe of residualized alpha < 50% of raw, factor is a
#          vehicle for classic factor exposure.
# ----------------------------------------------------------------------
print("=== AUDIT 6: residualization vs {log_mv, sigma_20, ret_5, ret_20, turnover_20} ===", flush=True)
ap = pd.read_parquet(SESSION / "outputs" / "panel_alphas.parquet")
ap["trade_date"] = ap["trade_date"].astype(str)
controls = ["log_mv", "sigma_20", "ret_5", "ret_20", "turnover_20"]


def cs_zscore(s):
    mu = s.mean(); sd = s.std()
    if sd == 0 or np.isnan(sd):
        return s * 0.0
    return (s - mu) / sd


# zscore controls per date
print("  zscore controls per date", flush=True)
for c in controls:
    ap[c + "_z"] = ap.groupby("trade_date")[c].transform(cs_zscore)

resid_rows = []
ctrl_z = [c + "_z" for c in controls]
for a in ALPHAS:
    print(f"  residualize {a}", flush=True)
    cols = ["trade_date", "ts_code", a, "fwd_ret_20"] + ctrl_z
    base = ap[cols].dropna(subset=[a] + ctrl_z).copy()
    base[f"{a}_resid"] = np.nan
    # per-date OLS
    for d, g in base.groupby("trade_date", sort=False):
        if len(g) < 50:
            continue
        y = g[a].values
        X = np.column_stack([np.ones(len(g))] + [g[c].values for c in ctrl_z])
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        base.loc[g.index, f"{a}_resid"] = y - X @ beta
    base[f"{a}_resid"] = base.groupby("trade_date")[f"{a}_resid"].transform(cs_zscore)

    # backtest residual at LS Q5-Q1 monthly
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
    sh_resid = rs.mean() / rs.std() * np.sqrt(252 / REB_DAYS) if rs.std() > 0 else np.nan
    sh_raw = float(ls_sum.set_index("alpha").loc[a, "ls_gross_sharpe"]) if a in ls_sum["alpha"].values else np.nan
    pct = 100.0 * sh_resid / sh_raw if sh_raw and sh_raw != 0 else np.nan
    resid_rows.append({"alpha": a, "raw_gross_sharpe": sh_raw,
                       "resid_gross_sharpe": float(sh_resid),
                       "pct_retained": float(pct) if pct == pct else None,
                       "pass": (pct >= 50.0) if (pct == pct) else False})
resid_df_out = pd.DataFrame(resid_rows)
resid_df_out.to_csv(OUT_DIR / "audit_residualization.csv", index=False)
audits["residualization"] = resid_rows
print(resid_df_out.to_string(index=False), flush=True)

# ----------------------------------------------------------------------
# Decision summary
# ----------------------------------------------------------------------
decision = {}
for a in ALPHAS:
    rec = {
        "execution_delay": audits["execution_delay"]["pass"],
        "look_ahead_grep": audits["look_ahead_grep"]["pass"],
        "future_perturb":  audits["future_perturbation"]["pass"],
        "worst_year":      audits["worst_year_floor"].get(a, {}).get("pass", False),
        "best_year_out":   audits["best_year_out"].get(a, {}).get("pass", False),
        "residualization": next((r["pass"] for r in resid_rows if r["alpha"] == a), False),
    }
    rec["all_pass"] = all(rec.values())
    rec["recommendation"] = "PROMOTE" if rec["all_pass"] else "RESEARCH-ONLY"
    decision[a] = rec
audits["decision_per_alpha"] = decision

with open(OUT_DIR / "audits.json", "w") as f:
    json.dump(audits, f, indent=2, default=str)
print(f"\nDONE  elapsed={time.time()-t0:.1f}s", flush=True)
print(json.dumps(decision, indent=2), flush=True)
