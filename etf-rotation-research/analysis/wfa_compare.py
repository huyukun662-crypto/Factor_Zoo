"""WFA comparison: R30 (no overlay) vs R37 (gold-conditioning overlay).

Same windows, same fixed signal params, same per-window re-derived
(regime × CN_CPI) mapping. The ONLY difference is the gold-conditioning
overlay applied (R37) or not (R30).

# [GUARDRAIL] All windows fall within IS_END=2023-12-31.

Output: report/outputs/wfa_compare_*.csv
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
from analysis.iterate_is_v7 import gold_conditioned_router  # noqa: E402
from analysis.wfa_is import (  # noqa: E402
    R37_GATE_FULL, R37_GATE_OFF, R37_OVERLAY, R37_PARAMS,
    STEP, TEST_WINDOW, TRAIN_WINDOW,
    _assemble, _build_signals, _daily_def_from_mapping,
    _def_w_from_daily, _equity_frac,
)
from data.fetch_macro import fetch_all_macro  # noqa: E402
from strategy.backtest import (  # noqa: E402
    CostConfig, annualize_metrics, per_year_metrics, run_backtest,
)
from strategy.defensive import (  # noqa: E402
    EXPANDED_DEFENSIVE, per_regime_per_macro_best,
)
from strategy.portfolio import _topk_equal_weight  # noqa: E402
from strategy.regime import build_defensive_returns, build_regime_panel  # noqa: E402
from strategy.universe import (  # noqa: E402
    BENCHMARK_SYMBOL, BOND_OR_MONEY_SET,
)

OUT = REPO_ROOT / "report" / "outputs"


def main():
    t0 = time.time()
    panels = load_is_panels()
    macro = fetch_all_macro()
    bench = panels["close"][BENCHMARK_SYMBOL]
    regime_panel = build_regime_panel(bench, macro=macro, ma_window=200, vol_window=60)

    p = expand_param(R37_PARAMS)
    rsrs, score, elig = _build_signals(panels, p)
    base_topk = _topk_equal_weight(score, elig, p["top_k"])

    defensive_pool = [s for s in EXPANDED_DEFENSIVE if s in panels["close"].columns]
    def_returns = build_defensive_returns(panels["close"], defensive_pool)
    cn_cpi_state = pd.cut(regime_panel["cpi_yoy"], [-np.inf, 1.0, 3.0, np.inf],
                            labels=["low", "mid", "high"]).astype(str)

    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)
    all_symbols = list(panels["close"].columns)
    ef = _equity_frac(regime_panel, R37_GATE_OFF, R37_GATE_FULL)

    full_dates = panels["close"].index
    n_dates = len(full_dates)
    starts = list(range(0, n_dates - TRAIN_WINDOW - TEST_WINDOW + 1, STEP))
    print(f"WFA comparison: {len(starts)} windows")

    rows = []  # one row per window with both R30 and R37 metrics

    r30_step_pnls = []
    r37_step_pnls = []

    for wi, s_idx in enumerate(starts):
        train_start = full_dates[s_idx]
        train_end = full_dates[s_idx + TRAIN_WINDOW - 1]
        test_start_idx = s_idx + TRAIN_WINDOW
        test_start = full_dates[test_start_idx]
        test_end_idx = min(s_idx + TRAIN_WINDOW + TEST_WINDOW - 1, n_dates - 1)
        test_end = full_dates[test_end_idx]
        step_end_idx = min(test_start_idx + STEP - 1, n_dates - 1)
        step_end = full_dates[step_end_idx]

        # Train mapping (shared by both R30 and R37)
        train_mask = (def_returns.index >= train_start) & (def_returns.index <= train_end)
        train_returns = def_returns.loc[train_mask]
        train_regime = regime_panel.loc[train_mask, "regime_state_2"]
        train_cpi = cn_cpi_state.loc[train_mask]
        if train_regime.dropna().empty or train_returns.empty:
            continue
        mapping = per_regime_per_macro_best(train_regime, train_cpi, train_returns,
                                              metric="sharpe_min_vol", min_obs=15)
        if not mapping:
            continue

        daily_base = _daily_def_from_mapping(regime_panel["regime_state_2"], cn_cpi_state, mapping)

        # ---- R30: just use base mapping ----
        def_w_r30 = _def_w_from_daily(daily_base, all_symbols)
        w_r30 = _assemble(base_topk, def_w_r30, ef, p["rebal_threshold"])
        res_r30 = run_backtest(w_r30, panels["close"], panels["open"], panels["amount"], cost_cfg)
        pnl_r30 = res_r30.pnl_net

        # ---- R37: apply gold-conditioning overlay ----
        daily_cond = gold_conditioned_router(daily_base, regime_panel,
                                                real_rate_pos_thresh=R37_OVERLAY["real_rate_pos_thresh"],
                                                real_rate_neg_thresh=R37_OVERLAY["real_rate_neg_thresh"],
                                                dxy_mom_thresh=R37_OVERLAY["dxy_mom_thresh"],
                                                fallback_when_gold_bad=R37_OVERLAY["fallback_when_gold_bad"])
        def_w_r37 = _def_w_from_daily(daily_cond, all_symbols)
        w_r37 = _assemble(base_topk, def_w_r37, ef, p["rebal_threshold"])
        res_r37 = run_backtest(w_r37, panels["close"], panels["open"], panels["amount"], cost_cfg)
        pnl_r37 = res_r37.pnl_net

        # Slice
        train_pnl_r30 = pnl_r30.loc[train_start:train_end]
        train_pnl_r37 = pnl_r37.loc[train_start:train_end]
        test_pnl_r30 = pnl_r30.loc[test_start:test_end]
        test_pnl_r37 = pnl_r37.loc[test_start:test_end]
        step_pnl_r30 = pnl_r30.loc[test_start:step_end]
        step_pnl_r37 = pnl_r37.loc[test_start:step_end]

        r30_step_pnls.append(step_pnl_r30)
        r37_step_pnls.append(step_pnl_r37)

        m_r30_train = annualize_metrics(train_pnl_r30)
        m_r30_test = annualize_metrics(test_pnl_r30)
        m_r37_train = annualize_metrics(train_pnl_r37)
        m_r37_test = annualize_metrics(test_pnl_r37)

        # Count days where overlay actually changed defensive
        changed_in_test = int(((daily_cond.loc[test_start:test_end]
                                 != daily_base.loc[test_start:test_end]).sum()))

        rows.append({
            "window": wi,
            "train_start": train_start.strftime("%Y-%m-%d"),
            "test_start": test_start.strftime("%Y-%m-%d"),
            "test_end": test_end.strftime("%Y-%m-%d"),
            "r30_train_sharpe": m_r30_train["sharpe"],
            "r30_test_sharpe": m_r30_test["sharpe"],
            "r30_test_ret": m_r30_test["ann_ret"],
            "r30_test_dd": m_r30_test["max_dd"],
            "r37_train_sharpe": m_r37_train["sharpe"],
            "r37_test_sharpe": m_r37_test["sharpe"],
            "r37_test_ret": m_r37_test["ann_ret"],
            "r37_test_dd": m_r37_test["max_dd"],
            "delta_test_sharpe": m_r37_test["sharpe"] - m_r30_test["sharpe"],
            "delta_test_ret": m_r37_test["ann_ret"] - m_r30_test["ann_ret"],
            "overlay_changed_days": changed_in_test,
        })
        if wi % 5 == 0 or wi == len(starts) - 1:
            print(f"  [{wi+1}/{len(starts)}] test {test_start.date()}..{test_end.date()}  "
                  f"R30={m_r30_test['sharpe']:+.2f}  R37={m_r37_test['sharpe']:+.2f}  "
                  f"Δ={m_r37_test['sharpe']-m_r30_test['sharpe']:+.2f}  "
                  f"changed={changed_in_test}d")

    if not rows:
        raise RuntimeError("no windows produced")

    win_df = pd.DataFrame(rows)
    win_df.to_csv(OUT / "wfa_compare_windows.csv", index=False)

    # Concat WF curves
    r30_wf = pd.concat(r30_step_pnls).sort_index()
    r30_wf = r30_wf[~r30_wf.index.duplicated(keep="first")]
    r37_wf = pd.concat(r37_step_pnls).sort_index()
    r37_wf = r37_wf[~r37_wf.index.duplicated(keep="first")]
    r30_metrics = annualize_metrics(r30_wf)
    r37_metrics = annualize_metrics(r37_wf)
    r30_per_year = per_year_metrics(r30_wf)
    r37_per_year = per_year_metrics(r37_wf)

    pd.DataFrame({"r30_pnl": r30_wf, "r37_pnl": r37_wf}).to_csv(OUT / "wfa_compare_pnl.csv")
    r30_per_year.to_csv(OUT / "wfa_compare_per_year_r30.csv")
    r37_per_year.to_csv(OUT / "wfa_compare_per_year_r37.csv")

    # Summary
    summary = {
        "n_windows": len(rows),
        "r30_wf_sharpe": r30_metrics["sharpe"],
        "r37_wf_sharpe": r37_metrics["sharpe"],
        "delta_wf_sharpe": r37_metrics["sharpe"] - r30_metrics["sharpe"],
        "r30_wf_ret": r30_metrics["ann_ret"],
        "r37_wf_ret": r37_metrics["ann_ret"],
        "r30_wf_dd": r30_metrics["max_dd"],
        "r37_wf_dd": r37_metrics["max_dd"],
        "r30_mean_test_sharpe": float(win_df["r30_test_sharpe"].mean()),
        "r37_mean_test_sharpe": float(win_df["r37_test_sharpe"].mean()),
        "r30_mean_train_sharpe": float(win_df["r30_train_sharpe"].mean()),
        "r37_mean_train_sharpe": float(win_df["r37_train_sharpe"].mean()),
        "r30_wf_efficiency": float(win_df["r30_test_sharpe"].mean() / win_df["r30_train_sharpe"].mean()) if win_df["r30_train_sharpe"].mean() > 0 else float("nan"),
        "r37_wf_efficiency": float(win_df["r37_test_sharpe"].mean() / win_df["r37_train_sharpe"].mean()) if win_df["r37_train_sharpe"].mean() > 0 else float("nan"),
        "windows_r37_better": int((win_df["delta_test_sharpe"] > 0).sum()),
        "windows_r37_worse": int((win_df["delta_test_sharpe"] < 0).sum()),
        "windows_tied": int((win_df["delta_test_sharpe"] == 0).sum()),
        "mean_overlay_changed_days_per_window": float(win_df["overlay_changed_days"].mean()),
        "median_overlay_changed_days_per_window": float(win_df["overlay_changed_days"].median()),
    }

    print("\n=== Side-by-side WFA summary ===")
    for k, v in summary.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.4f}")
        else:
            print(f"  {k}: {v}")

    pd.DataFrame([summary]).to_csv(OUT / "wfa_compare_summary.csv", index=False)

    # Per-year side-by-side
    py_compare = pd.DataFrame({
        "r30_sharpe": r30_per_year["sharpe"],
        "r37_sharpe": r37_per_year["sharpe"],
        "r30_ret": r30_per_year["ann_ret"],
        "r37_ret": r37_per_year["ann_ret"],
        "r30_dd": r30_per_year["max_dd"],
        "r37_dd": r37_per_year["max_dd"],
    })
    py_compare["delta_sharpe"] = py_compare["r37_sharpe"] - py_compare["r30_sharpe"]
    print("\nPer-year side-by-side WF Sharpe:")
    print(py_compare.round(3).to_string())
    py_compare.to_csv(OUT / "wfa_compare_per_year.csv")

    print(f"\nWall-clock: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
