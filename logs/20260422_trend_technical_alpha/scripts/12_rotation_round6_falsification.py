"""
Round-6 falsification for MOM↔Lottery dispersion-regime rotation.

Two tests:

A) Spec sensitivity — 7 variants of the dispersion gate:
   disp_lookback ∈ {60, 126, 252, 504}
   threshold_percentile ∈ {40, 50, 60}
   disp_window ∈ {20 baseline, 60}
   Pass threshold: LS full Sharpe ≥ 1.5 AND worst-year LS ≥ 0.5.

B) Placebo — 100 random complementary binary gate pairs at matched
   three-way fractions (P(mom=1)=0.457, P(inv=1)=0.433, P(both_off)=0.110).
   True rotation must beat placebo median at p<0.05 on:
     - LS full Sharpe
     - worst-year LS

Caches the industry-demeaned momentum panel to .cache/ to skip build_factor()
(75 s) on subsequent runs.
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

ALPHA_N_MOM_CACHE = CACHE / "alpha_n_mom_for_rotation.parquet"

sys.path.insert(0, str(ROOT / "factors/price_volume/idio_12_3_momentum_disp_gated_v1"))

COST_BPS = 5
REBAL = 20
TRAIN_END = pd.Timestamp("2022-12-31")
VALID_END = pd.Timestamp("2023-12-31")
PLACEBO_N = 100
PLACEBO_SEED = 20260422


# -------------------------------------------------------------------- #
# Portfolio helpers (copied from script 11 for self-containment)       #
# -------------------------------------------------------------------- #

def industry_demean(df, col):
    return df[col] - df.groupby(["trade_date", "industry"])[col].transform("mean")


def perf(r, ppy=12):
    r = r.dropna()
    if len(r) < 2:
        return {"sharpe": np.nan, "maxdd": np.nan}
    ann = r.mean() * ppy
    vol = r.std(ddof=0) * np.sqrt(ppy)
    eq = (1 + r).cumprod()
    return {"sharpe": ann / vol if vol > 0 else 0.0,
            "maxdd": float((eq / eq.cummax() - 1).min())}


def per_year_active(r):
    r = r.dropna()
    yrs = r.index.year
    out = {}
    for y in sorted(set(yrs)):
        rr = r[yrs == y]
        if len(rr) < 6:
            continue
        v = rr.std(ddof=0)
        if v > 0:
            out[int(y)] = float((rr.mean() * 12) / (v * np.sqrt(12)))
        elif abs(rr.mean()) < 1e-9:
            out[int(y)] = 0.0
    return out


def _quintile_ls(snap, alpha_col, ret_col):
    snap = snap.copy()
    snap["q"] = pd.qcut(snap[alpha_col].rank(method="first"), 5,
                        labels=False, duplicates="drop")
    if snap["q"].isna().all():
        return None
    q5 = snap[snap["q"] == 4]; q1 = snap[snap["q"] == 0]
    return dict(q5_ret=q5[ret_col].mean(), q1_ret=q1[ret_col].mean(),
                all_ret=snap[ret_col].mean(),
                q5_set=set(q5["ts_code"]), q1_set=set(q1["ts_code"]))


def rotate_portfolio(panel_mom, panel_lot, rebal_dates, gate_mom, gate_inv,
                     alpha_mom="alpha_n_mom", alpha_lot="alpha_17_n",
                     ret_col="fwd_ret_20"):
    rows = []
    prev_leg = "cash"; prev_q5 = set(); prev_q1 = set()
    pmom = panel_mom[["trade_date", "ts_code", alpha_mom, ret_col]].dropna()
    plot = panel_lot[["trade_date", "ts_code", alpha_lot, ret_col]].dropna()
    # Use dict lookups for speed
    gm = gate_mom.to_dict(); gi = gate_inv.to_dict()
    for t in rebal_dates:
        gmv = int(gm.get(t, 0)); giv = int(gi.get(t, 0))
        if gmv == 1:
            leg = "mom"; snap = pmom[pmom["trade_date"] == t]; acol = alpha_mom
        elif giv == 1:
            leg = "inv"; snap = plot[plot["trade_date"] == t]; acol = alpha_lot
        else:
            leg = "cash"; snap = None; acol = None
        if leg == "cash" or snap is None or len(snap) < 100:
            tov_q5 = 1.0 if prev_leg != "cash" and prev_q5 else 0.0
            tov_q1 = 1.0 if prev_leg != "cash" and prev_q1 else 0.0
            rows.append(dict(trade_date=t, leg="cash", ls=0.0, q5=0.0, q1=0.0,
                             all=0.0, tov_q5=tov_q5, tov_q1=tov_q1))
            prev_leg = "cash"; prev_q5 = set(); prev_q1 = set()
            continue
        res = _quintile_ls(snap, acol, ret_col)
        if res is None:
            continue
        if leg == prev_leg and prev_q5:
            tov_q5 = 1.0 - len(res["q5_set"] & prev_q5) / max(len(res["q5_set"]), 1)
            tov_q1 = 1.0 - len(res["q1_set"] & prev_q1) / max(len(res["q1_set"]), 1)
        else:
            tov_q5 = 1.0; tov_q1 = 1.0
        rows.append(dict(trade_date=t, leg=leg,
                         q5=res["q5_ret"], q1=res["q1_ret"],
                         ls=res["q5_ret"] - res["q1_ret"], all=res["all_ret"],
                         tov_q5=tov_q5, tov_q1=tov_q1))
        prev_leg = leg; prev_q5 = res["q5_set"]; prev_q1 = res["q1_set"]
    return pd.DataFrame(rows)


def summarize_rotation(res, cost_bps=COST_BPS):
    res = res.copy()
    res["on"] = (res["leg"] != "cash").astype(int)
    res = res.set_index("trade_date").sort_index()
    res["ls_after"] = res["ls"] - (res["tov_q5"] + res["tov_q1"]) * cost_bps / 1e4
    res["q5_excess_after"] = (res["q5"] - res["all"]) - res["tov_q5"] * cost_bps / 1e4
    full = perf(res["ls_after"]); full_q5 = perf(res["q5_excess_after"])
    py_ls = per_year_active(res["ls_after"])
    py_q5 = per_year_active(res["q5_excess_after"])
    return dict(
        ls_full=full["sharpe"], ls_maxdd=full["maxdd"],
        q5_full=full_q5["sharpe"],
        worst_year_ls=min(py_ls.values()) if py_ls else np.nan,
        best_year_ls=max(py_ls.values()) if py_ls else np.nan,
        worst_year_q5=min(py_q5.values()) if py_q5 else np.nan,
        on_frac=float(res["on"].mean()),
        per_year_ls=py_ls,
        mom_frac=float((res["leg"] == "mom").mean()),
        inv_frac=float((res["leg"] == "inv").mean()),
    )


# -------------------------------------------------------------------- #
# Panel construction (with caching)                                    #
# -------------------------------------------------------------------- #

def build_momentum_panel():
    if ALPHA_N_MOM_CACHE.exists():
        print(f"[cache] loading {ALPHA_N_MOM_CACHE}...")
        return pd.read_parquet(ALPHA_N_MOM_CACHE)
    print("[cache] cold — running build_factor() (~75s)...")
    from code import FactorConfig, build_factor  # noqa: E402
    mom = build_factor(FactorConfig())
    mom = mom[["ts_code", "trade_date", "industry", "alpha_n"]].rename(
        columns={"alpha_n": "alpha_n_mom"}
    )
    mom.to_parquet(ALPHA_N_MOM_CACHE, index=False)
    print(f"[cache] wrote {ALPHA_N_MOM_CACHE}")
    return mom


def build_daily_disp_features():
    """Return daily_ret_20 indexed by (ts_code, trade_date) and per-date
    dispersion series for configurable (window, lookback, percentile)."""
    daily = pd.read_parquet(CACHE / "daily.parquet").merge(
        pd.read_parquet(CACHE / "adj_factor.parquet"),
        on=["ts_code", "trade_date"], how="left"
    )
    daily["adj_factor"] = daily["adj_factor"].fillna(1.0)
    daily["P"] = daily["close"] * daily["adj_factor"]
    daily = daily.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)
    daily["trade_date"] = pd.to_datetime(daily["trade_date"])
    daily["ret"] = daily.groupby("ts_code")["P"].transform(lambda s: np.log(s).diff())
    # Pre-compute both 20d and 60d rolling return windows; each variant uses one.
    daily["ret_20"] = daily.groupby("ts_code")["ret"].transform(
        lambda s: s.rolling(20, min_periods=15).sum()
    )
    daily["ret_60"] = daily.groupby("ts_code")["ret"].transform(
        lambda s: s.rolling(60, min_periods=40).sum()
    )
    return daily


def make_gates(disp_window, disp_lookback, threshold_percentile, daily):
    """Build (gate_mom, gate_inv) per-date from given dispersion spec."""
    ret_col = f"ret_{disp_window}"
    disp = daily.groupby("trade_date")[ret_col].std()
    min_p = max(int(disp_lookback * 0.7), 40)
    if threshold_percentile == 50:
        threshold = disp.rolling(disp_lookback, min_periods=min_p).median()
    else:
        q = threshold_percentile / 100.0
        threshold = disp.rolling(disp_lookback, min_periods=min_p).quantile(q)
    gate_mom = (disp > threshold).astype(int)
    gate_inv = (disp < threshold).astype(int).where(~threshold.isna(), 0)
    return gate_mom, gate_inv


# -------------------------------------------------------------------- #
# Placebo                                                              #
# -------------------------------------------------------------------- #

def random_complementary_gates(dates, p_mom, p_inv, rng):
    """Three-way categorical: mom (p_mom), inv (p_inv), off (1-p_mom-p_inv).
    Returns (gate_mom, gate_inv) as pd.Series indexed by dates."""
    u = rng.random(len(dates))
    gm = np.zeros(len(dates), dtype=int)
    gi = np.zeros(len(dates), dtype=int)
    gm[u < p_mom] = 1
    gi[(u >= p_mom) & (u < p_mom + p_inv)] = 1
    # remaining → both 0 (boundary)
    return (pd.Series(gm, index=dates), pd.Series(gi, index=dates))


# -------------------------------------------------------------------- #
# Main                                                                 #
# -------------------------------------------------------------------- #

def main():
    t0 = time.time()
    print("[r6] loading / building momentum panel...")
    mom = build_momentum_panel()
    print(f"[r6] mom panel: {len(mom):,} rows  {time.time()-t0:.1f}s")

    print("[r6] loading lottery α_17 panel...")
    lot = pd.read_parquet(LOT / "outputs/panel_round3.parquet",
                          columns=["ts_code", "trade_date", "industry",
                                   "alpha_17", "fwd_ret_20"])
    lot["trade_date"] = pd.to_datetime(lot["trade_date"])
    lot = lot.dropna(subset=["industry"])
    lot["alpha_17_n"] = industry_demean(lot, "alpha_17")
    print(f"[r6] lot panel: {len(lot):,} rows  {time.time()-t0:.1f}s")

    # Bring fwd_ret_20 onto the momentum panel
    mom = mom.merge(
        lot[["ts_code", "trade_date", "fwd_ret_20"]],
        on=["ts_code", "trade_date"], how="inner"
    )
    print(f"[r6] mom after fwd merge: {len(mom):,} rows  {time.time()-t0:.1f}s")

    print("[r6] building daily dispersion features...")
    daily = build_daily_disp_features()
    print(f"[r6] daily ready  {time.time()-t0:.1f}s")

    common_dates = pd.Index(sorted(set(mom["trade_date"]) & set(lot["trade_date"])))
    rebal_dates = common_dates[::REBAL]
    print(f"[r6] {len(rebal_dates)} rebalance dates  [{rebal_dates[0].date()} → {rebal_dates[-1].date()}]")

    # --------------------------------------------------------------- #
    # A) Spec sensitivity                                             #
    # --------------------------------------------------------------- #
    specs = [
        dict(name="BASELINE",         disp_window=20, disp_lookback=252, threshold_percentile=50),
        dict(name="lookback_60",      disp_window=20, disp_lookback=60,  threshold_percentile=50),
        dict(name="lookback_126",     disp_window=20, disp_lookback=126, threshold_percentile=50),
        dict(name="lookback_504",     disp_window=20, disp_lookback=504, threshold_percentile=50),
        dict(name="threshold_p40",    disp_window=20, disp_lookback=252, threshold_percentile=40),
        dict(name="threshold_p60",    disp_window=20, disp_lookback=252, threshold_percentile=60),
        dict(name="disp_window_60",   disp_window=60, disp_lookback=252, threshold_percentile=50),
    ]

    print("\n" + "=" * 92)
    print("A) Spec sensitivity (7 variants of dispersion gate)")
    print("=" * 92)
    print(f"{'variant':<20} {'LS full':>9} {'Q5 full':>9} {'worst-yr':>9} {'best-yr':>9} {'on_frac':>9} {'PASS?':>7}")
    spec_results = []
    for s in specs:
        gm, gi = make_gates(s["disp_window"], s["disp_lookback"],
                            s["threshold_percentile"], daily)
        res = rotate_portfolio(mom, lot, rebal_dates, gm, gi)
        sm = summarize_rotation(res)
        sm["spec"] = s
        sm["gate_mom_frac"] = float(gm.mean())
        sm["gate_inv_frac"] = float(gi.mean())
        passed = bool(sm["ls_full"] >= 1.5 and sm["worst_year_ls"] >= 0.5)
        sm["passed"] = passed
        spec_results.append(sm)
        fmt = lambda v: f"{v:>9.3f}" if isinstance(v, float) and not np.isnan(v) else f"{'NA':>9}"
        print(f"  {s['name']:<18} {fmt(sm['ls_full'])} {fmt(sm['q5_full'])} "
              f"{fmt(sm['worst_year_ls'])} {fmt(sm['best_year_ls'])} "
              f"{fmt(sm['on_frac'])} {('PASS' if passed else 'FAIL'):>7}")
    n_pass_spec = sum(1 for s in spec_results if s["passed"])
    print(f"\n[r6] spec sensitivity: {n_pass_spec}/{len(specs)} pass")

    # --------------------------------------------------------------- #
    # B) Placebo (100 random complementary gates)                     #
    # --------------------------------------------------------------- #
    print("\n" + "=" * 92)
    print(f"B) Placebo — {PLACEBO_N} random complementary gates "
          "(p_mom=0.457, p_inv=0.433, p_both_off=0.110)")
    print("=" * 92)
    rng = np.random.default_rng(PLACEBO_SEED)
    baseline = spec_results[0]
    baseline_ls = baseline["ls_full"]
    baseline_worst = baseline["worst_year_ls"]

    placebo_metrics = []
    for i in range(PLACEBO_N):
        gm_p, gi_p = random_complementary_gates(
            rebal_dates, 0.457, 0.433, rng
        )
        res_p = rotate_portfolio(mom, lot, rebal_dates, gm_p, gi_p)
        sm_p = summarize_rotation(res_p)
        placebo_metrics.append(dict(
            ls_full=sm_p["ls_full"],
            worst_year_ls=sm_p["worst_year_ls"],
            best_year_ls=sm_p["best_year_ls"],
            q5_full=sm_p["q5_full"],
            ls_maxdd=sm_p["ls_maxdd"],
            on_frac=sm_p["on_frac"],
        ))
        if (i + 1) % 20 == 0:
            print(f"  [{i+1}/{PLACEBO_N}] placebo done  {time.time()-t0:.1f}s")

    pl_df = pd.DataFrame(placebo_metrics)
    ls_p50 = pl_df["ls_full"].median()
    ls_p95 = pl_df["ls_full"].quantile(0.95)
    ls_p_value = float((pl_df["ls_full"] >= baseline_ls).mean())

    wy_p50 = pl_df["worst_year_ls"].median()
    wy_p95 = pl_df["worst_year_ls"].quantile(0.95)
    wy_p_value = float((pl_df["worst_year_ls"] >= baseline_worst).mean())

    print(f"\n  baseline LS full: {baseline_ls:.3f}")
    print(f"  placebo LS full:  median={ls_p50:.3f}  p95={ls_p95:.3f}  "
          f"max={pl_df['ls_full'].max():.3f}")
    print(f"  empirical p-value (placebo >= baseline LS): {ls_p_value:.3f}")
    print(f"\n  baseline worst-year LS: {baseline_worst:.3f}")
    print(f"  placebo worst-year LS: median={wy_p50:.3f}  p95={wy_p95:.3f}  "
          f"max={pl_df['worst_year_ls'].max():.3f}")
    print(f"  empirical p-value (placebo >= baseline worst-yr): {wy_p_value:.3f}")

    # --------------------------------------------------------------- #
    # Output                                                          #
    # --------------------------------------------------------------- #
    out = dict(
        experiment="rotation_round6_falsification",
        cost_bps_per_side=COST_BPS, rebalance_days=REBAL,
        placebo_n=PLACEBO_N, placebo_seed=PLACEBO_SEED,
        baseline_gate_mom_frac=spec_results[0]["gate_mom_frac"],
        baseline_gate_inv_frac=spec_results[0]["gate_inv_frac"],
        spec_sensitivity=spec_results,
        spec_pass_count=n_pass_spec,
        spec_total=len(specs),
        placebo=dict(
            baseline_ls_full=baseline_ls,
            baseline_worst_year_ls=baseline_worst,
            placebo_ls_full_median=float(ls_p50),
            placebo_ls_full_p95=float(ls_p95),
            placebo_ls_full_max=float(pl_df["ls_full"].max()),
            placebo_ls_full_p_value=ls_p_value,
            placebo_worst_year_median=float(wy_p50),
            placebo_worst_year_p95=float(wy_p95),
            placebo_worst_year_max=float(pl_df["worst_year_ls"].max()),
            placebo_worst_year_p_value=wy_p_value,
            raw=placebo_metrics,
        ),
    )
    out_json = OUT_DIR / "rotation_round6_falsification.json"
    with open(out_json, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\n[r6] wrote {out_json}")
    print(f"[r6] done {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
