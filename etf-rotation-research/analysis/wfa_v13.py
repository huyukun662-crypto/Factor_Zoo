"""WFA on v13 candidates: cross-category risk-parity / softmax / MVO + intra vol-parity.

Tests 5 strategy variants on the same 27 windows, with per-window matrix re-derivation.
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
from analysis.macro_matrix import (  # noqa: E402
    _bucket_cpi, best_category_per_cell, per_cell_category_score,
)
from analysis.wfa_is import (  # noqa: E402
    R37_GATE_FULL, R37_GATE_OFF, R37_PARAMS, STEP, TEST_WINDOW, TRAIN_WINDOW,
)
from data.fetch_macro import fetch_all_macro  # noqa: E402
from strategy.backtest import (  # noqa: E402
    CostConfig, annualize_metrics, per_year_metrics, run_backtest,
)
from strategy.categories import CATEGORIES, build_category_returns  # noqa: E402
from strategy.cross_category import (  # noqa: E402
    build_score_panel, cross_category_weights, daily_top_n_categories,
    expand_category_to_symbol_weights, top_n_categories_per_cell,
)
from strategy.defensive import (  # noqa: E402
    EXPANDED_DEFENSIVE, per_regime_per_macro_best,
)
from strategy.intra_category import (  # noqa: E402
    intra_category_topk_aware, intra_category_vol_parity,
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


def _build_intra_panels(panels, score, all_symbols, kind="vol_parity_t2"):
    """Pre-compute per-category symbol panels."""
    out = {}
    for cat in CATEGORIES:
        if kind == "vol_parity_t2":
            out[cat] = intra_category_vol_parity(panels["close"], cat,
                                                    vol_lookback=60, top_k=2,
                                                    score=score, all_symbols=all_symbols)
        elif kind == "topk_aware_t2":
            out[cat] = intra_category_topk_aware(score, panels["close"], cat, k=2,
                                                    all_symbols=all_symbols)
    return out


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
    cpi_vel_b = _bucket_velocity_3(regime_panel.get("cpi_velocity_3m"), threshold=0.3)
    pmi_vel_b = _bucket_velocity_3(regime_panel.get("pmi_velocity_3m"), threshold=0.5)

    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)
    all_symbols = list(panels["close"].columns)
    ef = _equity_frac(regime_panel, R37_GATE_OFF, R37_GATE_FULL)

    intra_vp_t2 = _build_intra_panels(panels, score, all_symbols, kind="vol_parity_t2")
    intra_tk_t2 = _build_intra_panels(panels, score, all_symbols, kind="topk_aware_t2")

    full_dates = panels["close"].index
    n_dates = len(full_dates)
    starts = list(range(0, n_dates - TRAIN_WINDOW - TEST_WINDOW + 1, STEP))
    print(f"WFA windows: {len(starts)}")

    # Strategies to test
    strats = [
        "R30",
        "M6_top1_vp",         # baseline (cur best)
        "M6_top2_RP_vp",      # R74
        "M6_top3_RP_vp",      # R75
        "M6_softmax_vp",      # R76
        "M6_top3_MVO0.3_vp",  # R77
        "M6_softmax_tk",      # R78
        "static_RP_vp",       # R72 (no matrix control)
    ]
    pnls = {s: [] for s in strats}

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

        # M6 score from training only
        m6_score_df = per_cell_category_score(train_cpi_vel, train_pmi_vel, train_cat_ret,
                                                  metric="sharpe_min_vol")
        if m6_score_df.empty:
            continue
        # build score_panel for FULL date range using training-derived scores
        score_panel = build_score_panel(cpi_vel_b, pmi_vel_b, m6_score_df)

        top1 = top_n_categories_per_cell(m6_score_df, n=1)
        top2 = top_n_categories_per_cell(m6_score_df, n=2)
        top3 = top_n_categories_per_cell(m6_score_df, n=3)

        # Build selections
        sel1 = daily_top_n_categories(cpi_vel_b, pmi_vel_b, top1)
        sel2 = daily_top_n_categories(cpi_vel_b, pmi_vel_b, top2)
        sel3 = daily_top_n_categories(cpi_vel_b, pmi_vel_b, top3)
        sel_all = pd.DataFrame(True, index=cpi_vel_b.index, columns=list(CATEGORIES.keys()))

        # M6_top1_vp (baseline cur best)
        cw = cross_category_weights(cat_ret, sel1, method="equal")
        def_w = expand_category_to_symbol_weights(cw, intra_vp_t2, all_symbols)
        w_top1 = assemble(base_topk, def_w, ef, p["rebal_threshold"])

        # M6_top2_RP_vp
        cw = cross_category_weights(cat_ret, sel2, method="risk_parity")
        def_w = expand_category_to_symbol_weights(cw, intra_vp_t2, all_symbols)
        w_top2_rp = assemble(base_topk, def_w, ef, p["rebal_threshold"])

        # M6_top3_RP_vp
        cw = cross_category_weights(cat_ret, sel3, method="risk_parity")
        def_w = expand_category_to_symbol_weights(cw, intra_vp_t2, all_symbols)
        w_top3_rp = assemble(base_topk, def_w, ef, p["rebal_threshold"])

        # M6_softmax_vp
        cw = cross_category_weights(cat_ret, sel_all, method="softmax", score_panel=score_panel)
        def_w = expand_category_to_symbol_weights(cw, intra_vp_t2, all_symbols)
        w_softmax_vp = assemble(base_topk, def_w, ef, p["rebal_threshold"])

        # M6_top3_MVO0.3_vp
        cw = cross_category_weights(cat_ret, sel3, method="mvo_shrunk",
                                          score_panel=score_panel, shrink=0.3)
        def_w = expand_category_to_symbol_weights(cw, intra_vp_t2, all_symbols)
        w_mvo = assemble(base_topk, def_w, ef, p["rebal_threshold"])

        # M6_softmax_tk
        cw = cross_category_weights(cat_ret, sel_all, method="softmax", score_panel=score_panel)
        def_w = expand_category_to_symbol_weights(cw, intra_tk_t2, all_symbols)
        w_softmax_tk = assemble(base_topk, def_w, ef, p["rebal_threshold"])

        # static_RP_vp (no matrix)
        cw = cross_category_weights(cat_ret, sel_all, method="risk_parity")
        def_w = expand_category_to_symbol_weights(cw, intra_vp_t2, all_symbols)
        w_static_rp = assemble(base_topk, def_w, ef, p["rebal_threshold"])

        for label, ww in [
            ("R30", w_r30), ("M6_top1_vp", w_top1),
            ("M6_top2_RP_vp", w_top2_rp), ("M6_top3_RP_vp", w_top3_rp),
            ("M6_softmax_vp", w_softmax_vp),
            ("M6_top3_MVO0.3_vp", w_mvo),
            ("M6_softmax_tk", w_softmax_tk),
            ("static_RP_vp", w_static_rp),
        ]:
            res = run_backtest(ww, panels["close"], panels["open"], panels["amount"], cost_cfg)
            pnls[label].append(res.pnl_net.loc[test_start:step_end])

        if wi % 5 == 0 or wi == len(starts) - 1:
            print(f"  [{wi+1}/{len(starts)}] done {test_start.date()}..{test_end.date()}")

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

    print("\n=== WFA Comparison ===")
    sdf = pd.DataFrame(summary).T
    print(sdf[["sharpe", "ann_ret", "ann_vol", "max_dd", "calmar"]].round(3).to_string())
    sdf.to_csv(OUT / "wfa_v13_summary.csv")

    print("\n=== Per-year WF Sharpe ===")
    print(py_table.round(3).to_string())
    py_table.to_csv(OUT / "wfa_v13_per_year.csv")

    print(f"\nWall-clock: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
