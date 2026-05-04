"""V13: R72-R78 — Cross-category risk parity / softmax / MVO + intra-cat vol-parity.

Three-layer defensive construction:
  L1: M6 (CPI vel × PMI vel) → top-N categories per day (by sharpe_min_vol)
  L2: cross-category weighting (equal / risk_parity / softmax / mvo_shrunk)
  L3: intra-category (equal / topk / vol_parity)

Rounds:
  R72 Static risk parity across all 6 cats (no matrix) — control
  R73 M6 top-2 cats + cross equal + intra vol-parity top-2
  R74 M6 top-2 cats + cross risk parity + intra vol-parity top-2
  R75 M6 top-3 cats + cross risk parity + intra vol-parity top-2
  R76 M6 all-6 cats + softmax score + intra vol-parity top-2
  R77 M6 top-3 cats + cross MVO shrunk + intra vol-parity top-2
  R78 best L1×L2 + intra vol-parity top-3 (try k=3 too)

# [GUARDRAIL] All within IS (2013-2023). Matrix from full IS for these IS rounds.
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
from analysis.iterate_is_v9 import (  # noqa: E402
    _build_signals, _equity_frac, assemble,
)
from analysis.iterate_is_v10 import _bucket_velocity_3  # noqa: E402
from analysis.macro_matrix import (  # noqa: E402
    best_category_per_cell, per_cell_category_score,
)
from data.fetch_macro import fetch_all_macro  # noqa: E402
from strategy.backtest import (  # noqa: E402
    CostConfig, run_backtest, per_year_metrics,
)
from strategy.categories import (  # noqa: E402
    CATEGORIES, build_category_returns,
)
from strategy.cross_category import (  # noqa: E402
    build_score_panel, cross_category_weights, daily_top_n_categories,
    expand_category_to_symbol_weights, top_n_categories_per_cell,
)
from strategy.intra_category import (  # noqa: E402
    intra_category_topk_aware, intra_category_vol_parity,
)
from strategy.portfolio import _topk_equal_weight  # noqa: E402
from strategy.regime import build_regime_panel  # noqa: E402
from strategy.universe import (  # noqa: E402
    BENCHMARK_SYMBOL, BOND_OR_MONEY_SET,
)

OUT = REPO_ROOT / "report" / "outputs"


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

    cpi_vel_b = _bucket_velocity_3(regime_panel.get("cpi_velocity_3m"), threshold=0.3)
    pmi_vel_b = _bucket_velocity_3(regime_panel.get("pmi_velocity_3m"), threshold=0.5)

    # M6 score table (full IS)
    m6_score_df = per_cell_category_score(cpi_vel_b, pmi_vel_b, cat_ret, metric="sharpe_min_vol")
    m6_map = best_category_per_cell(m6_score_df)
    score_panel = build_score_panel(cpi_vel_b, pmi_vel_b, m6_score_df)

    # Pre-compute intra-category panels (vol-parity top-2) — common across rounds
    intra_vol_parity_t2 = {
        cat: intra_category_vol_parity(panels["close"], cat,
                                          vol_lookback=60, top_k=2,
                                          score=score, all_symbols=all_symbols)
        for cat in CATEGORIES
    }
    intra_vol_parity_t3 = {
        cat: intra_category_vol_parity(panels["close"], cat,
                                          vol_lookback=60, top_k=3,
                                          score=score, all_symbols=all_symbols)
        for cat in CATEGORIES
    }
    intra_topk_aware_t2 = {
        cat: intra_category_topk_aware(score, panels["close"], cat, k=2,
                                          all_symbols=all_symbols)
        for cat in CATEGORIES
    }

    rows = []

    # Reference: M6 + top-2 cats (single best per cell) + intra vol-parity (current best)
    print("\n=== R0 ref: M6 single-best + intra vol-parity top-2 ===")
    top1_map = top_n_categories_per_cell(m6_score_df, n=1)
    sel = daily_top_n_categories(cpi_vel_b, pmi_vel_b, top1_map)
    cat_w = cross_category_weights(cat_ret, sel, method="equal")
    def_w = expand_category_to_symbol_weights(cat_w, intra_vol_parity_t2, all_symbols)
    w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
    py = per_year_metrics(res.pnl_net)
    rows.append(to_row(0, "ref M6 top-1 + vol-parity t2", p,
                        {"L1_top": 1, "L2": "equal", "L3": "vol_parity_t2"}, res.metrics))
    print(f"  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%  2018={py.loc[2018,'sharpe']:+.2f}  2022={py.loc[2022,'sharpe']:+.2f}")

    # ========= R72: Static risk parity across all 6 (no matrix) =========
    print("\n=== R72: static risk-parity across all 6 cats (no matrix) ===")
    sel_all = pd.DataFrame(True, index=cpi_vel_b.index, columns=list(CATEGORIES.keys()))
    cat_w = cross_category_weights(cat_ret, sel_all, method="risk_parity")
    def_w = expand_category_to_symbol_weights(cat_w, intra_vol_parity_t2, all_symbols)
    w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
    py = per_year_metrics(res.pnl_net)
    rows.append(to_row(72, "static-RP all 6 + vol-parity t2", p,
                        {"L1_top": "all", "L2": "risk_parity", "L3": "vol_parity_t2"}, res.metrics))
    print(f"  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%  2018={py.loc[2018,'sharpe']:+.2f}  2022={py.loc[2022,'sharpe']:+.2f}")

    # ========= R73: M6 top-2 cats + cross equal + intra vol-parity =========
    print("\n=== R73: M6 top-2 cats + cross equal + intra vol-parity t2 ===")
    top2_map = top_n_categories_per_cell(m6_score_df, n=2)
    sel = daily_top_n_categories(cpi_vel_b, pmi_vel_b, top2_map)
    cat_w = cross_category_weights(cat_ret, sel, method="equal")
    def_w = expand_category_to_symbol_weights(cat_w, intra_vol_parity_t2, all_symbols)
    w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
    py = per_year_metrics(res.pnl_net)
    rows.append(to_row(73, "M6 top-2 cats equal + vol-p t2", p,
                        {"L1_top": 2, "L2": "equal", "L3": "vol_parity_t2"}, res.metrics))
    print(f"  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%  2018={py.loc[2018,'sharpe']:+.2f}  2022={py.loc[2022,'sharpe']:+.2f}")

    # ========= R74: M6 top-2 cats + cross risk parity + intra vol-parity =========
    print("\n=== R74: M6 top-2 cats + cross risk-parity + intra vol-parity t2 ===")
    cat_w = cross_category_weights(cat_ret, sel, method="risk_parity")
    def_w = expand_category_to_symbol_weights(cat_w, intra_vol_parity_t2, all_symbols)
    w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
    py = per_year_metrics(res.pnl_net)
    rows.append(to_row(74, "M6 top-2 cats RP + vol-p t2", p,
                        {"L1_top": 2, "L2": "risk_parity", "L3": "vol_parity_t2"}, res.metrics))
    print(f"  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%  2018={py.loc[2018,'sharpe']:+.2f}  2022={py.loc[2022,'sharpe']:+.2f}")

    # ========= R75: M6 top-3 cats + cross risk parity =========
    print("\n=== R75: M6 top-3 cats + RP + intra vol-parity t2 ===")
    top3_map = top_n_categories_per_cell(m6_score_df, n=3)
    sel = daily_top_n_categories(cpi_vel_b, pmi_vel_b, top3_map)
    cat_w = cross_category_weights(cat_ret, sel, method="risk_parity")
    def_w = expand_category_to_symbol_weights(cat_w, intra_vol_parity_t2, all_symbols)
    w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
    py = per_year_metrics(res.pnl_net)
    rows.append(to_row(75, "M6 top-3 cats RP + vol-p t2", p,
                        {"L1_top": 3, "L2": "risk_parity", "L3": "vol_parity_t2"}, res.metrics))
    print(f"  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%  2018={py.loc[2018,'sharpe']:+.2f}  2022={py.loc[2022,'sharpe']:+.2f}")

    # ========= R76: M6 all-6 cats + softmax score + intra vol-parity =========
    print("\n=== R76: M6 all 6 cats + softmax score + intra vol-parity t2 ===")
    sel_all = pd.DataFrame(True, index=cpi_vel_b.index, columns=list(CATEGORIES.keys()))
    cat_w = cross_category_weights(cat_ret, sel_all, method="softmax", score_panel=score_panel)
    def_w = expand_category_to_symbol_weights(cat_w, intra_vol_parity_t2, all_symbols)
    w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
    py = per_year_metrics(res.pnl_net)
    rows.append(to_row(76, "M6 all softmax + vol-p t2", p,
                        {"L1_top": "all", "L2": "softmax", "L3": "vol_parity_t2"}, res.metrics))
    print(f"  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%  2018={py.loc[2018,'sharpe']:+.2f}  2022={py.loc[2022,'sharpe']:+.2f}")

    # ========= R77: M6 top-3 + MVO shrunk =========
    print("\n=== R77: M6 top-3 + MVO shrunk + intra vol-parity t2 ===")
    sel = daily_top_n_categories(cpi_vel_b, pmi_vel_b, top3_map)
    for sh in [0.3, 0.5, 0.7]:
        cat_w = cross_category_weights(cat_ret, sel, method="mvo_shrunk",
                                            score_panel=score_panel, shrink=sh)
        def_w = expand_category_to_symbol_weights(cat_w, intra_vol_parity_t2, all_symbols)
        w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        py = per_year_metrics(res.pnl_net)
        rows.append(to_row(77, f"M6 top-3 MVO sh={sh} + vol-p t2", p,
                            {"L1_top": 3, "L2": "mvo_shrunk", "shrink": sh,
                             "L3": "vol_parity_t2"}, res.metrics))
        print(f"  shrink={sh}  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%  2018={py.loc[2018,'sharpe']:+.2f}  2022={py.loc[2022,'sharpe']:+.2f}")

    # ========= R78: best L1×L2 + intra vol-parity t3 vs topk_aware =========
    print("\n=== R78: try intra vol-parity t3 + topk-aware on top combos ===")
    df_now = pd.DataFrame(rows)
    best_so_far = df_now[df_now["round"] > 0].sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"  best so far: R{int(best_so_far['round'])} {best_so_far['label']} Sharpe={best_so_far['sharpe_net']:.3f}")

    # Try the best L1+L2 combo with t3 instead of t2
    L1_top = best_so_far.get("L1_top")
    L2 = best_so_far["L2"]
    if L1_top == 1:
        sel_b = daily_top_n_categories(cpi_vel_b, pmi_vel_b, top1_map)
    elif L1_top == 2:
        sel_b = daily_top_n_categories(cpi_vel_b, pmi_vel_b, top2_map)
    elif L1_top == 3:
        sel_b = daily_top_n_categories(cpi_vel_b, pmi_vel_b, top3_map)
    else:
        sel_b = pd.DataFrame(True, index=cpi_vel_b.index, columns=list(CATEGORIES.keys()))

    if L2 == "softmax":
        cat_w_b = cross_category_weights(cat_ret, sel_b, method="softmax", score_panel=score_panel)
    elif L2 == "mvo_shrunk":
        sh = float(best_so_far.get("shrink", 0.5))
        cat_w_b = cross_category_weights(cat_ret, sel_b, method="mvo_shrunk",
                                              score_panel=score_panel, shrink=sh)
    elif L2 == "risk_parity":
        cat_w_b = cross_category_weights(cat_ret, sel_b, method="risk_parity")
    else:
        cat_w_b = cross_category_weights(cat_ret, sel_b, method="equal")

    for intra_label, intra_panel in [("vol-p t3", intra_vol_parity_t3),
                                          ("topk-aware t2", intra_topk_aware_t2)]:
        def_w = expand_category_to_symbol_weights(cat_w_b, intra_panel, all_symbols)
        w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        py = per_year_metrics(res.pnl_net)
        rows.append(to_row(78, f"best L1L2 + intra {intra_label}", p,
                            {"L1_top": L1_top, "L2": L2, "L3": intra_label}, res.metrics))
        print(f"  intra={intra_label}  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%  2018={py.loc[2018,'sharpe']:+.2f}  2022={py.loc[2022,'sharpe']:+.2f}")

    # ---- Persist ----
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "all_candidates_v13.csv", index=False)

    print("\n=== Top 10 across R72-R78 ===")
    print(df[df["round"] > 0].sort_values("sharpe_net", ascending=False).head(10)[
        ["round", "label", "sharpe_net", "ann_ret", "ann_vol", "max_dd", "calmar", "ann_turnover"]
    ].to_string(index=False))

    print(f"\nWall-clock: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
