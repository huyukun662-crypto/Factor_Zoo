"""Re-run all 6 IS rounds and persist every candidate's full statistics.

Output: report/outputs/all_candidates.csv  (one row per evaluated parameter set)
        report/outputs/round{1..6}_grid.csv  (per-round grids)

# [GUARDRAIL] IS-only via is_search.load_is_panels (capped at 2019-12-31).
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

from analysis.is_search import (  # noqa: E402
    DEFAULT_PARAM_SPACE, DEFAULT_PARAMS,
    evaluate_params, expand_param, grid_search, load_is_panels,
)
from analysis.iterate_is import evaluate_with_extras  # noqa: E402

OUT = REPO_ROOT / "report" / "outputs"
OUT.mkdir(parents=True, exist_ok=True)


def to_row(params: dict, metrics: dict, round_n: int, label: str,
           extras: dict | None = None) -> dict:
    row = {"round": round_n, "label": label, **params}
    if extras:
        for k, v in extras.items():
            if k == "universe_df":
                continue
            row[k] = v if not isinstance(v, list) else "|".join(map(str, v))
    row.update({
        "ann_ret": metrics["ann_ret"],
        "ann_vol": metrics["ann_vol"],
        "sharpe_net": metrics["sharpe"],
        "sharpe_gross": metrics.get("gross_sharpe", float("nan")),
        "max_dd": metrics["max_dd"],
        "calmar": metrics["calmar"],
        "sortino": metrics["sortino"],
        "win_rate": metrics["win_rate"],
        "ann_turnover": metrics["ann_turnover"],
        "n_days": metrics["n"],
    })
    return row


def main():
    t0 = time.time()
    panels = load_is_panels()
    universe_df = pd.read_csv(OUT / "universe.csv")

    all_rows: list[dict] = []

    # ---- R1: baseline (single point) ----
    print("=== R1: baseline ===")
    p1 = dict(DEFAULT_PARAMS)
    r1 = evaluate_params(p1, panels=panels)
    row = to_row(p1, r1["metrics"], 1, "Baseline")
    all_rows.append(row)
    pd.DataFrame([row]).to_csv(OUT / "round1_grid.csv", index=False)

    # ---- R2: LHS 200 grid (use existing CSV if present, else re-run) ----
    print("=== R2: LHS 200 ===")
    r2_fp = OUT / "round2_grid.csv"
    if r2_fp.exists():
        r2_df = pd.read_csv(r2_fp)
        # Normalize columns to match all_rows schema
        for _, r in r2_df.iterrows():
            params = {k: r[k] for k in DEFAULT_PARAMS.keys()
                      if k in r and not (isinstance(r[k], float) and pd.isna(r[k]))}
            params["rsrs_form"] = "rsrs_skew"
            metrics = {"ann_ret": r["ann_ret"], "ann_vol": r["ann_vol"],
                       "sharpe": r["sharpe"], "max_dd": r["max_dd"],
                       "calmar": r["calmar"], "sortino": r["sortino"],
                       "win_rate": r["win_rate"], "n": int(r["n"]),
                       "gross_sharpe": r["gross_sharpe"],
                       "ann_turnover": r["ann_turnover"]}
            all_rows.append(to_row(params, metrics, 2, "LHS-200"))
    else:
        grid_df = grid_search(DEFAULT_PARAM_SPACE, n_samples=200, seed=20260503,
                               panels=panels, progress=False)
        grid_df.to_csv(r2_fp, index=False)
        # rebuild rows
        for _, r in grid_df.iterrows():
            params = {k: r[k] for k in DEFAULT_PARAMS.keys() if k in r}
            params["rsrs_form"] = "rsrs_skew"
            metrics = {"ann_ret": r["ann_ret"], "ann_vol": r["ann_vol"],
                       "sharpe": r["sharpe"], "max_dd": r["max_dd"],
                       "calmar": r["calmar"], "sortino": r["sortino"],
                       "win_rate": r["win_rate"], "n": int(r["n"]),
                       "gross_sharpe": r["gross_sharpe"],
                       "ann_turnover": r["ann_turnover"]}
            all_rows.append(to_row(params, metrics, 2, "LHS-200"))

    # Read R2 best to seed downstream rounds
    p2_best = pd.read_csv(r2_fp).iloc[0].to_dict()
    p2 = expand_param({k: p2_best[k] for k in DEFAULT_PARAMS.keys() if k in p2_best})
    p2["rsrs_form"] = "rsrs_skew"

    # ---- R3: trend MA grid (4 candidates) ----
    print("=== R3: trend MA grid ===")
    r3_rows = []
    best_r3_extra = None
    best_r3_sh = -1e9
    for ma in [60, 100, 150, 200]:
        extras = {"trend_ma_window": ma}
        r = evaluate_with_extras(panels, p2, extras=extras)
        row = to_row(p2, r["metrics"], 3, f"+ Trend MA{ma}", extras=extras)
        all_rows.append(row); r3_rows.append(row)
        if r["metrics"]["sharpe"] > best_r3_sh:
            best_r3_sh = r["metrics"]["sharpe"]
            best_r3_extra = extras
    pd.DataFrame(r3_rows).to_csv(OUT / "round3_grid.csv", index=False)

    # ---- R4: bucket trim grid (7 candidates) ----
    print("=== R4: bucket trim grid ===")
    bucket_options = [
        [], ["海外"], ["商品"], ["海外", "商品"],
        ["地产链", "农业"], ["海外", "地产链", "农业"], ["现金"],
    ]
    r4_rows = []
    best_r4_extra = best_r3_extra
    best_r4_sh = -1e9
    for excl in bucket_options:
        extras = {**best_r3_extra, "universe_df": universe_df, "exclude_buckets": excl}
        r = evaluate_with_extras(panels, p2, extras=extras)
        row = to_row(p2, r["metrics"], 4,
                     f"trim {excl or '(none)'}",
                     extras={"trend_ma_window": best_r3_extra["trend_ma_window"],
                              "exclude_buckets": excl})
        all_rows.append(row); r4_rows.append(row)
        if r["metrics"]["sharpe"] > best_r4_sh:
            best_r4_sh = r["metrics"]["sharpe"]
            best_r4_extra = extras
    pd.DataFrame(r4_rows).to_csv(OUT / "round4_grid.csv", index=False)

    # ---- R5: risk-off band x top_k (6 x 3 = 18) ----
    print("=== R5: band × top_k grid ===")
    bands = [(-1.0, 0.5), (-0.7, 0.7), (-0.5, 1.0),
              (-1.5, 0.0), (-0.7, 1.5), (-0.3, 0.3)]
    topks = [3, 5, 7]
    r5_rows = []
    best_r5_p = None
    best_r5_sh = -1e9
    for band in bands:
        for k in topks:
            p = dict(p2)
            p["theta_off"], p["theta_on"] = band
            p["top_k"] = k
            r = evaluate_with_extras(panels, p, extras=best_r4_extra)
            row = to_row(p, r["metrics"], 5,
                         f"band({band[0]},{band[1]}) k={k}",
                         extras={"trend_ma_window": best_r4_extra["trend_ma_window"],
                                 "exclude_buckets": best_r4_extra.get("exclude_buckets", [])})
            all_rows.append(row); r5_rows.append(row)
            if r["metrics"]["sharpe"] > best_r5_sh:
                best_r5_sh = r["metrics"]["sharpe"]
                best_r5_p = p
    pd.DataFrame(r5_rows).to_csv(OUT / "round5_grid.csv", index=False)

    # ---- R6: local refine mom_L × λ_s × rebal (5 × 5 × 5 = 125) ----
    print("=== R6: local refine grid ===")
    r6_rows = []
    for mom_L in [60, 90, 120, 150, 180]:
        for ls in [0.0, 0.2, 0.3, 0.5, 0.7]:
            for rb in [0.0, 0.10, 0.20, 0.30, 0.40]:
                p = dict(best_r5_p)
                p["mom_L"] = mom_L
                p["lambda_s"] = ls
                p["rebal_threshold"] = rb
                r = evaluate_with_extras(panels, p, extras=best_r4_extra)
                row = to_row(p, r["metrics"], 6,
                             f"refine L={mom_L} λs={ls} rb={rb}",
                             extras={"trend_ma_window": best_r4_extra["trend_ma_window"],
                                      "exclude_buckets": best_r4_extra.get("exclude_buckets", [])})
                all_rows.append(row); r6_rows.append(row)
    pd.DataFrame(r6_rows).to_csv(OUT / "round6_grid.csv", index=False)

    full = pd.DataFrame(all_rows)
    full.to_csv(OUT / "all_candidates.csv", index=False)
    print(f"\nTotal candidates evaluated: {len(full)}")
    print(f"Wall-clock: {time.time()-t0:.1f}s")
    print(f"Saved {OUT/'all_candidates.csv'}")

    # Summary by round
    print("\nSummary by round (best Sharpe net):")
    print(full.groupby("round")["sharpe_net"].agg(["count","max","mean","min"]).round(3))


if __name__ == "__main__":
    main()
