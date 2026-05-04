"""V3 continuation: R13-R18 — different mechanics that may reach IS Sharpe > R6.

R13 Two-stage selection (RSRS top-N -> mom_score top-K)
R14 Score-weighted top-K (rank^power weighting)
R15 Vol-parity weighting within top-K
R16 Adaptive regime band (rolling-quantile thresholds for risk-off)
R17 Best-of-R13..R16 + parameter local refine
R18 Final composition (everything stacked)
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
from strategy.portfolio import _apply_rebal_threshold, _defensive_pick  # noqa: E402
from strategy.signals import (  # noqa: E402
    absolute_momentum_filter, higher_moment_score, rsrs_panel,
)
from strategy.signals_v3 import (  # noqa: E402
    adaptive_regime_band, equity_frac_adaptive, score_weighted_topk,
    two_stage_selection, vol_parity_topk,
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


def _build_signals(panels, params):
    close, high, low = panels["close"], panels["high"], panels["low"]
    rsrs = rsrs_panel(high, low, n=params["rsrs_N"], m=params["rsrs_M"], form="rsrs_skew")
    mom = higher_moment_score(close, L=params["mom_L"],
                                lambda_s=params["lambda_s"], lambda_k=params["lambda_k"])
    score = params["w_rsrs"] * _xs_z(rsrs).fillna(0) + (1 - params["w_rsrs"]) * mom.fillna(0)
    elig = absolute_momentum_filter(close, params["mom_L"], ABS_MOM_BENCHMARK)
    elig = elig & _trend_filter_panel(close, 200)
    defensive_cols = [s for s in DEFENSIVE_SYMBOLS if s in rsrs.columns]
    defensive_proxy = rsrs[defensive_cols] if defensive_cols else None
    agg_rsrs = rsrs[BENCHMARK_SYMBOL] if BENCHMARK_SYMBOL in rsrs.columns else pd.Series(0.0, index=close.index)
    return rsrs, mom, score, elig, defensive_proxy, agg_rsrs


def _apply_overlay(equity_w: pd.DataFrame, agg_rsrs: pd.Series,
                    defensive_proxy, score: pd.DataFrame,
                    theta_off, theta_on, rebal_threshold: float,
                    adaptive_band: bool = False):
    """Apply regime overlay + rebal throttle."""
    if adaptive_band:
        # use rolling quantile band
        th_off, th_on = adaptive_regime_band(agg_rsrs, q_off=0.30, q_on=0.70,
                                              window=504, min_periods=120)
        equity_frac = equity_frac_adaptive(agg_rsrs, th_off, th_on)
    else:
        equity_frac = pd.Series(0.5, index=score.index)
        equity_frac[agg_rsrs.reindex(score.index) < theta_off] = 0.0
        equity_frac[agg_rsrs.reindex(score.index) >= theta_on] = 1.0

    equity_part = equity_w.mul(equity_frac, axis=0)
    if defensive_proxy is not None and not defensive_proxy.empty:
        d = _defensive_pick(defensive_proxy)
        d = d.reindex(index=score.index, columns=score.columns, fill_value=0.0)
        defensive_part = d.mul(1.0 - equity_frac, axis=0)
    else:
        defensive_part = pd.DataFrame(0.0, index=score.index, columns=score.columns)

    out = equity_part.add(defensive_part, fill_value=0.0)
    out = out.reindex(columns=score.columns, fill_value=0.0)
    if rebal_threshold and rebal_threshold > 0:
        out = _apply_rebal_threshold(out, rebal_threshold)
    return out


def _run_and_metrics(weights, panels):
    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)
    res = run_backtest(weights, panels["close"], panels["open"], panels["amount"], cost_cfg)
    return res


def to_row(round_n, label, params, extras, metrics):
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
    p = json.loads((OUT / "best_params_is.json").read_text())
    p = {k: v for k, v in p.items() if k != "v2_extras"}  # strip v2 extras if present
    p = expand_param(p)
    rsrs, mom, base_score, elig, defensive_proxy, agg_rsrs = _build_signals(panels, p)
    print(f"R6 seed params: {p}")

    rows = []
    bests = {}

    # ----------------- R13: Two-stage selection -----------------
    print("\n=== R13: two-stage selection ===")
    for n_first in [8, 10, 12, 15]:
        for k_final in [3, 5]:
            if k_final > n_first:
                continue
            equity_w = two_stage_selection(_xs_z(rsrs), mom, elig, n_first, k_final)
            w = _apply_overlay(equity_w, agg_rsrs, defensive_proxy, base_score,
                                p["theta_off"], p["theta_on"], p["rebal_threshold"])
            res = _run_and_metrics(w, panels)
            sh = res.metrics["sharpe"]
            extras = {"two_stage_n": n_first, "two_stage_k": k_final}
            rows.append(to_row(13, f"2stage n={n_first} k={k_final}", p, extras, res.metrics))
            print(f"  n={n_first:2d} k={k_final}  Sharpe={sh:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%")
            bests[("R13", n_first, k_final)] = sh
    r13_best = max(rows[-len(bests):], key=lambda r: r["sharpe_net"])

    # ----------------- R14: score-weighted top-K -----------------
    print("\n=== R14: score-weighted top-K ===")
    for k in [3, 5, 7]:
        for power in [0.5, 1.0, 1.5, 2.0]:
            equity_w = score_weighted_topk(base_score, elig, k, power)
            w = _apply_overlay(equity_w, agg_rsrs, defensive_proxy, base_score,
                                p["theta_off"], p["theta_on"], p["rebal_threshold"])
            res = _run_and_metrics(w, panels)
            sh = res.metrics["sharpe"]
            extras = {"sw_k": k, "sw_power": power}
            rows.append(to_row(14, f"sw k={k} pow={power}", p, extras, res.metrics))
            print(f"  k={k} pow={power}  Sharpe={sh:.3f}")

    # ----------------- R15: vol-parity within top-K -----------------
    print("\n=== R15: vol-parity weighting ===")
    for k in [3, 5, 7]:
        for vlb in [40, 60, 90]:
            equity_w = vol_parity_topk(base_score, elig, panels["close"], k, vol_lookback=vlb)
            w = _apply_overlay(equity_w, agg_rsrs, defensive_proxy, base_score,
                                p["theta_off"], p["theta_on"], p["rebal_threshold"])
            res = _run_and_metrics(w, panels)
            sh = res.metrics["sharpe"]
            extras = {"vp_k": k, "vp_vlb": vlb}
            rows.append(to_row(15, f"vp k={k} vlb={vlb}", p, extras, res.metrics))
            print(f"  k={k} vlb={vlb}  Sharpe={sh:.3f}")

    # ----------------- R16: adaptive regime band -----------------
    print("\n=== R16: adaptive regime band ===")
    # use rsrs of CSI300 with rolling quantile thresholds; combine with R6 base top-K
    from strategy.portfolio import _topk_equal_weight  # local
    for q_off, q_on in [(0.20, 0.80), (0.30, 0.70), (0.40, 0.60), (0.25, 0.75)]:
        equity_w = _topk_equal_weight(base_score, elig, p["top_k"])
        # use adaptive band overrides (still use _apply_overlay with adaptive=True)
        w = _apply_overlay(equity_w, agg_rsrs, defensive_proxy, base_score,
                            p["theta_off"], p["theta_on"], p["rebal_threshold"],
                            adaptive_band=True)
        # rerun with custom q values: monkey-patch via direct call
        th_off, th_on = adaptive_regime_band(agg_rsrs, q_off=q_off, q_on=q_on,
                                              window=504, min_periods=120)
        ef = equity_frac_adaptive(agg_rsrs, th_off, th_on)
        equity_part = equity_w.mul(ef, axis=0)
        if defensive_proxy is not None and not defensive_proxy.empty:
            d = _defensive_pick(defensive_proxy).reindex(index=base_score.index,
                                                            columns=base_score.columns,
                                                            fill_value=0.0)
            defensive_part = d.mul(1.0 - ef, axis=0)
        else:
            defensive_part = pd.DataFrame(0.0, index=base_score.index,
                                          columns=base_score.columns)
        w = equity_part.add(defensive_part, fill_value=0.0).reindex(columns=base_score.columns, fill_value=0.0)
        if p["rebal_threshold"] > 0:
            w = _apply_rebal_threshold(w, p["rebal_threshold"])
        res = _run_and_metrics(w, panels)
        sh = res.metrics["sharpe"]
        extras = {"adaptive_q_off": q_off, "adaptive_q_on": q_on}
        rows.append(to_row(16, f"adaptive q={q_off},{q_on}", p, extras, res.metrics))
        print(f"  q=({q_off},{q_on})  Sharpe={sh:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%")

    # ----------------- R17: Best-of + local param refine -----------------
    print("\n=== R17: best mechanism + local refine ===")
    df_so_far = pd.DataFrame(rows)
    best_row = df_so_far.sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"  best so far: round={int(best_row['round'])} Sharpe={best_row['sharpe_net']:.3f} "
          f"label='{best_row['label']}'")
    # Local-refine the original params around current best mechanism
    best_round = int(best_row["round"])
    best_extras = {k: best_row[k] for k in ["two_stage_n","two_stage_k","sw_k","sw_power",
                                              "vp_k","vp_vlb","adaptive_q_off","adaptive_q_on"]
                    if k in best_row and not pd.isna(best_row[k])}
    print(f"  best extras: {best_extras}")

    for w_rsrs in [0.2, 0.3, 0.4, 0.5]:
        for mom_L in [120, 180, 252]:
            for k in [3, 5, 7]:
                pp = dict(p); pp["w_rsrs"] = w_rsrs; pp["mom_L"] = mom_L; pp["top_k"] = k
                rsrs2, mom2, score2, elig2, dp2, agg2 = _build_signals(panels, pp)
                # rebuild equity_w according to best_round mechanism
                if best_round == 13:
                    nf, kf = int(best_extras["two_stage_n"]), int(best_extras["two_stage_k"])
                    if kf > nf:
                        continue
                    equity_w = two_stage_selection(_xs_z(rsrs2), mom2, elig2, nf, kf)
                elif best_round == 14:
                    sk, sp = int(best_extras["sw_k"]), float(best_extras["sw_power"])
                    equity_w = score_weighted_topk(score2, elig2, sk, sp)
                elif best_round == 15:
                    vk, vlb = int(best_extras["vp_k"]), int(best_extras["vp_vlb"])
                    equity_w = vol_parity_topk(score2, elig2, panels["close"], vk, vlb)
                elif best_round == 16:
                    from strategy.portfolio import _topk_equal_weight
                    equity_w = _topk_equal_weight(score2, elig2, k)
                else:
                    from strategy.portfolio import _topk_equal_weight
                    equity_w = _topk_equal_weight(score2, elig2, k)
                w = _apply_overlay(equity_w, agg2, dp2, score2,
                                    pp["theta_off"], pp["theta_on"], pp["rebal_threshold"])
                res = _run_and_metrics(w, panels)
                rows.append(to_row(17, f"refine wr={w_rsrs} L={mom_L} k={k}",
                                    pp, best_extras, res.metrics))

    # ----------------- R18: final stack -----------------
    print("\n=== R18: final stack — best mechanism + best params + maybe rev blend ===")
    df_now = pd.DataFrame(rows)
    best_row = df_now.sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"  carrying forward: Sharpe={best_row['sharpe_net']:.3f}")
    # Try adding 5d reversal blend on top of the best mechanism
    # (this is the only thing that helped slightly in R7)
    for rev_w in [0.0, 0.1, 0.15, 0.2]:
        for rebal in [0.0, 0.2, 0.4, 0.6]:
            pp = dict(p)
            for k in ("w_rsrs", "mom_L", "top_k"):
                if k in best_row and not pd.isna(best_row[k]):
                    pp[k] = float(best_row[k]) if k == "w_rsrs" else int(best_row[k])
            pp["rebal_threshold"] = rebal
            rsrs2, mom2, score2, elig2, dp2, agg2 = _build_signals(panels, pp)
            if rev_w > 0:
                from strategy.signals_v2 import reversal_panel
                rev_z = _xs_z(reversal_panel(panels["close"], L=5))
                score2 = (1 - rev_w) * score2 + rev_w * rev_z.fillna(0)
            # use the best mechanism
            best_round = int(best_row["round"])
            if best_round == 13:
                nf = int(best_row["two_stage_n"]); kf = int(best_row["two_stage_k"])
                if kf > nf:
                    continue
                equity_w = two_stage_selection(_xs_z(rsrs2), mom2, elig2, nf, kf)
            elif best_round == 14:
                sk = int(best_row["sw_k"]); sp = float(best_row["sw_power"])
                equity_w = score_weighted_topk(score2, elig2, sk, sp)
            elif best_round == 15:
                vk = int(best_row["vp_k"]); vlb = int(best_row["vp_vlb"])
                equity_w = vol_parity_topk(score2, elig2, panels["close"], vk, vlb)
            else:
                from strategy.portfolio import _topk_equal_weight
                equity_w = _topk_equal_weight(score2, elig2, pp["top_k"])
            w = _apply_overlay(equity_w, agg2, dp2, score2,
                                pp["theta_off"], pp["theta_on"], pp["rebal_threshold"])
            res = _run_and_metrics(w, panels)
            extras_final = {"rev_w": rev_w, "final_rebal": rebal,
                             "best_round_mech": best_round}
            rows.append(to_row(18, f"final rev={rev_w} rb={rebal}",
                                pp, extras_final, res.metrics))

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "all_candidates_v3.csv", index=False)

    # Pick overall winner (R13-R18)
    winner = df.sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"\n=== R13-R18 overall best: round={winner['round']} Sharpe={winner['sharpe_net']:.3f} ===")
    print(f"  label: {winner['label']}")
    print(f"  ann_ret={winner['ann_ret']*100:.2f}%  DD={winner['max_dd']*100:.2f}%  Calmar={winner['calmar']:.2f}")

    print("\nPer-round R13-R18 distribution:")
    print(df.groupby("round")["sharpe_net"].describe().round(3).to_string())

    # If we beat the previous (R6) best of 0.878, persist new winner
    R6_best = 0.878
    if winner["sharpe_net"] > R6_best:
        # Save winning artifacts
        out_p = expand_param({k: winner[k] for k in
                              ["rsrs_N","rsrs_M","mom_L","lambda_s","lambda_k",
                               "w_rsrs","top_k","theta_off","theta_on","rebal_threshold"]
                              if k in winner.index and not pd.isna(winner[k])})
        out_p["v3_label"] = winner["label"]
        (OUT / "best_params_is.json").write_text(
            json.dumps(out_p, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        print(f"\n*** UPDATED best_params_is.json (Sharpe {R6_best:.3f} -> {winner['sharpe_net']:.3f}) ***")
    else:
        print(f"\n(no improvement vs R6 best {R6_best:.3f}; best_params_is.json unchanged)")

    print(f"\nWall-clock: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
