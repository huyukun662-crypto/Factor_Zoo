"""WFA test on R50-R57 best candidates: M6 + top-2 vs M1 vs R30 vs R42.

Per-window: re-derive matrix mapping using TRAINING DATA ONLY.
For top-K intra-category: uses current-day RSRS+momentum score (fully OOS).

# [GUARDRAIL] All within IS (2013-2023). 27 windows.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from analysis.is_search import expand_param, load_is_panels  # noqa: E402
from analysis.iterate_is_v8 import (  # noqa: E402
    _build_signals as _build_signals_v8, _daily_def_from_mapping,
    _def_w_from_daily, double_pressure_override,
)
from analysis.iterate_is_v9 import (  # noqa: E402
    assemble, double_pressure_override_pool, matrix_defensive_weights,
)
from analysis.iterate_is_v10 import (  # noqa: E402
    _bucket_m2, _bucket_velocity_3, _matrix_intra_defensive,
)
from analysis.macro_matrix import (  # noqa: E402
    _bucket_cpi, _bucket_pmi, best_category_per_cell, per_cell_category_score,
)
from analysis.wfa_is import (  # noqa: E402
    R37_GATE_FULL, R37_GATE_OFF, R37_PARAMS, STEP, TEST_WINDOW, TRAIN_WINDOW,
)
from data.fetch_macro import fetch_all_macro  # noqa: E402
from strategy.backtest import (  # noqa: E402
    CostConfig, annualize_metrics, per_year_metrics, run_backtest,
)
from strategy.categories import build_category_returns  # noqa: E402
from strategy.defensive import (  # noqa: E402
    EXPANDED_DEFENSIVE, per_regime_per_macro_best,
)
from strategy.portfolio import _topk_equal_weight  # noqa: E402
from strategy.regime import build_defensive_returns, build_regime_panel  # noqa: E402
from strategy.universe import (  # noqa: E402
    BENCHMARK_SYMBOL, BOND_OR_MONEY_SET,
)

OUT = REPO_ROOT / "report" / "outputs"
DXY_THRESH = 0.04
RMB_THRESH = 0.02
DP_POOL = ["511260", "511880", "162411"]


def _equity_frac(regime_panel, off_set, full_set):
    s = regime_panel["regime_state_2"]
    ef = pd.Series(0.5, index=s.index)
    ef[s.isin(off_set)] = 0.0
    ef[s.isin(full_set)] = 1.0
    return ef


def main():
    t0 = time.time()
    panels = load_is_panels()
    macro = fetch_all_macro()
    bench = panels["close"][BENCHMARK_SYMBOL]
    regime_panel = build_regime_panel(bench, macro=macro, ma_window=200, vol_window=60)

    p = expand_param(R37_PARAMS)
    rsrs, score, elig = _build_signals_v8(panels, p)
    base_topk = _topk_equal_weight(score, elig, p["top_k"])

    cat_ret = build_category_returns(panels["close"])
    sym_returns = panels["close"].pct_change().fillna(0.0)
    defensive_pool = [s for s in EXPANDED_DEFENSIVE if s in panels["close"].columns]
    def_returns = build_defensive_returns(panels["close"], defensive_pool)

    cn_cpi_b = _bucket_cpi(regime_panel["cpi_yoy"])
    pmi_b = _bucket_pmi(regime_panel["pmi"])
    cpi_vel_b = _bucket_velocity_3(regime_panel.get("cpi_velocity_3m", pd.Series(0, index=regime_panel.index)),
                                       threshold=0.3)
    pmi_vel_b = _bucket_velocity_3(regime_panel.get("pmi_velocity_3m", pd.Series(0, index=regime_panel.index)),
                                       threshold=0.5)
    m2_b = _bucket_m2(regime_panel.get("m2_yoy", pd.Series(10, index=regime_panel.index)))

    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)
    all_symbols = list(panels["close"].columns)
    ef = _equity_frac(regime_panel, R37_GATE_OFF, R37_GATE_FULL)

    full_dates = panels["close"].index
    n_dates = len(full_dates)
    starts = list(range(0, n_dates - TRAIN_WINDOW - TEST_WINDOW + 1, STEP))
    print(f"WFA windows: {len(starts)}")

    rows = []
    pnls = {"R30": [], "R42": [],
            "M1_ew": [], "M1_top2": [],
            "M6_ew": [], "M6_top2": [], "M6_top1": [],
            "M9_ew": [],
            "M6_ew+DP": []}

    for wi, s_idx in enumerate(starts):
        train_start = full_dates[s_idx]
        train_end = full_dates[s_idx + TRAIN_WINDOW - 1]
        test_start = full_dates[s_idx + TRAIN_WINDOW]
        test_end_idx = min(s_idx + TRAIN_WINDOW + TEST_WINDOW - 1, n_dates - 1)
        test_end = full_dates[test_end_idx]
        step_end_idx = min(s_idx + TRAIN_WINDOW + STEP - 1, n_dates - 1)
        step_end = full_dates[step_end_idx]

        train_mask = (def_returns.index >= train_start) & (def_returns.index <= train_end)
        if train_mask.sum() < 60:
            continue

        # Slice training data
        train_returns = def_returns.loc[train_mask]
        train_regime = regime_panel.loc[train_mask, "regime_state_2"]
        train_cn_cpi = cn_cpi_b.loc[train_mask]
        train_pmi = pmi_b.loc[train_mask]
        train_cpi_vel = cpi_vel_b.loc[train_mask]
        train_pmi_vel = pmi_vel_b.loc[train_mask]
        train_cat_ret = cat_ret.loc[train_mask]

        # ---- R30 (baseline) ----
        r30_map = per_regime_per_macro_best(train_regime, train_cn_cpi, train_returns,
                                                metric="sharpe_min_vol", min_obs=15)
        if not r30_map:
            continue
        daily_r30 = _daily_def_from_mapping(regime_panel["regime_state_2"], cn_cpi_b, r30_map)
        def_w_r30 = _def_w_from_daily(daily_r30, all_symbols)
        w_r30 = assemble(base_topk, def_w_r30, ef, p["rebal_threshold"])

        # ---- R42 (DP override) ----
        def_w_r42 = double_pressure_override_pool(def_w_r30, regime_panel,
                                                       DXY_THRESH, RMB_THRESH, DP_POOL)
        w_r42 = assemble(base_topk, def_w_r42, ef, p["rebal_threshold"])

        # ---- Matrix mappings ----
        # M1 (PMI × CPI)
        m1_score = per_cell_category_score(train_pmi, train_cn_cpi, train_cat_ret,
                                              metric="sharpe_min_vol")
        m1_map = best_category_per_cell(m1_score) if not m1_score.empty else {}
        # M6 (CPI vel × PMI vel)
        m6_score = per_cell_category_score(train_cpi_vel, train_pmi_vel, train_cat_ret,
                                              metric="sharpe_min_vol")
        m6_map = best_category_per_cell(m6_score) if not m6_score.empty else {}
        # M9 (PMI vel × CPI)
        m9_score = per_cell_category_score(train_pmi_vel, train_cn_cpi, train_cat_ret,
                                              metric="sharpe_min_vol")
        m9_map = best_category_per_cell(m9_score) if not m9_score.empty else {}

        # Build defensive weight panels (multiple variants)
        def_w_M1_ew = _matrix_intra_defensive(pmi_b, cn_cpi_b, m1_map, score, all_symbols, "ew")
        def_w_M1_top2 = _matrix_intra_defensive(pmi_b, cn_cpi_b, m1_map, score, all_symbols,
                                                    "topk", top_k=2)

        def_w_M6_ew = _matrix_intra_defensive(cpi_vel_b, pmi_vel_b, m6_map, score, all_symbols, "ew")
        def_w_M6_top1 = _matrix_intra_defensive(cpi_vel_b, pmi_vel_b, m6_map, score, all_symbols,
                                                    "topk", top_k=1)
        def_w_M6_top2 = _matrix_intra_defensive(cpi_vel_b, pmi_vel_b, m6_map, score, all_symbols,
                                                    "topk", top_k=2)
        def_w_M6_DP = double_pressure_override_pool(def_w_M6_ew, regime_panel,
                                                         DXY_THRESH, RMB_THRESH, DP_POOL)

        def_w_M9_ew = _matrix_intra_defensive(pmi_vel_b, cn_cpi_b, m9_map, score, all_symbols, "ew")

        # Run all backtests
        results = {}
        for label, ww in [
            ("R30", w_r30), ("R42", w_r42),
            ("M1_ew", assemble(base_topk, def_w_M1_ew, ef, p["rebal_threshold"])),
            ("M1_top2", assemble(base_topk, def_w_M1_top2, ef, p["rebal_threshold"])),
            ("M6_ew", assemble(base_topk, def_w_M6_ew, ef, p["rebal_threshold"])),
            ("M6_top1", assemble(base_topk, def_w_M6_top1, ef, p["rebal_threshold"])),
            ("M6_top2", assemble(base_topk, def_w_M6_top2, ef, p["rebal_threshold"])),
            ("M9_ew", assemble(base_topk, def_w_M9_ew, ef, p["rebal_threshold"])),
            ("M6_ew+DP", assemble(base_topk, def_w_M6_DP, ef, p["rebal_threshold"])),
        ]:
            res = run_backtest(ww, panels["close"], panels["open"], panels["amount"], cost_cfg)
            results[label] = res
            pnls[label].append(res.pnl_net.loc[test_start:step_end])

        rec = {"window": wi, "test_start": test_start.strftime("%Y-%m-%d"),
                "test_end": test_end.strftime("%Y-%m-%d")}
        for label, res in results.items():
            tm = annualize_metrics(res.pnl_net.loc[test_start:test_end])
            rec[f"{label}_test_sh"] = tm["sharpe"]
            rec[f"{label}_test_ret"] = tm["ann_ret"]
            rec[f"{label}_test_dd"] = tm["max_dd"]
        rows.append(rec)
        if wi % 5 == 0 or wi == len(starts) - 1:
            sums = " ".join(
                f"{lbl}={annualize_metrics(results[lbl].pnl_net.loc[test_start:test_end])['sharpe']:+.2f}"
                for lbl in ["R30", "R42", "M1_ew", "M6_ew", "M6_top2"]
            )
            print(f"  [{wi+1}/{len(starts)}] test {test_start.date()}..{test_end.date()}  {sums}")

    if not rows:
        raise RuntimeError("no windows")

    df_w = pd.DataFrame(rows)
    df_w.to_csv(OUT / "wfa_v10_windows.csv", index=False)

    # Concat WF curves
    summary = {}
    py_table = pd.DataFrame()
    for label, plist in pnls.items():
        wf = pd.concat(plist).sort_index()
        wf = wf[~wf.index.duplicated(keep="first")]
        m = annualize_metrics(wf)
        summary[label] = m
        py_table[label] = per_year_metrics(wf)["sharpe"]

    print("\n=== WFA Comparison ===")
    summary_df = pd.DataFrame(summary).T
    print(summary_df[["sharpe", "ann_ret", "ann_vol", "max_dd", "calmar"]].round(3).to_string())
    summary_df.to_csv(OUT / "wfa_v10_summary.csv")

    print("\n=== Per-year WF Sharpe ===")
    print(py_table.round(3).to_string())
    py_table.to_csv(OUT / "wfa_v10_per_year.csv")

    print("\n=== Head-to-head vs R30 ===")
    for label in summary.keys():
        if label == "R30":
            continue
        if f"{label}_test_sh" not in df_w.columns:
            continue
        delta = df_w[f"{label}_test_sh"] - df_w["R30_test_sh"]
        better = int((delta > 0).sum())
        worse = int((delta < 0).sum())
        tied = int((delta == 0).sum())
        print(f"  {label:15s} vs R30: better={better:3d} worse={worse:3d} tied={tied:3d}")

    print(f"\nWall-clock: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
