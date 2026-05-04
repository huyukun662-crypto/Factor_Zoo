"""Walk-Forward Analysis inside IS (2013-2023) for the R37 strategy.

# [GUARDRAIL] All windows fall within IS_END=2023-12-31. No OOS / Hold-out touched.

Setup (per task spec):
  train_window = 756 days  (~3 years)
  test_window  = 252 days  (~1 year)
  step         = 63 days   (~1 quarter)

Per WFA iteration:
  1. Train segment: build (regime × CN_CPI) sharpe_min_vol mapping ON TRAINING DATA ONLY
  2. Test segment: apply trained mapping + R37 fixed gold-conditioning overlay rules
  3. Concatenate the FIRST `step` days (63) of each test period to form WF returns
     (avoids overlap between consecutive test windows)

Fixed across windows (R37 winner config):
  - Signal params: rsrs_N=30, rsrs_M=250, mom_L=180, lambda_s=0.2, lambda_k=0.0
  - Score weights: w_rsrs=0.2, top_k=7
  - Risk-off gate: off={0,1,3}, full={2}
  - Rebal threshold: 0.4
  - Gold-conditioning: rr_pos=2.0, rr_neg=-2.0, dxy_mom_thresh=-0.05, fb=511260

Re-derived per training window:
  - (regime × CN_CPI) defensive mapping using sharpe_min_vol on training data only

Output: report/outputs/wfa_*.csv
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
from data.fetch_macro import fetch_all_macro  # noqa: E402
from strategy.backtest import (  # noqa: E402
    CostConfig, annualize_metrics, per_year_metrics, run_backtest,
)
from strategy.defensive import (  # noqa: E402
    EXPANDED_DEFENSIVE, per_regime_per_macro_best,
)
from strategy.portfolio import _apply_rebal_threshold, _topk_equal_weight  # noqa: E402
from strategy.regime import build_defensive_returns, build_regime_panel  # noqa: E402
from strategy.signals import (  # noqa: E402
    absolute_momentum_filter, higher_moment_score, rsrs_panel,
)
from strategy.universe import (  # noqa: E402
    ABS_MOM_BENCHMARK, BENCHMARK_SYMBOL, BOND_OR_MONEY_SET,
)

# Match R37 module's local helper
sys.path.insert(0, str(REPO_ROOT / "analysis"))
from iterate_is_v7 import gold_conditioned_router  # noqa: E402

OUT = REPO_ROOT / "report" / "outputs"

# ---------- Fixed R37 winner config ----------
R37_PARAMS = dict(
    rsrs_N=30, rsrs_M=250, mom_L=180,
    lambda_s=0.2, lambda_k=0.0,
    w_rsrs=0.2, top_k=7,
    theta_off=-0.7, theta_on=0.7,
    rebal_threshold=0.4,
    rsrs_form="rsrs_skew",
)
R37_GATE_OFF = {0, 1, 3}
R37_GATE_FULL = {2}
R37_OVERLAY = dict(
    real_rate_pos_thresh=2.0,
    real_rate_neg_thresh=-2.0,
    dxy_mom_thresh=-0.05,
    fallback_when_gold_bad="511260",
)
R37_TARGET_IS_SHARPE = 1.423

TRAIN_WINDOW = 756
TEST_WINDOW = 252
STEP = 63


def _xs_z(df):
    mu = df.mean(axis=1); sd = df.std(axis=1).replace(0, np.nan)
    return df.sub(mu, axis=0).div(sd, axis=0)


def _build_signals(panels, params):
    close, high, low = panels["close"], panels["high"], panels["low"]
    rsrs = rsrs_panel(high, low, n=params["rsrs_N"], m=params["rsrs_M"], form="rsrs_skew")
    mom = higher_moment_score(close, L=params["mom_L"],
                                lambda_s=params["lambda_s"], lambda_k=params["lambda_k"])
    score = params["w_rsrs"] * _xs_z(rsrs).fillna(0) + (1 - params["w_rsrs"]) * mom.fillna(0)
    elig = absolute_momentum_filter(close, params["mom_L"], ABS_MOM_BENCHMARK)
    ma200 = close.rolling(200, min_periods=50).mean()
    elig = elig & (close > ma200)
    return rsrs, score, elig


def _equity_frac(regime_panel, off_set, full_set):
    s = regime_panel["regime_state_2"]
    ef = pd.Series(0.5, index=s.index)
    ef[s.isin(off_set)] = 0.0
    ef[s.isin(full_set)] = 1.0
    return ef


def _assemble(equity_w, defensive_w, equity_frac, rebal_thresh):
    cols = sorted(set(equity_w.columns) | set(defensive_w.columns))
    eq = equity_w.reindex(columns=cols, fill_value=0.0)
    de = defensive_w.reindex(columns=cols, fill_value=0.0)
    out = eq.mul(equity_frac, axis=0).add(de.mul(1 - equity_frac, axis=0), fill_value=0.0)
    if rebal_thresh and rebal_thresh > 0:
        out = _apply_rebal_threshold(out, rebal_thresh)
    return out


def _daily_def_from_mapping(regime_labels: pd.Series, cpi_state: pd.Series,
                              mapping: dict, default_sym: str = "511880") -> pd.Series:
    """Per-day defensive symbol from (regime × cpi) mapping. Falls back when bucket not in map."""
    out = pd.Series(default_sym, index=regime_labels.index)
    for dt in regime_labels.index:
        r = regime_labels.at[dt]
        if pd.isna(r):
            continue
        ms = cpi_state.at[dt] if dt in cpi_state.index else None
        sym = mapping.get((int(r), str(ms)))
        if sym is None:
            # try default per-regime fallback (most common across CPI buckets for that regime)
            for k, v in mapping.items():
                if isinstance(k, tuple) and k[0] == int(r):
                    sym = v
                    break
        if sym:
            out.at[dt] = sym
    return out


def _def_w_from_daily(daily_def: pd.Series, all_symbols: list[str]) -> pd.DataFrame:
    out = pd.DataFrame(0.0, index=daily_def.index, columns=all_symbols)
    for dt, sym in daily_def.items():
        if sym in out.columns:
            out.at[dt, sym] = 1.0
    return out


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

    # Pre-compute IS-full-window equity_frac (shared across windows)
    ef = _equity_frac(regime_panel, R37_GATE_OFF, R37_GATE_FULL)

    # ---------- Walk-Forward windows ----------
    n_dates = len(panels["close"].index)
    print(f"Total IS days: {n_dates}, train={TRAIN_WINDOW}, test={TEST_WINDOW}, step={STEP}")

    starts = list(range(0, n_dates - TRAIN_WINDOW - TEST_WINDOW + 1, STEP))
    print(f"WFA windows: {len(starts)}")

    wfa_test_returns: list[pd.Series] = []
    window_records = []
    overlap_test_returns: list[pd.Series] = []  # full 252d test segments (for diagnostics)

    full_dates = panels["close"].index

    for wi, s_idx in enumerate(starts):
        train_start = full_dates[s_idx]
        train_end_idx = s_idx + TRAIN_WINDOW - 1
        train_end = full_dates[train_end_idx]
        test_start_idx = s_idx + TRAIN_WINDOW
        test_end_idx = min(s_idx + TRAIN_WINDOW + TEST_WINDOW - 1, n_dates - 1)
        test_start = full_dates[test_start_idx]
        test_end = full_dates[test_end_idx]

        # Step segment: first STEP days of test period (for non-overlapping concat)
        step_end_idx = min(test_start_idx + STEP - 1, n_dates - 1)
        step_end = full_dates[step_end_idx]

        # 1. Train: derive (regime × CPI) mapping using sharpe_min_vol on TRAINING days
        train_mask = (def_returns.index >= train_start) & (def_returns.index <= train_end)
        train_returns = def_returns.loc[train_mask]
        train_regime = regime_panel.loc[train_mask, "regime_state_2"]
        train_cpi = cn_cpi_state.loc[train_mask]
        if train_regime.dropna().empty or train_returns.empty:
            continue
        mapping = per_regime_per_macro_best(train_regime, train_cpi, train_returns,
                                              metric="sharpe_min_vol", min_obs=15)
        # Fallback: if a regime has no obs in training, use defensive_pool top-Sharpe overall
        if not mapping:
            continue

        # 2. Apply mapping + gold-conditioning overlay across FULL panel,
        #    then take only the test/step segment.
        daily_base = _daily_def_from_mapping(regime_panel["regime_state_2"], cn_cpi_state, mapping)
        daily_cond = gold_conditioned_router(daily_base, regime_panel,
                                                real_rate_pos_thresh=R37_OVERLAY["real_rate_pos_thresh"],
                                                real_rate_neg_thresh=R37_OVERLAY["real_rate_neg_thresh"],
                                                dxy_mom_thresh=R37_OVERLAY["dxy_mom_thresh"],
                                                fallback_when_gold_bad=R37_OVERLAY["fallback_when_gold_bad"])
        def_w = _def_w_from_daily(daily_cond, all_symbols)

        # 3. Build full weights, then run backtest on the slice
        w = _assemble(base_topk, def_w, ef, p["rebal_threshold"])

        # Run backtest on test slice — need to also include some training history for shift math
        # Simplest: run on full panel, then slice the pnl by test window
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        full_pnl = res.pnl_net

        # Test (full 252d) — diagnostics
        test_pnl = full_pnl.loc[test_start:test_end]
        test_metrics = annualize_metrics(test_pnl)

        # Step (first 63d) — used for non-overlapping WF curve
        step_pnl = full_pnl.loc[test_start:step_end]

        wfa_test_returns.append(step_pnl)
        overlap_test_returns.append(test_pnl)

        # Train metrics (signal eval on training period)
        train_pnl = full_pnl.loc[train_start:train_end]
        train_metrics = annualize_metrics(train_pnl)

        record = {
            "window": wi,
            "train_start": train_start.strftime("%Y-%m-%d"),
            "train_end": train_end.strftime("%Y-%m-%d"),
            "test_start": test_start.strftime("%Y-%m-%d"),
            "test_end": test_end.strftime("%Y-%m-%d"),
            "step_end": step_end.strftime("%Y-%m-%d"),
            "train_sharpe": train_metrics["sharpe"],
            "test_sharpe": test_metrics["sharpe"],
            "test_ret": test_metrics["ann_ret"],
            "test_dd": test_metrics["max_dd"],
            "step_ret_total": float((1 + step_pnl).prod() - 1),
            "n_train_obs_per_regime": int(train_regime.value_counts().min()) if len(train_regime.dropna()) else 0,
            "mapping_size": len(mapping),
            "mapping": json.dumps({f"r{r}_cpi_{ms}": sym for (r, ms), sym in mapping.items()},
                                    ensure_ascii=False),
        }
        window_records.append(record)

        if wi % 5 == 0 or wi == len(starts) - 1:
            print(f"  [{wi+1}/{len(starts)}] train {train_start.date()}..{train_end.date()} "
                  f"test {test_start.date()}..{test_end.date()}  "
                  f"trainSh={train_metrics['sharpe']:.2f} testSh={test_metrics['sharpe']:.2f}")

    # ---------- Concatenate WF returns (non-overlapping step segments) ----------
    if not wfa_test_returns:
        raise RuntimeError("no WF test returns produced")
    wf_pnl = pd.concat(wfa_test_returns).sort_index()
    wf_pnl = wf_pnl[~wf_pnl.index.duplicated(keep="first")]
    wf_metrics = annualize_metrics(wf_pnl)
    wf_per_year = per_year_metrics(wf_pnl)

    print(f"\nWF concatenated PnL: {wf_pnl.index.min().date()} .. {wf_pnl.index.max().date()}, "
          f"{len(wf_pnl)} days")
    print(f"WF metrics:\n{json.dumps(wf_metrics, indent=2, default=str)}")
    print(f"\nWF per-year:")
    print(wf_per_year.to_string())

    # ---------- WF efficiency ----------
    train_sharpes = [r["train_sharpe"] for r in window_records]
    test_sharpes = [r["test_sharpe"] for r in window_records]
    mean_train_sh = float(np.nanmean(train_sharpes))
    mean_test_sh = float(np.nanmean(test_sharpes))
    wf_efficiency = mean_test_sh / mean_train_sh if mean_train_sh > 0 else float("nan")
    decay = 1 - mean_test_sh / mean_train_sh if mean_train_sh > 0 else float("nan")

    print(f"\n=== WF Efficiency ===")
    print(f"  mean_train_sharpe: {mean_train_sh:.3f}")
    print(f"  mean_test_sharpe : {mean_test_sh:.3f}")
    print(f"  wf_efficiency    : {wf_efficiency:.3f}  (target ≥ 0.6)")
    print(f"  IS->test decay   : {decay*100:.1f}%")
    print(f"  WF-concat Sharpe : {wf_metrics['sharpe']:.3f}")
    print(f"  R37 IS Sharpe    : {R37_TARGET_IS_SHARPE:.3f} (reference)")

    # ---------- Persist artifacts ----------
    pd.DataFrame(window_records).to_csv(OUT / "wfa_windows.csv", index=False)
    wf_pnl.to_csv(OUT / "wfa_concat_pnl.csv", header=["pnl"])
    wf_per_year.to_csv(OUT / "wfa_per_year.csv")
    pd.DataFrame([wf_metrics] + [{"wf_efficiency": wf_efficiency,
                                    "mean_train_sharpe": mean_train_sh,
                                    "mean_test_sharpe": mean_test_sh,
                                    "is_decay_pct": decay * 100,
                                    "n_windows": len(window_records)}]
                   ).to_csv(OUT / "wfa_summary.csv", index=False)

    print(f"\nArtifacts saved to {OUT}")
    print(f"Wall-clock: {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
