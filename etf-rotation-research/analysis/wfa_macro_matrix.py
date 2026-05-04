"""WFA on macro-matrix defensive routing vs R30 + R42 (best so far).

Per-window: re-derive the matrix mapping using TRAINING DATA ONLY.
This is the key WFA test: does the matrix approach generalize better?

Three strategies side-by-side:
  R30: per (regime × CN_CPI) sharpe_min_vol mapping (symbol-level)
  R42: R30 base + double-pressure override pool {国开,货币,油气}
  R45_M3 (matrix): macro matrix (us_real_rate × CPI) -> CATEGORY mapping
  R46_M5 (matrix): PMI × DXY -> CATEGORY
  R45_M3 + DP    : matrix + double-pressure override

# [GUARDRAIL] All within IS (2013-2023). 27 windows.
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
from analysis.iterate_is_v8 import (  # noqa: E402
    _build_signals as _build_signals_v8, _daily_def_from_mapping,
    _def_w_from_daily, double_pressure_override,
)
from analysis.iterate_is_v9 import (  # noqa: E402
    assemble, double_pressure_override_pool, matrix_defensive_weights,
)
from analysis.macro_matrix import (  # noqa: E402
    _bucket_cpi, _bucket_dxy_strong, _bucket_pmi, _bucket_real_rate,
    best_category_per_cell, per_cell_category_score,
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
    defensive_pool = [s for s in EXPANDED_DEFENSIVE if s in panels["close"].columns]
    def_returns = build_defensive_returns(panels["close"], defensive_pool)

    cn_cpi_b = _bucket_cpi(regime_panel["cpi_yoy"])
    pmi_b = _bucket_pmi(regime_panel["pmi"])
    real_b = _bucket_real_rate(regime_panel["us_real_rate"])
    dxy_b = _bucket_dxy_strong(regime_panel["dxy_strong"])

    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)
    all_symbols = list(panels["close"].columns)
    ef = _equity_frac(regime_panel, R37_GATE_OFF, R37_GATE_FULL)

    full_dates = panels["close"].index
    n_dates = len(full_dates)
    starts = list(range(0, n_dates - TRAIN_WINDOW - TEST_WINDOW + 1, STEP))
    print(f"WFA windows: {len(starts)}")

    rows = []
    pnls = {"R30": [], "R42": [], "M3": [], "M5": [], "M1": [],
             "M3+DP": [], "M5+DP": []}

    for wi, s_idx in enumerate(starts):
        train_start = full_dates[s_idx]
        train_end = full_dates[s_idx + TRAIN_WINDOW - 1]
        test_start = full_dates[s_idx + TRAIN_WINDOW]
        test_end_idx = min(s_idx + TRAIN_WINDOW + TEST_WINDOW - 1, n_dates - 1)
        test_end = full_dates[test_end_idx]
        step_end_idx = min(s_idx + TRAIN_WINDOW + STEP - 1, n_dates - 1)
        step_end = full_dates[step_end_idx]

        # Slice training data
        train_mask = (def_returns.index >= train_start) & (def_returns.index <= train_end)
        if train_mask.sum() < 60:
            continue

        # ---- R30: per-(regime × CN_CPI) symbol mapping ----
        train_returns = def_returns.loc[train_mask]
        train_regime = regime_panel.loc[train_mask, "regime_state_2"]
        train_cpi = cn_cpi_b.loc[train_mask]
        r30_map = per_regime_per_macro_best(train_regime, train_cpi, train_returns,
                                                metric="sharpe_min_vol", min_obs=15)
        if not r30_map:
            continue
        daily_r30 = _daily_def_from_mapping(regime_panel["regime_state_2"], cn_cpi_b, r30_map)
        def_w_r30 = _def_w_from_daily(daily_r30, all_symbols)
        w_r30 = assemble(base_topk, def_w_r30, ef, p["rebal_threshold"])

        # ---- R42: R30 + double-pressure override ----
        def_w_r42 = double_pressure_override_pool(def_w_r30, regime_panel,
                                                       DXY_THRESH, RMB_THRESH, DP_POOL)
        w_r42 = assemble(base_topk, def_w_r42, ef, p["rebal_threshold"])

        # ---- Matrix mappings: re-derive on training data ----
        train_cat_ret = cat_ret.loc[train_mask]
        train_real = real_b.loc[train_mask]
        train_pmi = pmi_b.loc[train_mask]
        train_cpi_b = cn_cpi_b.loc[train_mask]
        train_dxy = dxy_b.loc[train_mask]

        # M3: us_real × CPI
        m3_score = per_cell_category_score(train_real, train_cpi_b, train_cat_ret,
                                              metric="sharpe_min_vol")
        m3_map = best_category_per_cell(m3_score) if not m3_score.empty else {}
        def_w_m3 = matrix_defensive_weights(real_b, cn_cpi_b, m3_map, all_symbols)
        w_m3 = assemble(base_topk, def_w_m3, ef, p["rebal_threshold"])
        def_w_m3_dp = double_pressure_override_pool(def_w_m3, regime_panel,
                                                         DXY_THRESH, RMB_THRESH, DP_POOL)
        w_m3_dp = assemble(base_topk, def_w_m3_dp, ef, p["rebal_threshold"])

        # M5: PMI × DXY
        m5_score = per_cell_category_score(train_pmi, train_dxy, train_cat_ret,
                                              metric="sharpe_min_vol")
        m5_map = best_category_per_cell(m5_score) if not m5_score.empty else {}
        def_w_m5 = matrix_defensive_weights(pmi_b, dxy_b, m5_map, all_symbols)
        w_m5 = assemble(base_topk, def_w_m5, ef, p["rebal_threshold"])
        def_w_m5_dp = double_pressure_override_pool(def_w_m5, regime_panel,
                                                         DXY_THRESH, RMB_THRESH, DP_POOL)
        w_m5_dp = assemble(base_topk, def_w_m5_dp, ef, p["rebal_threshold"])

        # M1: PMI × CPI
        m1_score = per_cell_category_score(train_pmi, train_cpi_b, train_cat_ret,
                                              metric="sharpe_min_vol")
        m1_map = best_category_per_cell(m1_score) if not m1_score.empty else {}
        def_w_m1 = matrix_defensive_weights(pmi_b, cn_cpi_b, m1_map, all_symbols)
        w_m1 = assemble(base_topk, def_w_m1, ef, p["rebal_threshold"])

        # Run all backtests
        results = {}
        for label, ww in [("R30", w_r30), ("R42", w_r42), ("M3", w_m3), ("M5", w_m5),
                           ("M1", w_m1), ("M3+DP", w_m3_dp), ("M5+DP", w_m5_dp)]:
            res = run_backtest(ww, panels["close"], panels["open"], panels["amount"], cost_cfg)
            results[label] = res
            pnls[label].append(res.pnl_net.loc[test_start:step_end])

        rec = {
            "window": wi,
            "test_start": test_start.strftime("%Y-%m-%d"),
            "test_end": test_end.strftime("%Y-%m-%d"),
        }
        for label, res in results.items():
            test_pnl = res.pnl_net.loc[test_start:test_end]
            train_pnl = res.pnl_net.loc[train_start:train_end]
            tm = annualize_metrics(test_pnl)
            tr = annualize_metrics(train_pnl)
            rec[f"{label}_train_sh"] = tr["sharpe"]
            rec[f"{label}_test_sh"] = tm["sharpe"]
            rec[f"{label}_test_ret"] = tm["ann_ret"]
            rec[f"{label}_test_dd"] = tm["max_dd"]
        rows.append(rec)
        if wi % 5 == 0 or wi == len(starts) - 1:
            sums = " ".join(f"{lbl}={annualize_metrics(results[lbl].pnl_net.loc[test_start:test_end])['sharpe']:+.2f}"
                              for lbl in ["R30", "R42", "M3", "M5", "M3+DP"])
            print(f"  [{wi+1}/{len(starts)}] test {test_start.date()}..{test_end.date()}  {sums}")

    if not rows:
        raise RuntimeError("no windows")

    df_w = pd.DataFrame(rows)
    df_w.to_csv(OUT / "wfa_matrix_windows.csv", index=False)

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
    summary_df.to_csv(OUT / "wfa_matrix_summary.csv")

    print("\n=== Per-year WF Sharpe ===")
    print(py_table.round(3).to_string())
    py_table.to_csv(OUT / "wfa_matrix_per_year.csv")

    # Head-to-head vs R30 baseline
    print("\n=== Head-to-head vs R30 ===")
    for label in ["R42", "M3", "M5", "M1", "M3+DP", "M5+DP"]:
        delta = df_w[f"{label}_test_sh"] - df_w["R30_test_sh"]
        better = int((delta > 0).sum())
        worse = int((delta < 0).sum())
        tied = int((delta == 0).sum())
        print(f"  {label} vs R30: better={better} worse={worse} tied={tied}")

    print(f"\nWall-clock: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
