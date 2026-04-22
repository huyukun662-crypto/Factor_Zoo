"""
2025 regime-break attribution: universe alpha availability vs signal selection
quality. Answers the user's question:

  "2025 年的问题是标的池内没有区间内强势标的(无 alpha)
   还是没有选到(选择质量差)?"

For each monthly rebalance date t, on the cross-section of stocks with
(α_n_mom, α_17_n, fwd_ret_20) all non-null, we compute:

  Universe alpha availability (ex-post, ideal-bound)
    spread_top_bottom_20 = mean(top-20% fwd_ret) − mean(bot-20% fwd_ret)
    universe_std         = cs std of fwd_ret

  Signal selection quality
    ic_mom, ic_lot       = Spearman rank corr(signal, fwd_ret)
    spread_q5q1_mom/lot  = realized Q5 − Q1 under the signal
    capture_mom/lot      = |signal Q5 ∩ top-20% fwd_ret| / |top-20%|
    efficiency_mom/lot   = spread_q5q1 / spread_top_bottom_20  (0=random, 1=perfect)

  Gate attribution (whether it switched to the wrong leg)
    gate_on              = which leg the dispersion gate activated
    active_ls_ret        = realized LS of gate-active leg
    inactive_ls_ret      = realized LS of the other leg
    gate_wrongness       = inactive − active  (positive ⇒ gate picked worse leg)

Aggregates per year and calls out 2025 z-score relative to 2018-24.
"""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("/home/user/Factor_Zoo")
CACHE = ROOT / ".cache"
TREND_LOG = ROOT / "logs/20260422_trend_technical_alpha"
LOT = ROOT / "logs/20260421_volprice_max_lottery"
OUT_DIR = TREND_LOG / "outputs"

REBAL = 20

def industry_demean(df, col):
    return df[col] - df.groupby(["trade_date", "industry"])[col].transform("mean")


def build_gates_baseline():
    """Baseline dispersion gate (disp_window=20, disp_lookback=252, p50)."""
    daily = pd.read_parquet(CACHE / "daily.parquet").merge(
        pd.read_parquet(CACHE / "adj_factor.parquet"),
        on=["ts_code", "trade_date"], how="left")
    daily["adj_factor"] = daily["adj_factor"].fillna(1.0)
    daily["P"] = daily["close"] * daily["adj_factor"]
    daily = daily.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)
    daily["trade_date"] = pd.to_datetime(daily["trade_date"])
    daily["ret"] = daily.groupby("ts_code")["P"].transform(lambda s: np.log(s).diff())
    daily["ret_20"] = daily.groupby("ts_code")["ret"].transform(
        lambda s: s.rolling(20, min_periods=15).sum())
    disp = daily.groupby("trade_date")["ret_20"].std()
    disp_med = disp.rolling(252, min_periods=180).median()
    gate_mom = (disp > disp_med).astype(int)
    gate_inv = (disp < disp_med).astype(int).where(~disp_med.isna(), 0)
    return gate_mom, gate_inv


def date_metrics(snap, t, gate_mom_on, gate_inv_on):
    """Return a dict of per-date metrics."""
    s = snap.dropna(subset=["alpha_n_mom", "alpha_17_n", "fwd_ret_20"])
    n = len(s)
    if n < 200:
        return None
    fr = s["fwd_ret_20"].values
    am = s["alpha_n_mom"].values
    al = s["alpha_17_n"].values

    # Universe metrics
    fr_s = np.sort(fr)
    k20 = max(1, n // 5)
    spread_top_bot_20 = float(fr_s[-k20:].mean() - fr_s[:k20].mean())
    universe_std = float(fr.std(ddof=0))
    universe_mean = float(fr.mean())

    # Signal ICs (Spearman)
    def spearman(a, b):
        ra = pd.Series(a).rank().values
        rb = pd.Series(b).rank().values
        if ra.std() == 0 or rb.std() == 0:
            return 0.0
        return float(np.corrcoef(ra, rb)[0, 1])

    ic_mom = spearman(am, fr)
    ic_lot = spearman(al, fr)

    # Q5/Q1 spreads (under signal ranking)
    def q5q1_spread_and_capture(sig_vals, fr_vals, top_set_idx):
        order = np.argsort(sig_vals)
        k = len(order) // 5
        q1_idx = order[:k]; q5_idx = order[-k:]
        q5_ret = fr_vals[q5_idx].mean()
        q1_ret = fr_vals[q1_idx].mean()
        capture = len(set(q5_idx.tolist()) & top_set_idx) / max(len(top_set_idx), 1)
        return float(q5_ret - q1_ret), float(q5_ret), float(q1_ret), float(capture)

    top20_idx = set(np.argsort(fr)[-k20:].tolist())
    spread_mom, q5_mom, q1_mom, cap_mom = q5q1_spread_and_capture(am, fr, top20_idx)
    spread_lot, q5_lot, q1_lot, cap_lot = q5q1_spread_and_capture(al, fr, top20_idx)

    eff_mom = spread_mom / spread_top_bot_20 if spread_top_bot_20 > 1e-9 else np.nan
    eff_lot = spread_lot / spread_top_bot_20 if spread_top_bot_20 > 1e-9 else np.nan

    # Gate attribution
    if gate_mom_on:
        active_leg = "mom"; active_ls = spread_mom; inactive_ls = spread_lot
    elif gate_inv_on:
        active_leg = "inv"; active_ls = spread_lot; inactive_ls = spread_mom
    else:
        active_leg = "cash"; active_ls = 0.0; inactive_ls = max(spread_mom, spread_lot)
    gate_wrongness = float(inactive_ls - active_ls)

    return dict(
        trade_date=t,
        n_stocks=n,
        spread_top_bot_20=spread_top_bot_20,
        universe_std=universe_std,
        universe_mean=universe_mean,
        ic_mom=ic_mom, ic_lot=ic_lot,
        spread_mom_q5q1=spread_mom, q5_mom=q5_mom, q1_mom=q1_mom, cap_mom=cap_mom, eff_mom=eff_mom,
        spread_lot_q5q1=spread_lot, q5_lot=q5_lot, q1_lot=q1_lot, cap_lot=cap_lot, eff_lot=eff_lot,
        gate_mom_on=int(gate_mom_on), gate_inv_on=int(gate_inv_on),
        active_leg=active_leg,
        active_ls=active_ls, inactive_ls=inactive_ls, gate_wrongness=gate_wrongness,
    )


def per_year_stats(df, col):
    """Per-year mean + compare 2025 vs 2018-24 baseline."""
    df = df.dropna(subset=[col])
    py = {}
    for y, sub in df.groupby("year"):
        py[int(y)] = dict(n=len(sub), mean=float(sub[col].mean()),
                          median=float(sub[col].median()),
                          std=float(sub[col].std(ddof=0)))
    baseline = df[df["year"] < 2025][col]
    v_2025 = df[df["year"] == 2025][col]
    if len(v_2025) > 0 and len(baseline) > 0:
        base_mean = float(baseline.mean()); base_std = float(baseline.std(ddof=0))
        z_2025 = float((v_2025.mean() - base_mean) / base_std) if base_std > 0 else np.nan
        baseline_p25 = float(baseline.quantile(0.25))
        baseline_p75 = float(baseline.quantile(0.75))
    else:
        z_2025 = np.nan; base_mean = np.nan; baseline_p25 = baseline_p75 = np.nan
    return dict(per_year=py, baseline_2018_24_mean=base_mean,
                baseline_p25=baseline_p25, baseline_p75=baseline_p75,
                v_2025_mean=float(v_2025.mean()) if len(v_2025) else np.nan,
                z_2025=z_2025)


def main():
    t0 = time.time()
    print("[attr] loading momentum panel (cached)...")
    mom_cache = CACHE / "alpha_n_mom_for_rotation.parquet"
    mom = pd.read_parquet(mom_cache)

    print("[attr] loading lottery α_17 panel...")
    lot = pd.read_parquet(LOT / "outputs/panel_round3.parquet",
                          columns=["ts_code", "trade_date", "industry",
                                   "alpha_17", "fwd_ret_20"])
    lot["trade_date"] = pd.to_datetime(lot["trade_date"])
    lot = lot.dropna(subset=["industry"])
    lot["alpha_17_n"] = industry_demean(lot, "alpha_17")
    print(f"[attr] lot: {len(lot):,} rows  {time.time()-t0:.1f}s")

    # Merge both signals + fwd_ret on (ts_code, trade_date)
    panel = mom[["ts_code", "trade_date", "alpha_n_mom"]].merge(
        lot[["ts_code", "trade_date", "alpha_17_n", "fwd_ret_20"]],
        on=["ts_code", "trade_date"], how="inner")
    print(f"[attr] merged panel: {len(panel):,} rows")

    # Gates
    print("[attr] building baseline gates...")
    gate_mom, gate_inv = build_gates_baseline()

    # Rebalance grid — same as script 11
    common_dates = pd.Index(sorted(set(mom["trade_date"]) & set(lot["trade_date"])))
    rebal_dates = common_dates[::REBAL]
    print(f"[attr] {len(rebal_dates)} rebalance dates  [{rebal_dates[0].date()} → {rebal_dates[-1].date()}]")

    # Per-date metrics
    rows = []
    gm_dict = gate_mom.to_dict(); gi_dict = gate_inv.to_dict()
    for t in rebal_dates:
        snap = panel[panel["trade_date"] == t]
        gmv = int(gm_dict.get(t, 0)); giv = int(gi_dict.get(t, 0))
        m = date_metrics(snap, t, gmv, giv)
        if m is not None:
            rows.append(m)
    df = pd.DataFrame(rows)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.sort_values("trade_date").reset_index(drop=True)
    df["year"] = df["trade_date"].dt.year
    print(f"[attr] computed {len(df)} per-date metric rows  {time.time()-t0:.1f}s")

    # Per-year summary for key columns
    print("\n" + "=" * 100)
    print("Per-year summary (mean of monthly values)")
    print("=" * 100)
    key_cols = ["spread_top_bot_20", "universe_std", "universe_mean",
                "ic_mom", "ic_lot",
                "spread_mom_q5q1", "spread_lot_q5q1",
                "eff_mom", "eff_lot",
                "cap_mom", "cap_lot",
                "gate_wrongness"]
    yearly = df.groupby("year")[key_cols].mean().round(4)
    print(yearly.to_string())

    # 2025 deviation from 2018-24 baseline
    print("\n" + "=" * 100)
    print("2025 vs 2018-24 baseline (z-score)")
    print("=" * 100)
    attr_summary = {}
    for c in key_cols:
        stats = per_year_stats(df, c)
        attr_summary[c] = stats
        b = stats["baseline_2018_24_mean"]; v = stats["v_2025_mean"]; z = stats["z_2025"]
        if not (np.isnan(b) or np.isnan(v) or np.isnan(z)):
            print(f"  {c:<22} baseline={b:>+7.4f}  2025={v:>+7.4f}  z={z:>+5.2f}")

    # Verdict
    print("\n" + "=" * 100)
    print("Attribution verdict")
    print("=" * 100)
    y_2025 = yearly.loc[2025] if 2025 in yearly.index else None
    y_2024 = yearly.loc[2024] if 2024 in yearly.index else None
    baseline_spread = df[df["year"] < 2025]["spread_top_bot_20"].mean()
    spread_2025 = y_2025["spread_top_bot_20"] if y_2025 is not None else np.nan
    eff_mom_2025 = y_2025["eff_mom"] if y_2025 is not None else np.nan
    eff_mom_base = df[df["year"] < 2025]["eff_mom"].mean()
    ic_mom_2025 = y_2025["ic_mom"] if y_2025 is not None else np.nan
    ic_mom_base = df[df["year"] < 2025]["ic_mom"].mean()
    wrongness_2025 = y_2025["gate_wrongness"] if y_2025 is not None else np.nan
    wrongness_base = df[df["year"] < 2025]["gate_wrongness"].mean()

    print(f"  Universe spread_top_bot_20 — baseline={baseline_spread:.4f}  "
          f"2025={spread_2025:.4f}  ratio={spread_2025/baseline_spread:.2f}")
    print(f"  Momentum efficiency       — baseline={eff_mom_base:.4f}  "
          f"2025={eff_mom_2025:.4f}  ratio={eff_mom_2025/eff_mom_base:.2f}")
    print(f"  Momentum IC               — baseline={ic_mom_base:.4f}  "
          f"2025={ic_mom_2025:.4f}")
    print(f"  Gate wrongness            — baseline={wrongness_base:.4f}  "
          f"2025={wrongness_2025:.4f}")

    # Write out
    out_json = OUT_DIR / "attribution_2025.json"
    with open(out_json, "w") as f:
        json.dump({
            "n_rebal": len(df),
            "date_range": [str(df["trade_date"].min().date()), str(df["trade_date"].max().date())],
            "per_year_means": {str(y): v.to_dict() for y, v in yearly.iterrows()},
            "attr_summary": attr_summary,
            "baseline_spread_top_bot_20": float(baseline_spread),
            "spread_2025": float(spread_2025) if not np.isnan(spread_2025) else None,
            "eff_mom_baseline": float(eff_mom_base),
            "eff_mom_2025": float(eff_mom_2025) if not np.isnan(eff_mom_2025) else None,
            "ic_mom_baseline": float(ic_mom_base),
            "ic_mom_2025": float(ic_mom_2025) if not np.isnan(ic_mom_2025) else None,
            "gate_wrongness_baseline": float(wrongness_base),
            "gate_wrongness_2025": float(wrongness_2025) if not np.isnan(wrongness_2025) else None,
        }, f, indent=2, default=str)
    print(f"\n[attr] wrote {out_json}")

    # Also save full per-date tape for inspection
    tape_csv = OUT_DIR / "attribution_2025_tape.csv"
    df.to_csv(tape_csv, index=False)
    print(f"[attr] wrote {tape_csv}")
    print(f"[attr] done {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
