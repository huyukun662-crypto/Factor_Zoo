"""Save R30 winner artifacts: equity curve, per-year, defensive mapping."""
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
from strategy.defensive import (  # noqa: E402
    EXPANDED_DEFENSIVE, per_regime_per_macro_best, routed_defensive_weights,
)
from strategy.portfolio import _apply_rebal_threshold, _topk_equal_weight  # noqa: E402
from strategy.regime import build_defensive_returns, build_regime_panel  # noqa: E402
from strategy.signals import (  # noqa: E402
    absolute_momentum_filter, higher_moment_score, rsrs_panel,
)
from strategy.universe import (  # noqa: E402
    ABS_MOM_BENCHMARK, BENCHMARK_SYMBOL, BOND_OR_MONEY_SET,
)

OUT = REPO_ROOT / "report" / "outputs"


def _xs_z(df):
    mu = df.mean(axis=1); sd = df.std(axis=1).replace(0, np.nan)
    return df.sub(mu, axis=0).div(sd, axis=0)


def main():
    panels = load_is_panels()
    macro = fetch_all_macro()
    bench = panels["close"][BENCHMARK_SYMBOL]
    regime_panel = build_regime_panel(bench, macro=macro, ma_window=200, vol_window=60)

    # R30 winner config
    p = expand_param({
        "rsrs_N": 30, "rsrs_M": 250, "mom_L": 180,
        "lambda_s": 0.2, "lambda_k": 0.0,
        "w_rsrs": 0.2, "top_k": 7,
        "theta_off": -0.7, "theta_on": 0.7,
        "rebal_threshold": 0.4,
    })
    p["rsrs_form"] = "rsrs_skew"

    # Build signals
    rsrs = rsrs_panel(panels["high"], panels["low"], n=p["rsrs_N"], m=p["rsrs_M"], form="rsrs_skew")
    mom = higher_moment_score(panels["close"], L=p["mom_L"],
                                lambda_s=p["lambda_s"], lambda_k=p["lambda_k"])
    score = p["w_rsrs"] * _xs_z(rsrs).fillna(0) + (1 - p["w_rsrs"]) * mom.fillna(0)
    elig = absolute_momentum_filter(panels["close"], p["mom_L"], ABS_MOM_BENCHMARK)
    ma200 = panels["close"].rolling(200, min_periods=50).mean()
    elig = elig & (panels["close"] > ma200)
    topk = _topk_equal_weight(score, elig, p["top_k"])

    # Defensive mapping: per (regime × CPI bucket), sharpe_min_vol
    defensive_pool = [s for s in EXPANDED_DEFENSIVE if s in panels["close"].columns]
    def_returns = build_defensive_returns(panels["close"], defensive_pool)
    cpi = regime_panel["cpi_yoy"]
    cpi_state = pd.cut(cpi, [-np.inf, 1.0, 3.0, np.inf],
                        labels=["low", "mid", "high"]).astype(str)
    mapping = per_regime_per_macro_best(regime_panel["regime_state_2"], cpi_state,
                                         def_returns, metric="sharpe_min_vol")
    print("R30 (regime × CPI) defensive mapping:")
    for (r, ms), sym in sorted(mapping.items()):
        print(f"  regime={r} cpi={ms:5s} -> {sym}")

    def_w = routed_defensive_weights(regime_panel["regime_state_2"], mapping,
                                       list(panels["close"].columns), macro_state=cpi_state)

    # R30 winner gate: off={0, 1, 3}, full={2}
    off_set = {0, 1, 3}; full_set = {2}
    s = regime_panel["regime_state_2"]
    ef = pd.Series(0.5, index=s.index)
    ef[s.isin(off_set)] = 0.0
    ef[s.isin(full_set)] = 1.0

    cols = sorted(set(topk.columns) | set(def_w.columns))
    eq = topk.reindex(columns=cols, fill_value=0.0)
    de = def_w.reindex(columns=cols, fill_value=0.0)
    w = eq.mul(ef, axis=0).add(de.mul(1 - ef, axis=0), fill_value=0.0)
    if p["rebal_threshold"] > 0:
        w = _apply_rebal_threshold(w, p["rebal_threshold"])

    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)
    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
    print(f"\nReproduced R30 winner: Sharpe={res.metrics['sharpe']:.3f} "
          f"ret={res.metrics['ann_ret']*100:.2f}% DD={res.metrics['max_dd']*100:.2f}% "
          f"Calmar={res.metrics['calmar']:.2f} turn={res.metrics['ann_turnover']:.1f}x")

    res.equity.to_csv(OUT / "v5_winner_equity.csv", header=["equity"])
    py = per_year_metrics(res.pnl_net)
    py.to_csv(OUT / "v5_winner_per_year.csv")
    print("\nPer-year breakdown:")
    print(py.to_string())

    # Defensive usage breakdown
    holdings = (w[defensive_pool] > 0).sum() if all(d in w.columns for d in defensive_pool) else None
    if holdings is not None:
        print("\nDefensive symbol usage (days with >0 weight):")
        print(holdings.to_string())

    # Update best_params_is.json
    full_params = dict(p)
    full_params["v5_label"] = "R30 regime×CPI sharpe_min_vol + gate off={0,1,3} full={2}"
    full_params["v5_off_set"] = sorted(off_set)
    full_params["v5_full_set"] = sorted(full_set)
    full_params["v5_defensive_mapping"] = {f"regime{r}_cpi_{ms}": sym
                                             for (r, ms), sym in mapping.items()}
    full_params["v5_metric"] = "sharpe_min_vol (excludes ann_vol < 2%)"
    full_params["v5_defensive_pool"] = defensive_pool
    (OUT / "best_params_is.json").write_text(
        json.dumps(full_params, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nSaved best_params_is.json")


if __name__ == "__main__":
    main()
