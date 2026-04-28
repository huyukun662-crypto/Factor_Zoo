"""
Round 3: spec sensitivity of the winner alpha_04 across windows {10,15,20,25,30,40}.

For each window w:
  alpha_04(w) = sum(log_ON, w) - sum(log_ID, w)
  -> winsor 1/99 -> industry-demean -> cs-zscore (per date)
  -> LS Q5-Q1 monthly net Sharpe + worst-year-floor + Q5 IR

Pass criterion: 5 of 6 windows must have
  LS net Sharpe >= 1.5 AND worst-year LS Sharpe >= 0.5

Reads:  outputs/panel_overnight.parquet
Writes: outputs/round3_spec_sensitivity.csv
"""
from __future__ import annotations
import time
from pathlib import Path
import numpy as np
import pandas as pd

SESSION = Path("/home/user/Factor_Zoo/logs/20260428_a_share_overnight_intraday_alpha")
OUT = SESSION / "outputs"

WINDOWS = [10, 15, 20, 25, 30, 40]
REB_DAYS = 20
COST = 5e-4              # 5 bps per side = 5 / 1e4
ann = np.sqrt(252 / REB_DAYS)


def cs_z(s):
    mu, sd = s.mean(), s.std()
    return (s - mu) / sd if sd and not np.isnan(sd) else s * 0.0


def per_date_winsor(s, lo=0.01, hi=0.99):
    return s.clip(s.quantile(lo), s.quantile(hi))


t0 = time.time()
panel = pd.read_parquet(OUT / "panel_overnight.parquet")
panel["trade_date"] = panel["trade_date"].astype(str)
panel = panel.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)

g = panel.groupby("ts_code", sort=False)

rows = []
yearly = []
for w in WINDOWS:
    print(f"=== window {w} ===", flush=True)
    panel[f"sum_ON_{w}"] = g["log_ON"].transform(lambda s: s.rolling(w, min_periods=int(w*0.75)).sum())
    panel[f"sum_ID_{w}"] = g["log_ID"].transform(lambda s: s.rolling(w, min_periods=int(w*0.75)).sum())
    raw = panel[f"sum_ON_{w}"] - panel[f"sum_ID_{w}"]
    panel[f"a_{w}_raw"] = raw

    # per-date pipeline
    panel[f"a_{w}_raw"] = panel.groupby("trade_date")[f"a_{w}_raw"].transform(per_date_winsor)
    panel[f"a_{w}"] = panel[f"a_{w}_raw"] - panel.groupby(["trade_date","industry"])[f"a_{w}_raw"].transform("mean")
    panel[f"a_{w}"] = panel.groupby("trade_date")[f"a_{w}"].transform(cs_z)

    # backtest
    dates = sorted(panel["trade_date"].unique())
    rebs = dates[::REB_DAYS]
    by_date = {d: gx for d, gx in panel.groupby("trade_date", sort=False)}

    prev_q5 = prev_q1 = None
    R = []
    for d in rebs:
        snap = by_date.get(d)
        if snap is None: continue
        sub = snap[[f"a_{w}", "ts_code", "fwd_ret_20"]].dropna()
        if len(sub) < 200: continue
        sub = sub.sort_values(f"a_{w}")
        n = len(sub); q = n // 5
        q1 = sub.iloc[:q]; q5 = sub.iloc[-q:]
        r_q5 = q5["fwd_ret_20"].mean()
        r_q1 = q1["fwd_ret_20"].mean()
        r_uni = sub["fwd_ret_20"].mean()
        if prev_q5 is None:
            t5 = t1 = 1.0
        else:
            t5 = 1.0 - len(set(q5["ts_code"]) & set(prev_q5)) / max(len(prev_q5), 1)
            t1 = 1.0 - len(set(q1["ts_code"]) & set(prev_q1)) / max(len(prev_q1), 1)
        prev_q5, prev_q1 = q5["ts_code"].tolist(), q1["ts_code"].tolist()
        ls_net = (r_q5 - r_q1) - COST * (t5 + t1)
        q5_exc = (r_q5 - r_uni) - COST * t5
        R.append({"date": d, "year": d[:4], "ls_net": ls_net, "q5_exc": q5_exc})
    R = pd.DataFrame(R)
    sh = R["ls_net"].mean() / R["ls_net"].std() * ann if R["ls_net"].std() > 0 else np.nan
    q5ir = R["q5_exc"].mean() / R["q5_exc"].std() * ann if R["q5_exc"].std() > 0 else np.nan

    # worst-year
    yr_sh = []
    for y, gy in R.groupby("year"):
        if len(gy) >= 3 and gy["ls_net"].std() > 0:
            sy = gy["ls_net"].mean() / gy["ls_net"].std() * ann
            yr_sh.append((y, sy))
            yearly.append({"window": w, "year": y, "ls_sharpe": sy})
    worst = min(s for _, s in yr_sh) if yr_sh else np.nan
    rows.append({"window": w, "ls_sharpe_net": float(sh), "q5_ir_net": float(q5ir),
                 "worst_year_sharpe": float(worst),
                 "pass_sh_15": sh >= 1.5, "pass_worst_05": worst >= 0.5,
                 "pass_both":  (sh >= 1.5) and (worst >= 0.5)})
    print(f"  w={w}: LS Sharpe {sh:.2f}, Q5 IR {q5ir:.2f}, worst-year {worst:.2f}", flush=True)
    # cleanup
    panel.drop(columns=[f"sum_ON_{w}", f"sum_ID_{w}", f"a_{w}_raw", f"a_{w}"], inplace=True)

df = pd.DataFrame(rows)
df.to_csv(OUT / "round3_spec_sensitivity.csv", index=False)
yr_df = pd.DataFrame(yearly)
yr_df.to_csv(OUT / "round3_spec_sensitivity_yearly.csv", index=False)
n_pass = int(df["pass_both"].sum())
print(f"\n=== Round 3 ===\n{df.to_string(index=False)}")
print(f"\nWindows passing both criteria: {n_pass}/{len(df)}  -> {'PASS' if n_pass>=5 else 'FAIL'}")
print(f"DONE  elapsed={time.time()-t0:.1f}s")
