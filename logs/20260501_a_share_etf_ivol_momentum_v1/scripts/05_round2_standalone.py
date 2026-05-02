#!/usr/bin/env python3
"""IVOL-momentum R2 — 8 expressions targeting standalone PROMOTE.

Round-1 best (m1 LS no-gate) had Sharpe 0.66 / worst-year 0.04. Round 1
MA50 gate didn't rescue 2024 because 2024 was a within-narrative collapse
during a broad-market up year.

R2 strategies target narrative-collapse detection directly:
- RS gate (thematic vs 510300 relative strength)
- Persistence filter (IVOL must be high for >= 2 of last 3 months)
- Vol-target (dynamic exposure scaling to 10% ann vol)
- Combinations
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, "/home/user/Factor_Zoo/logs/20260501_a_share_etf_ivol_momentum_v1/scripts")
m = __import__("02_backtest_ivol_momentum")

ROOT = Path("/home/user/Factor_Zoo/logs/20260501_a_share_etf_ivol_momentum_v1")
OUT = ROOT / "outputs"
WORK = ROOT / "working"

DELAY = 1
COST_BPS = 5.0
PRIMARY_K = 20
REBAL = 21
WORST_YEAR_FLOOR = 0.5
TRAIN_END = pd.Timestamp("2021-12-31")
VAL_END = pd.Timestamp("2022-12-31")
VOL_TARGET = 0.10  # 10% ann vol

# Identify thematic vs broad
BROAD = {"510300.SS", "510500.SS", "510050.SS", "159915.SZ", "510180.SS",
         "159949.SZ", "588000.SS", "588080.SS", "510880.SS"}
COMMODITY = {"518880.SS"}
# Thematic = everything else after dropping the 4 truncated tickers


def load_setup():
    panel = m.load_panel()
    rets = m.to_wide(panel, "ret")
    closes = m.to_wide(panel, "close")
    bench = rets[m.BENCH]
    bench_close = closes[m.BENCH]
    fwd = m.fwd_ret(rets, PRIMARY_K)
    sig = m.signal_ivol(rets, bench, m.BETA_W, m.IVOL_W, residualize=True, lag=0)
    return panel, rets, closes, bench, bench_close, fwd, sig


def gate_rs_thematic_vs_broad(rets: pd.DataFrame, win: int = 60) -> pd.Series:
    """Gate on when median(thematic ETF) cumulative return > 510300 cum return over win days."""
    thematic = [c for c in rets.columns if c not in BROAD and c not in COMMODITY]
    cum_t = rets[thematic].rolling(win).sum().median(axis=1)
    cum_b = rets["510300.SS"].rolling(win).sum()
    g = (cum_t > cum_b).astype(float)
    g[cum_t.isna() | cum_b.isna()] = np.nan
    return g


def gate_dispersion(sig: pd.DataFrame, lookback: int = 252) -> pd.Series:
    """Gate on when cross-sectional std of signal is above its rolling median.
    Captures narrative-divergence regimes."""
    disp = sig.std(axis=1)
    med = disp.rolling(lookback).median()
    g = (disp > med).astype(float)
    g[disp.isna() | med.isna()] = np.nan
    return g


def persistence_filter(sig: pd.DataFrame, top_q: float = 0.67,
                       n_required: int = 2, lookback_months: int = 3,
                       month_step: int = 21) -> pd.DataFrame:
    """Returns boolean mask: True if ETF was in top quantile (top_q) for >=
    n_required of the last lookback_months monthly observations."""
    rk = sig.rank(axis=1, pct=True)
    # sample at monthly frequency to avoid noise
    sample_dates = rk.index[::month_step]
    sample = rk.loc[sample_dates]
    in_top = (sample >= top_q).astype(int)
    # count over last lookback_months samples
    count = in_top.rolling(lookback_months).sum()
    mask_monthly = (count >= n_required)
    # broadcast to daily
    mask = mask_monthly.reindex(rk.index, method="ffill").fillna(False)
    return mask


def topn_with_mask(sig: pd.DataFrame, fwd: pd.DataFrame, n: int,
                   mask: pd.DataFrame | None = None) -> dict:
    """Top-N long-only with optional pre-filter mask."""
    if mask is not None:
        sig_f = sig.where(mask)
    else:
        sig_f = sig
    rk = sig_f.rank(axis=1, ascending=False, method="first")
    sel = (rk <= n).astype(float)
    sel[rk.isna()] = np.nan
    longo = (sel * fwd).sum(axis=1) / sel.sum(axis=1).replace(0, np.nan)
    return {"longonly": longo, "selection": sel}


def vol_target_overlay(ret_series: pd.Series, target_ann_vol: float = VOL_TARGET,
                       vol_window_days: int = 60, max_lev: float = 2.0) -> tuple[pd.Series, pd.Series]:
    """Scale daily-equivalent return to target ann vol. Returns (scaled_ret, exposure)."""
    daily_vol = ret_series.rolling(vol_window_days).std() * np.sqrt(252 / PRIMARY_K)
    exposure = (target_ann_vol / daily_vol).clip(upper=max_lev).shift(1)
    scaled = ret_series * exposure
    return scaled, exposure


def annualize_sharpe(s, k=PRIMARY_K):
    return m.annualize_sharpe(s, k)


def per_year(s, k=PRIMARY_K):
    return m.per_year_sharpe(s, k)


def main():
    panel, rets, closes, bench, bench_close, fwd, sig = load_setup()
    ew_universe = fwd.mean(axis=1)
    ma50 = m.regime_gate(bench_close, 50)

    # build R2 gates / filters
    rs_gate = gate_rs_thematic_vs_broad(rets, 60)
    disp_gate = gate_dispersion(sig, 252)
    persist_mask = persistence_filter(sig, top_q=0.67, n_required=2,
                                      lookback_months=3, month_step=21)

    # ---- 8 R2 expressions ----
    def make_topn(n: int, gates: list[pd.Series] | None = None,
                  pre_mask: pd.DataFrame | None = None) -> dict:
        t = topn_with_mask(sig, fwd, n, mask=pre_mask)
        out = t["longonly"]
        if gates:
            for g in gates:
                out = m.apply_gate(out, g)
        return {"longonly": out, "selection": t["selection"]}

    # m1 baseline (no gate, no filter)
    res_LS_baseline = m.quintile_LS(sig, fwd)

    expressions = {}

    # E1 — top-5 no gate (R1 m2 baseline for control)
    t = make_topn(5)
    expressions["r2_topN_no_gate"] = {"ret": t["longonly"], "sel": t["selection"], "type": "topN", "n": 5, "gates": None, "vol_target": False}

    # E2 — top-5 with RS gate (thematic > broad)
    t = make_topn(5, gates=[rs_gate])
    expressions["r2_topN_RS_gate"] = {"ret": t["longonly"], "sel": t["selection"], "type": "topN", "n": 5, "gates": ["rs"], "vol_target": False}

    # E3 — top-5 with dispersion gate
    t = make_topn(5, gates=[disp_gate])
    expressions["r2_topN_disp_gate"] = {"ret": t["longonly"], "sel": t["selection"], "type": "topN", "n": 5, "gates": ["disp"], "vol_target": False}

    # E4 — top-5 with persistence filter
    t = make_topn(5, pre_mask=persist_mask)
    expressions["r2_topN_persist"] = {"ret": t["longonly"], "sel": t["selection"], "type": "topN", "n": 5, "gates": None, "pre_filter": "persist", "vol_target": False}

    # E5 — top-5 with RS gate + persistence
    t = make_topn(5, gates=[rs_gate], pre_mask=persist_mask)
    expressions["r2_topN_RS_persist"] = {"ret": t["longonly"], "sel": t["selection"], "type": "topN", "n": 5, "gates": ["rs"], "pre_filter": "persist", "vol_target": False}

    # E6 — m1 LS baseline + 10% vol target
    ls_vt, ls_exp = vol_target_overlay(res_LS_baseline["ls"], VOL_TARGET, 60, 2.0)
    expressions["r2_LS_voltarget_10"] = {"ret": ls_vt, "sel": None, "type": "LS_vt", "exposure": ls_exp, "vol_target": True}

    # E7 — top-5 + RS gate + 10% vol target
    t = make_topn(5, gates=[rs_gate])
    vt_ret, vt_exp = vol_target_overlay(t["longonly"], VOL_TARGET, 60, 2.0)
    expressions["r2_topN_RS_voltarget"] = {"ret": vt_ret, "sel": t["selection"], "type": "topN_vt", "n": 5, "gates": ["rs"], "exposure": vt_exp, "vol_target": True}

    # E8 — kitchen sink: top-5 + RS gate + persistence + 10% vol target
    t = make_topn(5, gates=[rs_gate], pre_mask=persist_mask)
    vt_ret, vt_exp = vol_target_overlay(t["longonly"], VOL_TARGET, 60, 2.0)
    expressions["r2_kitchen_sink"] = {"ret": vt_ret, "sel": t["selection"], "type": "topN_vt", "n": 5, "gates": ["rs"], "pre_filter": "persist", "exposure": vt_exp, "vol_target": True}

    # ---- evaluate ----
    rows, year_rows, cost_rows = [], [], []
    for fid, e in expressions.items():
        r = e["ret"]
        # net Sharpe (cost approximated from underlying selection turnover)
        if e.get("sel") is not None:
            drag = m.cost_drag_topn(e["sel"], COST_BPS, REBAL)
            if "rs" in (e.get("gates") or []):
                g = rs_gate.reindex(drag.index).ffill().fillna(0)
                drag = drag * g
            r_net = r.sub(drag.reindex(r.index).fillna(0))
        else:
            # LS — use rank-based cost
            drag = m.cost_drag_LS(res_LS_baseline["rank"], COST_BPS, REBAL)
            if e.get("vol_target") and "exposure" in e:
                drag = drag * e["exposure"].reindex(drag.index).fillna(1.0)
            r_net = r.sub(drag.reindex(r.index).fillna(0))

        sharpe = annualize_sharpe(r)
        sharpe_net = annualize_sharpe(r_net)
        ex = (r - ew_universe) if e["type"].startswith("topN") else None
        sharpe_ex = annualize_sharpe(ex) if ex is not None else float("nan")

        def slc(s, lo, hi):
            return s[(s.index > lo) & (s.index <= hi)]
        s_train = annualize_sharpe(slc(r, pd.Timestamp("1900-01-01"), TRAIN_END))
        s_val   = annualize_sharpe(slc(r, TRAIN_END, VAL_END))
        s_test  = annualize_sharpe(slc(r, VAL_END, pd.Timestamp("2030-01-01")))

        # turnover
        if e.get("sel") is not None:
            to_yr = m.turnover_annualized_topn(e["sel"], REBAL) * 100
        else:
            to_yr = m.turnover_LS(res_LS_baseline["rank"], REBAL) * 100
        if e.get("vol_target") and "exposure" in e:
            avg_exp = float(e["exposure"].mean())
            to_yr_eff = to_yr * avg_exp
        else:
            avg_exp = 1.0
            to_yr_eff = to_yr

        rows.append({"expr": fid, "type": e["type"],
                     "sharpe_gross": sharpe, "sharpe_net5bps": sharpe_net,
                     "sharpe_excess": sharpe_ex,
                     "sharpe_train": s_train, "sharpe_val": s_val, "sharpe_test": s_test,
                     "ann_turnover_pct": to_yr_eff,
                     "avg_exposure": avg_exp,
                     "n_days": int(r.dropna().shape[0])})
        ys = per_year(r)
        for y, sh in ys.items():
            year_rows.append({"expr": fid, "year": int(y), "sharpe": sh})

        for c in (0, 2, 5, 10, 20):
            if e.get("sel") is not None:
                d = m.cost_drag_topn(e["sel"], c, REBAL)
            else:
                d = m.cost_drag_LS(res_LS_baseline["rank"], c, REBAL)
            if "rs" in (e.get("gates") or []) and e.get("sel") is not None:
                g = rs_gate.reindex(d.index).ffill().fillna(0)
                d = d * g
            if e.get("vol_target") and "exposure" in e:
                d = d * e["exposure"].reindex(d.index).fillna(1.0)
            cost_rows.append({"expr": fid, "cost_bps_per_side": c,
                              "sharpe_net": annualize_sharpe(r.sub(d.reindex(r.index).fillna(0)))})

    # save
    pd.DataFrame(rows).to_csv(OUT / "r2_summary_batch_0002.csv", index=False)
    yr_df = pd.DataFrame(year_rows)
    yr_df.to_csv(OUT / "r2_per_year_batch_0002.csv", index=False)
    pd.DataFrame(cost_rows).to_csv(OUT / "r2_cost_sensitivity_batch_0002.csv", index=False)

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
        floors[fid] = {
            "worst_year": wy, "byo_avg": byo_avg,
            "headline_sharpe": sh,
            "wy_pass_0p5": (wy >= WORST_YEAR_FLOOR) if np.isfinite(wy) else False,
            "byo_pass_50pct_headline": (byo_avg >= 0.5 * sh) if np.isfinite(byo_avg) and np.isfinite(sh) and sh > 0 else False,
        }
    with (OUT / "r2_floors_batch_0002.json").open("w") as f:
        json.dump(floors, f, indent=2)

    # markdown
    lines = ["# Backtest R2 — IVOL-momentum standalone PROMOTE attempt", ""]
    lines.append("Targeted at rescuing 2024 worst-year via narrative-collapse-aware gates.")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| expr | type | gross | net@5bps | excess | s_train | s_val | s_test | turnover% |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        ex_s = f"{r['sharpe_excess']:.2f}" if np.isfinite(r["sharpe_excess"]) else "n/a"
        lines.append(f"| {r['expr']} | {r['type']} | {r['sharpe_gross']:.2f} | {r['sharpe_net5bps']:.2f} | {ex_s} | {r['sharpe_train']:.2f} | {r['sharpe_val']:.2f} | {r['sharpe_test']:.2f} | {r['ann_turnover_pct']:.0f} |")
    lines.append("")
    lines.append("## Per-year Sharpe")
    lines.append("")
    lines.append(yr_df.pivot(index="expr", columns="year", values="sharpe").round(2).to_markdown())
    lines.append("")
    lines.append("## Floors (worst-year >= 0.5 is the binding gate)")
    lines.append("")
    lines.append("| expr | wy | wy_pass | byo_avg | byo_pass |")
    lines.append("|---|---:|---|---:|---|")
    for fid in expressions:
        fl = floors[fid]
        lines.append(f"| {fid} | {fl['worst_year']:.2f} | {fl['wy_pass_0p5']} | {fl['byo_avg']:.2f} | {fl['byo_pass_50pct_headline']} |")
    (OUT / "backtest_results_batch_0002.md").write_text("\n".join(lines))
    print("OK; rows:", len(rows))


if __name__ == "__main__":
    main()
