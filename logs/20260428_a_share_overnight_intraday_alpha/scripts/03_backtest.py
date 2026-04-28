"""
Backtest — IC table, LS Q5-Q1, Q5 long-only excess, monthly rebalance.

Reads:  outputs/panel_alphas.parquet
Writes:
  outputs/ic_table_batch_0001.csv
  outputs/ls_summary_batch_0001.csv
  outputs/ls_annual_batch_0001.csv
  outputs/q5_excess_summary_batch_0001.csv
  outputs/q5_excess_annual_batch_0001.csv
  outputs/rebalances_alpha_<id>.csv  (per-rebalance state for top alpha)
"""
from __future__ import annotations
import time
from pathlib import Path
import numpy as np
import pandas as pd

SESSION = Path("/home/user/Factor_Zoo/logs/20260428_a_share_overnight_intraday_alpha")
IN_     = SESSION / "outputs" / "panel_alphas.parquet"
OUT_DIR = SESSION / "outputs"
OUT_DIR.mkdir(exist_ok=True)

ALPHAS = ["alpha_01", "alpha_02", "alpha_03", "alpha_04",
          "alpha_05", "alpha_06", "alpha_07", "alpha_08"]

REB_DAYS_PRIMARY = 20
COST_BPS = 5         # per side
ANN_FACTOR_LS = np.sqrt(252.0 / REB_DAYS_PRIMARY)
DELAY = 1


t0 = time.time()
df = pd.read_parquet(IN_)
df["trade_date"] = df["trade_date"].astype(str)
df = df.sort_values(["trade_date", "ts_code"]).reset_index(drop=True)
print(f"loaded {df.shape}  dates={df['trade_date'].nunique()}", flush=True)

# IC table  --------------------------------------------------------
print("=== IC table ===", flush=True)
ic_rows = []
for a in ALPHAS:
    for k in [1, 5, 10, 20, 60]:
        sub = df[[a, f"fwd_ret_{k}"]].dropna()
        if len(sub) == 0:
            continue
        # rank-IC per date
        per_date = df[["trade_date", a, f"fwd_ret_{k}"]].dropna()
        ic_series = per_date.groupby("trade_date").apply(
            lambda g: g[a].rank().corr(g[f"fwd_ret_{k}"].rank())
        )
        ic_series = ic_series.dropna()
        ic_mean = ic_series.mean()
        ic_std  = ic_series.std()
        n       = len(ic_series)
        icir    = ic_mean / ic_std if ic_std > 0 else np.nan
        tstat   = icir * np.sqrt(n) if n > 0 else np.nan
        ic_rows.append({"alpha": a, "horizon": k, "ic_mean": ic_mean, "ic_std": ic_std,
                        "icir": icir, "n_dates": n, "t_stat": tstat})
ic_df = pd.DataFrame(ic_rows)
ic_df.to_csv(OUT_DIR / "ic_table_batch_0001.csv", index=False)
print(ic_df.to_string(index=False), flush=True)


# LS / Q5 backtest at monthly rebalance ----------------------------
print(f"=== LS + Q5 backtest (rebal={REB_DAYS_PRIMARY}d, cost={COST_BPS}bps/side, delay={DELAY}) ===",
      flush=True)

dates = sorted(df["trade_date"].unique())
reb_dates = dates[::REB_DAYS_PRIMARY]
print(f"  {len(reb_dates)} rebalance dates", flush=True)

# Pre-compute per-date dict for fast lookup
by_date = {d: g for d, g in df.groupby("trade_date", sort=False)}

ls_summary = {}
ls_annual_rows = []
q5_summary = {}
q5_annual_rows = []
rebalances_for_top = {}    # only saved for headline-best alpha after evaluation

for a in ALPHAS:
    print(f"  alpha {a} ...", flush=True)
    prev_q5 = None
    prev_q1 = None
    rebal_records = []
    for d in reb_dates:
        snap = by_date.get(d)
        if snap is None:
            continue
        sub = snap[[a, "ts_code", f"fwd_ret_{REB_DAYS_PRIMARY}"]].dropna()
        if len(sub) < 200:
            continue
        # quintiles
        sub = sub.sort_values(a)
        n = len(sub)
        q = n // 5
        q1 = sub.iloc[:q]
        q5 = sub.iloc[-q:]

        # gross returns at rebalance d (using fwd_ret_20 from this snapshot)
        r_q5 = q5[f"fwd_ret_{REB_DAYS_PRIMARY}"].mean()
        r_q1 = q1[f"fwd_ret_{REB_DAYS_PRIMARY}"].mean()
        r_uni = sub[f"fwd_ret_{REB_DAYS_PRIMARY}"].mean()

        # turnover (fraction of names changed since last rebal)
        if prev_q5 is None:
            tov_q5 = tov_q1 = 1.0
        else:
            tov_q5 = 1.0 - len(set(q5["ts_code"]) & set(prev_q5)) / max(len(prev_q5), 1)
            tov_q1 = 1.0 - len(set(q1["ts_code"]) & set(prev_q1)) / max(len(prev_q1), 1)
        prev_q5, prev_q1 = q5["ts_code"].tolist(), q1["ts_code"].tolist()

        cost_ls    = (COST_BPS / 1e4) * (tov_q5 + tov_q1)
        cost_q5    = (COST_BPS / 1e4) * tov_q5
        ls_gross   = r_q5 - r_q1
        ls_net     = ls_gross - cost_ls
        q5_excess  = r_q5 - r_uni - cost_q5
        rebal_records.append({"date": d, "n": n, "r_q5": r_q5, "r_q1": r_q1, "r_uni": r_uni,
                              "tov_q5": tov_q5, "tov_q1": tov_q1, "ls_gross": ls_gross,
                              "ls_net": ls_net, "q5_excess": q5_excess,
                              "year": d[:4]})
    R = pd.DataFrame(rebal_records)
    if len(R) == 0:
        continue
    rebalances_for_top[a] = R

    # headline summary
    ls_summary[a] = {
        "alpha": a,
        "n_reb": len(R),
        "ls_ann_ret": R["ls_net"].mean() * (252 / REB_DAYS_PRIMARY),
        "ls_ann_vol": R["ls_net"].std()  * np.sqrt(252 / REB_DAYS_PRIMARY),
        "ls_sharpe": R["ls_net"].mean() / R["ls_net"].std() * np.sqrt(252 / REB_DAYS_PRIMARY) if R["ls_net"].std() > 0 else np.nan,
        "ls_gross_sharpe": R["ls_gross"].mean() / R["ls_gross"].std() * np.sqrt(252 / REB_DAYS_PRIMARY) if R["ls_gross"].std() > 0 else np.nan,
        "ls_max_dd": ((1 + R["ls_net"]).cumprod() / (1 + R["ls_net"]).cumprod().cummax() - 1).min(),
        "avg_tov_q5": R["tov_q5"].mean(),
        "avg_tov_q1": R["tov_q1"].mean(),
        "avg_cost_per_reb_bps": (R["tov_q5"] + R["tov_q1"]).mean() * COST_BPS,
    }
    q5_summary[a] = {
        "alpha": a,
        "q5_ann_excess": R["q5_excess"].mean() * (252 / REB_DAYS_PRIMARY),
        "q5_ann_vol":    R["q5_excess"].std()  * np.sqrt(252 / REB_DAYS_PRIMARY),
        "q5_ir": R["q5_excess"].mean() / R["q5_excess"].std() * np.sqrt(252 / REB_DAYS_PRIMARY) if R["q5_excess"].std() > 0 else np.nan,
        "q5_max_dd": ((1 + R["q5_excess"]).cumprod() / (1 + R["q5_excess"]).cumprod().cummax() - 1).min(),
    }

    # per year
    for y, gy in R.groupby("year"):
        if len(gy) >= 3:
            ls_ann_y = gy["ls_net"].mean() * (252 / REB_DAYS_PRIMARY)
            ls_sh_y  = gy["ls_net"].mean() / gy["ls_net"].std() * np.sqrt(252 / REB_DAYS_PRIMARY) if gy["ls_net"].std() > 0 else np.nan
            q5_ex_y  = gy["q5_excess"].mean() * (252 / REB_DAYS_PRIMARY)
            q5_ir_y  = gy["q5_excess"].mean() / gy["q5_excess"].std() * np.sqrt(252 / REB_DAYS_PRIMARY) if gy["q5_excess"].std() > 0 else np.nan
        else:
            ls_ann_y = ls_sh_y = q5_ex_y = q5_ir_y = np.nan
        ls_annual_rows.append({"alpha": a, "year": y, "n": len(gy), "ls_ann_ret": ls_ann_y, "ls_sharpe": ls_sh_y})
        q5_annual_rows.append({"alpha": a, "year": y, "n": len(gy), "q5_ann_excess": q5_ex_y, "q5_ir": q5_ir_y})

ls_sum_df = pd.DataFrame(ls_summary).T.reset_index(drop=True)
ls_ann_df = pd.DataFrame(ls_annual_rows)
q5_sum_df = pd.DataFrame(q5_summary).T.reset_index(drop=True)
q5_ann_df = pd.DataFrame(q5_annual_rows)

ls_sum_df.to_csv(OUT_DIR / "ls_summary_batch_0001.csv", index=False)
ls_ann_df.to_csv(OUT_DIR / "ls_annual_batch_0001.csv", index=False)
q5_sum_df.to_csv(OUT_DIR / "q5_excess_summary_batch_0001.csv", index=False)
q5_ann_df.to_csv(OUT_DIR / "q5_excess_annual_batch_0001.csv", index=False)

# Save rebalance series for the top-LS alpha
top = ls_sum_df.sort_values("ls_sharpe", ascending=False).iloc[0]["alpha"]
print(f"  top LS-sharpe alpha: {top}", flush=True)
rebalances_for_top[top].to_csv(OUT_DIR / f"rebalances_{top}.csv", index=False)
for a, R in rebalances_for_top.items():
    R.to_csv(OUT_DIR / f"rebalances_{a}.csv", index=False)

print("\n=== LS summary ===\n", ls_sum_df.to_string(), flush=True)
print("\n=== Q5 long-only summary ===\n", q5_sum_df.to_string(), flush=True)
print(f"DONE  elapsed={time.time()-t0:.1f}s", flush=True)
