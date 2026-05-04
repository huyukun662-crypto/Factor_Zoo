"""V9: R45-R49 — Macro-matrix driven defensive CATEGORY routing.

Architecture:
  Equity selection (top-K from full universe by RSRS+momentum) — UNCHANGED
  Risk-off regime gate (regime_state_2: trend × vol)            — UNCHANGED
  Defensive CATEGORY: macro-matrix → category mapping            — NEW

  Within category: equal-weight constituents
  Categories: 长债, 货币, 黄金, 红利低波, 商品, 海外股

Per round, try a different matrix definition + scoring metric.
For each matrix, IS-best mapping is automatically discovered.

R45 M3 (us_real_rate × CPI) sharpe_min_vol
R46 M5 (PMI × DXY) sharpe_min_vol
R47 M1 (PMI × CPI) sharpe_min_vol  -- Merrill Lynch clock
R48 best matrix + R42 double-pressure override stacked
R49 final param refine

# [GUARDRAIL] All within IS (2013-2023). Matrix derived from full IS.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from analysis.is_search import expand_param, load_is_panels  # noqa: E402
from analysis.macro_matrix import (  # noqa: E402
    _bucket_cpi, _bucket_dxy_strong, _bucket_pmi, _bucket_real_rate,
    best_category_per_cell, per_cell_category_score,
)
from data.fetch_macro import fetch_all_macro  # noqa: E402
from strategy.backtest import (  # noqa: E402
    CostConfig, annualize_metrics, per_year_metrics, run_backtest,
)
from strategy.categories import CATEGORIES, build_category_returns, build_category_weights  # noqa: E402
from strategy.portfolio import _apply_rebal_threshold, _topk_equal_weight  # noqa: E402
from strategy.regime import build_regime_panel  # noqa: E402
from strategy.signals import (  # noqa: E402
    absolute_momentum_filter, higher_moment_score, rsrs_panel,
)
from strategy.universe import (  # noqa: E402
    BENCHMARK_SYMBOL, BOND_OR_MONEY_SET,
)

OUT = REPO_ROOT / "report" / "outputs"


def _xs_z(df):
    mu = df.mean(axis=1); sd = df.std(axis=1).replace(0, np.nan)
    return df.sub(mu, axis=0).div(sd, axis=0)


def _build_signals(panels, params):
    close, high, low = panels["close"], panels["high"], panels["low"]
    rsrs = rsrs_panel(high, low, n=params["rsrs_N"], m=params["rsrs_M"], form="rsrs_skew")
    mom = higher_moment_score(close, L=params["mom_L"],
                                lambda_s=params["lambda_s"], lambda_k=params["lambda_k"])
    score = params["w_rsrs"] * _xs_z(rsrs).fillna(0) + (1 - params["w_rsrs"]) * mom.fillna(0)
    elig = absolute_momentum_filter(close, params["mom_L"], "511010")
    ma200 = close.rolling(200, min_periods=50).mean()
    elig = elig & (close > ma200)
    return rsrs, score, elig


def _equity_frac(regime_panel, off_set, full_set):
    s = regime_panel["regime_state_2"]
    ef = pd.Series(0.5, index=s.index)
    ef[s.isin(off_set)] = 0.0
    ef[s.isin(full_set)] = 1.0
    return ef


def assemble(equity_w, defensive_w, equity_frac, rebal_thresh):
    cols = sorted(set(equity_w.columns) | set(defensive_w.columns))
    eq = equity_w.reindex(columns=cols, fill_value=0.0)
    de = defensive_w.reindex(columns=cols, fill_value=0.0)
    out = eq.mul(equity_frac, axis=0).add(de.mul(1 - equity_frac, axis=0), fill_value=0.0)
    if rebal_thresh and rebal_thresh > 0:
        out = _apply_rebal_threshold(out, rebal_thresh)
    return out


def matrix_defensive_weights(a1: pd.Series, a2: pd.Series,
                                cell_to_category: dict[tuple, str],
                                all_symbols: list[str],
                                default_category: str = "货币",
                                ) -> pd.DataFrame:
    """Build per-day defensive weight panel based on (axis1, axis2) -> category mapping."""
    out = pd.DataFrame(0.0, index=a1.index, columns=all_symbols)
    # Cache category weight vectors
    cat_w_cache = {cat: build_category_weights(cat, all_symbols) for cat in CATEGORIES}
    default_w = cat_w_cache.get(default_category, build_category_weights(default_category, all_symbols))
    for dt in a1.index:
        v1 = a1.at[dt] if dt in a1.index else None
        v2 = a2.at[dt] if dt in a2.index else None
        if pd.isna(v1) or pd.isna(v2):
            out.loc[dt] = default_w.values
            continue
        cat = cell_to_category.get((str(v1), str(v2)))
        if cat and cat in cat_w_cache:
            out.loc[dt] = cat_w_cache[cat].values
        else:
            out.loc[dt] = default_w.values
    return out


def double_pressure_override_pool(weights: pd.DataFrame, regime_panel: pd.DataFrame,
                                     dxy_thresh: float, rmb_thresh: float,
                                     pool: list[str]) -> pd.DataFrame:
    """When (dxy_mom > X AND usdcny_mom > Y), force defensive = equal-weight pool."""
    out = weights.copy()
    mask = ((regime_panel["dxy_mom_60"] > dxy_thresh) &
             (regime_panel["usdcny_mom_60"] > rmb_thresh)).fillna(False)
    if not mask.any():
        return out
    eqw = 1.0 / len(pool) if pool else 0.0
    for dt in regime_panel.index[mask]:
        for s in out.columns:
            out.at[dt, s] = 0.0
        for s in pool:
            if s in out.columns:
                out.at[dt, s] = eqw
    return out


def to_row(round_n, label, params, extras, metrics):
    row = {"round": round_n, "label": label, **params, **extras}
    row.update({
        "ann_ret": metrics["ann_ret"], "ann_vol": metrics["ann_vol"],
        "sharpe_net": metrics["sharpe"], "sharpe_gross": metrics.get("gross_sharpe", float("nan")),
        "max_dd": metrics["max_dd"], "calmar": metrics["calmar"],
        "sortino": metrics["sortino"], "win_rate": metrics["win_rate"],
        "ann_turnover": metrics["ann_turnover"], "n_days": metrics["n"],
    })
    return row


def main():
    t0 = time.time()
    panels = load_is_panels()
    macro = fetch_all_macro()
    bench = panels["close"][BENCHMARK_SYMBOL]
    regime_panel = build_regime_panel(bench, macro=macro, ma_window=200, vol_window=60)

    p = expand_param({
        "rsrs_N": 30, "rsrs_M": 250, "mom_L": 180,
        "lambda_s": 0.2, "lambda_k": 0.0,
        "w_rsrs": 0.2, "top_k": 7,
        "theta_off": -0.7, "theta_on": 0.7,
        "rebal_threshold": 0.4,
    })
    p["rsrs_form"] = "rsrs_skew"

    rsrs, score, elig = _build_signals(panels, p)
    base_topk = _topk_equal_weight(score, elig, p["top_k"])

    cat_ret = build_category_returns(panels["close"])
    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)
    all_symbols = list(panels["close"].columns)
    ef = _equity_frac(regime_panel, {0, 1, 3}, {2})

    # Axis variants
    cpi_b = _bucket_cpi(regime_panel["cpi_yoy"])
    pmi_b = _bucket_pmi(regime_panel["pmi"])
    real_b = _bucket_real_rate(regime_panel["us_real_rate"])
    dxy_b = _bucket_dxy_strong(regime_panel["dxy_strong"])

    rows = []

    # R30 baseline reference (no matrix)
    print("=== R30 baseline (per-(regime × CN_CPI) symbol mapping) ===")
    from analysis.iterate_is_v8 import (  # noqa: E402
        _daily_def_from_mapping, _def_w_from_daily,
    )
    from strategy.defensive import EXPANDED_DEFENSIVE, per_regime_per_macro_best
    from strategy.regime import build_defensive_returns
    defensive_pool = [s for s in EXPANDED_DEFENSIVE if s in panels["close"].columns]
    def_returns = build_defensive_returns(panels["close"], defensive_pool)
    base_map = per_regime_per_macro_best(regime_panel["regime_state_2"], cpi_b,
                                            def_returns, metric="sharpe_min_vol")
    daily_base = _daily_def_from_mapping(regime_panel["regime_state_2"], cpi_b, base_map)
    def_w_r30 = _def_w_from_daily(daily_base, all_symbols)
    w_r30 = assemble(base_topk, def_w_r30, ef, p["rebal_threshold"])
    res_r30 = run_backtest(w_r30, panels["close"], panels["open"], panels["amount"], cost_cfg)
    print(f"  Sharpe={res_r30.metrics['sharpe']:.3f} (target 1.457)")
    rows.append(to_row(0, "R30 baseline", p, {"matrix": "none"}, res_r30.metrics))

    # ========= R45-R47: macro matrix variants =========
    matrices = {
        "R45_M3": ("us_real_rate × CPI", real_b, cpi_b, "M3"),
        "R46_M5": ("PMI × DXY", pmi_b, dxy_b, "M5"),
        "R47_M1": ("PMI × CPI", pmi_b, cpi_b, "M1"),
    }

    matrix_results = {}

    for round_label, (desc, a1, a2, mid) in matrices.items():
        round_n = int(round_label.split("_")[0][1:])
        print(f"\n=== {round_label}: {desc} ===")
        score_df = per_cell_category_score(a1, a2, cat_ret, metric="sharpe_min_vol")
        cell_map = best_category_per_cell(score_df)
        # Print mapping
        for (v1, v2), cat in sorted(cell_map.items()):
            n = int(score_df[(score_df["a1"] == v1) & (score_df["a2"] == v2)]["n"].iloc[0])
            print(f"    ({v1:8s}, {v2:5s}) n={n:4d}  -> {cat}")

        def_w = matrix_defensive_weights(a1, a2, cell_map, all_symbols)
        w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        rows.append(to_row(round_n, f"matrix {mid}", p,
                            {"matrix": mid, "axis1": desc.split(" × ")[0],
                             "axis2": desc.split(" × ")[1], "n_cells": len(cell_map)},
                            res.metrics))
        matrix_results[round_label] = (cell_map, a1, a2, def_w, res)
        print(f"    Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%  "
              f"DD={res.metrics['max_dd']*100:.2f}%  Calmar={res.metrics['calmar']:.2f}")

    # ========= R48: best matrix + double-pressure override =========
    print("\n=== R48: best matrix + double-pressure override pool ===")
    best_matrix = max(matrix_results.items(),
                      key=lambda x: x[1][4].metrics["sharpe"])
    best_label, (best_map, a1_b, a2_b, def_w_b, res_b) = best_matrix
    print(f"  Best matrix from R45-R47: {best_label} Sharpe={res_b.metrics['sharpe']:.3f}")

    POOL = ["511260", "511880", "162411"]
    for dxy_t, rmb_t in [(0.02, 0.01), (0.04, 0.02), (0.06, 0.03)]:
        def_w_ovr = double_pressure_override_pool(def_w_b, regime_panel,
                                                       dxy_t, rmb_t, POOL)
        w = assemble(base_topk, def_w_ovr, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        rows.append(to_row(48, f"{best_label} + override pool dxy>{dxy_t} rmb>{rmb_t}",
                            p, {"matrix": best_label, "dp_dxy": dxy_t, "dp_rmb": rmb_t},
                            res.metrics))
        print(f"    dxy>{dxy_t:.2f} rmb>{rmb_t:.3f}  Sharpe={res.metrics['sharpe']:.3f}  "
              f"Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%")

    # ========= R49: param refine + gate exploration on best of R45-R48 =========
    df_so_far = pd.DataFrame(rows)
    win = df_so_far[df_so_far["round"] > 0].sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"\n=== R49: param refine (best so far Sharpe={win['sharpe_net']:.3f} from R{int(win['round'])}) ===")

    # Recover the best def_w
    if int(win["round"]) == 48:
        # apply override on best matrix
        bm = win["matrix"]
        best_map_w, a1_w, a2_w, def_w_pre, _ = matrix_results[bm]
        def_w_best = double_pressure_override_pool(def_w_pre, regime_panel,
                                                       float(win["dp_dxy"]),
                                                       float(win["dp_rmb"]), POOL)
    else:
        # one of R45-R47
        bm = win["matrix"]
        round_label = next((k for k in matrix_results if matrix_results[k][4].metrics["sharpe"]
                                  == win["sharpe_net"]), None)
        if round_label is None:
            round_label = next(k for k in matrix_results if k.endswith(bm)) if bm in {"M3", "M5", "M1"} else "R45_M3"
        best_map_w, a1_w, a2_w, def_w_best, _ = matrix_results[round_label]

    for k in [3, 5, 7]:
        for wr in [0.20, 0.30, 0.40]:
            for mL in [120, 180, 252]:
                for rb in [0.0, 0.20, 0.40]:
                    pp = dict(p); pp["top_k"]=k; pp["w_rsrs"]=wr; pp["mom_L"]=mL; pp["rebal_threshold"]=rb
                    rsrs2, score2, elig2 = _build_signals(panels, pp)
                    topk2 = _topk_equal_weight(score2, elig2, k)
                    w = assemble(topk2, def_w_best, ef, rb)
                    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
                    rows.append(to_row(49, f"refine k={k} wr={wr} L={mL} rb={rb}",
                                        pp, {"matrix": win.get("matrix", "")}, res.metrics))

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "all_candidates_v9.csv", index=False)

    winner = df[df["round"] > 0].sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"\n=== R45-R49 overall best: round={int(winner['round'])} Sharpe={winner['sharpe_net']:.3f} ===")
    print(f"  label: {winner['label']}")
    print(f"  ann_ret={winner['ann_ret']*100:.2f}%  DD={winner['max_dd']*100:.2f}%  Calmar={winner['calmar']:.2f}  Turn={winner['ann_turnover']:.1f}x")

    # Compare to R30 1.457 and R42 1.454
    R30_BEST = 1.457
    if winner["sharpe_net"] > R30_BEST:
        print(f"\n*** IMPROVED IS Sharpe {R30_BEST:.3f} -> {winner['sharpe_net']:.3f} ***")
    else:
        print(f"\n(IS Sharpe {winner['sharpe_net']:.3f} vs R30 {R30_BEST:.3f})")
        print("(but matrix approach may be more WFA-stable -- needs WFA test)")

    print("\nTop 10 across R45-R49:")
    print(df[df["round"] > 0].sort_values("sharpe_net", ascending=False).head(10)[
        ["round","label","sharpe_net","ann_ret","ann_vol","max_dd","calmar","ann_turnover"]
    ].to_string(index=False))

    print("\nPer-round R45-R49 distribution:")
    print(df[df["round"] > 0].groupby("round")["sharpe_net"].describe().round(3).to_string())

    # Save best matrix's mapping + per-year for later WFA reproduction
    if "M3" in [m[0] for m in matrix_results.items()]:
        # Save M3 mapping (most economic)
        m3_map, _, _, _, _ = matrix_results["R45_M3"]
        json_map = {f"{k[0]}_{k[1]}": v for k, v in m3_map.items()}
        (OUT / "macro_matrix_M3_mapping.json").write_text(
            json.dumps(json_map, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nWall-clock: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
