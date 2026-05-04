"""WFA on R41 (double-pressure override → 511260 国开) vs R30 baseline.

Same setup as wfa_compare.py: 27 windows, 756/252/63.
Per window: re-derive (regime × CN_CPI) sharpe_min_vol mapping (R30 base),
then apply double-pressure override (R41).

Three variants compared:
  R30           : pure (regime × CN_CPI) mapping, no override
  R41           : + override → 511260 when (dxy_mom>0.04 AND usdcny_mom>0.02)
  R42_pool      : + override → equal-weight {511260, 511880, 162411}

# [GUARDRAIL] All within IS_END=2023-12-31.
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
    _build_signals, _equity_frac, _daily_def_from_mapping,
    _def_w_from_daily, assemble, double_pressure_override,
)
from analysis.wfa_is import (  # noqa: E402
    R37_GATE_FULL, R37_GATE_OFF, R37_PARAMS,
    STEP, TEST_WINDOW, TRAIN_WINDOW,
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

DXY_THRESH = 0.04
RMB_THRESH = 0.02
POOL = ["511260", "511880", "162411"]


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
    print(f"WFA windows: {len(starts)}")

    rows = []
    r30_pnls, r41_pnls, r42_pnls = [], [], []

    for wi, s_idx in enumerate(starts):
        train_start = full_dates[s_idx]
        train_end = full_dates[s_idx + TRAIN_WINDOW - 1]
        test_start_idx = s_idx + TRAIN_WINDOW
        test_start = full_dates[test_start_idx]
        test_end_idx = min(s_idx + TRAIN_WINDOW + TEST_WINDOW - 1, n_dates - 1)
        test_end = full_dates[test_end_idx]
        step_end_idx = min(test_start_idx + STEP - 1, n_dates - 1)
        step_end = full_dates[step_end_idx]

        # Train mapping on training data only
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

        # ---- R30: base mapping ----
        def_w_r30 = _def_w_from_daily(daily_base, all_symbols)
        w_r30 = assemble(base_topk, def_w_r30, ef, p["rebal_threshold"])
        res_r30 = run_backtest(w_r30, panels["close"], panels["open"], panels["amount"], cost_cfg)
        pnl_r30 = res_r30.pnl_net

        # ---- R41: override → 511260 ----
        daily_r41 = double_pressure_override(daily_base, regime_panel,
                                                DXY_THRESH, RMB_THRESH, "511260")
        def_w_r41 = _def_w_from_daily(daily_r41, all_symbols)
        w_r41 = assemble(base_topk, def_w_r41, ef, p["rebal_threshold"])
        res_r41 = run_backtest(w_r41, panels["close"], panels["open"], panels["amount"], cost_cfg)
        pnl_r41 = res_r41.pnl_net

        # ---- R42_pool: override → pool ----
        def_w_r42 = _def_w_from_daily(daily_base, all_symbols).copy()
        mask_dp = ((regime_panel["dxy_mom_60"] > DXY_THRESH) &
                    (regime_panel["usdcny_mom_60"] > RMB_THRESH)).fillna(False)
        for dt in regime_panel.index[mask_dp]:
            for sym in def_w_r42.columns:
                def_w_r42.at[dt, sym] = 0.0
            for s in POOL:
                if s in def_w_r42.columns:
                    def_w_r42.at[dt, s] = 1.0 / len(POOL)
        w_r42 = assemble(base_topk, def_w_r42, ef, p["rebal_threshold"])
        res_r42 = run_backtest(w_r42, panels["close"], panels["open"], panels["amount"], cost_cfg)
        pnl_r42 = res_r42.pnl_net

        # Slice
        r30_step = pnl_r30.loc[test_start:step_end]
        r41_step = pnl_r41.loc[test_start:step_end]
        r42_step = pnl_r42.loc[test_start:step_end]

        r30_pnls.append(r30_step)
        r41_pnls.append(r41_step)
        r42_pnls.append(r42_step)

        # Test segment metrics
        r30_test = annualize_metrics(pnl_r30.loc[test_start:test_end])
        r41_test = annualize_metrics(pnl_r41.loc[test_start:test_end])
        r42_test = annualize_metrics(pnl_r42.loc[test_start:test_end])
        train_r30 = annualize_metrics(pnl_r30.loc[train_start:train_end])
        train_r41 = annualize_metrics(pnl_r41.loc[train_start:train_end])
        train_r42 = annualize_metrics(pnl_r42.loc[train_start:train_end])

        n_dp_in_test = int(((regime_panel["dxy_mom_60"].loc[test_start:test_end] > DXY_THRESH) &
                              (regime_panel["usdcny_mom_60"].loc[test_start:test_end] > RMB_THRESH))
                             .fillna(False).sum())

        rows.append({
            "window": wi,
            "test_start": test_start.strftime("%Y-%m-%d"),
            "test_end": test_end.strftime("%Y-%m-%d"),
            "n_dp_days_in_test": n_dp_in_test,
            "r30_train_sh": train_r30["sharpe"], "r30_test_sh": r30_test["sharpe"],
            "r30_test_ret": r30_test["ann_ret"], "r30_test_dd": r30_test["max_dd"],
            "r41_train_sh": train_r41["sharpe"], "r41_test_sh": r41_test["sharpe"],
            "r41_test_ret": r41_test["ann_ret"], "r41_test_dd": r41_test["max_dd"],
            "r42_train_sh": train_r42["sharpe"], "r42_test_sh": r42_test["sharpe"],
            "r42_test_ret": r42_test["ann_ret"], "r42_test_dd": r42_test["max_dd"],
            "delta_r41_r30": r41_test["sharpe"] - r30_test["sharpe"],
            "delta_r42_r30": r42_test["sharpe"] - r30_test["sharpe"],
        })
        if wi % 5 == 0 or wi == len(starts) - 1:
            print(f"  [{wi+1}/{len(starts)}] test {test_start.date()}..{test_end.date()}  "
                  f"R30={r30_test['sharpe']:+.2f}  R41={r41_test['sharpe']:+.2f}  "
                  f"R42={r42_test['sharpe']:+.2f}  dp_days={n_dp_in_test}")

    if not rows:
        raise RuntimeError("no windows")

    df_w = pd.DataFrame(rows)
    df_w.to_csv(OUT / "wfa_dp_windows.csv", index=False)

    # Concat WF curves
    r30_wf = pd.concat(r30_pnls).sort_index()
    r41_wf = pd.concat(r41_pnls).sort_index()
    r42_wf = pd.concat(r42_pnls).sort_index()
    r30_wf = r30_wf[~r30_wf.index.duplicated(keep="first")]
    r41_wf = r41_wf[~r41_wf.index.duplicated(keep="first")]
    r42_wf = r42_wf[~r42_wf.index.duplicated(keep="first")]

    m_r30 = annualize_metrics(r30_wf)
    m_r41 = annualize_metrics(r41_wf)
    m_r42 = annualize_metrics(r42_wf)
    py_r30 = per_year_metrics(r30_wf)
    py_r41 = per_year_metrics(r41_wf)
    py_r42 = per_year_metrics(r42_wf)

    print("\n=== WFA Side-by-side (R30 vs R41 vs R42_pool) ===")
    summary = {
        "R30": {"sharpe": m_r30["sharpe"], "ret": m_r30["ann_ret"], "vol": m_r30["ann_vol"],
                "dd": m_r30["max_dd"], "calmar": m_r30["calmar"]},
        "R41 override→511260": {"sharpe": m_r41["sharpe"], "ret": m_r41["ann_ret"], "vol": m_r41["ann_vol"],
                                  "dd": m_r41["max_dd"], "calmar": m_r41["calmar"]},
        "R42 pool {国开,货币,油气}": {"sharpe": m_r42["sharpe"], "ret": m_r42["ann_ret"], "vol": m_r42["ann_vol"],
                                  "dd": m_r42["max_dd"], "calmar": m_r42["calmar"]},
    }
    for name, m in summary.items():
        print(f"  {name:40s}  Sharpe={m['sharpe']:.3f}  Ret={m['ret']*100:.2f}%  "
              f"Vol={m['vol']*100:.2f}%  DD={m['dd']*100:.2f}%  Calmar={m['calmar']:.2f}")
    pd.DataFrame(summary).T.to_csv(OUT / "wfa_dp_summary.csv")

    print("\nPer-year side-by-side WF Sharpe:")
    py_compare = pd.DataFrame({
        "r30_sh": py_r30["sharpe"], "r41_sh": py_r41["sharpe"], "r42_sh": py_r42["sharpe"],
        "r30_ret": py_r30["ann_ret"], "r41_ret": py_r41["ann_ret"], "r42_ret": py_r42["ann_ret"],
    })
    print(py_compare.round(3).to_string())
    py_compare.to_csv(OUT / "wfa_dp_per_year.csv")

    print("\n2022 deep-dive (the failure year):")
    if 2022 in py_r30.index:
        print(f"  R30 2022:  Sharpe={py_r30.loc[2022,'sharpe']:.3f}  Ret={py_r30.loc[2022,'ann_ret']*100:.2f}%  DD={py_r30.loc[2022,'max_dd']*100:.2f}%")
        print(f"  R41 2022:  Sharpe={py_r41.loc[2022,'sharpe']:.3f}  Ret={py_r41.loc[2022,'ann_ret']*100:.2f}%  DD={py_r41.loc[2022,'max_dd']*100:.2f}%")
        print(f"  R42 2022:  Sharpe={py_r42.loc[2022,'sharpe']:.3f}  Ret={py_r42.loc[2022,'ann_ret']*100:.2f}%  DD={py_r42.loc[2022,'max_dd']*100:.2f}%")

    head_to_head = {
        "r41_vs_r30_better": int((df_w["delta_r41_r30"] > 0).sum()),
        "r41_vs_r30_worse": int((df_w["delta_r41_r30"] < 0).sum()),
        "r41_vs_r30_tied": int((df_w["delta_r41_r30"] == 0).sum()),
        "r42_vs_r30_better": int((df_w["delta_r42_r30"] > 0).sum()),
        "r42_vs_r30_worse": int((df_w["delta_r42_r30"] < 0).sum()),
        "r42_vs_r30_tied": int((df_w["delta_r42_r30"] == 0).sum()),
    }
    print("\nHead-to-head:")
    for k, v in head_to_head.items():
        print(f"  {k}: {v}")

    print(f"\nWall-clock: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
