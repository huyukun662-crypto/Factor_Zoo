"""
Session: lottery_megacap_overlay — round 1 (candidates)

Goal: find a regime overlay that lifts α_17 Q5 long-only worst-year
(2020 = -0.33) above 0.5, preserving full-sample IR ≥ 1.0.

α_17 failure mechanism (from diagnosis_2025_regime_break.md): lottery
premium dies in A-share megacap-rally regimes (2020 was the megacap
rally year). This script tests 4 candidate signals as "megacap-regime
detectors", each with a gate:

  gate_on(t) = 1 if NOT megacap-rally regime at t, else 0

Candidate signals (all from .cache/daily.parquet × daily_basic.parquet):

  A) size_spread_60d  — top-100-cap mean 60d log-ret minus bottom-1000-cap mean
  B) concentration    — top-100-cap total_mv / all total_mv (rolling)
  C) size_q5q1_12m_sh — Sharpe of top-mv-quintile minus bottom-mv-quintile,
                        trailing 12-month rolling
  D) size_disp_60d    — cross-section std of 5 size-quintile 60d mean returns

For each candidate, compute two gate regimes:
  gate-type-P : gate_on = 1 if signal < rolling_pct(signal, lookback=252, p=75)
  gate-type-Z : gate_on = 1 if signal < rolling_median(signal, lookback=252)

Then apply each gate to the α_17 Q5 long-only baseline from script 16
(logs/20260422_trend_technical_alpha/scripts/16_alpha17_longonly_review.py)
in TWO fallback modes:
  "benchmark" : gate-off → hold universe (excess = 0 that month)
  "cash"      : gate-off → 0 return (excess = -universe that month)

Output: per-candidate + per-fallback results table, ranked by worst-year IR.
"""
from __future__ import annotations
import json, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("/home/user/Factor_Zoo")
CACHE = ROOT / ".cache"
LOT = ROOT / "logs/20260421_volprice_max_lottery"
SESSION = ROOT / "logs/20260422_lottery_megacap_overlay"
OUT_DIR = SESSION / "outputs"

COST_BPS = 5
REBAL = 20
TRAIN_END = pd.Timestamp("2022-12-31")
VALID_END = pd.Timestamp("2023-12-31")


# ---------------------------------------------------------------- #
# Helpers                                                          #
# ---------------------------------------------------------------- #

def industry_demean(df, col):
    return df[col] - df.groupby(["trade_date", "industry"])[col].transform("mean")


def perf(r, ppy=12):
    r = r.dropna()
    if len(r) < 2:
        return {"sharpe": np.nan, "ann": np.nan, "maxdd": np.nan}
    ann = r.mean() * ppy
    vol = r.std(ddof=0) * np.sqrt(ppy)
    eq = (1 + r).cumprod()
    return {"sharpe": ann / vol if vol > 0 else 0.0,
            "ann": float(ann),
            "maxdd": float((eq / eq.cummax() - 1).min())}


def per_year_ir(r):
    r = r.dropna()
    out = {}
    for y in sorted(set(r.index.year)):
        rr = r[r.index.year == y]
        if len(rr) < 6:
            continue
        v = rr.std(ddof=0)
        if v > 0:
            out[int(y)] = float((rr.mean() * 12) / (v * np.sqrt(12)))
        elif abs(rr.mean()) < 1e-9:
            out[int(y)] = 0.0
    return out


# ---------------------------------------------------------------- #
# Build megacap regime features                                    #
# ---------------------------------------------------------------- #

def build_megacap_features():
    print("[feat] loading daily + daily_basic...")
    daily = pd.read_parquet(CACHE / "daily.parquet").merge(
        pd.read_parquet(CACHE / "adj_factor.parquet"),
        on=["ts_code", "trade_date"], how="left"
    ).merge(
        pd.read_parquet(CACHE / "daily_basic.parquet")[["ts_code", "trade_date", "total_mv"]],
        on=["ts_code", "trade_date"], how="left"
    )
    daily["adj_factor"] = daily["adj_factor"].fillna(1.0)
    daily["P"] = daily["close"] * daily["adj_factor"]
    daily["trade_date"] = pd.to_datetime(daily["trade_date"])
    daily = daily.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)
    daily["log_ret"] = daily.groupby("ts_code")["P"].transform(lambda s: np.log(s).diff())
    daily["ret_60"] = daily.groupby("ts_code")["log_ret"].transform(
        lambda s: s.rolling(60, min_periods=40).sum())

    # Per-date size ranks
    daily = daily.dropna(subset=["total_mv"])

    print("[feat] computing per-date size quintiles + ret_60 by bucket...")
    daily["size_rank"] = daily.groupby("trade_date")["total_mv"].rank(
        method="first", pct=True, ascending=True)
    # Quintiles: 0-0.2=Q1 (small) ... 0.8-1.0=Q5 (large)
    # Top-100 proxy: top 100 stocks by mv (per date)
    daily["is_top100"] = daily.groupby("trade_date")["total_mv"].rank(
        method="first", ascending=False) <= 100
    daily["is_bot1000"] = daily.groupby("trade_date")["total_mv"].rank(
        method="first", ascending=False) > (daily.groupby("trade_date")["ts_code"].transform("count") - 1000)

    # Top/bottom mean ret_60 per date
    top100_ret = daily[daily["is_top100"]].groupby("trade_date")["ret_60"].mean()
    bot1000_ret = daily[daily["is_bot1000"]].groupby("trade_date")["ret_60"].mean()
    size_spread_60d = (top100_ret - bot1000_ret).rename("size_spread_60d")
    print(f"[feat] size_spread_60d ready, n={len(size_spread_60d)}")

    # Concentration: top100 total_mv / all total_mv
    top100_mv = daily[daily["is_top100"]].groupby("trade_date")["total_mv"].sum()
    all_mv = daily.groupby("trade_date")["total_mv"].sum()
    concentration = (top100_mv / all_mv).rename("concentration")

    # Size Q5-Q1 (by market cap) 60d spread ≠ Sharpe. Use TS-Sharpe of daily spread.
    daily["size_q"] = daily.groupby("trade_date")["size_rank"].transform(
        lambda s: pd.qcut(s.rank(method="first"), 5, labels=False, duplicates="drop"))
    q5_ret = daily[daily["size_q"] == 4].groupby("trade_date")["log_ret"].mean()
    q1_ret = daily[daily["size_q"] == 0].groupby("trade_date")["log_ret"].mean()
    size_factor = (q5_ret - q1_ret).rename("size_factor_ret")  # daily Q5-Q1 return
    # Rolling 252d Sharpe of size factor
    sf_ann = size_factor.rolling(252, min_periods=120).mean() * 252
    sf_vol = size_factor.rolling(252, min_periods=120).std(ddof=0) * np.sqrt(252)
    size_q5q1_12m_sh = (sf_ann / sf_vol).rename("size_q5q1_12m_sh")

    # Size-bucket 60d mean return dispersion
    q_ret_60 = {}
    for qi in range(5):
        q_ret_60[qi] = daily[daily["size_q"] == qi].groupby("trade_date")["ret_60"].mean()
    size_ret_df = pd.DataFrame(q_ret_60)
    size_disp_60d = size_ret_df.std(axis=1, ddof=0).rename("size_disp_60d")

    feats = pd.concat([size_spread_60d, concentration, size_q5q1_12m_sh, size_disp_60d], axis=1)
    feats.index.name = "trade_date"
    feats = feats.sort_index()
    print(f"[feat] all 4 features ready, shape={feats.shape}")
    return feats


def make_gate(signal, mode="pct75", lookback=252, min_periods=180):
    """Binary gate: 1 = α_17 ON, 0 = OFF.
    mode:
      'pct75': on when signal < rolling p75
      'pct90': on when signal < rolling p90
      'median': on when signal < rolling median
    """
    if mode == "median":
        threshold = signal.rolling(lookback, min_periods=min_periods).median()
    elif mode == "pct75":
        threshold = signal.rolling(lookback, min_periods=min_periods).quantile(0.75)
    elif mode == "pct90":
        threshold = signal.rolling(lookback, min_periods=min_periods).quantile(0.90)
    else:
        raise ValueError(mode)
    gate = (signal < threshold).astype(int).where(~threshold.isna(), 0)
    return gate


# ---------------------------------------------------------------- #
# Apply gate to α_17 Q5 long-only                                  #
# ---------------------------------------------------------------- #

def q5_long_only_with_gate(panel, alpha_col, ret_col, rebal_dates,
                           gate_series, top_pct=0.20, cost_bps=COST_BPS,
                           fallback="benchmark"):
    """Apply gate to Q5 long-only; gate=0 → fallback.
    fallback='benchmark': hold universe (excess=0, abs=universe_mean)
    fallback='cash': 0 return (abs=0, excess=-universe_mean)
    """
    rows = []
    prev_set = set(); prev_state = 0
    panel_l = panel[["trade_date", "ts_code", alpha_col, ret_col]].dropna()
    gate_dict = gate_series.to_dict()
    for t in rebal_dates:
        g = int(gate_dict.get(t, 0))
        snap = panel_l[panel_l["trade_date"] == t]
        if len(snap) < 100:
            continue
        uni_mean = snap[ret_col].mean()
        if g == 0:
            # fallback
            cur_set = set()
            if fallback == "benchmark":
                abs_r = uni_mean; exc_r = 0.0
            else:  # cash
                abs_r = 0.0; exc_r = -uni_mean
            if prev_state == 1 and prev_set:
                tov = 1.0  # full liquidation
            else:
                tov = 0.0
            rows.append(dict(trade_date=t, gate=0, abs_ret=abs_r, exc_ret=exc_r,
                             uni=uni_mean, tov=tov, cost=tov * cost_bps / 1e4))
            prev_state = 0; prev_set = set()
            continue
        snap_sorted = snap.sort_values(alpha_col, ascending=False)
        k = max(int(len(snap_sorted) * top_pct), 20)
        top = snap_sorted.head(k)
        cur_set = set(top["ts_code"])
        mean_ret = top[ret_col].mean()
        if prev_state == 1 and prev_set:
            tov = 1.0 - len(cur_set & prev_set) / max(len(cur_set), 1)
        else:
            tov = 1.0  # open from fallback/flat
        rows.append(dict(trade_date=t, gate=1, abs_ret=mean_ret,
                         exc_ret=mean_ret - uni_mean, uni=uni_mean,
                         tov=tov, cost=tov * cost_bps / 1e4))
        prev_state = 1; prev_set = cur_set
    df = pd.DataFrame(rows).set_index("trade_date").sort_index()
    df["abs_net"] = df["abs_ret"] - df["cost"]
    df["exc_net"] = df["exc_ret"] - df["cost"]
    return df


def summarize_gated(df, name):
    abs_p = perf(df["abs_net"])
    exc_p = perf(df["exc_net"])
    py_abs = per_year_ir(df["abs_net"])
    py_exc = per_year_ir(df["exc_net"])
    train = df[df.index <= TRAIN_END]
    valid = df[(df.index > TRAIN_END) & (df.index <= VALID_END)]
    test = df[df.index > VALID_END]
    return dict(
        name=name,
        abs_ann=abs_p["ann"], abs_sharpe=abs_p["sharpe"], abs_maxdd=abs_p["maxdd"],
        exc_ann=exc_p["ann"], exc_ir=exc_p["sharpe"], exc_maxdd=exc_p["maxdd"],
        exc_train_ir=perf(train["exc_net"])["sharpe"],
        exc_valid_ir=perf(valid["exc_net"])["sharpe"],
        exc_test_ir=perf(test["exc_net"])["sharpe"],
        worst_year_exc=min(py_exc.values()) if py_exc else np.nan,
        best_year_exc=max(py_exc.values()) if py_exc else np.nan,
        ir_2020=py_exc.get(2020, np.nan),
        ir_2025=py_exc.get(2025, np.nan),
        on_frac=float(df["gate"].mean()),
        avg_tov=float(df["tov"].mean()),
        per_year_exc=py_exc,
        per_year_abs=py_abs,
    )


# ---------------------------------------------------------------- #
# Main                                                              #
# ---------------------------------------------------------------- #

def main():
    t0 = time.time()

    # Load lottery α_17
    print("[r1] loading α_17 panel...")
    lot = pd.read_parquet(LOT / "outputs/panel_round3.parquet",
                          columns=["ts_code", "trade_date", "industry",
                                   "alpha_17", "fwd_ret_20"])
    lot["trade_date"] = pd.to_datetime(lot["trade_date"])
    lot = lot.dropna(subset=["industry"])
    lot["alpha_17_n"] = industry_demean(lot, "alpha_17")
    print(f"[r1] α_17 rows={len(lot):,}  {time.time()-t0:.1f}s")

    # Build features
    feats = build_megacap_features()
    print(f"[r1] features shape={feats.shape}  {time.time()-t0:.1f}s")

    # Save features for re-use
    feats.to_parquet(OUT_DIR / "megacap_features.parquet")

    # Rebalance grid
    dates = pd.Index(sorted(lot["trade_date"].unique()))
    rebal_dates = dates[::REBAL]
    print(f"[r1] {len(rebal_dates)} rebalance dates  "
          f"[{rebal_dates[0].date()} → {rebal_dates[-1].date()}]")

    # Baseline (no gate)
    from itertools import product

    # Baseline: always-on gate (for comparison)
    always_on = pd.Series(1, index=feats.index)
    base = q5_long_only_with_gate(lot, "alpha_17_n", "fwd_ret_20", rebal_dates,
                                    always_on, fallback="benchmark")
    S_base = summarize_gated(base, "BASELINE (no overlay)")
    print(f"\n[r1] BASELINE (no overlay) IR={S_base['exc_ir']:.3f}  "
          f"worst_yr={S_base['worst_year_exc']:.3f}  2020={S_base['ir_2020']:.3f}")

    # Grid: 4 features × 3 gate modes × 2 fallbacks = 24 combos
    results = [S_base]
    combos = list(product(
        ["size_spread_60d", "concentration", "size_q5q1_12m_sh", "size_disp_60d"],
        ["median", "pct75", "pct90"],
        ["benchmark", "cash"],
    ))
    print(f"\n[r1] testing {len(combos)} candidate gate combos...")
    for (feat_name, mode, fallback) in combos:
        signal = feats[feat_name].dropna()
        gate = make_gate(signal, mode=mode)
        df = q5_long_only_with_gate(lot, "alpha_17_n", "fwd_ret_20",
                                     rebal_dates, gate, fallback=fallback)
        sm = summarize_gated(df, f"{feat_name} | {mode} | {fallback}")
        sm["feature"] = feat_name; sm["mode"] = mode; sm["fallback"] = fallback
        results.append(sm)

    # Rank by worst-year IR then full IR
    ranked = sorted(results[1:], key=lambda s: (
        s["worst_year_exc"] if not np.isnan(s["worst_year_exc"]) else -99,
        s["exc_ir"] if not np.isnan(s["exc_ir"]) else -99,
    ), reverse=True)

    print("\n" + "=" * 110)
    print("Ranked candidates (by worst-year IR, then full IR)")
    print("=" * 110)
    print(f"{'feature':<22} {'mode':<8} {'fb':<10} "
          f"{'full IR':>8} {'worst':>7} {'2020':>7} {'2025':>7} "
          f"{'on_frac':>8} {'MaxDD%':>7} {'PASS?':>7}")
    for s in ranked:
        passed = (s["exc_ir"] >= 1.0) and (s["worst_year_exc"] >= 0.5)
        fmt = lambda v: f"{v:>8.3f}" if isinstance(v, float) and not np.isnan(v) else f"{'NA':>8}"
        print(f"  {s['feature']:<20} {s['mode']:<8} {s['fallback']:<10} "
              f"{fmt(s['exc_ir'])} {fmt(s['worst_year_exc']):>7} "
              f"{fmt(s['ir_2020']):>7} {fmt(s['ir_2025']):>7} "
              f"{fmt(s['on_frac']):>8} {s['exc_maxdd']*100:>+7.2f} "
              f"{('PASS' if passed else 'FAIL'):>7}")

    # Best candidate
    best = ranked[0]
    print(f"\n[r1] Best: {best['feature']} | {best['mode']} | {best['fallback']}")
    print(f"     full_IR={best['exc_ir']:.3f}  worst={best['worst_year_exc']:.3f}  "
          f"2020={best['ir_2020']:.3f}  2025={best['ir_2025']:.3f}  "
          f"on_frac={best['on_frac']:.3f}")

    # Write all results
    out = dict(
        experiment="overlay_candidates_round1",
        n_rebal=len(rebal_dates),
        baseline=S_base,
        candidates=results[1:],
        ranked_top5=ranked[:5],
        best=best,
    )
    with open(OUT_DIR / "overlay_candidates.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\n[r1] wrote {OUT_DIR / 'overlay_candidates.json'}")
    print(f"[r1] done {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
