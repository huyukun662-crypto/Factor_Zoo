#!/usr/bin/env python3
"""IVOL-momentum R3 — universe expansion to 70 ETFs + cross-asset hedge variants.

Goal: rescue worst-year via (a) wider cross-section (b) bond-ETF overlays.

Universe: etf_daily_extended.parquet (70 ETFs).
Bond ETFs: 511010 国债 / 511220 城投债 / 511260 10年国债 / 511810 易方达国债
Cross-market: 159920 恒生 / 513050 中概 / 513100 纳指 / 513500 标普 / 513900 港股通
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, "/home/user/Factor_Zoo/logs/20260501_a_share_etf_ivol_momentum_v1/scripts")
m = __import__("02_backtest_ivol_momentum")

ROOT = Path("/home/user/Factor_Zoo/logs/20260501_a_share_etf_ivol_momentum_v1")
SHARED = Path("/home/user/Factor_Zoo/logs/_shared_cache")
OUT = ROOT / "outputs"

DELAY = 1
COST_BPS = 5.0
PRIMARY_K = 20
REBAL = 21
WORST_YEAR_FLOOR = 0.5
TRAIN_END = pd.Timestamp("2021-12-31")
VAL_END = pd.Timestamp("2022-12-31")
VOL_TARGET = 0.10
BENCH = "510300.SS"

BOND_ETFS = {"511010.SS", "511220.SS", "511260.SS", "511810.SS"}
CROSS_MARKET = {"159920.SZ", "513050.SS", "513100.SS", "513500.SS", "513900.SS"}
DEFENSIVE_BOND = "511010.SS"  # primary bond proxy for hedge


def load_panel():
    df = pd.read_parquet(SHARED / "etf_daily_extended.parquet")
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    # robust ret calculation per symbol
    df["ret"] = df.groupby("symbol")["close"].pct_change()
    return df


def to_wide(df, col):
    return df.pivot(index="date", columns="symbol", values=col).sort_index()


def compute_ivol(rets: pd.DataFrame, bench: pd.Series, beta_w: int = 60, ivol_w: int = 20):
    cov = rets.rolling(beta_w).cov(bench)
    var = bench.rolling(beta_w).var()
    beta = cov.div(var, axis=0)
    eps = rets.sub(beta.mul(bench, axis=0))
    return eps.rolling(ivol_w).std() * np.sqrt(252)


def fwd_ret(rets: pd.DataFrame, k: int):
    return rets.rolling(k).sum().shift(-(DELAY + k))


def quintile_LS(sig, fwd, n_q=5, restrict_short_to=None):
    """Long top quintile, short bottom quintile.
    restrict_short_to: optional list of symbols to allow in short leg (for bond-exclusion variants)."""
    rk = sig.rank(axis=1, pct=True)
    q_top = rk >= (n_q - 1) / n_q
    if restrict_short_to is not None:
        sig_short = sig[[c for c in sig.columns if c in restrict_short_to]]
        rk_short = sig_short.rank(axis=1, pct=True)
        q_bot = rk_short < 1 / n_q
        q_bot = q_bot.reindex(columns=sig.columns, fill_value=False)
    else:
        q_bot = rk < 1 / n_q
    n_top = q_top.sum(axis=1).replace(0, np.nan)
    n_bot = q_bot.sum(axis=1).replace(0, np.nan)
    long_ret = (q_top.astype(float).where(q_top) * fwd).sum(axis=1) / n_top
    short_ret = (q_bot.astype(float).where(q_bot) * fwd).sum(axis=1) / n_bot
    return {"ls": long_ret - short_ret, "longonly": long_ret,
            "rank": rk, "q5": q_top, "q1": q_bot}


def topn_long_only(sig: pd.DataFrame, fwd: pd.DataFrame, n: int):
    rk = sig.rank(axis=1, ascending=False, method="first")
    sel = (rk <= n).astype(float).where(rk.notna())
    longo = (sel * fwd).sum(axis=1) / sel.sum(axis=1).replace(0, np.nan)
    return {"longonly": longo, "selection": sel}


def vol_target_overlay(ret: pd.Series, k: int = PRIMARY_K, target: float = VOL_TARGET, w: int = 60, max_lev: float = 2.0):
    rv = ret.rolling(w).std() * np.sqrt(252 / k)
    expo = (target / rv).clip(upper=max_lev).shift(1)
    return ret * expo, expo


def bond_rotation_overlay(equity_ret: pd.Series, bond_ret: pd.Series, lookback_weeks: int = 12,
                           dd_threshold: float = -0.03):
    """When trailing 12-week (60d) cumulative return of equity_ret < threshold,
    switch to bond_ret. Otherwise hold equity_ret."""
    cum = equity_ret.rolling(lookback_weeks * 5).sum()  # 12 weeks ~= 60 trading days
    use_bond = (cum < dd_threshold).shift(1).fillna(False).astype(bool)
    out = equity_ret.where(~use_bond, bond_ret)
    return out, use_bond


def annualize_sharpe(s, k=PRIMARY_K):
    return m.annualize_sharpe(s, k)


def per_year(s, k=PRIMARY_K):
    return m.per_year_sharpe(s, k)


def main():
    panel = load_panel()
    rets = to_wide(panel, "ret")
    bench = rets[BENCH]
    fwd = fwd_ret(rets, PRIMARY_K)

    n_total = rets.shape[1]
    print(f"Total universe: {n_total} ETFs")
    print(f"Bond ETFs in universe: {sum(1 for s in BOND_ETFS if s in rets.columns)}")
    print(f"Cross-market: {sum(1 for s in CROSS_MARKET if s in rets.columns)}")

    sig = compute_ivol(rets, bench, 60, 20)

    # universe variants
    eq_only = sorted(set(rets.columns) - BOND_ETFS - CROSS_MARKET)
    rets_eq = rets[eq_only]
    sig_eq = compute_ivol(rets_eq, bench, 60, 20) if BENCH in eq_only else compute_ivol(rets_eq, bench, 60, 20)
    fwd_eq = fwd_ret(rets_eq, PRIMARY_K)

    print(f"Equity-only universe: {len(eq_only)}")

    # bond return series for overlays
    bond_close = rets[DEFENSIVE_BOND]  # this is daily ret of 511010
    bond_fwd = bond_close.rolling(PRIMARY_K).sum().shift(-(DELAY + PRIMARY_K))

    # Build expressions
    expressions = {}

    # E1 — vol-target LS, full 70 universe (R2 winner re-applied)
    res = quintile_LS(sig, fwd)
    vt_ret, vt_expo = vol_target_overlay(res["ls"])
    expressions["r3_vt_LS_70"] = {"ret": vt_ret, "type": "LS_vt", "exposure": vt_expo,
                                   "rank": res["rank"], "n_universe": n_total}

    # E2 — vol-target LS, equity-only ~60 (no bonds, no foreign equity)
    res = quintile_LS(sig_eq, fwd_eq)
    vt_ret, vt_expo = vol_target_overlay(res["ls"])
    expressions["r3_vt_LS_eq_only"] = {"ret": vt_ret, "type": "LS_vt", "exposure": vt_expo,
                                        "rank": res["rank"], "n_universe": len(eq_only)}

    # E3 — vol-target LS, all 70 but Q1 short restricted to non-bond
    non_bond = sorted(set(rets.columns) - BOND_ETFS)
    res = quintile_LS(sig, fwd, restrict_short_to=non_bond)
    vt_ret, vt_expo = vol_target_overlay(res["ls"])
    expressions["r3_vt_LS_70_q1_no_bonds"] = {"ret": vt_ret, "type": "LS_vt", "exposure": vt_expo,
                                                "rank": res["rank"], "n_universe": n_total}

    # E4 — long-only top-5, full 70
    t = topn_long_only(sig, fwd, 5)
    expressions["r3_top5_lo_70"] = {"ret": t["longonly"], "type": "topN", "n": 5,
                                     "selection": t["selection"], "n_universe": n_total}

    # E5 — long-only top-5 with bond rotation when DD < -3% over 12w
    t = topn_long_only(sig, fwd, 5)
    rot_ret, use_bond = bond_rotation_overlay(t["longonly"], bond_fwd, 12, -0.03)
    expressions["r3_top5_lo_bond_rotate"] = {"ret": rot_ret, "type": "topN_rotate", "n": 5,
                                              "selection": t["selection"], "use_bond_pct": float(use_bond.mean()),
                                              "n_universe": n_total}

    # E6 — 50/50 long-only top-5 + bond ETF (always-on ballast)
    t = topn_long_only(sig, fwd, 5)
    ballast = 0.5 * t["longonly"] + 0.5 * bond_fwd
    expressions["r3_top5_5050_bond_ballast"] = {"ret": ballast, "type": "topN_ballast", "n": 5,
                                                  "selection": t["selection"], "n_universe": n_total}

    # E7 — vol-target LS on 70, longer beta window (90d) for stability
    sig_90 = compute_ivol(rets, bench, 90, 20)
    res = quintile_LS(sig_90, fwd)
    vt_ret, vt_expo = vol_target_overlay(res["ls"])
    expressions["r3_vt_LS_70_beta90"] = {"ret": vt_ret, "type": "LS_vt", "exposure": vt_expo,
                                          "rank": res["rank"], "n_universe": n_total}

    # E8 — kitchen sink: vol-target LS on equity-only + bond rotation on the LS itself
    res = quintile_LS(sig_eq, fwd_eq)
    vt_ret, vt_expo = vol_target_overlay(res["ls"])
    rot_ret, _ = bond_rotation_overlay(vt_ret, bond_fwd, 12, -0.03)
    expressions["r3_kitchen_sink"] = {"ret": rot_ret, "type": "LS_vt_rotate", "exposure": vt_expo,
                                       "rank": res["rank"], "n_universe": len(eq_only)}

    # ---- evaluate ----
    rows, year_rows = [], []
    for fid, e in expressions.items():
        r = e["ret"]
        # cost drag
        if e["type"].startswith("topN"):
            drag = m.cost_drag_topn(e["selection"], COST_BPS, REBAL)
            if e["type"] == "topN_ballast":
                drag = drag * 0.5  # half exposure to equity leg
            elif e["type"] == "topN_rotate":
                # rotation between bond and equity: assume equal trading frequency on switch dates
                pass
        else:
            drag = m.cost_drag_LS(e["rank"], COST_BPS, REBAL)
            if "exposure" in e:
                drag = drag * e["exposure"].reindex(drag.index).fillna(1.0)
        r_net = r.sub(drag.reindex(r.index).fillna(0))

        sharpe = annualize_sharpe(r); sharpe_net = annualize_sharpe(r_net)

        def slc(s, lo, hi):
            return s[(s.index > lo) & (s.index <= hi)]
        s_train = annualize_sharpe(slc(r, pd.Timestamp("1900-01-01"), TRAIN_END))
        s_val   = annualize_sharpe(slc(r, TRAIN_END, VAL_END))
        s_test  = annualize_sharpe(slc(r, VAL_END, pd.Timestamp("2030-01-01")))

        # turnover
        if e["type"].startswith("topN"):
            to_yr = m.turnover_annualized_topn(e["selection"], REBAL) * 100
        else:
            to_yr = m.turnover_LS(e["rank"], REBAL) * 100
        if "exposure" in e:
            avg_exp = float(e["exposure"].mean())
        else:
            avg_exp = 1.0

        rows.append({"expr": fid, "type": e["type"], "n_universe": e["n_universe"],
                     "sharpe_gross": sharpe, "sharpe_net5bps": sharpe_net,
                     "sharpe_train": s_train, "sharpe_val": s_val, "sharpe_test": s_test,
                     "ann_turnover_pct": to_yr, "avg_exposure": avg_exp,
                     "n_days": int(r.dropna().shape[0])})
        ys = per_year(r)
        for y, sh in ys.items():
            year_rows.append({"expr": fid, "year": int(y), "sharpe": sh})

    pd.DataFrame(rows).to_csv(OUT / "r3_summary_batch_0003.csv", index=False)
    yr_df = pd.DataFrame(year_rows)
    yr_df.to_csv(OUT / "r3_per_year_batch_0003.csv", index=False)

    # floors
    floors = {}
    for fid in expressions:
        ys = yr_df[yr_df.expr == fid].sort_values("year")
        wy = float(ys.sharpe.min()) if len(ys) else float("nan")
        if len(ys) >= 2:
            best_y = ys.sharpe.idxmax()
            byo_avg = float(ys.drop(best_y).sharpe.mean())
        else:
            byo_avg = float("nan")
        sh = next(r for r in rows if r["expr"] == fid)["sharpe_gross"]
        floors[fid] = {"worst_year": wy, "byo_avg": byo_avg, "headline_sharpe": sh,
                       "wy_pass_0p5": (wy >= WORST_YEAR_FLOOR) if np.isfinite(wy) else False,
                       "byo_pass_50pct": (byo_avg >= 0.5 * sh) if np.isfinite(byo_avg) and np.isfinite(sh) and sh > 0 else False}
    with (OUT / "r3_floors_batch_0003.json").open("w") as f:
        json.dump(floors, f, indent=2)

    print()
    print("=== R3 SUMMARY ===")
    print(pd.DataFrame(rows).to_string(index=False))
    print()
    print("=== PER-YEAR ===")
    print(yr_df.pivot(index="expr", columns="year", values="sharpe").round(2).to_string())
    print()
    print("=== FLOORS ===")
    for fid in expressions:
        fl = floors[fid]
        print(f"{fid}: wy={fl['worst_year']:+.2f} pass={fl['wy_pass_0p5']} | byo={fl['byo_avg']:+.2f} | head={fl['headline_sharpe']:+.2f}")


if __name__ == "__main__":
    main()
