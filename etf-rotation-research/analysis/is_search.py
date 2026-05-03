"""IS (in-sample) only evaluator — locked to 2013-01-01 to 2019-12-31.

# [GUARDRAIL] This module raises if asked to evaluate any date past 2019-12-31.
# Do NOT remove the guardrail until the user explicitly approves OOS evaluation.

Public API:
    IS_START, IS_END  : the locked window
    load_is_panels()  : returns (close, open, high, low, amount) restricted to IS
    evaluate_params(params, panels=None) -> dict (metrics + equity series)
    grid_search_lhs(param_space, n_samples, ...) -> pd.DataFrame
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Make repo root importable
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from data.fetch_data import build_close_open_panels, load_panel  # noqa: E402
from strategy.backtest import CostConfig, run_backtest, annualize_metrics, per_year_metrics  # noqa: E402
from strategy.portfolio import build_target_weights  # noqa: E402
from strategy.signals import (
    absolute_momentum_filter,
    composite_score,
    higher_moment_score,
    rsrs_panel,
)  # noqa: E402
from strategy.universe import (
    ABS_MOM_BENCHMARK,
    BENCHMARK_SYMBOL,
    BOND_OR_MONEY_SET,
    DEFENSIVE_SYMBOLS,
    SYMBOLS,
    build_universe,
)  # noqa: E402

IS_START = pd.Timestamp("2013-01-01")
IS_END = pd.Timestamp("2019-12-31")


def _assert_is_window(close: pd.DataFrame) -> None:
    if close.index.max() > IS_END:
        raise RuntimeError(
            f"IS guardrail: panel max date {close.index.max()} exceeds IS_END {IS_END}. "
            "Refusing to evaluate. Trim panels before passing to is_search."
        )


def load_is_panels() -> dict[str, pd.DataFrame]:
    panel_dict = load_panel(SYMBOLS, start="2013-01-01", end="2019-12-31")
    if not panel_dict:
        raise RuntimeError("No cached parquets — run scripts_fetch_all.py first.")
    close, open_, high, low, volume, amount = build_close_open_panels(panel_dict)
    out = {"close": close, "open": open_, "high": high, "low": low,
           "volume": volume, "amount": amount, "panel_dict": panel_dict}
    _assert_is_window(close)
    return out


def _build_signals_and_weights(panels: dict, params: dict
                                ) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.DataFrame]:
    close = panels["close"]
    high = panels["high"]
    low = panels["low"]

    rsrs = rsrs_panel(high, low,
                      n=params["rsrs_N"], m=params["rsrs_M"],
                      form=params.get("rsrs_form", "rsrs_skew"))
    mom = higher_moment_score(close, L=params["mom_L"],
                              lambda_s=params["lambda_s"],
                              lambda_k=params["lambda_k"])
    score = composite_score(rsrs, mom, w_rsrs=params["w_rsrs"])
    elig = absolute_momentum_filter(close, params["mom_L"], ABS_MOM_BENCHMARK)

    # Defensive proxy score: rsrs_skew restricted to defensive bucket
    defensive_cols = [s for s in DEFENSIVE_SYMBOLS if s in rsrs.columns]
    defensive_proxy = rsrs[defensive_cols] if defensive_cols else None

    agg_rsrs = rsrs[BENCHMARK_SYMBOL] if BENCHMARK_SYMBOL in rsrs.columns else pd.Series(0.0, index=rsrs.index)

    weights = build_target_weights(
        score=score, eligibility=elig, agg_rsrs=agg_rsrs,
        defensive_proxy_score=defensive_proxy,
        top_k=params["top_k"],
        theta_off=params["theta_off"], theta_on=params["theta_on"],
        rebal_threshold=params.get("rebal_threshold", 0.0),
    )
    return score, elig, agg_rsrs, weights


def evaluate_params(params: dict, panels: dict | None = None,
                     return_artifacts: bool = False) -> dict:
    if panels is None:
        panels = load_is_panels()
    _assert_is_window(panels["close"])

    score, elig, agg_rsrs, weights = _build_signals_and_weights(panels, params)

    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)
    result = run_backtest(weights, panels["close"], panels["open"], panels["amount"], cost_cfg)

    out = dict(params=dict(params), metrics=result.metrics,
               n_days=len(result.pnl_net), n_eligible_universe=int(elig.sum().sum()))
    if return_artifacts:
        out["pnl_net"] = result.pnl_net
        out["equity"] = result.equity
        out["weights"] = result.weights_realized
        out["turnover"] = result.turnover
        out["per_year"] = per_year_metrics(result.pnl_net)
    return out


# ---------- LHS grid search ----------

def latin_hypercube(param_space: dict[str, list], n_samples: int, seed: int = 42
                     ) -> list[dict]:
    """Simple LHS: for each param, partition its candidate list into n_samples
    strata (uniform over the index) and randomly pair across params.
    Discrete params: sample with replacement weighted by stratification.
    """
    rng = np.random.default_rng(seed)
    keys = list(param_space.keys())
    samples = []
    for _ in range(n_samples):
        s = {}
        for k in keys:
            opts = param_space[k]
            s[k] = opts[int(rng.integers(0, len(opts)))]
        samples.append(s)
    # Deduplicate while preserving order
    uniq = []
    seen = set()
    for s in samples:
        key = tuple(sorted(s.items()))
        if key not in seen:
            seen.add(key)
            uniq.append(s)
    return uniq


def expand_param(p: dict) -> dict:
    """Resolve `theta_pair` shorthand into theta_off / theta_on; coerce types."""
    p = dict(p)
    if "theta_pair" in p:
        val = p.pop("theta_pair")
        # if it came back from a CSV/df it might be a string; tolerate
        if isinstance(val, str):
            val = eval(val)  # noqa: S307 (controlled space)
        off, on = val
        p["theta_off"] = float(off)
        p["theta_on"] = float(on)
    # coerce ints
    for k in ("rsrs_N", "rsrs_M", "mom_L", "top_k"):
        if k in p and p[k] is not None and not (isinstance(p[k], float) and np.isnan(p[k])):
            p[k] = int(p[k])
    # coerce floats
    for k in ("lambda_s", "lambda_k", "w_rsrs", "theta_off", "theta_on", "rebal_threshold"):
        if k in p and p[k] is not None and not (isinstance(p[k], float) and np.isnan(p[k])):
            p[k] = float(p[k])
    return p


def grid_search(param_space: dict[str, list], n_samples: int = 200,
                seed: int = 42, panels: dict | None = None,
                progress: bool = True) -> pd.DataFrame:
    if panels is None:
        panels = load_is_panels()
    _assert_is_window(panels["close"])

    samples = latin_hypercube(param_space, n_samples, seed=seed)

    iterator = samples
    if progress:
        try:
            from tqdm import tqdm
            iterator = tqdm(samples, desc=f"grid({len(samples)})")
        except Exception:  # noqa: BLE001
            pass

    rows = []
    for p in iterator:
        pp = expand_param(p)
        try:
            r = evaluate_params(pp, panels=panels)
            row = {**pp, **r["metrics"]}
            rows.append(row)
        except Exception as e:  # noqa: BLE001
            rows.append({**pp, "error": str(e)})
    df = pd.DataFrame(rows)
    if "sharpe" in df.columns:
        df = df.sort_values("sharpe", ascending=False).reset_index(drop=True)
    return df


# ---------- defaults ----------

DEFAULT_PARAMS = dict(
    rsrs_N=18,
    rsrs_M=600,
    rsrs_form="rsrs_skew",
    mom_L=120,
    lambda_s=0.3,
    lambda_k=0.2,
    w_rsrs=0.4,
    top_k=5,
    theta_off=-0.7,
    theta_on=+0.7,
    rebal_threshold=0.0,
)


DEFAULT_PARAM_SPACE = dict(
    rsrs_N=[14, 18, 24, 30],
    rsrs_M=[250, 600],
    mom_L=[60, 120, 180, 252],
    lambda_s=[0.0, 0.3, 0.5],
    lambda_k=[0.0, 0.2],
    w_rsrs=[0.3, 0.4, 0.5],
    top_k=[3, 5, 8],
    theta_pair=[(-1.0, 0.5), (-0.7, 0.7), (-0.5, 1.0)],
    rebal_threshold=[0.0, 0.10, 0.20, 0.40],
)


if __name__ == "__main__":
    panels = load_is_panels()
    print(f"IS panel: {panels['close'].index.min().date()} .. {panels['close'].index.max().date()} "
          f"shape={panels['close'].shape}")
    res = evaluate_params(DEFAULT_PARAMS, panels=panels)
    print(json.dumps(res, indent=2, default=str))
