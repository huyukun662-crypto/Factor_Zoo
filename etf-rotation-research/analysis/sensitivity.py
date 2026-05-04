"""Sensitivity analysis for R77 final strategy.

Generates:
  - 1D perturbation lines for core params (±10/20/30%)
  - 2D heatmaps for two key parameter pairs
  - Saves CSV + PNG artifacts

# [GUARDRAIL] All within IS (2013-2023). Matrix from full IS.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from analysis.is_search import expand_param, load_is_panels  # noqa: E402
from analysis.iterate_is_v9 import _build_signals, _equity_frac, assemble  # noqa: E402
from analysis.iterate_is_v10 import _bucket_velocity_3  # noqa: E402
from analysis.macro_matrix import per_cell_category_score  # noqa: E402
from data.fetch_macro import fetch_all_macro  # noqa: E402
from strategy.backtest import (  # noqa: E402
    CostConfig, run_backtest,
)
from strategy.categories import CATEGORIES, build_category_returns  # noqa: E402
from strategy.cross_category import (  # noqa: E402
    build_score_panel, cross_category_weights, daily_top_n_categories,
    expand_category_to_symbol_weights, top_n_categories_per_cell,
)
from strategy.intra_category import intra_category_vol_parity  # noqa: E402
from strategy.portfolio import _topk_equal_weight  # noqa: E402
from strategy.regime import build_regime_panel  # noqa: E402
from strategy.universe import (  # noqa: E402
    BENCHMARK_SYMBOL, BOND_OR_MONEY_SET,
)

OUT = REPO_ROOT / "report" / "outputs"


def _setup_font():
    cands = ["WenQuanYi Zen Hei", "Noto Sans CJK SC", "SimHei",
              "Microsoft YaHei", "Arial Unicode MS", "DejaVu Sans"]
    avail = {f.name for f in font_manager.fontManager.ttflist}
    chosen = next((c for c in cands if c in avail), "DejaVu Sans")
    plt.rcParams["font.sans-serif"] = [chosen]
    plt.rcParams["axes.unicode_minus"] = False
    return chosen


# Base R77 parameters
BASE = dict(
    rsrs_N=30, rsrs_M=250, mom_L=180,
    lambda_s=0.2, lambda_k=0.0,
    w_rsrs=0.2, top_k=7,
    theta_off=-0.7, theta_on=0.7,
    rebal_threshold=0.4,
    rsrs_form="rsrs_skew",
    cpi_vel_thresh=0.3, pmi_vel_thresh=0.5,
    top_n_cats=3, mvo_shrink=0.3,
    intra_vol_lb=60, intra_top_k=2,
)


def evaluate_r77(panels, regime_panel, cat_ret, all_symbols, params):
    """Run R77 strategy with `params` (dict). Returns (Sharpe_net, ann_ret, max_dd, ann_turnover)."""
    p = expand_param(params)
    p["rsrs_form"] = "rsrs_skew"

    rsrs, score, elig = _build_signals(panels, p)
    base_topk = _topk_equal_weight(score, elig, p["top_k"])

    cpi_vel_b = _bucket_velocity_3(regime_panel.get("cpi_velocity_3m"),
                                       threshold=params["cpi_vel_thresh"])
    pmi_vel_b = _bucket_velocity_3(regime_panel.get("pmi_velocity_3m"),
                                       threshold=params["pmi_vel_thresh"])
    m6_score_df = per_cell_category_score(cpi_vel_b, pmi_vel_b, cat_ret, metric="sharpe_min_vol")
    score_panel = build_score_panel(cpi_vel_b, pmi_vel_b, m6_score_df)

    n_top = int(params["top_n_cats"])
    top_map = top_n_categories_per_cell(m6_score_df, n=n_top)
    sel = daily_top_n_categories(cpi_vel_b, pmi_vel_b, top_map)

    cat_w = cross_category_weights(cat_ret, sel, method="mvo_shrunk",
                                       score_panel=score_panel,
                                       shrink=params["mvo_shrink"],
                                       vol_lookback=60)

    intra_panels = {
        cat: intra_category_vol_parity(panels["close"], cat,
                                          vol_lookback=int(params["intra_vol_lb"]),
                                          top_k=int(params["intra_top_k"]),
                                          score=score, all_symbols=all_symbols)
        for cat in CATEGORIES
    }

    def_w = expand_category_to_symbol_weights(cat_w, intra_panels, all_symbols)

    ef = _equity_frac(regime_panel, {0, 1, 3}, {2})
    w = assemble(base_topk, def_w, ef, p["rebal_threshold"])

    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)
    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
    return {
        "sharpe": res.metrics["sharpe"],
        "ann_ret": res.metrics["ann_ret"],
        "max_dd": res.metrics["max_dd"],
        "calmar": res.metrics["calmar"],
        "ann_turnover": res.metrics["ann_turnover"],
    }


def perturb_param(name, base_val, pct):
    """Apply ±pct% to a numeric base value, with type coercion."""
    if name in ("rsrs_N", "rsrs_M", "mom_L", "top_k", "top_n_cats",
                  "intra_vol_lb", "intra_top_k"):
        return max(1, int(round(base_val * (1 + pct / 100))))
    return float(base_val) * (1 + pct / 100)


def main():
    t0 = time.time()
    _setup_font()
    panels = load_is_panels()
    macro = fetch_all_macro()
    bench = panels["close"][BENCHMARK_SYMBOL]
    regime_panel = build_regime_panel(bench, macro=macro, ma_window=200, vol_window=60)
    cat_ret = build_category_returns(panels["close"])
    all_symbols = list(panels["close"].columns)

    # Base evaluation
    base_res = evaluate_r77(panels, regime_panel, cat_ret, all_symbols, dict(BASE))
    print(f"=== Base R77 ===  Sharpe={base_res['sharpe']:.3f}  "
          f"Ret={base_res['ann_ret']*100:.2f}%  DD={base_res['max_dd']*100:.2f}%")

    # ============= 1D PERTURBATION =============
    PARAMS_TO_PERTURB = ["rsrs_N", "mom_L", "w_rsrs", "top_k", "rebal_threshold",
                          "mvo_shrink", "top_n_cats", "intra_vol_lb"]
    PCTS = [-30, -20, -10, 0, 10, 20, 30]

    perturb_records = []
    for name in PARAMS_TO_PERTURB:
        print(f"\n--- 1D perturbation: {name} (base={BASE[name]}) ---")
        for pct in PCTS:
            params = dict(BASE)
            new_val = perturb_param(name, BASE[name], pct)
            # constrain top_n_cats to [1, 6]
            if name == "top_n_cats":
                new_val = max(1, min(6, int(new_val)))
            # mvo_shrink in [0, 1]
            if name == "mvo_shrink":
                new_val = max(0.0, min(1.0, new_val))
            # w_rsrs in [0, 1]
            if name == "w_rsrs":
                new_val = max(0.0, min(1.0, new_val))
            params[name] = new_val
            r = evaluate_r77(panels, regime_panel, cat_ret, all_symbols, params)
            perturb_records.append({
                "param": name, "pct": pct, "value": new_val,
                "sharpe": r["sharpe"], "ann_ret": r["ann_ret"],
                "max_dd": r["max_dd"], "calmar": r["calmar"],
            })
            print(f"  {name}={new_val} (pct={pct:+3d}%)  Sharpe={r['sharpe']:.3f}  "
                  f"Ret={r['ann_ret']*100:.2f}%  DD={r['max_dd']*100:.2f}%")

    perturb_df = pd.DataFrame(perturb_records)
    perturb_df.to_csv(OUT / "sensitivity_1d.csv", index=False)

    # Plot 1D perturbation
    n_params = len(PARAMS_TO_PERTURB)
    fig, axes = plt.subplots(2, 4, figsize=(16, 8), sharey=True)
    for i, name in enumerate(PARAMS_TO_PERTURB):
        ax = axes[i // 4, i % 4]
        sub = perturb_df[perturb_df["param"] == name]
        ax.plot(sub["pct"], sub["sharpe"], "o-", lw=1.5, color="#1f77b4")
        ax.axhline(base_res["sharpe"], color="#888", ls="--", lw=0.8, label="base")
        ax.axhline(0.5, color="red", ls=":", lw=0.5)
        ax.set_title(f"{name} (base={BASE[name]})")
        ax.set_xlabel("pct change")
        ax.grid(alpha=0.3)
    axes[0, 0].set_ylabel("IS Sharpe")
    axes[1, 0].set_ylabel("IS Sharpe")
    fig.suptitle("R77 单参数 ±10/20/30% 敏感性分析（IS Sharpe）", y=1.02)
    fig.tight_layout()
    fig.savefig(OUT / "sensitivity_1d.png", dpi=140, bbox_inches="tight")
    print(f"\nSaved {OUT / 'sensitivity_1d.png'}")

    # Compute MAX sharpe drop for risk assessment
    drops = []
    for name in PARAMS_TO_PERTURB:
        sub = perturb_df[perturb_df["param"] == name]
        max_drop = base_res["sharpe"] - sub["sharpe"].min()
        drops.append({"param": name, "max_drop": max_drop,
                       "min_sharpe": sub["sharpe"].min(),
                       "max_sharpe": sub["sharpe"].max()})
    drops_df = pd.DataFrame(drops).sort_values("max_drop", ascending=False)
    drops_df.to_csv(OUT / "sensitivity_1d_max_drops.csv", index=False)
    print("\nMax Sharpe drop per param:")
    print(drops_df.to_string(index=False))

    # ============= 2D HEATMAPS =============
    print("\n=== 2D Heatmap 1: rsrs_N × mom_L ===")
    rsrs_grid = [14, 18, 24, 30, 36, 42]
    mom_grid = [60, 90, 120, 150, 180, 252]
    h1 = pd.DataFrame(index=rsrs_grid, columns=mom_grid, dtype=float)
    for n in rsrs_grid:
        for m in mom_grid:
            params = dict(BASE)
            params["rsrs_N"] = n; params["mom_L"] = m
            r = evaluate_r77(panels, regime_panel, cat_ret, all_symbols, params)
            h1.at[n, m] = r["sharpe"]
        print(f"  rsrs_N={n}: " + " ".join(f"L={m}:{h1.at[n,m]:.2f}" for m in mom_grid))
    h1.to_csv(OUT / "sensitivity_heatmap_rsrs_x_mom.csv")

    print("\n=== 2D Heatmap 2: top_n_cats × mvo_shrink ===")
    n_grid = [1, 2, 3, 4, 5, 6]
    sh_grid = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
    h2 = pd.DataFrame(index=n_grid, columns=sh_grid, dtype=float)
    for n in n_grid:
        for sh in sh_grid:
            params = dict(BASE)
            params["top_n_cats"] = n; params["mvo_shrink"] = sh
            r = evaluate_r77(panels, regime_panel, cat_ret, all_symbols, params)
            h2.at[n, sh] = r["sharpe"]
        print(f"  top_n={n}: " + " ".join(f"sh={sh}:{h2.at[n,sh]:.2f}" for sh in sh_grid))
    h2.to_csv(OUT / "sensitivity_heatmap_topn_x_shrink.csv")

    # Plot heatmaps
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ax = axes[0]
    im = ax.imshow(h1.values.astype(float), aspect="auto", cmap="RdYlGn",
                    origin="lower")
    ax.set_xticks(range(len(mom_grid))); ax.set_xticklabels(mom_grid)
    ax.set_yticks(range(len(rsrs_grid))); ax.set_yticklabels(rsrs_grid)
    ax.set_xlabel("mom_L"); ax.set_ylabel("rsrs_N")
    ax.set_title(f"IS Sharpe heatmap: rsrs_N × mom_L (base 30×180={base_res['sharpe']:.2f})")
    for i, n in enumerate(rsrs_grid):
        for j, m in enumerate(mom_grid):
            ax.text(j, i, f"{h1.at[n, m]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax)

    ax = axes[1]
    im = ax.imshow(h2.values.astype(float), aspect="auto", cmap="RdYlGn",
                    origin="lower")
    ax.set_xticks(range(len(sh_grid))); ax.set_xticklabels(sh_grid)
    ax.set_yticks(range(len(n_grid))); ax.set_yticklabels(n_grid)
    ax.set_xlabel("mvo_shrink"); ax.set_ylabel("top_n_cats")
    ax.set_title(f"IS Sharpe heatmap: top_n_cats × mvo_shrink (base 3×0.3={base_res['sharpe']:.2f})")
    for i, n in enumerate(n_grid):
        for j, sh in enumerate(sh_grid):
            ax.text(j, i, f"{h2.at[n, sh]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax)

    fig.tight_layout()
    fig.savefig(OUT / "sensitivity_heatmaps.png", dpi=140, bbox_inches="tight")
    print(f"\nSaved {OUT / 'sensitivity_heatmaps.png'}")

    # Plateau detection — count cells within 0.1 Sharpe of base
    def plateau_pct(h):
        return float((h >= base_res["sharpe"] - 0.1).sum().sum()) / (h.shape[0] * h.shape[1])

    p1 = plateau_pct(h1)
    p2 = plateau_pct(h2)
    print(f"\nPlateau analysis (cells within 0.1 Sharpe of base):")
    print(f"  rsrs_N × mom_L:        {p1:.1%}  ({'平台' if p1 > 0.4 else '孤立峰'})")
    print(f"  top_n_cats × mvo_shrink: {p2:.1%}  ({'平台' if p2 > 0.4 else '孤立峰'})")

    summary = {
        "base_sharpe": base_res["sharpe"],
        "max_drop_param": drops_df.iloc[0]["param"],
        "max_drop_value": drops_df.iloc[0]["max_drop"],
        "heatmap_1_plateau_pct": p1,
        "heatmap_2_plateau_pct": p2,
        "n_perturb_evals": len(perturb_df),
        "n_heatmap_cells": h1.size + h2.size,
    }
    pd.Series(summary).to_csv(OUT / "sensitivity_summary.csv")
    print(f"\nSummary: {summary}")

    print(f"\nWall-clock: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
