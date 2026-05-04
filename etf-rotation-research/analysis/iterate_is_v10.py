"""V10: R50-R57 — (A) intra-category dynamic + EPO; (B) velocity matrices.

(A) Intra-category selection variants:
  R50 M1 + intra-category top-1 by RSRS+mom score
  R51 M1 + intra-category top-2 by score
  R52 M1 + intra-category EPO (w_shrink in {0.3, 0.5, 0.7})

(B) New macro matrix axes:
  R53 M6  CPI velocity × PMI velocity  (4-cell)
  R54 M7  CPI level × M2 YoY level
  R55 M8  PMI level × CPI velocity
  R56 M9  PMI velocity × CPI velocity (sub-variant)
  R57 best-of-(A) on best-of-(B)

# [GUARDRAIL] All within IS (2013-2023). Matrix derived from full IS for these IS rounds.
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
from analysis.iterate_is_v9 import (  # noqa: E402
    _build_signals, _equity_frac, assemble, matrix_defensive_weights,
)
from analysis.macro_matrix import (  # noqa: E402
    _bucket_cpi, _bucket_dxy_strong, _bucket_pmi, _bucket_real_rate,
    best_category_per_cell, per_cell_category_score,
)
from data.fetch_macro import fetch_all_macro  # noqa: E402
from strategy.backtest import (  # noqa: E402
    CostConfig, annualize_metrics, per_year_metrics, run_backtest,
)
from strategy.categories import (  # noqa: E402
    CATEGORIES, build_category_returns, build_category_weights,
)
from strategy.intra_category import (  # noqa: E402
    intra_category_epo_panel, intra_category_topk,
)
from strategy.portfolio import _topk_equal_weight  # noqa: E402
from strategy.regime import build_regime_panel  # noqa: E402
from strategy.universe import (  # noqa: E402
    BENCHMARK_SYMBOL, BOND_OR_MONEY_SET,
)

OUT = REPO_ROOT / "report" / "outputs"


def _bucket_velocity_3(s: pd.Series, threshold: float = 0.5) -> pd.Series:
    """3-level bucket for velocities: rising / flat / falling."""
    return pd.Series(
        np.where(s > threshold, "rising",
                 np.where(s < -threshold, "falling", "flat")),
        index=s.index,
    )


def _bucket_m2(s: pd.Series) -> pd.Series:
    """3-level bucket for M2 YoY: tight (<8), neutral (8-12), loose (≥12)."""
    return pd.cut(s, [-np.inf, 8.0, 12.0, np.inf],
                   labels=["tight", "neutral", "loose"]).astype(str)


def _matrix_intra_defensive(a1: pd.Series, a2: pd.Series,
                              cell_to_category: dict[tuple, str],
                              score_panel: pd.DataFrame,
                              all_symbols: list[str],
                              method: str = "ew",
                              top_k: int = 1,
                              w_shrink: float = 0.5,
                              returns_panel: pd.DataFrame = None,
                              default_category: str = "红利低波") -> pd.DataFrame:
    """Build defensive weight panel: for each day, look up cell -> category,
    then within category, use chosen intra-method.

    method:
      'ew'    - equal-weight constituents (matches macro_matrix.matrix_defensive_weights)
      'topk'  - top-k by score within category
      'epo'   - EPO weighting using returns_panel + score_panel signals
    """
    out = pd.DataFrame(0.0, index=score_panel.index, columns=all_symbols)

    # Pre-compute: for 'topk' method, we can do per-category panels and slice
    if method == "topk":
        # Compute top-k weight panels for each category once
        topk_panels = {cat: intra_category_topk(score_panel, cat, k=top_k,
                                                  all_symbols=all_symbols)
                        for cat in CATEGORIES}
    elif method == "epo":
        if returns_panel is None:
            raise ValueError("epo requires returns_panel")
        epo_panels = {cat: intra_category_epo_panel(returns_panel, cat, score_panel,
                                                       w_shrink=w_shrink,
                                                       cov_window=252,
                                                       rebal_freq=21,
                                                       all_symbols=all_symbols)
                       for cat in CATEGORIES}
    else:
        # equal-weight: compute once per category
        ew_w = {cat: build_category_weights(cat, all_symbols) for cat in CATEGORIES}

    for dt in score_panel.index:
        v1 = a1.get(dt) if dt in a1.index else None
        v2 = a2.get(dt) if dt in a2.index else None
        if pd.isna(v1) or pd.isna(v2):
            cat = default_category
        else:
            cat = cell_to_category.get((str(v1), str(v2)), default_category)

        if method == "topk":
            out.loc[dt] = topk_panels[cat].loc[dt].values
        elif method == "epo":
            out.loc[dt] = epo_panels[cat].loc[dt].values
        else:
            out.loc[dt] = ew_w[cat].values
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

    rsrs, score, elig = _build_signals(panels, p)  # `score` is per-symbol composite
    base_topk = _topk_equal_weight(score, elig, p["top_k"])

    cat_ret = build_category_returns(panels["close"])
    sym_returns = panels["close"].pct_change().fillna(0.0)

    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)
    all_symbols = list(panels["close"].columns)
    ef = _equity_frac(regime_panel, {0, 1, 3}, {2})

    # M1 axes
    cpi_b = _bucket_cpi(regime_panel["cpi_yoy"])
    pmi_b = _bucket_pmi(regime_panel["pmi"])
    cpi_vel_b = _bucket_velocity_3(regime_panel.get("cpi_velocity_3m", pd.Series(0, index=regime_panel.index)),
                                       threshold=0.3)
    pmi_vel_b = _bucket_velocity_3(regime_panel.get("pmi_velocity_3m", pd.Series(0, index=regime_panel.index)),
                                       threshold=0.5)
    m2_b = _bucket_m2(regime_panel.get("m2_yoy", pd.Series(10, index=regime_panel.index)))

    rows = []

    # ---- Reference: M1 with equal-weight (matches R47) ----
    print("=== Reference: M1 (PMI × CPI) equal-weight ===")
    score_df = per_cell_category_score(pmi_b, cpi_b, cat_ret, metric="sharpe_min_vol")
    M1_map = best_category_per_cell(score_df)
    print(f"  M1 mapping: {M1_map}")
    def_w = _matrix_intra_defensive(pmi_b, cpi_b, M1_map, score, all_symbols, method="ew")
    w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
    rows.append(to_row(0, "M1 ew (ref)", p, {"matrix": "M1", "method": "ew"}, res.metrics))
    print(f"  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%")

    # ========= (A) Intra-category variants on M1 =========
    print("\n=== R50: M1 + intra-category top-1 ===")
    def_w = _matrix_intra_defensive(pmi_b, cpi_b, M1_map, score, all_symbols,
                                       method="topk", top_k=1)
    w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
    rows.append(to_row(50, "M1 top-1", p, {"matrix": "M1", "method": "topk", "k": 1}, res.metrics))
    print(f"  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%")

    print("\n=== R51: M1 + intra-category top-2 ===")
    def_w = _matrix_intra_defensive(pmi_b, cpi_b, M1_map, score, all_symbols,
                                       method="topk", top_k=2)
    w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
    rows.append(to_row(51, "M1 top-2", p, {"matrix": "M1", "method": "topk", "k": 2}, res.metrics))
    print(f"  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%")

    print("\n=== R52: M1 + intra-category EPO ===")
    for ws in [0.3, 0.5, 0.7]:
        def_w = _matrix_intra_defensive(pmi_b, cpi_b, M1_map, score, all_symbols,
                                           method="epo", w_shrink=ws,
                                           returns_panel=sym_returns)
        w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        rows.append(to_row(52, f"M1 EPO w={ws}", p,
                            {"matrix": "M1", "method": "epo", "w_shrink": ws},
                            res.metrics))
        print(f"  w_shrink={ws}  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%")

    # ========= (B) New matrix axes =========
    print("\n=== R53: M6 (CPI velocity × PMI velocity) ===")
    score_df = per_cell_category_score(cpi_vel_b, pmi_vel_b, cat_ret, metric="sharpe_min_vol")
    if not score_df.empty:
        M6_map = best_category_per_cell(score_df)
        print(f"  M6 mapping ({len(M6_map)} cells):")
        for (a, b), c in sorted(M6_map.items()):
            n = int(score_df[(score_df["a1"] == a) & (score_df["a2"] == b)]["n"].iloc[0])
            print(f"    cpi_vel={a:8s} pmi_vel={b:8s} n={n:4d}  -> {c}")
        def_w = _matrix_intra_defensive(cpi_vel_b, pmi_vel_b, M6_map, score, all_symbols, method="ew")
        w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        rows.append(to_row(53, "M6 ew", p, {"matrix": "M6"}, res.metrics))
        print(f"  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%")

    print("\n=== R54: M7 (CPI level × M2 YoY) ===")
    score_df = per_cell_category_score(cpi_b, m2_b, cat_ret, metric="sharpe_min_vol")
    if not score_df.empty:
        M7_map = best_category_per_cell(score_df)
        print(f"  M7 mapping ({len(M7_map)} cells):")
        for (a, b), c in sorted(M7_map.items()):
            n = int(score_df[(score_df["a1"] == a) & (score_df["a2"] == b)]["n"].iloc[0])
            print(f"    cpi={a:5s} m2={b:8s} n={n:4d}  -> {c}")
        def_w = _matrix_intra_defensive(cpi_b, m2_b, M7_map, score, all_symbols, method="ew")
        w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        rows.append(to_row(54, "M7 ew", p, {"matrix": "M7"}, res.metrics))
        print(f"  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%")

    print("\n=== R55: M8 (PMI level × CPI velocity) ===")
    score_df = per_cell_category_score(pmi_b, cpi_vel_b, cat_ret, metric="sharpe_min_vol")
    if not score_df.empty:
        M8_map = best_category_per_cell(score_df)
        print(f"  M8 mapping ({len(M8_map)} cells):")
        for (a, b), c in sorted(M8_map.items()):
            n = int(score_df[(score_df["a1"] == a) & (score_df["a2"] == b)]["n"].iloc[0])
            print(f"    pmi={a:8s} cpi_vel={b:8s} n={n:4d}  -> {c}")
        def_w = _matrix_intra_defensive(pmi_b, cpi_vel_b, M8_map, score, all_symbols, method="ew")
        w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        rows.append(to_row(55, "M8 ew", p, {"matrix": "M8"}, res.metrics))
        print(f"  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%")

    print("\n=== R56: M9 (PMI velocity × CPI level) ===")
    score_df = per_cell_category_score(pmi_vel_b, cpi_b, cat_ret, metric="sharpe_min_vol")
    if not score_df.empty:
        M9_map = best_category_per_cell(score_df)
        print(f"  M9 mapping ({len(M9_map)} cells):")
        for (a, b), c in sorted(M9_map.items()):
            n = int(score_df[(score_df["a1"] == a) & (score_df["a2"] == b)]["n"].iloc[0])
            print(f"    pmi_vel={a:8s} cpi={b:5s} n={n:4d}  -> {c}")
        def_w = _matrix_intra_defensive(pmi_vel_b, cpi_b, M9_map, score, all_symbols, method="ew")
        w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        rows.append(to_row(56, "M9 ew", p, {"matrix": "M9"}, res.metrics))
        print(f"  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%")

    # ========= R57: combine best-(A) intra-method on best-(B) matrix =========
    print("\n=== R57: best matrix + best intra-method ===")
    df_now = pd.DataFrame(rows)

    # Find best matrix from the equal-weight rounds (R0 ref / R53-R56)
    matrix_rounds = df_now[df_now["round"].isin([0, 53, 54, 55, 56])].copy()
    best_matrix_row = matrix_rounds.sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"  Best matrix base (ew): {best_matrix_row['matrix']} Sharpe={best_matrix_row['sharpe_net']:.3f}")

    # Find best intra-method from R50-R52
    intra_rounds = df_now[df_now["round"].isin([50, 51, 52])].copy()
    best_intra_row = intra_rounds.sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"  Best intra-method (on M1): {best_intra_row['method']} k/w={best_intra_row.get('k', best_intra_row.get('w_shrink'))}")

    # Apply best intra-method on best matrix
    target_matrix = best_matrix_row["matrix"]
    target_method = best_intra_row["method"]
    matrix_axes = {"M1": (pmi_b, cpi_b), "M6": (cpi_vel_b, pmi_vel_b),
                    "M7": (cpi_b, m2_b), "M8": (pmi_b, cpi_vel_b),
                    "M9": (pmi_vel_b, cpi_b)}
    if target_matrix not in matrix_axes:
        target_matrix = "M1"
    a1_t, a2_t = matrix_axes[target_matrix]
    score_df = per_cell_category_score(a1_t, a2_t, cat_ret, metric="sharpe_min_vol")
    target_map = best_category_per_cell(score_df)

    if target_method == "topk":
        kt = int(best_intra_row.get("k", 1))
        def_w = _matrix_intra_defensive(a1_t, a2_t, target_map, score, all_symbols,
                                           method="topk", top_k=kt)
        method_desc = f"topk k={kt}"
    elif target_method == "epo":
        ws_t = float(best_intra_row.get("w_shrink", 0.5))
        def_w = _matrix_intra_defensive(a1_t, a2_t, target_map, score, all_symbols,
                                           method="epo", w_shrink=ws_t,
                                           returns_panel=sym_returns)
        method_desc = f"epo w={ws_t}"
    else:
        def_w = _matrix_intra_defensive(a1_t, a2_t, target_map, score, all_symbols,
                                           method="ew")
        method_desc = "ew"

    w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
    rows.append(to_row(57, f"{target_matrix} + {method_desc}",
                        p, {"matrix": target_matrix, "method": target_method},
                        res.metrics))
    print(f"  {target_matrix} + {method_desc}  Sharpe={res.metrics['sharpe']:.3f}  "
          f"Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%")

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "all_candidates_v10.csv", index=False)

    # Sort by Sharpe
    print("\n=== Top 10 across R50-R57 ===")
    print(df.sort_values("sharpe_net", ascending=False).head(10)[
        ["round","label","sharpe_net","ann_ret","ann_vol","max_dd","calmar","ann_turnover"]
    ].to_string(index=False))

    R30_BEST = 1.457
    M1_EW_REF = df[df["round"] == 0]["sharpe_net"].iloc[0]
    print(f"\nReference: R30 IS Sharpe = {R30_BEST:.3f}, M1 ew IS Sharpe = {M1_EW_REF:.3f}")
    print(f"Best of R50-R57: {df[df['round']>0].sort_values('sharpe_net',ascending=False).iloc[0]['label']}  "
          f"Sharpe={df[df['round']>0]['sharpe_net'].max():.3f}")
    print(f"\nWall-clock: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
