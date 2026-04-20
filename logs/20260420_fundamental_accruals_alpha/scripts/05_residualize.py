"""
Round 2A: Residualize alpha_03 (industry-neutral Sloan CFS) against classic factors.

Classic factor controls computed from our own panel:
- log_mv       : size
- mom_20       : 20-day price momentum (return over [-21, -1])
- rev_5        : 5-day short-term reversal (return over [-6, -1])
- turnover_z   : 20-day z-score of amount / total_mv (liquidity)
- vol_20       : 20-day realized volatility (log-return std)

Method:
For each trade_date, run an OLS cross-sectional regression:
    alpha_03 = a + b1*log_mv + b2*mom_20 + b3*rev_5 + b4*turnover_z + b5*vol_20 + eps
The residual (eps) is the "orthogonalized alpha_03". Report IC/LS on it.
Headline gate: residual LS Sharpe >= 50% of original (1.38 net -> >= 0.69).
"""
import os, sys, time
import numpy as np
import pandas as pd

CACHE = "/home/user/Factor_Zoo/.cache"
SESSION = "/home/user/Factor_Zoo/logs/20260420_fundamental_accruals_alpha"
OUT = f"{SESSION}/outputs"


def log(s):
    print(f"[{time.strftime('%H:%M:%S')}] {s}", flush=True)


# ---- load panel + daily for building classic factors ----
log("loading panel + daily")
panel = pd.read_parquet(f"{CACHE}/panel.parquet")
daily = pd.read_parquet(f"{CACHE}/daily.parquet")
adj = pd.read_parquet(f"{CACHE}/adj_factor.parquet")
db = pd.read_parquet(f"{CACHE}/daily_basic.parquet")

# merge adj_close and mv
daily = daily.merge(adj, on=["ts_code", "trade_date"])
daily = daily.merge(db, on=["ts_code", "trade_date"], how="left")
daily["close_adj"] = daily["close"] * daily["adj_factor"]
daily = daily.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)

# ---- classic factors ----
log("building classic factors: mom_20, rev_5, turnover_z, vol_20, log_mv")
g = daily.groupby("ts_code")
daily["log_ret"] = g["close_adj"].transform(lambda s: np.log(s).diff())
daily["mom_20"] = g["close_adj"].transform(lambda s: s.shift(1) / s.shift(21) - 1)
daily["rev_5"] = g["close_adj"].transform(lambda s: s.shift(1) / s.shift(6) - 1)
daily["vol_20"] = g["log_ret"].transform(lambda s: s.rolling(20).std())
daily["turnover"] = daily["amount"] / daily["total_mv"].clip(lower=1)
daily["turnover_z"] = g["turnover"].transform(
    lambda s: (s.rolling(20).mean()) / (s.rolling(20).std() + 1e-9)
)
daily["log_mv"] = np.log(daily["total_mv"].clip(lower=1))

# ---- merge to panel ----
log("merging classics into panel")
panel = panel.merge(
    daily[["ts_code", "trade_date", "log_mv", "mom_20", "rev_5", "turnover_z", "vol_20"]],
    on=["ts_code", "trade_date"], how="left"
)

CONTROLS = ["log_mv", "mom_20", "rev_5", "turnover_z", "vol_20"]
panel = panel.dropna(subset=["alpha_03"] + CONTROLS + ["fwd_ret_20"]).copy()
log(f"rows after dropping NaN controls: {len(panel):,}")


# ---- cross-sectional residualization per trade_date ----
log("cross-sectional OLS residualization per trade_date")
def residualize_group(df):
    X = df[CONTROLS].values
    y = df["alpha_03"].values
    X = np.column_stack([np.ones(len(X)), X])
    try:
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ beta
    except Exception:
        resid = y
    df["alpha_03_resid"] = resid
    return df

out = []
for d, grp in panel.groupby("trade_date"):
    out.append(residualize_group(grp))
panel = pd.concat(out, ignore_index=True)
log("residualization complete")


# ---- IC comparison: raw alpha_03 vs residualized ----
def ic_summary(df, alpha_col, ret_col):
    ic = df.dropna(subset=[alpha_col, ret_col]).groupby("trade_date").apply(
        lambda x: x[alpha_col].corr(x[ret_col], method="spearman"),
        include_groups=False,
    ).dropna()
    if len(ic) < 10:
        return dict(ic_mean=np.nan, icir=np.nan, tstat=np.nan, n=len(ic))
    return dict(
        ic_mean=float(ic.mean()),
        icir=float(ic.mean() / ic.std()),
        tstat=float(ic.mean() / ic.std() * np.sqrt(len(ic))),
        n=int(len(ic)),
    )


log("IC on raw vs residualized alpha_03")
for h in (5, 20, 60):
    r_raw = ic_summary(panel, "alpha_03", f"fwd_ret_{h}")
    r_res = ic_summary(panel, "alpha_03_resid", f"fwd_ret_{h}")
    log(f"  h={h:>2}  raw IC={r_raw['ic_mean']:.4f} ICIR={r_raw['icir']:.3f} | resid IC={r_res['ic_mean']:.4f} ICIR={r_res['icir']:.3f}  kept={r_res['ic_mean']/r_raw['ic_mean']*100:.0f}%")


# ---- LS portfolio on residualized alpha_03 ----
def monthly_ls(df, alpha_col, cost_bps=10.0):
    dfa = df.dropna(subset=[alpha_col, "fwd_ret_20"]).copy()
    all_dates = np.sort(dfa["trade_date"].unique())
    reb_dates = all_dates[::20]
    dfa = dfa[dfa["trade_date"].isin(reb_dates)].copy()
    dfa["q"] = dfa.groupby("trade_date")[alpha_col].transform(
        lambda s: pd.qcut(s.rank(method="first"), 5, labels=False, duplicates="drop")
    )
    dfa = dfa.dropna(subset=["q"])
    port = dfa.groupby(["trade_date", "q"])["fwd_ret_20"].mean().unstack("q")
    port.columns = [f"Q{int(c)+1}" for c in sorted(port.columns)]
    port["LS"] = port["Q5"] - port["Q1"]
    port["LS_net"] = port["LS"] - 2 * cost_bps / 1e4
    return port


def sharpe_annual(r):
    return r.mean() / r.std() * np.sqrt(12) if r.std() > 0 else np.nan


log("LS on raw vs residualized alpha_03")
port_raw = monthly_ls(panel, "alpha_03")
port_res = monthly_ls(panel, "alpha_03_resid")


def summary(port):
    port = port.copy()
    port["year"] = pd.to_datetime(port.index).year
    s_gross = sharpe_annual(port["LS"])
    s_net = sharpe_annual(port["LS_net"])
    annual = port.groupby("year")["LS"].agg(sharpe_annual).dropna()
    worst = annual.min() if len(annual) else np.nan
    cumret = (1 + port["LS"]).cumprod()
    dd = (cumret / cumret.cummax() - 1).min()
    return dict(
        ls_sharpe_gross=float(s_gross),
        ls_sharpe_net_10bps=float(s_net),
        worst_year_sharpe=float(worst),
        max_dd=float(dd),
        n_rebalances=int(len(port)),
        annual=annual.round(3).to_dict(),
    )


s_raw = summary(port_raw)
s_res = summary(port_res)

log(f"raw    LS: Sharpe_net={s_raw['ls_sharpe_net_10bps']:.3f} worst={s_raw['worst_year_sharpe']:.3f} DD={s_raw['max_dd']:.3f}")
log(f"resid  LS: Sharpe_net={s_res['ls_sharpe_net_10bps']:.3f} worst={s_res['worst_year_sharpe']:.3f} DD={s_res['max_dd']:.3f}")
kept_pct = s_res['ls_sharpe_net_10bps'] / s_raw['ls_sharpe_net_10bps'] * 100
log(f"kept = {kept_pct:.1f}% of headline net Sharpe")
log(f"gate (>= 50%): {'PASS' if kept_pct >= 50 else 'FAIL'}")


# ---- save ----
import json
out_data = dict(
    controls=CONTROLS,
    raw=s_raw,
    residualized=s_res,
    pct_headline_kept=float(kept_pct),
    gate_50pct=bool(kept_pct >= 50),
)
with open(f"{OUT}/audit_residualization.json", "w") as f:
    json.dump(out_data, f, indent=2, default=str)
log(f"wrote {OUT}/audit_residualization.json")


# ---- also save annual breakdown as csv for comparison ----
annual_raw = pd.DataFrame([{"year": y, "raw_sharpe": v} for y, v in s_raw["annual"].items()])
annual_res = pd.DataFrame([{"year": y, "resid_sharpe": v} for y, v in s_res["annual"].items()])
ann = annual_raw.merge(annual_res, on="year")
ann["delta"] = ann["resid_sharpe"] - ann["raw_sharpe"]
ann.to_csv(f"{OUT}/audit_residualization_annual.csv", index=False)
log(ann.to_string(index=False))
