"""
Final audit + placebo for winning overlay.

Winner from round 3:
  signal = size_q5q1_12m_sh (daily returns of top-size-quintile minus
           bottom-size-quintile; trailing 252d Sharpe)
  lookback = 63 trade days for gate threshold
  percentile = 97 (α_17 ON only when size_q5q1_12m_sh < 97th percentile
                   of its 63d rolling distribution)
  fallback = benchmark (hold universe Q1..Q5 equal-weight when gate OFF)

Audit checklist (7):
  1. Full-sample excess IR ≥ 1.0
  2. Worst-year excess IR ≥ 0.5
  3. Best-year-out Sharpe ≥ 50% × full
  4. Spec sensitivity — ≥ 4/8 variants pass
  5. Placebo excess IR p < 0.05
  6. Placebo worst-year p < 0.05
  7. Excess MaxDD > −10%

Also checks:
  - Execution delay (inherited: α_17 panel uses target_shift=-2, delay=1)
  - Look-ahead (inherited: trailing rolling median for all signals)
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
PLACEBO_N = 100
PLACEBO_SEED = 20260422

# Winner spec
WIN_SIGNAL = "size_q5q1_12m_sh"
WIN_LOOKBACK = 63
WIN_PCT = 97


def industry_demean(df, col):
    return df[col] - df.groupby(["trade_date", "industry"])[col].transform("mean")


def perf(r, ppy=12):
    r = r.dropna()
    if len(r) < 2:
        return {"sharpe": np.nan, "ann": np.nan, "maxdd": np.nan}
    ann = r.mean() * ppy; vol = r.std(ddof=0) * np.sqrt(ppy)
    eq = (1 + r).cumprod()
    return {"sharpe": ann / vol if vol > 0 else 0.0, "ann": float(ann),
            "maxdd": float((eq / eq.cummax() - 1).min())}


def per_year_ir(r):
    r = r.dropna(); out = {}
    for y in sorted(set(r.index.year)):
        rr = r[r.index.year == y]
        if len(rr) < 6: continue
        v = rr.std(ddof=0)
        out[int(y)] = float((rr.mean() * 12) / (v * np.sqrt(12))) if v > 0 else 0.0
    return out


def make_gate_pct(signal, percentile, lookback):
    mp = max(int(lookback * 0.7), 20)
    threshold = signal.rolling(lookback, min_periods=mp).quantile(percentile / 100.0)
    return (signal < threshold).astype(int).where(~threshold.isna(), 0)


def q5_long_only(panel, alpha_col, ret_col, rebal_dates, gate_series,
                 top_pct=0.20, cost_bps=COST_BPS):
    rows = []; prev_set = set(); prev_state = 0
    panel_l = panel[["trade_date", "ts_code", alpha_col, ret_col]].dropna()
    gate_dict = gate_series.to_dict() if hasattr(gate_series, 'to_dict') else dict(zip(gate_series.index, gate_series.values))
    for t in rebal_dates:
        g = int(gate_dict.get(t, 0))
        snap = panel_l[panel_l["trade_date"] == t]
        if len(snap) < 100: continue
        uni_mean = snap[ret_col].mean()
        if g == 0:
            tov = 1.0 if prev_state == 1 and prev_set else 0.0
            rows.append(dict(trade_date=t, gate=0, abs_ret=uni_mean, exc_ret=0.0,
                             uni=uni_mean, tov=tov, cost=tov * cost_bps / 1e4))
            prev_state = 0; prev_set = set(); continue
        snap_s = snap.sort_values(alpha_col, ascending=False)
        k = max(int(len(snap_s) * top_pct), 20)
        top = snap_s.head(k); cur_set = set(top["ts_code"])
        mean_ret = top[ret_col].mean()
        tov = (1.0 - len(cur_set & prev_set) / max(len(cur_set), 1)) if (prev_state == 1 and prev_set) else 1.0
        rows.append(dict(trade_date=t, gate=1, abs_ret=mean_ret,
                         exc_ret=mean_ret - uni_mean, uni=uni_mean,
                         tov=tov, cost=tov * cost_bps / 1e4))
        prev_state = 1; prev_set = cur_set
    df = pd.DataFrame(rows).set_index("trade_date").sort_index()
    df["abs_net"] = df["abs_ret"] - df["cost"]
    df["exc_net"] = df["exc_ret"] - df["cost"]
    return df


def summarize(df):
    abs_p = perf(df["abs_net"]); exc_p = perf(df["exc_net"])
    py_exc = per_year_ir(df["exc_net"])
    train = df[df.index <= TRAIN_END]; valid = df[(df.index > TRAIN_END) & (df.index <= VALID_END)]
    test = df[df.index > VALID_END]
    return dict(
        abs_ann=abs_p["ann"], abs_sharpe=abs_p["sharpe"], abs_maxdd=abs_p["maxdd"],
        exc_ann=exc_p["ann"], exc_ir=exc_p["sharpe"], exc_maxdd=exc_p["maxdd"],
        exc_train_ir=perf(train["exc_net"])["sharpe"],
        exc_valid_ir=perf(valid["exc_net"])["sharpe"],
        exc_test_ir=perf(test["exc_net"])["sharpe"],
        abs_test_sharpe=perf(test["abs_net"])["sharpe"],
        worst_year_exc=min(py_exc.values()) if py_exc else np.nan,
        best_year_exc=max(py_exc.values()) if py_exc else np.nan,
        per_year_exc=py_exc,
        on_frac=float(df["gate"].mean()),
        avg_tov=float(df["tov"].mean()),
        avg_cost_bps=float(df["cost"].mean() * 1e4),
    )


def main():
    t0 = time.time()
    print("[audit] loading panels + features...")
    lot = pd.read_parquet(LOT / "outputs/panel_round3.parquet",
                          columns=["ts_code", "trade_date", "industry",
                                   "alpha_17", "fwd_ret_20"])
    lot["trade_date"] = pd.to_datetime(lot["trade_date"])
    lot = lot.dropna(subset=["industry"])
    lot["alpha_17_n"] = industry_demean(lot, "alpha_17")
    feats = pd.read_parquet(OUT_DIR / "megacap_features_r2.parquet")
    dates = pd.Index(sorted(lot["trade_date"].unique()))
    rebal_dates = dates[::REBAL]
    print(f"[audit] {len(rebal_dates)} rebalance dates  {time.time()-t0:.1f}s")

    # ---------------- BASELINE with winning gate ----------------
    sig = feats[WIN_SIGNAL].dropna()
    gate = make_gate_pct(sig, WIN_PCT, WIN_LOOKBACK)
    df_win = q5_long_only(lot, "alpha_17_n", "fwd_ret_20", rebal_dates, gate)
    S = summarize(df_win)
    print("\n" + "=" * 95)
    print(f"WINNING SPEC: {WIN_SIGNAL} | pct{WIN_PCT} | lb={WIN_LOOKBACK}")
    print("=" * 95)
    for k in ["abs_ann","abs_sharpe","abs_maxdd","exc_ann","exc_ir","exc_maxdd",
              "exc_train_ir","exc_valid_ir","exc_test_ir",
              "worst_year_exc","best_year_exc","on_frac","avg_tov","avg_cost_bps"]:
        v = S[k]
        print(f"  {k:<22} {'{:>+9.4f}'.format(v) if isinstance(v,float) and not np.isnan(v) else 'NA':>14}")
    print(f"\n  per-year excess IR:")
    for y, v in sorted(S["per_year_exc"].items()):
        print(f"    {y}: {v:>+6.3f}")

    # ---------------- SPEC SENSITIVITY ----------------
    print("\n" + "=" * 95)
    print("Spec sensitivity — neighborhood of winner")
    print("=" * 95)
    specs = [
        dict(lb=50, pct=97),
        dict(lb=75, pct=97),
        dict(lb=90, pct=97),
        dict(lb=63, pct=95),
        dict(lb=63, pct=96),
        dict(lb=63, pct=98),
        dict(lb=63, pct=99),
        dict(lb=63, pct=97),  # winner itself
    ]
    print(f"  {'lb':>4} {'pct':>4} {'full_IR':>8} {'worst':>7} {'2020':>7} {'2025':>7} "
          f"{'train':>6} {'valid':>6} {'test':>6} {'on_fr':>6} {'PASS':>5}")
    spec_results = []
    for s in specs:
        g = make_gate_pct(sig, s["pct"], s["lb"])
        df = q5_long_only(lot, "alpha_17_n", "fwd_ret_20", rebal_dates, g)
        sm = summarize(df)
        passed = bool(sm["exc_ir"] >= 1.0 and sm["worst_year_exc"] >= 0.5)
        sm["passed"] = passed
        sm["spec"] = s
        spec_results.append(sm)
        print(f"  {s['lb']:>4} {s['pct']:>4} {sm['exc_ir']:>+8.3f} "
              f"{sm['worst_year_exc']:>+7.3f} {sm.get('per_year_exc',{}).get(2020,np.nan):>+7.3f} "
              f"{sm.get('per_year_exc',{}).get(2025,np.nan):>+7.3f} "
              f"{sm['exc_train_ir']:>+6.3f} {sm['exc_valid_ir']:>+6.3f} "
              f"{sm['exc_test_ir']:>+6.3f} {sm['on_frac']:>+6.3f} "
              f"{('PASS' if passed else 'FAIL'):>5}")
    n_pass_spec = sum(1 for s in spec_results if s["passed"])
    print(f"  {n_pass_spec}/{len(specs)} pass")

    # ---------------- PLACEBO ----------------
    print("\n" + "=" * 95)
    print(f"Placebo — {PLACEBO_N} random on/off gates at matched on_frac")
    print("=" * 95)
    rng = np.random.default_rng(PLACEBO_SEED)
    on_frac = S["on_frac"]
    placebo_rows = []
    for i in range(PLACEBO_N):
        # Random binary gate at matched rate
        u = rng.random(len(rebal_dates))
        g_p = pd.Series((u < on_frac).astype(int), index=rebal_dates)
        df_p = q5_long_only(lot, "alpha_17_n", "fwd_ret_20", rebal_dates, g_p)
        sm_p = summarize(df_p)
        placebo_rows.append(dict(
            exc_ir=sm_p["exc_ir"], worst_year=sm_p["worst_year_exc"],
            ir_2020=sm_p["per_year_exc"].get(2020, np.nan),
            on_frac=sm_p["on_frac"],
        ))
        if (i + 1) % 20 == 0:
            print(f"  [{i+1}/{PLACEBO_N}]  {time.time()-t0:.1f}s")

    pl = pd.DataFrame(placebo_rows)
    baseline_ir = S["exc_ir"]; baseline_worst = S["worst_year_exc"]
    baseline_2020 = S["per_year_exc"].get(2020, np.nan)
    p_ir = float((pl["exc_ir"] >= baseline_ir).mean())
    p_worst = float((pl["worst_year"] >= baseline_worst).mean())
    p_2020 = float((pl["ir_2020"] >= baseline_2020).mean())

    print(f"\n  baseline excess IR: {baseline_ir:.3f}")
    print(f"  placebo median IR: {pl['exc_ir'].median():.3f}, max: {pl['exc_ir'].max():.3f}")
    print(f"  p-value (placebo >= baseline IR): {p_ir:.3f}")
    print(f"\n  baseline worst-year: {baseline_worst:.3f}")
    print(f"  placebo worst-year median: {pl['worst_year'].median():.3f}, max: {pl['worst_year'].max():.3f}")
    print(f"  p-value (placebo >= baseline worst): {p_worst:.3f}")
    print(f"\n  baseline 2020 IR: {baseline_2020:.3f}")
    print(f"  placebo 2020 median: {pl['ir_2020'].median():.3f}, max: {pl['ir_2020'].max():.3f}")
    print(f"  p-value (placebo >= baseline 2020): {p_2020:.3f}")

    # ---------------- AUDIT CHECKLIST ----------------
    print("\n" + "=" * 95)
    print("Full 7-audit checklist")
    print("=" * 95)

    r = df_win["exc_net"]
    py = per_year_ir(r)
    best_y = max(py, key=py.get)
    r_no_best = r[r.index.year != best_y]
    full_ir = perf(r)["sharpe"]
    no_best_ir = perf(r_no_best)["sharpe"]

    audit = dict(
        rule_1_full_ir_1p0=bool(S["exc_ir"] >= 1.0),
        rule_2_worst_year_0p5=bool(S["worst_year_exc"] >= 0.5),
        rule_3_best_year_out_50pct=bool(no_best_ir >= 0.5 * full_ir),
        rule_4_spec_majority_pass=bool(n_pass_spec >= len(specs) // 2 + 1),
        rule_5_placebo_ir_p_le_05=bool(p_ir < 0.05),
        rule_6_placebo_worst_p_le_05=bool(p_worst < 0.05),
        rule_7_excess_maxdd_ok=bool(S["exc_maxdd"] > -0.10),
        best_year_dropped=int(best_y),
        ir_without_best_year=float(no_best_ir),
        ir_ratio_vs_full=float(no_best_ir / full_ir) if full_ir > 0 else np.nan,
    )

    for k, v in audit.items():
        print(f"  {k:<32} {v}")

    n_pass_audit = sum(1 for k, v in audit.items() if k.startswith("rule_") and v is True)
    total = sum(1 for k in audit if k.startswith("rule_"))
    print(f"\n[audit] AUDIT RESULT: {n_pass_audit}/{total}")

    if n_pass_audit == total:
        print("[audit] ✓ ALL AUDITS PASS — deployment candidate ready.")
    else:
        fails = [k for k, v in audit.items() if k.startswith("rule_") and v is False]
        print(f"[audit] ✗ FAILS: {fails}")

    # ---------------- OUTPUT ----------------
    out = dict(
        experiment="overlay_final_audit",
        spec=dict(signal=WIN_SIGNAL, lookback=WIN_LOOKBACK, percentile=WIN_PCT,
                  fallback="benchmark"),
        baseline=S,
        spec_sensitivity=spec_results,
        spec_pass_count=n_pass_spec, spec_total=len(specs),
        placebo=dict(
            baseline_ir=baseline_ir, baseline_worst=baseline_worst,
            baseline_2020=baseline_2020,
            placebo_ir_median=float(pl["exc_ir"].median()),
            placebo_ir_max=float(pl["exc_ir"].max()),
            placebo_ir_p_value=p_ir,
            placebo_worst_median=float(pl["worst_year"].median()),
            placebo_worst_max=float(pl["worst_year"].max()),
            placebo_worst_p_value=p_worst,
            placebo_2020_median=float(pl["ir_2020"].median()),
            placebo_2020_max=float(pl["ir_2020"].max()),
            placebo_2020_p_value=p_2020,
        ),
        audit=audit,
        audit_pass=n_pass_audit, audit_total=total,
        deploy_ready=(n_pass_audit == total),
    )
    out_json = OUT_DIR / "overlay_final_audit.json"
    with open(out_json, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\n[audit] wrote {out_json}")

    # Save baseline tape (for deployment)
    df_win.to_csv(OUT_DIR / "overlay_winning_tape.csv")
    print(f"[audit] wrote overlay_winning_tape.csv")
    print(f"[audit] done {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
