"""
Follow-on #2: MOM ↔ Lottery dispersion-regime rotation.

Follow-on #1 established dispersion gate is momentum-specific. But the two
gates (MOM: disp>med, INV: disp<med) are nearly complementary in coverage
(~43% each). A natural composite strategy:

    if gate_mom(t):  use α_35 (idio 12-3 momentum × MOM-gate)
    elif gate_inv(t): use α_17 (lottery × INV-gate)
    else:            cash  (rare boundary, disp ≈ med)

This keeps capital deployed year-round — α_35 is fully cash in 2018 while
α_17 INV has its best year (1.72) in 2018. Question: does rotation pass
worst-year audit that neither leg passes alone?

Four strategies compared:
  S1 MOM-only   = α_35 baseline (DEPLOYED today)
  S2 INV-only   = α_17 × INV-gate (follow-on #1b)
  S3 Rotation   = regime-switching composite above
  S4 Static50/50 = 0.5 α_35_LS + 0.5 α_17_LS (ungated, diversification baseline)
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

# Allow importing the deployed factor's build_factor()
sys.path.insert(0, str(ROOT / "factors/price_volume/idio_12_3_momentum_disp_gated_v1"))
from code import FactorConfig, build_factor  # noqa: E402

COST_BPS = 5
REBAL = 20
TRAIN_END = pd.Timestamp("2022-12-31")
VALID_END = pd.Timestamp("2023-12-31")


def industry_demean(df, col):
    return df[col] - df.groupby(["trade_date", "industry"])[col].transform("mean")


def perf(r, ppy=12):
    r = r.dropna()
    if len(r) < 2:
        return {"sharpe": np.nan, "ann": np.nan, "maxdd": np.nan}
    ann = r.mean() * ppy
    vol = r.std(ddof=0) * np.sqrt(ppy)
    eq = (1 + r).cumprod()
    return {"sharpe": ann / vol if vol > 0 else 0.0, "ann": ann,
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


# -------------------------------------------------------------------- #
# Rotation-aware portfolio construction                                #
# -------------------------------------------------------------------- #

def _quintile_ls(snap, alpha_col, ret_col):
    """One-period quintile LS; returns q5/q1/ls returns + holding sets."""
    snap = snap.copy()
    snap["q"] = pd.qcut(snap[alpha_col].rank(method="first"), 5,
                        labels=False, duplicates="drop")
    if snap["q"].isna().all():
        return None
    q5 = snap[snap["q"] == 4]; q1 = snap[snap["q"] == 0]
    return dict(
        q5_ret=q5[ret_col].mean(), q1_ret=q1[ret_col].mean(),
        all_ret=snap[ret_col].mean(),
        q5_set=set(q5["ts_code"]), q1_set=set(q1["ts_code"]),
    )


def rotate_portfolio(panel_mom, panel_lot, alpha_mom, alpha_lot, ret_col,
                     rebal_dates, gate_mom, gate_inv):
    """Regime-switching rotation: MOM-leg → INV-leg → cash at each rebal.
    Turnover is charged for full-portfolio replacement when active leg changes."""
    rows = []
    prev_leg = "cash"; prev_q5 = set(); prev_q1 = set()

    pmom = panel_mom[["trade_date", "ts_code", alpha_mom, ret_col]].dropna()
    plot = panel_lot[["trade_date", "ts_code", alpha_lot, ret_col]].dropna()

    for t in rebal_dates:
        gm = int(gate_mom.get(t, 0))
        gi = int(gate_inv.get(t, 0))

        if gm == 1:
            leg = "mom"; snap = pmom[pmom["trade_date"] == t]; acol = alpha_mom
        elif gi == 1:
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

        # Leg-aware turnover
        if leg == prev_leg and prev_q5:
            tov_q5 = 1.0 - len(res["q5_set"] & prev_q5) / max(len(res["q5_set"]), 1)
            tov_q1 = 1.0 - len(res["q1_set"] & prev_q1) / max(len(res["q1_set"]), 1)
        else:
            tov_q5 = 1.0; tov_q1 = 1.0  # full rebuild: cross-leg switch or open from cash

        rows.append(dict(
            trade_date=t, leg=leg, q5=res["q5_ret"], q1=res["q1_ret"],
            ls=res["q5_ret"] - res["q1_ret"], all=res["all_ret"],
            tov_q5=tov_q5, tov_q1=tov_q1,
        ))
        prev_leg = leg; prev_q5 = res["q5_set"]; prev_q1 = res["q1_set"]

    return pd.DataFrame(rows)


def single_leg_portfolio(panel, alpha_col, ret_col, rebal_dates, gate):
    """Single-alpha gated LS (matches script 10 quintile_portfolios_gated, kept
    self-contained for consistent turnover accounting with rotation)."""
    rows = []
    prev_q5 = set(); prev_q1 = set(); prev_on = 0
    panel_l = panel[["trade_date", "ts_code", alpha_col, ret_col]].dropna()

    for t in rebal_dates:
        g = int(gate.get(t, 0))
        if g == 0:
            tov_q5 = 1.0 if prev_on == 1 and prev_q5 else 0.0
            tov_q1 = 1.0 if prev_on == 1 and prev_q1 else 0.0
            rows.append(dict(trade_date=t, ls=0.0, q5=0.0, q1=0.0, all=0.0,
                             tov_q5=tov_q5, tov_q1=tov_q1, on=0))
            prev_on = 0; prev_q5 = set(); prev_q1 = set()
            continue
        snap = panel_l[panel_l["trade_date"] == t]
        if len(snap) < 100:
            rows.append(dict(trade_date=t, ls=0.0, q5=0.0, q1=0.0, all=0.0,
                             tov_q5=0.0, tov_q1=0.0, on=0))
            prev_on = 0
            continue
        res = _quintile_ls(snap, alpha_col, ret_col)
        if res is None:
            continue
        if prev_on == 1 and prev_q5:
            tov_q5 = 1.0 - len(res["q5_set"] & prev_q5) / max(len(res["q5_set"]), 1)
            tov_q1 = 1.0 - len(res["q1_set"] & prev_q1) / max(len(res["q1_set"]), 1)
        else:
            tov_q5 = 1.0; tov_q1 = 1.0
        rows.append(dict(
            trade_date=t, q5=res["q5_ret"], q1=res["q1_ret"],
            ls=res["q5_ret"] - res["q1_ret"], all=res["all_ret"],
            tov_q5=tov_q5, tov_q1=tov_q1, on=1,
        ))
        prev_q5 = res["q5_set"]; prev_q1 = res["q1_set"]; prev_on = 1
    return pd.DataFrame(rows)


# -------------------------------------------------------------------- #
# Reporting                                                            #
# -------------------------------------------------------------------- #

def summarize(res, name, cost_bps=COST_BPS):
    res = res.copy()
    if "on" not in res.columns and "leg" in res.columns:
        res["on"] = (res["leg"] != "cash").astype(int)
    res["ls_after"] = res["ls"] - (res["tov_q5"] + res["tov_q1"]) * cost_bps / 1e4
    res["q5_excess_after"] = (res["q5"] - res["all"]) - res["tov_q5"] * cost_bps / 1e4
    full = perf(res["ls_after"])
    full_q5 = perf(res["q5_excess_after"])
    train = res[res.index <= TRAIN_END]
    valid = res[(res.index > TRAIN_END) & (res.index <= VALID_END)]
    test = res[res.index > VALID_END]
    py_ls = per_year_active(res["ls_after"])
    py_q5 = per_year_active(res["q5_excess_after"])
    return dict(
        name=name,
        ls_full=full["sharpe"], ls_ann=full["ann"], ls_maxdd=full["maxdd"],
        ls_train=perf(train["ls_after"])["sharpe"],
        ls_valid=perf(valid["ls_after"])["sharpe"],
        ls_test=perf(test["ls_after"])["sharpe"],
        q5_full=full_q5["sharpe"],
        q5_train=perf(train["q5_excess_after"])["sharpe"],
        q5_valid=perf(valid["q5_excess_after"])["sharpe"],
        q5_test=perf(test["q5_excess_after"])["sharpe"],
        worst_year_ls=min(py_ls.values()) if py_ls else np.nan,
        best_year_ls=max(py_ls.values()) if py_ls else np.nan,
        worst_year_q5=min(py_q5.values()) if py_q5 else np.nan,
        on_frac=float(res["on"].mean()),
        per_year_ls=py_ls, per_year_q5=py_q5,
        avg_cost_bps=float((res["tov_q5"] + res["tov_q1"]).mean() * cost_bps),
    )


# -------------------------------------------------------------------- #
# Main                                                                 #
# -------------------------------------------------------------------- #

def main():
    t0 = time.time()
    print("[fu2] building momentum panel via deployed factor code...")
    mom = build_factor(FactorConfig())
    mom = mom[["ts_code", "trade_date", "industry", "alpha_n"]].copy()
    # Build fwd_ret_20 on the momentum panel from cached daily
    print(f"[fu2] momentum panel: {len(mom):,} rows  {time.time()-t0:.1f}s")

    print("[fu2] loading lottery α_17 panel...")
    lot = pd.read_parquet(LOT / "outputs/panel_round3.parquet",
                          columns=["ts_code", "trade_date", "industry",
                                   "alpha_17", "fwd_ret_20"])
    lot["trade_date"] = pd.to_datetime(lot["trade_date"])
    lot = lot.dropna(subset=["industry"])
    lot["alpha_17_n"] = industry_demean(lot, "alpha_17")
    print(f"[fu2] lottery panel: {len(lot):,} rows  {time.time()-t0:.1f}s")

    # fwd_ret_20 for momentum panel: reuse from lottery panel keyed by (ts_code, trade_date)
    # (Both panels cover the same A-share universe with identical conventions.)
    fwd = lot[["ts_code", "trade_date", "fwd_ret_20"]]
    mom = mom.merge(fwd, on=["ts_code", "trade_date"], how="inner")
    print(f"[fu2] momentum panel after fwd merge: {len(mom):,} rows  {time.time()-t0:.1f}s")

    # Build dispersion gates from daily cache
    print("[fu2] building dispersion gates...")
    daily = pd.read_parquet(CACHE / "daily.parquet").merge(
        pd.read_parquet(CACHE / "adj_factor.parquet"),
        on=["ts_code", "trade_date"], how="left"
    )
    daily["adj_factor"] = daily["adj_factor"].fillna(1.0)
    daily["P"] = daily["close"] * daily["adj_factor"]
    daily = daily.sort_values(["ts_code", "trade_date"]).reset_index(drop=True)
    daily["trade_date"] = pd.to_datetime(daily["trade_date"])
    daily["ret"] = daily.groupby("ts_code")["P"].transform(lambda s: np.log(s).diff())
    daily["ret_20"] = daily.groupby("ts_code")["ret"].transform(
        lambda s: s.rolling(20, min_periods=15).sum()
    )
    disp = daily.groupby("trade_date")["ret_20"].std()
    disp_med = disp.rolling(252, min_periods=180).median()
    gate_mom = (disp > disp_med).astype(int)
    gate_inv = (disp < disp_med).astype(int).where(~disp_med.isna(), 0)
    print(f"[fu2] gate_mom on-frac = {gate_mom.mean():.3f}, "
          f"gate_inv on-frac = {gate_inv.mean():.3f}, "
          f"both-off = {((gate_mom == 0) & (gate_inv == 0)).mean():.3f}")

    # Common rebalance grid from the intersection of panels
    common_dates = pd.Index(sorted(set(mom["trade_date"]) & set(lot["trade_date"])))
    rebal_dates = common_dates[::REBAL]
    print(f"[fu2] rebalance dates: {len(rebal_dates)}  "
          f"[{rebal_dates[0].date()} → {rebal_dates[-1].date()}]")

    # -- S1: MOM-only (α_35 baseline) --
    print("[fu2] S1 MOM-only (α_35 baseline)...")
    s1 = single_leg_portfolio(mom, "alpha_n", "fwd_ret_20", rebal_dates, gate_mom)
    s1 = s1.set_index("trade_date").sort_index()

    # -- S2: INV-only (α_17 × INV-gate) --
    print("[fu2] S2 INV-only (α_17 × INV-gate)...")
    s2 = single_leg_portfolio(lot, "alpha_17_n", "fwd_ret_20", rebal_dates, gate_inv)
    s2 = s2.set_index("trade_date").sort_index()

    # -- S3: Rotation --
    print("[fu2] S3 rotation (MOM→INV→cash)...")
    s3 = rotate_portfolio(mom, lot, "alpha_n", "alpha_17_n",
                          "fwd_ret_20", rebal_dates, gate_mom, gate_inv)
    s3 = s3.set_index("trade_date").sort_index()

    # -- S4: Static 50/50 (both ungated, always on) --
    print("[fu2] S4 static 50/50 (ungated)...")
    always_on = pd.Series(1, index=common_dates)
    mom_u = single_leg_portfolio(mom, "alpha_n", "fwd_ret_20", rebal_dates, always_on)
    lot_u = single_leg_portfolio(lot, "alpha_17_n", "fwd_ret_20", rebal_dates, always_on)
    mom_u = mom_u.set_index("trade_date").sort_index()
    lot_u = lot_u.set_index("trade_date").sort_index()
    s4 = pd.DataFrame(index=mom_u.index)
    s4["ls"] = 0.5 * mom_u["ls"] + 0.5 * lot_u["ls"]
    s4["q5"] = 0.5 * mom_u["q5"] + 0.5 * lot_u["q5"]
    s4["q1"] = 0.5 * mom_u["q1"] + 0.5 * lot_u["q1"]
    s4["all"] = 0.5 * mom_u["all"] + 0.5 * lot_u["all"]
    # Turnover: 0.5× each leg's turnover (independent legs)
    s4["tov_q5"] = 0.5 * mom_u["tov_q5"] + 0.5 * lot_u["tov_q5"]
    s4["tov_q1"] = 0.5 * mom_u["tov_q1"] + 0.5 * lot_u["tov_q1"]
    s4["on"] = 1

    S1 = summarize(s1, "S1 MOM-only (α_35)")
    S2 = summarize(s2, "S2 INV-only (α_17·INV)")
    S3 = summarize(s3, "S3 Rotation")
    S4 = summarize(s4, "S4 Static 50/50")

    print("\n" + "=" * 92)
    print("MOM ↔ Lottery rotation comparison")
    print("=" * 92)
    fmt = lambda v: f"{v:>7.3f}" if isinstance(v, float) and not np.isnan(v) else f"{'NA':>7}"
    metrics = ["ls_full", "ls_train", "ls_valid", "ls_test",
               "q5_full", "q5_test", "ls_maxdd",
               "worst_year_ls", "best_year_ls", "worst_year_q5",
               "on_frac", "avg_cost_bps"]
    print(f"{'metric':<18} {'S1 MOM':>10} {'S2 INV':>10} {'S3 ROT':>10} {'S4 50/50':>10}")
    for m in metrics:
        print(f"  {m:<16} {fmt(S1[m])} {fmt(S2[m])} {fmt(S3[m])} {fmt(S4[m])}")

    print("\nPer-year LS Sharpe:")
    years = sorted(set(list(S1["per_year_ls"].keys()) +
                       list(S2["per_year_ls"].keys()) +
                       list(S3["per_year_ls"].keys()) +
                       list(S4["per_year_ls"].keys())))
    print(f"{'year':<6} {'S1 MOM':>10} {'S2 INV':>10} {'S3 ROT':>10} {'S4 50/50':>10}")
    for y in years:
        def v(dic):
            x = dic["per_year_ls"].get(y, np.nan)
            if isinstance(x, float) and np.isnan(x): return f"{'cash':>10}"
            return f"{x:>10.3f}"
        print(f"  {y:<4} {v(S1)} {v(S2)} {v(S3)} {v(S4)}")

    # Audit verdict for S3
    audit = dict(
        worst_year_floor_05=bool(S3["worst_year_ls"] >= 0.5),
        best_year_out_50pct=bool(S3["best_year_ls"] <= 2 * S3["ls_full"]) if S3["ls_full"] > 0 else False,
        headline_sharpe_12=bool(S3["ls_full"] >= 1.2),
        q5_ir_1=bool(S3["q5_full"] >= 1.0),
    )
    print(f"\n[fu2] S3 audit: {audit}")

    out_json = OUT_DIR / "followup_mom_lottery_rotation.json"
    out = dict(
        experiment="follow_on_2_mom_lottery_rotation",
        hypothesis=("dispersion-regime rotation between α_35 (MOM-gate ON) "
                    "and α_17·INV (INV-gate ON) keeps capital deployed "
                    "year-round and passes the worst-year audit that "
                    "neither leg satisfies alone."),
        gate_mom_on_frac=float(gate_mom.mean()),
        gate_inv_on_frac=float(gate_inv.mean()),
        both_off_frac=float(((gate_mom == 0) & (gate_inv == 0)).mean()),
        cost_bps_per_side=COST_BPS,
        rebalance_days=REBAL,
        S1_MOM_only=S1,
        S2_INV_only=S2,
        S3_Rotation=S3,
        S4_Static_50_50=S4,
        S3_audit=audit,
    )
    with open(out_json, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"[fu2] wrote {out_json}")

    # Save rebalance tape for S3 (for debugging / report inclusion)
    s3_tape = s3.copy()
    s3_tape["ls_after"] = s3_tape["ls"] - (s3_tape["tov_q5"] + s3_tape["tov_q1"]) * COST_BPS / 1e4
    tape_csv = OUT_DIR / "followup_mom_lottery_rotation_tape.csv"
    s3_tape.to_csv(tape_csv)
    print(f"[fu2] wrote {tape_csv}")
    print(f"[fu2] done {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
