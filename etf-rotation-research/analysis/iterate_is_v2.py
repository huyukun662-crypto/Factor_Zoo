"""Continuation iteration: R7-R12 building on R6 best params.

# [GUARDRAIL] IS-only via is_search.load_is_panels (capped at IS_END=2023-12-31).

Each round overrides one architectural piece:
  R7  Add short-term reversal blend (5d) into composite
  R8  Multi-horizon momentum (60/120/252 weighted)
  R9  Multi-horizon RSRS (18+60)
  R10 Vol-target overlay (target ann vol)
  R11 12-1 momentum (skip last N days)
  R12 Bucket-relative cross-sectional z + final tune
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
from strategy.backtest import CostConfig, run_backtest, per_year_metrics  # noqa: E402
from strategy.portfolio import build_target_weights  # noqa: E402
from strategy.signals import (  # noqa: E402
    absolute_momentum_filter, composite_score, higher_moment_score, rsrs_panel,
)
from strategy.signals_v2 import (  # noqa: E402
    apply_vol_target, bucket_relative_score, multi_horizon_momentum,
    multi_horizon_rsrs, reversal_panel, skip_momentum_panel,
)
from strategy.universe import (  # noqa: E402
    ABS_MOM_BENCHMARK, BENCHMARK_SYMBOL, BOND_OR_MONEY_SET, DEFENSIVE_SYMBOLS,
)

OUT = REPO_ROOT / "report" / "outputs"


def _trend_filter_panel(close: pd.DataFrame, ma_window: int = 200) -> pd.DataFrame:
    ma = close.rolling(ma_window, min_periods=max(20, ma_window // 4)).mean()
    return close > ma


def _xs_z(df: pd.DataFrame) -> pd.DataFrame:
    mu = df.mean(axis=1)
    sd = df.std(axis=1).replace(0, np.nan)
    return df.sub(mu, axis=0).div(sd, axis=0)


def evaluate_v2(panels: dict, params: dict, extras: dict) -> dict:
    """Evaluate with v2 extensions. extras controls which mechanism is on."""
    params = expand_param(params)
    close = panels["close"]
    high = panels["high"]
    low = panels["low"]
    universe_df = extras.get("universe_df")

    # ---- RSRS component ----
    if extras.get("multi_rsrs"):
        rsrs_score = multi_horizon_rsrs(high, low,
                                         configs=tuple(extras["multi_rsrs"]),
                                         weights=tuple(extras.get("multi_rsrs_w", [])) or None)
    else:
        rsrs_raw = rsrs_panel(high, low, n=params["rsrs_N"], m=params["rsrs_M"], form="rsrs_skew")
        rsrs_score = _xs_z(rsrs_raw)

    # Aggregate market RSRS (always single-horizon for regime gate, on benchmark)
    rsrs_bench = rsrs_panel(high, low, n=params["rsrs_N"], m=params["rsrs_M"], form="rsrs_skew")

    # ---- Momentum / higher-moment component ----
    if extras.get("multi_horizon_mom"):
        # blend higher-moment score with multi-horizon momentum
        z_mh = multi_horizon_momentum(close,
                                       horizons=tuple(extras["multi_horizon_mom"]),
                                       weights=tuple(extras.get("multi_horizon_w", [])) or None)
        mom_score = higher_moment_score(close, L=params["mom_L"],
                                         lambda_s=params["lambda_s"],
                                         lambda_k=params["lambda_k"]) + z_mh
    elif extras.get("skip_mom"):
        skip = extras["skip_mom"]
        skip_z = _xs_z(skip_momentum_panel(close, L=params["mom_L"], skip=skip))
        hm = higher_moment_score(close, L=params["mom_L"],
                                  lambda_s=params["lambda_s"], lambda_k=params["lambda_k"])
        mom_score = 0.5 * skip_z.fillna(0) + 0.5 * hm
    else:
        mom_score = higher_moment_score(close, L=params["mom_L"],
                                         lambda_s=params["lambda_s"],
                                         lambda_k=params["lambda_k"])

    # ---- Reversal component (R7) ----
    if extras.get("reversal_L"):
        rev_z = _xs_z(reversal_panel(close, L=extras["reversal_L"]))
        rev_w = float(extras.get("reversal_w", 0.2))
        mom_score = (1 - rev_w) * mom_score + rev_w * rev_z.fillna(0)

    # ---- Composite ----
    score = params["w_rsrs"] * rsrs_score.fillna(0) + (1 - params["w_rsrs"]) * mom_score.fillna(0)

    # ---- Bucket-relative (R12) ----
    if extras.get("bucket_relative") and universe_df is not None:
        score = bucket_relative_score(score, universe_df).fillna(0)

    # ---- Eligibility ----
    elig = absolute_momentum_filter(close, params["mom_L"], ABS_MOM_BENCHMARK)
    if extras.get("trend_ma_window"):
        elig = elig & _trend_filter_panel(close, extras["trend_ma_window"])

    defensive_cols = [s for s in DEFENSIVE_SYMBOLS if s in rsrs_bench.columns]
    defensive_proxy = rsrs_bench[defensive_cols] if defensive_cols else None
    agg_rsrs = rsrs_bench[BENCHMARK_SYMBOL] if BENCHMARK_SYMBOL in rsrs_bench.columns else pd.Series(0.0, index=close.index)

    weights = build_target_weights(
        score=score, eligibility=elig, agg_rsrs=agg_rsrs,
        defensive_proxy_score=defensive_proxy,
        top_k=params["top_k"], theta_off=params["theta_off"], theta_on=params["theta_on"],
        rebal_threshold=params.get("rebal_threshold", 0.0),
    )

    # ---- Vol target (R10) ----
    if extras.get("vol_target"):
        weights = apply_vol_target(weights, close,
                                    target_vol=extras["vol_target"],
                                    vol_lookback=extras.get("vol_lb", 60),
                                    max_leverage=1.0)

    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)
    res = run_backtest(weights, close, panels["open"], panels["amount"], cost_cfg)
    return {"params": params, "extras": extras, "metrics": res.metrics, "result": res}


def to_row(round_n: int, label: str, params: dict, extras: dict, metrics: dict) -> dict:
    row = {"round": round_n, "label": label, **params}
    for k, v in extras.items():
        if k == "universe_df":
            continue
        row[k] = v if not isinstance(v, (list, tuple)) else "|".join(map(str, v))
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
    universe_df = pd.read_csv(OUT / "universe.csv")

    # Load R6 best params (the seed point for R7+)
    p6 = json.loads((OUT / "best_params_is.json").read_text())
    base_extras = {"trend_ma_window": p6.get("trend_ma_window", 200),
                   "universe_df": universe_df}

    rows = []
    print(f"Seed (R6 best): {p6}")
    print(f"Seed Sharpe: 0.878 (per round6_grid)")

    # ================================================================
    # ROUND 7 — Reversal blend
    # ================================================================
    print("\n=== R7: short-term reversal blend ===")
    best7 = (-1e9, None, None)
    for L in [3, 5, 10, 21]:
        for w in [0.10, 0.20, 0.30, 0.40]:
            extras = {**base_extras, "reversal_L": L, "reversal_w": w}
            r = evaluate_v2(panels, p6, extras)
            sh = r["metrics"]["sharpe"]
            print(f"  L={L:2d} w={w:.2f}  Sharpe={sh:.3f}  Ret={r['metrics']['ann_ret']*100:5.2f}% DD={r['metrics']['max_dd']*100:6.2f}%")
            rows.append(to_row(7, f"reversal L={L} w={w}", p6, extras, r["metrics"]))
            if sh > best7[0]:
                best7 = (sh, p6, extras)
    print(f"R7 best: Sharpe={best7[0]:.3f}  extras={best7[2]}")

    # ================================================================
    # ROUND 8 — Multi-horizon momentum blend
    # ================================================================
    print("\n=== R8: multi-horizon momentum ===")
    best8 = (-1e9, None, None)
    horizon_sets = [
        ((60, 120), (0.5, 0.5)),
        ((60, 120, 252), (0.33, 0.34, 0.33)),
        ((90, 180, 252), (0.33, 0.34, 0.33)),
        ((60, 120, 180, 252), (0.25, 0.25, 0.25, 0.25)),
        ((120, 252), (0.5, 0.5)),
    ]
    for hs, ws in horizon_sets:
        extras = {**base_extras, "multi_horizon_mom": list(hs), "multi_horizon_w": list(ws)}
        # also keep best R7 reversal in
        if best7[2]:
            extras["reversal_L"] = best7[2]["reversal_L"]
            extras["reversal_w"] = best7[2]["reversal_w"]
        r = evaluate_v2(panels, p6, extras)
        sh = r["metrics"]["sharpe"]
        print(f"  horizons={hs}  Sharpe={sh:.3f}  Ret={r['metrics']['ann_ret']*100:5.2f}%")
        rows.append(to_row(8, f"mh-mom {hs}", p6, extras, r["metrics"]))
        if sh > best8[0]:
            best8 = (sh, p6, extras)
    print(f"R8 best: Sharpe={best8[0]:.3f}")

    # ================================================================
    # ROUND 9 — Multi-horizon RSRS
    # ================================================================
    print("\n=== R9: multi-horizon RSRS ===")
    best9 = (-1e9, None, None)
    rsrs_sets = [
        [(18, 600), (60, 600)],
        [(18, 250), (60, 250)],
        [(14, 600), (30, 600), (60, 600)],
        [(18, 600), (40, 600), (90, 600)],
    ]
    for rs in rsrs_sets:
        extras = dict(best8[2]) if best8[2] else dict(base_extras)
        extras["multi_rsrs"] = rs
        extras["multi_rsrs_w"] = [1.0 / len(rs)] * len(rs)
        r = evaluate_v2(panels, p6, extras)
        sh = r["metrics"]["sharpe"]
        print(f"  rsrs_set={rs}  Sharpe={sh:.3f}  Ret={r['metrics']['ann_ret']*100:5.2f}%")
        rows.append(to_row(9, f"mh-rsrs {rs}", p6, extras, r["metrics"]))
        if sh > best9[0]:
            best9 = (sh, p6, extras)
    print(f"R9 best: Sharpe={best9[0]:.3f}")

    # ================================================================
    # ROUND 10 — Vol target overlay
    # ================================================================
    print("\n=== R10: vol-target overlay ===")
    best10 = (-1e9, None, None)
    for tv in [0.08, 0.10, 0.12, 0.15, 0.18]:
        for vlb in [40, 60, 90]:
            extras = dict(best9[2]) if best9[2] else dict(base_extras)
            extras["vol_target"] = tv
            extras["vol_lb"] = vlb
            r = evaluate_v2(panels, p6, extras)
            sh = r["metrics"]["sharpe"]
            rows.append(to_row(10, f"vt={tv} lb={vlb}", p6, extras, r["metrics"]))
            if sh > best10[0]:
                best10 = (sh, p6, extras)
                print(f"  vt={tv} lb={vlb}  Sharpe={sh:.3f}  *new best*")
    print(f"R10 best: Sharpe={best10[0]:.3f}  vt={best10[2].get('vol_target')} lb={best10[2].get('vol_lb')}")

    # ================================================================
    # ROUND 11 — Skip momentum (12-1)
    # ================================================================
    print("\n=== R11: skip momentum (12-1) ===")
    best11 = (-1e9, None, None)
    for skip in [5, 10, 21, 42]:
        extras = dict(best10[2]) if best10[2] else dict(base_extras)
        # Disable multi_horizon_mom for this round (skip_mom replaces it)
        extras.pop("multi_horizon_mom", None)
        extras.pop("multi_horizon_w", None)
        extras["skip_mom"] = skip
        r = evaluate_v2(panels, p6, extras)
        sh = r["metrics"]["sharpe"]
        print(f"  skip={skip:2d}  Sharpe={sh:.3f}")
        rows.append(to_row(11, f"skip-mom skip={skip}", p6, extras, r["metrics"]))
        if sh > best11[0]:
            best11 = (sh, p6, extras)
    print(f"R11 best: Sharpe={best11[0]:.3f}")

    # ================================================================
    # ROUND 12 — Bucket relative + final mom_L / w_rsrs / top_k local refine
    # ================================================================
    print("\n=== R12: bucket-relative + local refine ===")
    # Pick the best running config across R7-R11
    candidates = [(best7[0], best7[2]), (best8[0], best8[2]), (best9[0], best9[2]),
                   (best10[0], best10[2]), (best11[0], best11[2])]
    bestR_extra = max(candidates)[1]
    print(f"  using extras seed: keys={list(bestR_extra.keys())}")

    best12 = (-1e9, None, None)
    # explore bucket_relative on/off + small param grid
    for br in [False, True]:
        for k in [3, 5, 7]:
            for w_rsrs in [0.2, 0.3, 0.4, 0.5]:
                for mL in [120, 180, 252]:
                    p = dict(p6)
                    p["top_k"] = k
                    p["w_rsrs"] = w_rsrs
                    p["mom_L"] = mL
                    extras = dict(bestR_extra)
                    extras["bucket_relative"] = br
                    extras["universe_df"] = universe_df
                    r = evaluate_v2(panels, p, extras)
                    sh = r["metrics"]["sharpe"]
                    rows.append(to_row(12, f"br={br} k={k} wr={w_rsrs} L={mL}", p, extras, r["metrics"]))
                    if sh > best12[0]:
                        best12 = (sh, p, extras)
    print(f"R12 best: Sharpe={best12[0]:.3f}  params={best12[1]}  br={best12[2].get('bucket_relative')}")

    # ---- Persist ----
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "all_candidates_v2.csv", index=False)

    # Pick overall winner (R7-R12)
    overall_winner = df.sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"\n=== Overall best (R7-R12): round={overall_winner['round']} "
          f"sharpe={overall_winner['sharpe_net']:.3f} ===")
    print(overall_winner.to_dict())

    # Recompute & save artifacts for the overall winner
    win_round = int(overall_winner["round"])
    win_label = overall_winner["label"]
    win_params = expand_param({k: overall_winner[k] for k in
                                ["rsrs_N","rsrs_M","mom_L","lambda_s","lambda_k",
                                 "w_rsrs","top_k","theta_off","theta_on","rebal_threshold"]
                                if k in overall_winner.index and not pd.isna(overall_winner[k])})
    win_params["rsrs_form"] = "rsrs_skew"
    # Need the matching extras — re-pick from rows
    win_row = df[df["sharpe_net"] == overall_winner["sharpe_net"]].iloc[0]
    win_extras = {**base_extras}
    for col in ["reversal_L","reversal_w","multi_horizon_mom","multi_horizon_w",
                "multi_rsrs","multi_rsrs_w","vol_target","vol_lb","skip_mom",
                "bucket_relative"]:
        if col in win_row.index and not pd.isna(win_row[col]):
            v = win_row[col]
            if isinstance(v, str) and "|" in v:
                # parse list-encoded
                parts = v.split("|")
                # try numeric
                try:
                    if "(" in parts[0]:
                        v = [eval(p) for p in parts]  # noqa: S307
                    else:
                        v = [float(p) for p in parts]
                except Exception:
                    v = parts
            win_extras[col] = v
    win_extras["universe_df"] = universe_df

    rfinal = evaluate_v2(panels, win_params, win_extras)
    res = rfinal["result"]
    pd.DataFrame([{"round": win_round, "label": win_label,
                    **rfinal["metrics"]}]).to_csv(OUT / "v2_overall_best.csv", index=False)
    res.equity.to_csv(OUT / "v2_winner_equity.csv", header=["equity"])
    per_year_metrics(res.pnl_net).to_csv(OUT / "v2_winner_per_year.csv")

    # Update best_params_is.json with v2 winner config if it improved
    win_sharpe = float(overall_winner["sharpe_net"])
    prev_best_sh = 0.878  # from R6
    if win_sharpe > prev_best_sh:
        out_params = dict(win_params)
        out_params["v2_extras"] = {k: (list(v) if isinstance(v, tuple) else v)
                                    for k, v in win_extras.items() if k != "universe_df"}
        (OUT / "best_params_is.json").write_text(
            json.dumps(out_params, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        print(f"\nUpdated best_params_is.json (Sharpe {prev_best_sh:.3f} -> {win_sharpe:.3f})")

    print(f"\nWall-clock: {time.time()-t0:.1f}s")
    print(f"Saved {OUT / 'all_candidates_v2.csv'}")
    print("\nPer-round R7-R12 distribution:")
    print(df.groupby("round")["sharpe_net"].describe().round(3).to_string())


if __name__ == "__main__":
    main()
