"""V11: R58-R64 — More macro axes + M6 + top-2 + DP optimization.

(A) New macro matrix axes (defensive routing):
  R58 M10 cn_10_2_spread × CPI level         (term-structure × inflation)
  R59 M11 us_cn_10y_spread × CPI             (cross-border yield × inflation)
  R60 M12 USD/CNY momentum × CPI velocity   (FX × inflation cycle)
  R61 M13 cn_10y velocity × CPI velocity    (rate cycle × inflation cycle)
  R62 M14 m2_velocity × CPI velocity         (liquidity × inflation cycle)

(B) M6 + top-2 + DP optimization:
  R63 Various DP thresholds AND DP only on selected M6 cells
  R64 Final stack: best matrix + top-2 + selective DP

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
    _build_signals, _equity_frac, assemble, double_pressure_override_pool,
)
from analysis.iterate_is_v10 import (  # noqa: E402
    _bucket_m2, _bucket_velocity_3, _matrix_intra_defensive,
)
from analysis.macro_matrix import (  # noqa: E402
    _bucket_cpi, _bucket_pmi, best_category_per_cell, per_cell_category_score,
)
from data.fetch_macro import fetch_all_macro  # noqa: E402
from strategy.backtest import (  # noqa: E402
    CostConfig, run_backtest,
)
from strategy.categories import build_category_returns  # noqa: E402
from strategy.portfolio import _topk_equal_weight  # noqa: E402
from strategy.regime import build_regime_panel  # noqa: E402
from strategy.universe import (  # noqa: E402
    BENCHMARK_SYMBOL, BOND_OR_MONEY_SET,
)

OUT = REPO_ROOT / "report" / "outputs"


def _bucket_spread_3(s: pd.Series, lo: float, hi: float, labels=("inverted", "flat", "steep")
                      ) -> pd.Series:
    return pd.cut(s, [-np.inf, lo, hi, np.inf], labels=labels).astype(str)


def _bucket_continuous_3(s: pd.Series, lo: float, hi: float, labels) -> pd.Series:
    return pd.cut(s, [-np.inf, lo, hi, np.inf], labels=list(labels)).astype(str)


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


def evaluate_matrix(name, a1, a2, score_panel, all_symbols, base_topk, ef, p,
                      cat_ret, panels, method="ew", top_k=2, return_panel=None):
    """Build matrix + apply intra-method, return res object."""
    score_df = per_cell_category_score(a1, a2, cat_ret, metric="sharpe_min_vol")
    if score_df.empty:
        return None, {}
    cell_map = best_category_per_cell(score_df)
    def_w = _matrix_intra_defensive(a1, a2, cell_map, score_panel, all_symbols,
                                       method=method, top_k=top_k,
                                       returns_panel=return_panel)
    w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)
    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
    return res, cell_map


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
    sym_returns = panels["close"].pct_change().fillna(0.0)

    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)
    all_symbols = list(panels["close"].columns)
    ef = _equity_frac(regime_panel, {0, 1, 3}, {2})

    # Reference axes
    cpi_b = _bucket_cpi(regime_panel["cpi_yoy"])
    pmi_b = _bucket_pmi(regime_panel["pmi"])
    cpi_vel_b = _bucket_velocity_3(regime_panel.get("cpi_velocity_3m", pd.Series(0, index=regime_panel.index)),
                                       threshold=0.3)
    pmi_vel_b = _bucket_velocity_3(regime_panel.get("pmi_velocity_3m", pd.Series(0, index=regime_panel.index)),
                                       threshold=0.5)

    # New axes
    cn_2_10_spread = regime_panel.get("cn_10_2_spread")
    spread_b = _bucket_spread_3(cn_2_10_spread, 0.0, 0.8, ("inverted", "flat", "steep")) \
                if cn_2_10_spread is not None else None

    us_cn_spread = regime_panel.get("us_cn_10y_spread")
    us_cn_b = _bucket_continuous_3(us_cn_spread, 0.0, 1.5,
                                       ("us_cheap", "neutral", "us_expensive")) \
              if us_cn_spread is not None else None

    usd_cny_mom = regime_panel.get("usdcny_mom_60")
    usd_cny_b = _bucket_velocity_3(usd_cny_mom, threshold=0.005) \
                  if usd_cny_mom is not None else None

    cn_10y_vel = regime_panel.get("cn_10y_velocity_3m")
    cn_10y_vel_b = _bucket_velocity_3(cn_10y_vel, threshold=0.05) \
                       if cn_10y_vel is not None else None

    m2_vel = regime_panel.get("m2_velocity_3m")
    m2_vel_b = _bucket_velocity_3(m2_vel, threshold=0.5) \
                  if m2_vel is not None else None

    rows = []

    # ========= R58-R62: New matrix axes =========
    new_matrices = [
        ("R58_M10", "spread × CPI", spread_b, cpi_b),
        ("R59_M11", "us_cn_spread × CPI", us_cn_b, cpi_b),
        ("R60_M12", "USD/CNY mom × CPI vel", usd_cny_b, cpi_vel_b),
        ("R61_M13", "cn_10y vel × CPI vel", cn_10y_vel_b, cpi_vel_b),
        ("R62_M14", "m2_vel × CPI vel", m2_vel_b, cpi_vel_b),
    ]

    for label, desc, a1, a2 in new_matrices:
        round_n = int(label.split("_")[0][1:])
        print(f"\n=== {label}: {desc} ===")
        if a1 is None or a2 is None:
            print("  axis missing")
            continue
        score_df = per_cell_category_score(a1, a2, cat_ret, metric="sharpe_min_vol")
        if score_df.empty:
            print("  no cells")
            continue
        cell_map = best_category_per_cell(score_df)
        for (v1, v2), cat in sorted(cell_map.items()):
            n = int(score_df[(score_df["a1"] == v1) & (score_df["a2"] == v2)]["n"].iloc[0])
            print(f"    {v1:13s} × {v2:13s} n={n:4d}  -> {cat}")

        # Test ew
        res_ew, _ = evaluate_matrix(label, a1, a2, score, all_symbols, base_topk, ef, p,
                                      cat_ret, panels, method="ew")
        if res_ew is not None:
            rows.append(to_row(round_n, f"{label.split('_')[1]} ew", p,
                                {"matrix": label.split("_")[1]}, res_ew.metrics))
            print(f"  ew      Sharpe={res_ew.metrics['sharpe']:.3f}  Ret={res_ew.metrics['ann_ret']*100:.2f}%  DD={res_ew.metrics['max_dd']*100:.2f}%")

        # Test top-2
        res_t2, _ = evaluate_matrix(label, a1, a2, score, all_symbols, base_topk, ef, p,
                                      cat_ret, panels, method="topk", top_k=2)
        if res_t2 is not None:
            rows.append(to_row(round_n, f"{label.split('_')[1]} top-2", p,
                                {"matrix": label.split("_")[1], "method": "topk", "k": 2},
                                res_t2.metrics))
            print(f"  top-2   Sharpe={res_t2.metrics['sharpe']:.3f}  Ret={res_t2.metrics['ann_ret']*100:.2f}%  DD={res_t2.metrics['max_dd']*100:.2f}%")

    # ========= R63: M6 + top-2 + DP variants =========
    print("\n=== R63: M6 + top-2 + DP variants ===")
    # Reproduce M6 + top-2 base
    score_df_m6 = per_cell_category_score(cpi_vel_b, pmi_vel_b, cat_ret, metric="sharpe_min_vol")
    m6_map = best_category_per_cell(score_df_m6)
    def_w_m6_t2 = _matrix_intra_defensive(cpi_vel_b, pmi_vel_b, m6_map, score, all_symbols,
                                              method="topk", top_k=2)
    w_m6_t2 = assemble(base_topk, def_w_m6_t2, ef, p["rebal_threshold"])
    res_m6_t2 = run_backtest(w_m6_t2, panels["close"], panels["open"], panels["amount"], cost_cfg)
    rows.append(to_row(0, "M6 top-2 base", p, {"matrix": "M6", "method": "topk", "k": 2},
                        res_m6_t2.metrics))
    print(f"  base M6 top-2  Sharpe={res_m6_t2.metrics['sharpe']:.3f}")

    # DP variants
    DP_POOLS = [
        ["511260"],
        ["511260", "511880"],
        ["511260", "511880", "162411"],
        ["511260", "162411"],
        ["511880", "162411"],
        ["511010", "511260", "511880"],
    ]
    DP_THRESHOLDS = [(0.02, 0.01), (0.04, 0.02), (0.06, 0.03)]

    for pool in DP_POOLS:
        for dxy_t, rmb_t in DP_THRESHOLDS:
            def_w_dp = double_pressure_override_pool(def_w_m6_t2, regime_panel,
                                                          dxy_t, rmb_t, pool)
            w_dp = assemble(base_topk, def_w_dp, ef, p["rebal_threshold"])
            res_dp = run_backtest(w_dp, panels["close"], panels["open"], panels["amount"], cost_cfg)
            rows.append(to_row(63, f"M6 top-2 + DP pool={'|'.join(pool)} dxy>{dxy_t} rmb>{rmb_t}",
                                p, {"matrix": "M6", "dp_pool": "|".join(pool),
                                     "dp_dxy": dxy_t, "dp_rmb": rmb_t}, res_dp.metrics))

    # Print top R63 results
    df_r63 = pd.DataFrame([r for r in rows if r["round"] == 63]).sort_values("sharpe_net", ascending=False)
    print(f"  Top 5 R63 DP variants:")
    print(df_r63.head(5)[["dp_pool", "dp_dxy", "dp_rmb", "sharpe_net", "ann_ret", "max_dd"]].to_string(index=False))

    # Selective DP: only override M6 picks of certain categories (e.g., only when M6 picks 黄金)
    print("\n=== R63b: Selective DP (only when M6 picks 黄金) ===")
    # Identify days where M6 mapping picks 黄金
    daily_m6_cat = pd.Series("货币", index=cpi_vel_b.index)
    for dt in cpi_vel_b.index:
        v1 = cpi_vel_b.at[dt]; v2 = pmi_vel_b.at[dt]
        if pd.notna(v1) and pd.notna(v2):
            cat = m6_map.get((str(v1), str(v2)))
            if cat:
                daily_m6_cat.at[dt] = cat
    days_picking_gold = daily_m6_cat == "黄金"
    print(f"  M6 picks 黄金 on {int(days_picking_gold.sum())} days")

    for dxy_t, rmb_t in [(0.02, 0.01), (0.04, 0.02)]:
        for pool in [["511260"], ["511260", "511880"], ["511260", "511880", "162411"]]:
            mask = (regime_panel["dxy_mom_60"] > dxy_t) & (regime_panel["usdcny_mom_60"] > rmb_t)
            mask = mask & days_picking_gold  # ONLY override gold days
            mask = mask.fillna(False)
            def_w = def_w_m6_t2.copy()
            for dt in regime_panel.index[mask]:
                for s in def_w.columns:
                    def_w.at[dt, s] = 0.0
                for s in pool:
                    if s in def_w.columns:
                        def_w.at[dt, s] = 1.0 / len(pool)
            w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
            res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
            rows.append(to_row(63, f"M6 top-2 + selective-DP-gold pool={'|'.join(pool)} dxy>{dxy_t} rmb>{rmb_t}",
                                p, {"matrix": "M6", "selective": "gold-only",
                                     "dp_pool": "|".join(pool),
                                     "dp_dxy": dxy_t, "dp_rmb": rmb_t}, res.metrics))
            n_changed = int(mask.sum())
            print(f"  pool={pool} dxy>{dxy_t:.2f} rmb>{rmb_t:.3f}  changed={n_changed}d  "
                  f"Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%")

    # ========= R64: Final stack =========
    print("\n=== R64: final ranking ===")
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "all_candidates_v11.csv", index=False)
    print("\nTop 15 across R58-R63:")
    print(df.sort_values("sharpe_net", ascending=False).head(15)[
        ["round","label","sharpe_net","ann_ret","ann_vol","max_dd","calmar","ann_turnover"]
    ].to_string(index=False))

    print(f"\nWall-clock: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
