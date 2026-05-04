"""V12: R65-R71 — Fix 2018 (inception-aware categories) + intra-category weighting variants.

Categories revised:
  红利低波 = 510880 红利 (2013) + 515080 红利低波 (2019-12)
  商品    = 518880 黄金 + 162411 油气 + 515220 煤炭 + 159980 有色

Rounds:
  R65 M6 + top-2 with NEW categories (inception-aware top-K)
  R66 M6 + vol-parity top-2
  R67 M6 + sharpe-weighted top-2
  R68 M6 + vol-parity top-3
  R69 M6 + top-2 + 2018-specific gate (additional risk-off in slow bear)
  R70 stress check on 2018 specifically
  R71 final stack

# [GUARDRAIL] All within IS (2013-2023). Matrix from full IS.
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
from analysis.iterate_is_v10 import (  # noqa: E402
    _bucket_velocity_3,
)
from analysis.macro_matrix import (  # noqa: E402
    best_category_per_cell, per_cell_category_score,
)
from data.fetch_macro import fetch_all_macro  # noqa: E402
from strategy.backtest import (  # noqa: E402
    CostConfig, annualize_metrics, per_year_metrics, run_backtest,
)
from strategy.categories import (  # noqa: E402
    CATEGORIES, build_category_returns,
)
from strategy.intra_category import (  # noqa: E402
    intra_category_sharpe_weighted, intra_category_topk_aware,
    intra_category_vol_parity,
)
from strategy.portfolio import _topk_equal_weight  # noqa: E402
from strategy.regime import build_regime_panel  # noqa: E402
from strategy.universe import (  # noqa: E402
    BENCHMARK_SYMBOL, BOND_OR_MONEY_SET,
)

OUT = REPO_ROOT / "report" / "outputs"


def matrix_intra_dispatcher(a1, a2, cell_to_category, score, close, all_symbols,
                              method="topk_aware", top_k=2,
                              vol_lookback=60, default_cat="红利低波"):
    """Apply matrix mapping → category, then per-day pick using `method`."""
    out = pd.DataFrame(0.0, index=score.index, columns=all_symbols)

    # Pre-compute per-category panel of weights based on `method`
    cat_panels = {}
    for cat in CATEGORIES:
        if method == "topk_aware":
            cat_panels[cat] = intra_category_topk_aware(score, close, cat, k=top_k,
                                                            all_symbols=all_symbols)
        elif method == "vol_parity":
            cat_panels[cat] = intra_category_vol_parity(close, cat,
                                                            vol_lookback=vol_lookback,
                                                            top_k=top_k, score=score,
                                                            all_symbols=all_symbols)
        elif method == "sharpe_weighted":
            cat_panels[cat] = intra_category_sharpe_weighted(close, cat,
                                                                  lookback=vol_lookback,
                                                                  top_k=top_k,
                                                                  all_symbols=all_symbols)
        else:
            raise ValueError(method)

    for dt in score.index:
        v1 = a1.get(dt) if dt in a1.index else None
        v2 = a2.get(dt) if dt in a2.index else None
        if pd.isna(v1) or pd.isna(v2):
            cat = default_cat
        else:
            cat = cell_to_category.get((str(v1), str(v2)), default_cat)
        out.loc[dt] = cat_panels[cat].loc[dt].values

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
    print(f"Updated CATEGORIES:")
    for name, cfg in CATEGORIES.items():
        avail = [c for c in cfg["constituents"] if c in panels["close"].columns]
        first_dates = {c: panels["close"][c].first_valid_index() for c in avail}
        print(f"  {name}: {avail} (inception: {{ {', '.join(f'{c}: {dt.year if dt else None}' for c, dt in first_dates.items())} }})")

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

    # Re-derive M6 with NEW categories
    score_df = per_cell_category_score(cpi_vel_b, pmi_vel_b, cat_ret, metric="sharpe_min_vol")
    m6_map = best_category_per_cell(score_df)
    print(f"\nM6 mapping (with new categories):")
    for (a, b), c in sorted(m6_map.items()):
        n = int(score_df[(score_df["a1"] == a) & (score_df["a2"] == b)]["n"].iloc[0])
        print(f"  cpi_vel={a:8s} pmi_vel={b:8s} n={n:4d}  -> {c}")

    rows = []

    # ========= R65: M6 + inception-aware top-2 =========
    print("\n=== R65: M6 + top-2 (inception-aware new categories) ===")
    def_w = matrix_intra_dispatcher(cpi_vel_b, pmi_vel_b, m6_map, score, panels["close"],
                                       all_symbols, method="topk_aware", top_k=2)
    w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
    rows.append(to_row(65, "M6 top-2 (new cats)", p,
                        {"matrix": "M6", "method": "topk_aware", "k": 2}, res.metrics))
    print(f"  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%")

    # 2018 deep-dive
    py = per_year_metrics(res.pnl_net)
    print(f"  2018 sharpe: {py.loc[2018, 'sharpe']:.3f} (target > 0.5; was -0.20 with old cats)")

    # Full per-year for record
    print(f"  Per-year:\n    " + " ".join(f"{int(yr)}={py.loc[yr,'sharpe']:+.2f}" for yr in py.index))

    # ========= R66: vol-parity top-2 =========
    print("\n=== R66: M6 + vol-parity top-2 ===")
    for vlb in [40, 60, 90]:
        def_w = matrix_intra_dispatcher(cpi_vel_b, pmi_vel_b, m6_map, score, panels["close"],
                                           all_symbols, method="vol_parity", top_k=2,
                                           vol_lookback=vlb)
        w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        py = per_year_metrics(res.pnl_net)
        rows.append(to_row(66, f"M6 vol-parity top-2 vlb={vlb}", p,
                            {"matrix": "M6", "method": "vol_parity", "vlb": vlb},
                            res.metrics))
        print(f"  vlb={vlb}  Sharpe={res.metrics['sharpe']:.3f}  2018={py.loc[2018, 'sharpe']:+.3f}  DD={res.metrics['max_dd']*100:.2f}%")

    # ========= R67: sharpe-weighted top-2 =========
    print("\n=== R67: M6 + sharpe-weighted top-2 ===")
    for lb in [40, 60, 120]:
        def_w = matrix_intra_dispatcher(cpi_vel_b, pmi_vel_b, m6_map, score, panels["close"],
                                           all_symbols, method="sharpe_weighted", top_k=2,
                                           vol_lookback=lb)
        w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        py = per_year_metrics(res.pnl_net)
        rows.append(to_row(67, f"M6 sharpe-w top-2 lb={lb}", p,
                            {"matrix": "M6", "method": "sharpe_weighted", "lb": lb},
                            res.metrics))
        print(f"  lb={lb}  Sharpe={res.metrics['sharpe']:.3f}  2018={py.loc[2018, 'sharpe']:+.3f}  DD={res.metrics['max_dd']*100:.2f}%")

    # ========= R68: vol-parity top-3 =========
    print("\n=== R68: M6 + vol-parity top-3 ===")
    for vlb in [60]:
        def_w = matrix_intra_dispatcher(cpi_vel_b, pmi_vel_b, m6_map, score, panels["close"],
                                           all_symbols, method="vol_parity", top_k=3,
                                           vol_lookback=vlb)
        w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        py = per_year_metrics(res.pnl_net)
        rows.append(to_row(68, f"M6 vol-parity top-3 vlb={vlb}", p,
                            {"matrix": "M6", "method": "vol_parity", "vlb": vlb, "k": 3},
                            res.metrics))
        print(f"  vlb={vlb} k=3  Sharpe={res.metrics['sharpe']:.3f}  2018={py.loc[2018, 'sharpe']:+.3f}")

    # ========= R69: M6 + top-2 + 2018-specific overlay (slow-bear gate) =========
    print("\n=== R69: M6 + top-2 + slow-bear extra overlay ===")
    # Slow bear: trend down (CSI300 < MA200) AND realized vol < 12% (low vol, slow decline)
    csi_close = panels["close"][BENCHMARK_SYMBOL]
    ma200_csi = csi_close.rolling(200, min_periods=50).mean()
    log_ret_csi = np.log(csi_close).diff()
    realized_vol = log_ret_csi.rolling(60, min_periods=20).std() * np.sqrt(252)
    slow_bear = (csi_close < ma200_csi) & (realized_vol < 0.18)

    base_def_w = matrix_intra_dispatcher(cpi_vel_b, pmi_vel_b, m6_map, score, panels["close"],
                                            all_symbols, method="topk_aware", top_k=2)

    # In slow bear: switch to long-bond + cash blend
    SLOW_BEAR_POOL = ["511010", "511260", "511880"]
    for pool_label, pool in [("long-bond+cash", SLOW_BEAR_POOL),
                                ("gold+cash", ["518880", "511880"]),
                                ("dividend+cash", ["510880", "511880"])]:
        def_w_sb = base_def_w.copy()
        for dt in slow_bear[slow_bear == True].index:
            if dt not in def_w_sb.index:
                continue
            for s in def_w_sb.columns:
                def_w_sb.at[dt, s] = 0.0
            avail_pool = [s for s in pool if s in def_w_sb.columns and not pd.isna(panels["close"].at[dt, s])]
            if not avail_pool:
                continue
            for s in avail_pool:
                def_w_sb.at[dt, s] = 1.0 / len(avail_pool)
        w = assemble(base_topk, def_w_sb, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        py = per_year_metrics(res.pnl_net)
        rows.append(to_row(69, f"M6 top-2 + slow-bear -> {pool_label}", p,
                            {"matrix": "M6", "method": "topk_aware", "slow_bear": pool_label},
                            res.metrics))
        n_changed = int(slow_bear.sum())
        print(f"  slow_bear days={n_changed}  pool={pool_label}  Sharpe={res.metrics['sharpe']:.3f}  2018={py.loc[2018, 'sharpe']:+.3f}  DD={res.metrics['max_dd']*100:.2f}%")

    # ========= R70: 2018 stress test — what does R65 hold on each 2018 day? =========
    print("\n=== R70: 2018 deep-dive (what M6 picks each 2018 day) ===")
    days_2018 = score.index[score.index.year == 2018]
    cat_picks_2018 = pd.Series("?", index=days_2018)
    for dt in days_2018:
        v1 = cpi_vel_b.get(dt); v2 = pmi_vel_b.get(dt)
        if pd.notna(v1) and pd.notna(v2):
            cat = m6_map.get((str(v1), str(v2)), "default")
            cat_picks_2018.at[dt] = cat
    print("  M6 category picks in 2018:")
    print("  " + cat_picks_2018.value_counts().to_string().replace("\n", "\n  "))

    # ========= R71: final ranking =========
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "all_candidates_v12.csv", index=False)
    print("\n=== Top 10 across R65-R69 ===")
    print(df.sort_values("sharpe_net", ascending=False).head(10)[
        ["round","label","sharpe_net","ann_ret","ann_vol","max_dd","calmar","ann_turnover"]
    ].to_string(index=False))

    # 2018 comparison table
    print("\n2018 Sharpe by variant:")
    for _, r in df.iterrows():
        # need to re-run to get per-year, or save it
        pass
    print(f"\nWall-clock: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
