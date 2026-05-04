"""Re-run R23 / R24 best config to save equity + per-year artifacts.

Picks the most "realistic" winner: highest IS Sharpe with ann_ret > 10% and
ann_turnover > 10x. R20's 1.194 has only 6.88% return so we explicitly skip it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from analysis.is_search import expand_param, load_is_panels  # noqa: E402
from data.fetch_macro import fetch_all_macro  # noqa: E402
from strategy.backtest import CostConfig, run_backtest, per_year_metrics  # noqa: E402
from strategy.portfolio import _apply_rebal_threshold, _topk_equal_weight  # noqa: E402
from strategy.regime import (  # noqa: E402
    best_defensive_per_regime, build_defensive_returns, build_regime_panel,
    regime_routed_defensive_weights,
)
from strategy.signals import (  # noqa: E402
    absolute_momentum_filter, higher_moment_score, rsrs_panel,
)
from strategy.universe import (  # noqa: E402
    ABS_MOM_BENCHMARK, BENCHMARK_SYMBOL, BOND_OR_MONEY_SET, DEFENSIVE_SYMBOLS,
)

OUT = REPO_ROOT / "report" / "outputs"


def _xs_z(df):
    mu = df.mean(axis=1); sd = df.std(axis=1).replace(0, np.nan)
    return df.sub(mu, axis=0).div(sd, axis=0)


def main():
    panels = load_is_panels()
    universe_df = pd.read_csv(OUT / "universe.csv")
    macro = fetch_all_macro()
    bench = panels["close"][BENCHMARK_SYMBOL]
    regime_panel = build_regime_panel(bench, macro=macro, ma_window=200, vol_window=60)

    # Pick realistic winner (R23 best with ann_ret > 10%)
    df = pd.read_csv(OUT / "all_candidates_v4.csv")
    realistic = df[(df["sharpe_net"].notna()) & (df["ann_ret"] > 0.10)
                    & (df["ann_turnover"] > 10) & (df["round"].isin([23, 24]))]
    if realistic.empty:
        raise RuntimeError("no realistic winner found")
    winner = realistic.sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"Realistic winner: round={int(winner['round'])} Sharpe={winner['sharpe_net']:.3f} "
          f"ret={winner['ann_ret']*100:.2f}% DD={winner['max_dd']*100:.2f}%")
    print(f"  label: {winner['label']}")

    win_p = expand_param({k: float(winner[k]) if k not in ("rsrs_N","rsrs_M","mom_L","top_k") else int(winner[k])
                          for k in ["rsrs_N","rsrs_M","mom_L","lambda_s","lambda_k",
                                     "w_rsrs","top_k","theta_off","theta_on","rebal_threshold"]})
    win_p["rsrs_form"] = "rsrs_skew"

    # Build signals
    rsrs = rsrs_panel(panels["high"], panels["low"], n=win_p["rsrs_N"], m=win_p["rsrs_M"], form="rsrs_skew")
    mom = higher_moment_score(panels["close"], L=win_p["mom_L"],
                                lambda_s=win_p["lambda_s"], lambda_k=win_p["lambda_k"])
    score = win_p["w_rsrs"] * _xs_z(rsrs).fillna(0) + (1 - win_p["w_rsrs"]) * mom.fillna(0)
    elig = absolute_momentum_filter(panels["close"], win_p["mom_L"], ABS_MOM_BENCHMARK)
    ma200 = panels["close"].rolling(200, min_periods=50).mean()
    elig = elig & (panels["close"] > ma200)

    topk = _topk_equal_weight(score, elig, win_p["top_k"])

    # Defensive routing using 4-cell regime
    defensive_in_panel = [s for s in DEFENSIVE_SYMBOLS if s in panels["close"].columns]
    def_returns = build_defensive_returns(panels["close"], defensive_in_panel)
    map_2 = best_defensive_per_regime(regime_panel["regime_state_2"], def_returns)
    print(f"  IS-best defensive per 4-cell regime: {map_2}")
    def_w = regime_routed_defensive_weights(regime_panel["regime_state_2"], map_2,
                                              list(panels["close"].columns))

    # Regime gate: off={1,3} (high-vol cells), full={2} (up-trend low-vol)
    off_set = {1, 3}; full_set = {2}
    s = regime_panel["regime_state_2"]
    ef = pd.Series(0.5, index=s.index)
    ef[s.isin(off_set)] = 0.0
    ef[s.isin(full_set)] = 1.0

    cols = sorted(set(topk.columns) | set(def_w.columns))
    eq = topk.reindex(columns=cols, fill_value=0.0)
    de = def_w.reindex(columns=cols, fill_value=0.0)
    w = eq.mul(ef, axis=0).add(de.mul(1 - ef, axis=0), fill_value=0.0)
    if win_p["rebal_threshold"] > 0:
        w = _apply_rebal_threshold(w, win_p["rebal_threshold"])

    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)
    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
    print(f"  reproduced metrics: Sharpe={res.metrics['sharpe']:.3f}  ret={res.metrics['ann_ret']*100:.2f}% "
          f"DD={res.metrics['max_dd']*100:.2f}%")

    res.equity.to_csv(OUT / "v4_winner_equity.csv", header=["equity"])
    py = per_year_metrics(res.pnl_net)
    py.to_csv(OUT / "v4_winner_per_year.csv")
    print("Per-year:")
    print(py.to_string())

    # Update best_params_is.json with realistic winner
    win_p_full = dict(win_p)
    win_p_full["v4_label"] = winner["label"]
    win_p_full["v4_off_set"] = sorted(off_set)
    win_p_full["v4_full_set"] = sorted(full_set)
    win_p_full["v4_defensive_map"] = {int(k): v for k, v in map_2.items()}
    win_p_full["v4_regime_state"] = "regime_state_2 (4-cell trend × vol)"
    (OUT / "best_params_is.json").write_text(
        json.dumps(win_p_full, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nSaved best_params_is.json")


if __name__ == "__main__":
    main()
