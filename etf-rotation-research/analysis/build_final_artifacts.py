"""Build final report artifacts: equity curve PNG + per-year tables for R77 winner.

R77 winner (M6 top-3 + MVO sh=0.3 + intra vol-parity top-2):
  IS Sharpe 1.317 / WFA Sharpe 1.522 / Max DD -17.8% / Calmar 1.38
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from analysis.is_search import expand_param, load_is_panels  # noqa: E402
from analysis.iterate_is_v9 import _build_signals, _equity_frac, assemble  # noqa: E402
from analysis.iterate_is_v10 import _bucket_velocity_3  # noqa: E402
from analysis.macro_matrix import per_cell_category_score  # noqa: E402
from analysis.sensitivity import BASE  # noqa: E402
from data.fetch_macro import fetch_all_macro  # noqa: E402
from strategy.backtest import (  # noqa: E402
    CostConfig, run_backtest, per_year_metrics,
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


def main():
    _setup_font()
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
    all_symbols = list(panels["close"].columns)

    cpi_vel_b = _bucket_velocity_3(regime_panel.get("cpi_velocity_3m"), threshold=0.3)
    pmi_vel_b = _bucket_velocity_3(regime_panel.get("pmi_velocity_3m"), threshold=0.5)

    m6_score_df = per_cell_category_score(cpi_vel_b, pmi_vel_b, cat_ret, metric="sharpe_min_vol")
    score_panel = build_score_panel(cpi_vel_b, pmi_vel_b, m6_score_df)
    top3 = top_n_categories_per_cell(m6_score_df, n=3)
    sel = daily_top_n_categories(cpi_vel_b, pmi_vel_b, top3)

    cat_w = cross_category_weights(cat_ret, sel, method="mvo_shrunk",
                                       score_panel=score_panel, shrink=0.3,
                                       vol_lookback=60)

    intra_panels = {
        cat: intra_category_vol_parity(panels["close"], cat,
                                          vol_lookback=60, top_k=2,
                                          score=score, all_symbols=all_symbols)
        for cat in CATEGORIES
    }
    def_w = expand_category_to_symbol_weights(cat_w, intra_panels, all_symbols)

    ef = _equity_frac(regime_panel, {0, 1, 3}, {2})
    w = assemble(base_topk, def_w, ef, p["rebal_threshold"])

    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)
    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
    print(f"R77 IS metrics: Sharpe={res.metrics['sharpe']:.3f} "
          f"Ret={res.metrics['ann_ret']*100:.2f}% DD={res.metrics['max_dd']*100:.2f}%")

    res.equity.to_csv(OUT / "r77_winner_equity.csv", header=["equity"])
    py = per_year_metrics(res.pnl_net)
    py.to_csv(OUT / "r77_winner_per_year.csv")

    # CSI300 benchmark equity (qfq cum return on 510300)
    bench_close = panels["close"][BENCHMARK_SYMBOL].dropna()
    bench_eq = bench_close / bench_close.iloc[0]
    bench_eq.to_csv(OUT / "r77_benchmark_equity.csv", header=["equity"])

    # Plot: 4-panel
    fig = plt.figure(figsize=(13, 10))
    gs = fig.add_gridspec(3, 2, height_ratios=[2, 1, 1])

    ax = fig.add_subplot(gs[0, :])
    ax.plot(res.equity.index, res.equity.values, color="#1f77b4", lw=1.5,
             label="R77 strategy (net)")
    ax.plot(bench_eq.index, bench_eq.values, color="#888", ls="--", lw=1,
             label="510300 沪深300 (qfq)")
    ax.set_title(f"IS 2013-2023 净值曲线 — R77 final (Sharpe={res.metrics['sharpe']:.2f}, DD={res.metrics['max_dd']*100:.1f}%)")
    ax.set_ylabel("equity (start=1)")
    ax.grid(alpha=0.3)
    ax.legend(loc="upper left")

    ax = fig.add_subplot(gs[1, :])
    eq = res.equity
    peak = eq.cummax()
    dd = (eq / peak - 1) * 100
    ax.fill_between(dd.index, dd.values, 0, color="#d62728", alpha=0.4)
    ax.set_title("回撤")
    ax.set_ylabel("DD %")
    ax.grid(alpha=0.3)

    ax = fig.add_subplot(gs[2, 0])
    colors = ["#d62728" if s < 0 else "#2ca02c" for s in py["sharpe"]]
    ax.bar(py.index.astype(str), py["sharpe"], color=colors)
    ax.axhline(0.5, color="gray", ls="--", lw=0.6, label="0.5 floor")
    ax.axhline(0, color="black", lw=0.6)
    ax.set_title("逐年 Sharpe")
    ax.set_ylabel("Sharpe")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, axis="y")

    ax = fig.add_subplot(gs[2, 1])
    ax.bar(py.index.astype(str), py["ann_ret"] * 100,
            color=["#d62728" if r < 0 else "#2ca02c" for r in py["ann_ret"]])
    ax.axhline(0, color="black", lw=0.6)
    ax.set_title("逐年收益 (%)")
    ax.set_ylabel("ann ret %")
    ax.grid(alpha=0.3, axis="y")

    fig.tight_layout()
    fig.savefig(OUT / "r77_final_diagnostics.png", dpi=140, bbox_inches="tight")
    print(f"saved {OUT / 'r77_final_diagnostics.png'}")

    # Compare equity vs CSI300
    final_strategy_value = res.equity.iloc[-1]
    final_bench_value = bench_eq.reindex(res.equity.index, method="ffill").iloc[-1]
    print(f"R77 final equity:    {final_strategy_value:.2f} (vs 1.00 start)")
    print(f"CSI300 final equity: {final_bench_value:.2f} (vs 1.00 start)")
    print(f"Ratio R77/CSI300:    {final_strategy_value / final_bench_value:.2f}x")

    # Print per-year side-by-side
    bench_pnl = bench_close.pct_change().reindex(res.pnl_net.index).fillna(0)
    bench_py = per_year_metrics(bench_pnl)
    side = pd.DataFrame({
        "R77_sharpe": py["sharpe"], "R77_ret": py["ann_ret"] * 100,
        "R77_dd": py["max_dd"] * 100,
        "CSI300_sharpe": bench_py["sharpe"], "CSI300_ret": bench_py["ann_ret"] * 100,
        "CSI300_dd": bench_py["max_dd"] * 100,
    })
    print("\nPer-year R77 vs CSI300:")
    print(side.round(2).to_string())
    side.to_csv(OUT / "r77_vs_csi300_per_year.csv")


if __name__ == "__main__":
    main()
