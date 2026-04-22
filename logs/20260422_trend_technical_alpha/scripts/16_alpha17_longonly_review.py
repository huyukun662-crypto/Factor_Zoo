"""
α_17 long-only deployment review — comprehensive audit.

α_17 = σ-bucket rank of α_08 (idio-MAX / lottery) from lottery session
round 3 (logs/20260421_volprice_max_lottery). Attribution (script 15) shows
α_17 Q5 ungated excess IR 1.29 full-sample / 1.56 in 2025 OOS, vs α_35 Q5
excess IR 0.34. Hypothesis: α_17 is deployable as a long-only index-
enhancement factor, even if LS rotation failed in 2025.

Audit suite:
  1) Baseline Q5 long-only backtest (industry-demeaned α_17, monthly,
     5 bps/side turnover-aware cost)
  2) Per-year + TVT split (Train ≤2022, Validate 2023, Test 2024-26YTD)
  3) Mandatory-audit checklist (7 items, see CLAUDE.md)
  4) Spec sensitivity — 8 variants on top-K, rebalance freq, industry
     demeaning, winsorization
  5) Placebo — 100 random top-20% portfolios at matched size
  6) Verdict + disposition recommendation

Outputs:
  outputs/alpha17_longonly_review.json
  outputs/alpha17_longonly_review.md
"""
from __future__ import annotations
import json, time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("/home/user/Factor_Zoo")
LOT = ROOT / "logs/20260421_volprice_max_lottery"
OUT_DIR = ROOT / "logs/20260422_trend_technical_alpha/outputs"

COST_BPS = 5
PLACEBO_N = 100
PLACEBO_SEED = 20260422
TRAIN_END = pd.Timestamp("2022-12-31")
VALID_END = pd.Timestamp("2023-12-31")


# ---------------------------------------------------------------- #
# Helpers                                                          #
# ---------------------------------------------------------------- #

def industry_demean(df, col):
    return df[col] - df.groupby(["trade_date", "industry"])[col].transform("mean")


def winsorize(s, lo=0.01, hi=0.99):
    l, h = s.quantile([lo, hi])
    return s.clip(l, h)


def perf(r, ppy=12):
    r = r.dropna()
    if len(r) < 2:
        return {"sharpe": np.nan, "ann": np.nan, "vol": np.nan, "maxdd": np.nan}
    ann = r.mean() * ppy
    vol = r.std(ddof=0) * np.sqrt(ppy)
    eq = (1 + r).cumprod()
    dd = float((eq / eq.cummax() - 1).min())
    return {"sharpe": ann / vol if vol > 0 else 0.0, "ann": float(ann),
            "vol": float(vol), "maxdd": dd}


def per_year_ir(r):
    r = r.dropna()
    out = {}
    for y in sorted(set(r.index.year)):
        rr = r[r.index.year == y]
        if len(rr) < 6:
            continue
        v = rr.std(ddof=0)
        out[int(y)] = float((rr.mean() * 12) / (v * np.sqrt(12))) if v > 0 else 0.0
    return out


def q5_long_only_backtest(panel, alpha_col, ret_col, rebal_dates,
                          top_k=None, top_pct=0.20, cost_bps=COST_BPS):
    """Long-only top-K (or top-pct) portfolio with turnover-aware cost.
    Returns DataFrame with per-rebal metrics.
    """
    rows = []
    prev_set = set()
    panel_l = panel[["trade_date", "ts_code", alpha_col, ret_col]].dropna()
    for t in rebal_dates:
        snap = panel_l[panel_l["trade_date"] == t]
        if len(snap) < 100:
            continue
        snap = snap.sort_values(alpha_col, ascending=False)
        k = top_k if top_k else max(int(len(snap) * top_pct), 20)
        top = snap.head(k)
        cur_set = set(top["ts_code"])
        if prev_set:
            tov = 1.0 - len(cur_set & prev_set) / max(len(cur_set), 1)
        else:
            tov = 1.0
        mean_ret = top[ret_col].mean()
        uni_mean = snap[ret_col].mean()
        rows.append(dict(
            trade_date=t, q5_ret=mean_ret, uni_ret=uni_mean,
            excess=mean_ret - uni_mean, tov=tov, n_stocks=k,
        ))
        prev_set = cur_set
    df = pd.DataFrame(rows).set_index("trade_date").sort_index()
    df["cost"] = df["tov"] * cost_bps / 1e4
    df["q5_net"] = df["q5_ret"] - df["cost"]
    df["excess_net"] = df["excess"] - df["cost"]
    return df


def random_placebo_backtest(panel, ret_col, rebal_dates, top_pct=0.20,
                             cost_bps=COST_BPS, rng=None):
    """Pick random top_pct at each rebal."""
    rows = []
    prev_set = set()
    panel_l = panel[["trade_date", "ts_code", ret_col]].dropna()
    for t in rebal_dates:
        snap = panel_l[panel_l["trade_date"] == t]
        if len(snap) < 100:
            continue
        k = max(int(len(snap) * top_pct), 20)
        idx = rng.choice(len(snap), size=k, replace=False)
        top = snap.iloc[idx]
        cur_set = set(top["ts_code"])
        if prev_set:
            tov = 1.0 - len(cur_set & prev_set) / max(len(cur_set), 1)
        else:
            tov = 1.0
        mean_ret = top[ret_col].mean()
        uni_mean = snap[ret_col].mean()
        rows.append(dict(trade_date=t, q5_ret=mean_ret, uni_ret=uni_mean,
                         excess=mean_ret - uni_mean, tov=tov))
        prev_set = cur_set
    df = pd.DataFrame(rows).set_index("trade_date").sort_index()
    df["cost"] = df["tov"] * cost_bps / 1e4
    df["q5_net"] = df["q5_ret"] - df["cost"]
    df["excess_net"] = df["excess"] - df["cost"]
    return df


def summarize(df, name):
    abs_perf = perf(df["q5_net"])
    exc_perf = perf(df["excess_net"])
    py_abs = per_year_ir(df["q5_net"])
    py_exc = per_year_ir(df["excess_net"])
    train = df[df.index <= TRAIN_END]
    valid = df[(df.index > TRAIN_END) & (df.index <= VALID_END)]
    test = df[df.index > VALID_END]
    return dict(
        name=name,
        abs_ann=abs_perf["ann"], abs_sharpe=abs_perf["sharpe"], abs_maxdd=abs_perf["maxdd"],
        exc_ann=exc_perf["ann"], exc_ir=exc_perf["sharpe"], exc_maxdd=exc_perf["maxdd"],
        exc_train_ir=perf(train["excess_net"])["sharpe"],
        exc_valid_ir=perf(valid["excess_net"])["sharpe"],
        exc_test_ir=perf(test["excess_net"])["sharpe"],
        abs_test_sharpe=perf(test["q5_net"])["sharpe"],
        worst_year_abs=min(py_abs.values()) if py_abs else np.nan,
        worst_year_exc=min(py_exc.values()) if py_exc else np.nan,
        best_year_exc=max(py_exc.values()) if py_exc else np.nan,
        avg_tov=float(df["tov"].mean()),
        avg_cost_bps=float(df["cost"].mean() * 1e4),
        per_year_exc=py_exc,
        per_year_abs=py_abs,
    )


# ---------------------------------------------------------------- #
# Main                                                              #
# ---------------------------------------------------------------- #

def main():
    t0 = time.time()
    print("[r] loading lottery α_17 panel (extended)...")
    lot = pd.read_parquet(LOT / "outputs/panel_round3.parquet",
                          columns=["ts_code", "trade_date", "industry",
                                   "alpha_17", "fwd_ret_20"])
    lot["trade_date"] = pd.to_datetime(lot["trade_date"])
    lot = lot.dropna(subset=["industry"])
    lot["alpha_17_n"] = industry_demean(lot, "alpha_17")
    lot["alpha_17_raw"] = lot["alpha_17"]
    # winsorized variant
    lot["alpha_17_wn"] = lot.groupby("trade_date")["alpha_17"].transform(winsorize)
    lot["alpha_17_wn_ind"] = industry_demean(lot, "alpha_17_wn")
    print(f"[r] α_17 rows={len(lot):,}  {time.time()-t0:.1f}s")

    dates = pd.Index(sorted(lot["trade_date"].unique()))

    # ---------------- baseline ----------------
    rebal20 = dates[::20]
    print(f"[r] baseline rebalance: {len(rebal20)} dates  "
          f"[{rebal20[0].date()} → {rebal20[-1].date()}]")
    base = q5_long_only_backtest(lot, "alpha_17_n", "fwd_ret_20", rebal20,
                                  top_pct=0.20, cost_bps=COST_BPS)
    S_base = summarize(base, "BASELINE (α_17_n industry-demeaned, top 20%, 20d rebal)")

    print("\n" + "=" * 95)
    print("Baseline: α_17 Q5 long-only")
    print("=" * 95)
    fmt = lambda k, v: f"  {k:<28} {'{:>+9.4f}'.format(v) if isinstance(v, float) and not np.isnan(v) else str(v)}"
    for k in ["abs_ann","abs_sharpe","abs_maxdd","exc_ann","exc_ir","exc_maxdd",
              "exc_train_ir","exc_valid_ir","exc_test_ir",
              "worst_year_exc","best_year_exc","avg_tov","avg_cost_bps"]:
        print(fmt(k, S_base[k]))

    print("\n  per-year excess IR:")
    for y, v in sorted(S_base["per_year_exc"].items()):
        print(f"    {y}: {v:>+6.3f}")

    # ---------------- spec sensitivity ----------------
    print("\n" + "=" * 95)
    print("Spec sensitivity")
    print("=" * 95)
    specs = [
        dict(name="top_10pct",          alpha="alpha_17_n", top_pct=0.10, rebal=20),
        dict(name="top_30pct",          alpha="alpha_17_n", top_pct=0.30, rebal=20),
        dict(name="top_50_stocks",      alpha="alpha_17_n", top_pct=None, top_k=50, rebal=20),
        dict(name="top_100_stocks",     alpha="alpha_17_n", top_pct=None, top_k=100, rebal=20),
        dict(name="rebal_10d",          alpha="alpha_17_n", top_pct=0.20, rebal=10),
        dict(name="rebal_40d",          alpha="alpha_17_n", top_pct=0.20, rebal=40),
        dict(name="no_industry_demean", alpha="alpha_17_raw", top_pct=0.20, rebal=20),
        dict(name="winsorized+ind",     alpha="alpha_17_wn_ind", top_pct=0.20, rebal=20),
    ]
    print(f"  {'variant':<22} {'abs_ann':>9} {'exc_ann':>9} {'exc_IR':>8} "
          f"{'worst_yr':>9} {'test_IR':>8} {'MaxDD':>9} {'PASS?':>7}")

    spec_results = [S_base.copy()]
    spec_results[0]["name"] = "BASELINE"
    spec_results[0]["passed"] = bool(S_base["exc_ir"] >= 1.0 and S_base["worst_year_exc"] >= 0.5)
    print(f"  {'BASELINE':<22} {S_base['abs_ann']*100:>+8.2f}% {S_base['exc_ann']*100:>+8.2f}% "
          f"{S_base['exc_ir']:>+8.3f} {S_base['worst_year_exc']:>+9.3f} "
          f"{S_base['exc_test_ir']:>+8.3f} {S_base['exc_maxdd']*100:>+8.2f}% "
          f"{'PASS' if spec_results[0]['passed'] else 'FAIL':>7}")

    for s in specs:
        rebal = dates[::s["rebal"]]
        df = q5_long_only_backtest(
            lot, s["alpha"], "fwd_ret_20", rebal,
            top_pct=s.get("top_pct"), top_k=s.get("top_k"), cost_bps=COST_BPS
        )
        sm = summarize(df, s["name"])
        sm["spec"] = s
        # For 10/40-day rebal, we run per-K-days so IR annualization is different
        # Use ppy = 12 * (20/rebal) for adjustment? No — q5_net is per-rebal return,
        # and we use 12 ppy throughout. That under/over-annualizes for non-20d rebal.
        # Recompute with correct ppy.
        ppy = 252 / s["rebal"]
        abs_p = perf(df["q5_net"], ppy=ppy)
        exc_p = perf(df["excess_net"], ppy=ppy)
        py_exc = {}
        for y in sorted(set(df.index.year)):
            rr = df["excess_net"][df.index.year == y]
            if len(rr) < 4:
                continue
            v = rr.std(ddof=0)
            py_exc[int(y)] = float((rr.mean() * ppy) / (v * np.sqrt(ppy))) if v > 0 else 0.0
        sm["abs_ann"] = abs_p["ann"]; sm["abs_sharpe"] = abs_p["sharpe"]; sm["abs_maxdd"] = abs_p["maxdd"]
        sm["exc_ann"] = exc_p["ann"]; sm["exc_ir"] = exc_p["sharpe"]; sm["exc_maxdd"] = exc_p["maxdd"]
        sm["worst_year_exc"] = min(py_exc.values()) if py_exc else np.nan
        sm["best_year_exc"] = max(py_exc.values()) if py_exc else np.nan
        sm["per_year_exc"] = py_exc
        test = df[df.index > VALID_END]
        sm["exc_test_ir"] = perf(test["excess_net"], ppy=ppy)["sharpe"]
        sm["passed"] = bool(sm["exc_ir"] >= 1.0 and sm["worst_year_exc"] >= 0.5)
        spec_results.append(sm)
        print(f"  {s['name']:<22} {sm['abs_ann']*100:>+8.2f}% {sm['exc_ann']*100:>+8.2f}% "
              f"{sm['exc_ir']:>+8.3f} {sm['worst_year_exc']:>+9.3f} "
              f"{sm['exc_test_ir']:>+8.3f} {sm['exc_maxdd']*100:>+8.2f}% "
              f"{'PASS' if sm['passed'] else 'FAIL':>7}")

    n_pass_spec = sum(1 for s in spec_results if s.get("passed"))
    print(f"\n  spec sensitivity: {n_pass_spec}/{len(spec_results)} pass")

    # ---------------- placebo ----------------
    print("\n" + "=" * 95)
    print(f"Placebo — {PLACEBO_N} random top-20% portfolios")
    print("=" * 95)
    rng = np.random.default_rng(PLACEBO_SEED)
    placebo_rows = []
    for i in range(PLACEBO_N):
        df_p = random_placebo_backtest(lot, "fwd_ret_20", rebal20, top_pct=0.20,
                                        cost_bps=COST_BPS, rng=rng)
        p = perf(df_p["excess_net"]); p_abs = perf(df_p["q5_net"])
        py = per_year_ir(df_p["excess_net"])
        placebo_rows.append(dict(
            exc_ann=p["ann"], exc_ir=p["sharpe"], exc_maxdd=p["maxdd"],
            abs_ann=p_abs["ann"], abs_sharpe=p_abs["sharpe"],
            worst_year_exc=min(py.values()) if py else np.nan,
        ))
        if (i + 1) % 20 == 0:
            print(f"  [{i+1}/{PLACEBO_N}] placebo done  {time.time()-t0:.1f}s")
    pl_df = pd.DataFrame(placebo_rows)

    baseline_exc_ir = S_base["exc_ir"]
    baseline_worst = S_base["worst_year_exc"]

    p_ir = float((pl_df["exc_ir"] >= baseline_exc_ir).mean())
    p_wy = float((pl_df["worst_year_exc"] >= baseline_worst).mean())

    print(f"\n  baseline excess IR: {baseline_exc_ir:.3f}")
    print(f"  placebo excess IR: median={pl_df['exc_ir'].median():.3f}  "
          f"p95={pl_df['exc_ir'].quantile(0.95):.3f}  max={pl_df['exc_ir'].max():.3f}")
    print(f"  p-value (placebo >= baseline excess IR): {p_ir:.3f}")
    print(f"\n  baseline worst-year excess: {baseline_worst:.3f}")
    print(f"  placebo worst-year: median={pl_df['worst_year_exc'].median():.3f}  "
          f"p95={pl_df['worst_year_exc'].quantile(0.95):.3f}  "
          f"max={pl_df['worst_year_exc'].max():.3f}")
    print(f"  p-value (placebo >= baseline worst-yr): {p_wy:.3f}")

    # ---------------- audit verdict ----------------
    print("\n" + "=" * 95)
    print("Full audit checklist")
    print("=" * 95)
    audit = dict(
        rule_1_full_ir_1p0   = bool(S_base["exc_ir"] >= 1.0),
        rule_2_worst_year_05 = bool(S_base["worst_year_exc"] >= 0.5),
        rule_3_best_year_out = None,  # compute below
        rule_4_spec_majority = bool(n_pass_spec >= len(spec_results) // 2 + 1),
        rule_5_placebo_ir_p  = bool(p_ir < 0.05),
        rule_6_placebo_wy_p  = bool(p_wy < 0.05),
        rule_7_maxdd_abs_20  = bool(S_base["exc_maxdd"] > -0.10),  # excess MaxDD
    )
    # best-year-out
    r = base["excess_net"].dropna()
    best_y = max(per_year_ir(r), key=per_year_ir(r).get)
    r_no_best = r[r.index.year != best_y]
    full_ir = perf(r)["sharpe"]
    no_best_ir = perf(r_no_best)["sharpe"]
    audit["rule_3_best_year_out"] = bool(no_best_ir >= 0.5 * full_ir)
    audit["best_year_dropped"] = int(best_y)
    audit["ir_without_best_year"] = float(no_best_ir)
    audit["ir_ratio_vs_full"] = float(no_best_ir / full_ir) if full_ir > 0 else np.nan

    for k, v in audit.items():
        print(f"  {k:<30}  {v}")

    n_pass_audit = sum(1 for k, v in audit.items() if k.startswith("rule_") and v is True)
    total_audit = sum(1 for k in audit if k.startswith("rule_"))
    print(f"\n  audit pass: {n_pass_audit}/{total_audit}")

    # ---------------- output ----------------
    out = dict(
        experiment="alpha17_longonly_deployment_review",
        sample_start="2018-01-23",
        sample_end=str(rebal20[-1].date()),
        n_rebal=len(rebal20),
        cost_bps=COST_BPS,
        baseline=S_base,
        spec_sensitivity=spec_results,
        spec_pass_count=n_pass_spec,
        placebo=dict(
            baseline_exc_ir=baseline_exc_ir,
            baseline_worst_year_exc=baseline_worst,
            placebo_exc_ir_median=float(pl_df["exc_ir"].median()),
            placebo_exc_ir_p95=float(pl_df["exc_ir"].quantile(0.95)),
            placebo_exc_ir_max=float(pl_df["exc_ir"].max()),
            placebo_exc_ir_p_value=p_ir,
            placebo_worst_year_median=float(pl_df["worst_year_exc"].median()),
            placebo_worst_year_max=float(pl_df["worst_year_exc"].max()),
            placebo_worst_year_p_value=p_wy,
        ),
        audit=audit,
        n_pass_audit=n_pass_audit,
        total_audit=total_audit,
    )
    out_json = OUT_DIR / "alpha17_longonly_review.json"
    with open(out_json, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\n[r] wrote {out_json}")
    # save baseline tape for deployment
    tape_csv = OUT_DIR / "alpha17_longonly_baseline_tape.csv"
    base.to_csv(tape_csv)
    print(f"[r] wrote {tape_csv}")
    print(f"[r] done {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
