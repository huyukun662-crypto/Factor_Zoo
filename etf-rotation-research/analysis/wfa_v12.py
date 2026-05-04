"""WFA on v12 candidates: M6 with FIXED categories + intra-method variants.

Compare R65 (M6 top-2 inception-aware new cats) vs old R57 (M6 top-2 old cats).

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
    _def_w_from_daily,
)
from analysis.iterate_is_v9 import assemble  # noqa: E402
from analysis.iterate_is_v10 import _bucket_velocity_3  # noqa: E402
from analysis.iterate_is_v12 import matrix_intra_dispatcher  # noqa: E402
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

    cat_ret = build_category_returns(panels["close"])  # uses NEW categories
    defensive_pool = [s for s in EXPANDED_DEFENSIVE if s in panels["close"].columns]
    def_returns = build_defensive_returns(panels["close"], defensive_pool)

    cn_cpi_b = _bucket_cpi(regime_panel["cpi_yoy"])
    pmi_b = _bucket_pmi(regime_panel["pmi"])
    cpi_vel_b = _bucket_velocity_3(regime_panel.get("cpi_velocity_3m"), threshold=0.3)
    pmi_vel_b = _bucket_velocity_3(regime_panel.get("pmi_velocity_3m"), threshold=0.5)

    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)
    all_symbols = list(panels["close"].columns)
    ef = _equity_frac(regime_panel, R37_GATE_OFF, R37_GATE_FULL)

    full_dates = panels["close"].index
    n_dates = len(full_dates)
    starts = list(range(0, n_dates - TRAIN_WINDOW - TEST_WINDOW + 1, STEP))

    pnls = {"R30": [], "M6_top2_new": [], "M6_volparity_t2": [], "M6_sharpew_t2": []}

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
        train_returns = def_returns.loc[train_mask]
        train_regime = regime_panel.loc[train_mask, "regime_state_2"]
        train_cn_cpi = cn_cpi_b.loc[train_mask]
        train_cat_ret = cat_ret.loc[train_mask]
        train_cpi_vel = cpi_vel_b.loc[train_mask]
        train_pmi_vel = pmi_vel_b.loc[train_mask]

        # R30 baseline
        r30_map = per_regime_per_macro_best(train_regime, train_cn_cpi, train_returns,
                                                metric="sharpe_min_vol", min_obs=15)
        if not r30_map:
            continue
        daily_r30 = _daily_def_from_mapping(regime_panel["regime_state_2"], cn_cpi_b, r30_map)
        def_w_r30 = _def_w_from_daily(daily_r30, all_symbols)
        w_r30 = assemble(base_topk, def_w_r30, ef, p["rebal_threshold"])

        # M6 with NEW categories
        m6_score = per_cell_category_score(train_cpi_vel, train_pmi_vel, train_cat_ret,
                                                metric="sharpe_min_vol")
        m6_map = best_category_per_cell(m6_score) if not m6_score.empty else {}

        # M6 + top-2 (inception-aware)
        def_w_t2 = matrix_intra_dispatcher(cpi_vel_b, pmi_vel_b, m6_map, score, panels["close"],
                                                all_symbols, method="topk_aware", top_k=2)
        w_t2 = assemble(base_topk, def_w_t2, ef, p["rebal_threshold"])

        # M6 + vol-parity top-2
        def_w_vp = matrix_intra_dispatcher(cpi_vel_b, pmi_vel_b, m6_map, score, panels["close"],
                                                all_symbols, method="vol_parity", top_k=2,
                                                vol_lookback=60)
        w_vp = assemble(base_topk, def_w_vp, ef, p["rebal_threshold"])

        # M6 + sharpe-weighted top-2
        def_w_sw = matrix_intra_dispatcher(cpi_vel_b, pmi_vel_b, m6_map, score, panels["close"],
                                                all_symbols, method="sharpe_weighted", top_k=2,
                                                vol_lookback=60)
        w_sw = assemble(base_topk, def_w_sw, ef, p["rebal_threshold"])

        for label, ww in [("R30", w_r30), ("M6_top2_new", w_t2),
                            ("M6_volparity_t2", w_vp), ("M6_sharpew_t2", w_sw)]:
            res = run_backtest(ww, panels["close"], panels["open"], panels["amount"], cost_cfg)
            pnls[label].append(res.pnl_net.loc[test_start:step_end])

        if wi % 5 == 0 or wi == len(starts) - 1:
            print(f"  [{wi+1}/{len(starts)}] test {test_start.date()}..{test_end.date()}  done")

    summary = {}
    py_table = pd.DataFrame()
    for label, plist in pnls.items():
        if not plist:
            continue
        wf = pd.concat(plist).sort_index()
        wf = wf[~wf.index.duplicated(keep="first")]
        m = annualize_metrics(wf)
        summary[label] = m
        py_table[label] = per_year_metrics(wf)["sharpe"]

    print("\n=== WFA Comparison (NEW categories) ===")
    sdf = pd.DataFrame(summary).T
    print(sdf[["sharpe", "ann_ret", "ann_vol", "max_dd", "calmar"]].round(3).to_string())
    sdf.to_csv(OUT / "wfa_v12_summary.csv")

    print("\n=== Per-year WF Sharpe ===")
    print(py_table.round(3).to_string())
    py_table.to_csv(OUT / "wfa_v12_per_year.csv")

    print(f"\nWall-clock: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
