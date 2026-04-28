"""
Round 4: TVT split + 100 random placebos for alpha_04.

Part A — TVT
  Train     2018-01-02 .. 2022-12-31
  Validate  2023-01-01 .. 2023-12-31
  Test      2024-01-01 .. 2026-04-25
  Pass: train/validate/test LS net Sharpe each >= 0.5; train/validate gradient
  in [1.0, 3.0]; test Sharpe >= 50% of train Sharpe.

Part B — Placebo (100 trials)
  At each rebal date, randomly permute alpha_04 across stocks (within the same
  date), then re-backtest. Compare distribution of placebo LS Sharpes to the
  actual headline. Pass: actual Sharpe > 99th percentile of placebos AND
  Bonferroni-equivalent p < 0.01.

Reads:  outputs/panel_alphas.parquet, outputs/rebalances_alpha_04.csv
Writes: outputs/round4_tvt.csv, outputs/round4_placebo.csv
"""
from __future__ import annotations
import time
from pathlib import Path
import numpy as np
import pandas as pd

SESSION = Path("/home/user/Factor_Zoo/logs/20260428_a_share_overnight_intraday_alpha")
OUT = SESSION / "outputs"
ALPHA = "alpha_04"
REB_DAYS = 20
COST = 5e-4
ann = np.sqrt(252 / REB_DAYS)


def cs_z(s):
    mu, sd = s.mean(), s.std()
    return (s - mu) / sd if sd and not np.isnan(sd) else s * 0.0


t0 = time.time()

# ============================== Part A: TVT ==============================
print("=== Part A: TVT split ===", flush=True)
R = pd.read_csv(OUT / f"rebalances_{ALPHA}.csv")
R["date"] = R["date"].astype(str)


def split_sharpe(R, lo, hi):
    sub = R[(R["date"] >= lo) & (R["date"] <= hi)]
    if len(sub) < 3 or sub["ls_net"].std() == 0:
        return np.nan, len(sub)
    sh = sub["ls_net"].mean() / sub["ls_net"].std() * ann
    q5 = sub["q5_excess"].mean() / sub["q5_excess"].std() * ann if sub["q5_excess"].std() > 0 else np.nan
    return float(sh), int(len(sub)), float(q5)


splits = [("train",    "20180102", "20221231"),
          ("validate", "20230101", "20231231"),
          ("test",     "20240101", "20260425")]
tvt = []
for nm, lo, hi in splits:
    sh, n, q5 = split_sharpe(R, lo, hi)
    tvt.append({"split": nm, "from": lo, "to": hi, "n_rebal": n, "ls_sharpe_net": sh, "q5_ir_net": q5})
tvt_df = pd.DataFrame(tvt)
print(tvt_df.to_string(index=False))

tr_sh = tvt_df.loc[tvt_df["split"] == "train", "ls_sharpe_net"].iloc[0]
va_sh = tvt_df.loc[tvt_df["split"] == "validate", "ls_sharpe_net"].iloc[0]
te_sh = tvt_df.loc[tvt_df["split"] == "test", "ls_sharpe_net"].iloc[0]
gradient = tr_sh / va_sh if va_sh > 0 else np.nan
test_pct = 100.0 * te_sh / tr_sh if tr_sh > 0 else np.nan
checks = {
    "train_sh_ge_05":   tr_sh >= 0.5,
    "validate_sh_ge_05": va_sh >= 0.5,
    "test_sh_ge_05":    te_sh >= 0.5,
    "tv_gradient_in_1_3": (1.0 <= gradient <= 3.0),
    "test_pct_of_train_ge_50": test_pct >= 50.0,
}
print(f"\n  train Sharpe = {tr_sh:.2f},  validate = {va_sh:.2f},  test = {te_sh:.2f}")
print(f"  train/validate gradient = {gradient:.2f},  test/train pct = {test_pct:.1f}%")
print(f"  TVT checks: {checks}")
all_tvt_pass = all(checks.values())

tvt_df["check"] = ["pass" if v else "FAIL" for v in [tr_sh >= 0.5, va_sh >= 0.5, te_sh >= 0.5]]
tvt_df.to_csv(OUT / "round4_tvt.csv", index=False)

# ============================== Part B: Placebo ==============================
print("\n=== Part B: 100-placebo ===", flush=True)
ap = pd.read_parquet(OUT / "panel_alphas.parquet")
ap["trade_date"] = ap["trade_date"].astype(str)

dates = sorted(ap["trade_date"].unique())
rebs = dates[::REB_DAYS]
by_date = {d: g for d, g in ap.groupby("trade_date", sort=False)}

# Pre-build per-date rank-aligned slots
def backtest_signal_array(by_date, rebs, sig_per_date):
    """sig_per_date: dict trade_date -> ndarray aligned to (ts_code, fwd_ret, alpha)
    rows after dropna(subset=[ts_code, fwd_ret_20, ALPHA])."""
    prev_q5 = prev_q1 = None
    out = []
    for d in rebs:
        snap = by_date.get(d)
        if snap is None: continue
        sub = snap[["ts_code", "fwd_ret_20", ALPHA]].dropna().reset_index(drop=True)
        if len(sub) < 200: continue
        sig = sig_per_date.get(d)
        if sig is None or len(sig) != len(sub): continue
        sub["sig"] = sig
        sub = sub.sort_values("sig")
        n = len(sub); q = n // 5
        q1 = sub.iloc[:q]; q5 = sub.iloc[-q:]
        r_q5 = q5["fwd_ret_20"].mean(); r_q1 = q1["fwd_ret_20"].mean()
        if prev_q5 is None:
            t5 = t1 = 1.0
        else:
            t5 = 1.0 - len(set(q5["ts_code"]) & set(prev_q5)) / max(len(prev_q5), 1)
            t1 = 1.0 - len(set(q1["ts_code"]) & set(prev_q1)) / max(len(prev_q1), 1)
        prev_q5, prev_q1 = q5["ts_code"].tolist(), q1["ts_code"].tolist()
        out.append((r_q5 - r_q1) - COST * (t5 + t1))
    out = np.array(out)
    if len(out) < 5 or out.std() == 0:
        return np.nan
    return float(out.mean() / out.std() * ann)


# Pre-compute aligned signal arrays for actual alpha
sig_actual = {}
for d in rebs:
    snap = by_date.get(d)
    if snap is None: continue
    sub = snap[["ts_code", "fwd_ret_20", ALPHA]].dropna()
    sig_actual[d] = sub.set_index("ts_code")[ALPHA].values  # NOTE: order from snap

# Sanity check: actual reproduces ~2.44
def signal_for_actual():
    sd = {}
    for d in rebs:
        snap = by_date.get(d)
        if snap is None: continue
        sub = snap[["ts_code", "fwd_ret_20", ALPHA]].dropna().reset_index(drop=True)
        sd[d] = sub[ALPHA].values
    return sd

sd_actual = signal_for_actual()
sh_actual = backtest_signal_array(by_date, rebs, sd_actual)
print(f"  sanity: actual alpha_04 LS Sharpe = {sh_actual:.3f}")

placebo_shs = []
np.random.seed(42)
for trial in range(100):
    sd_perm = {}
    for d, arr in sd_actual.items():
        a2 = arr.copy()
        np.random.shuffle(a2)
        sd_perm[d] = a2
    sh = backtest_signal_array(by_date, rebs, sd_perm)
    placebo_shs.append(sh)
    if (trial + 1) % 20 == 0:
        print(f"  placebo {trial+1}/100  ... mean={np.nanmean(placebo_shs):.3f}", flush=True)

placebo = np.array(placebo_shs)
p_max = float(np.nanmax(placebo))
p_99  = float(np.nanpercentile(placebo, 99))
p_95  = float(np.nanpercentile(placebo, 95))
p_50  = float(np.nanpercentile(placebo, 50))
p_value = float(np.mean(placebo >= sh_actual))

print(f"\n  actual = {sh_actual:.3f}")
print(f"  placebo max  = {p_max:.3f}")
print(f"  placebo 99th = {p_99:.3f}")
print(f"  placebo 95th = {p_95:.3f}")
print(f"  placebo 50th = {p_50:.3f}")
print(f"  empirical p (placebo >= actual) = {p_value:.4f}")

placebo_df = pd.DataFrame({"trial": range(1, 101), "ls_sharpe": placebo})
placebo_df.to_csv(OUT / "round4_placebo.csv", index=False)

placebo_pass = sh_actual > p_max  # actual exceeds the worst-case placebo
print(f"  Placebo pass (actual > max placebo): {placebo_pass}")

print(f"\n=== Round 4 summary ===")
print(f"  TVT: train={tr_sh:.2f}  validate={va_sh:.2f}  test={te_sh:.2f}  -> {'PASS' if all_tvt_pass else 'FAIL'}")
print(f"  Placebo: actual {sh_actual:.2f} vs max {p_max:.2f}  -> {'PASS' if placebo_pass else 'FAIL'}")
print(f"DONE  elapsed={time.time()-t0:.1f}s")
