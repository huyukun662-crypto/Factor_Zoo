"""V4 continuation: R19-R24 — regime-based defensive routing + macro factors.

R19 Build regime panel (trend × vol) and find IS-best defensive per regime
R20 Same with 3-axis (trend × vol × PMI growth)
R21 Macro tilts: blend macro signals into composite score
R22 Yield-curve gate (use cn_10_2_spread or us_cn spread as additional gate)
R23 Local param search around the best regime config
R24 Final stacked: regime + macro + best params

# [GUARDRAIL] IS_END=2023-12-31. All evaluations strictly inside IS.
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
from data.fetch_macro import align_to_daily, fetch_all_macro  # noqa: E402
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


def _trend_filter_panel(close, ma_window=200):
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
    agg_rsrs = rsrs[BENCHMARK_SYMBOL] if BENCHMARK_SYMBOL in rsrs.columns else pd.Series(0.0, index=close.index)
    return rsrs, mom, score, elig, agg_rsrs


# ---- core engine that takes pre-computed equity/defensive parts ----

def assemble_weights(equity_w: pd.DataFrame, defensive_w: pd.DataFrame,
                      equity_frac: pd.Series, rebal_threshold: float = 0.0):
    cols = sorted(set(equity_w.columns) | set(defensive_w.columns))
    eq = equity_w.reindex(columns=cols, fill_value=0.0)
    de = defensive_w.reindex(columns=cols, fill_value=0.0)
    ef = equity_frac.reindex(eq.index)
    out = eq.mul(ef, axis=0).add(de.mul(1 - ef, axis=0), fill_value=0.0)
    if rebal_threshold and rebal_threshold > 0:
        out = _apply_rebal_threshold(out, rebal_threshold)
    return out


def _equity_frac_from_band(agg_rsrs, theta_off, theta_on):
    ef = pd.Series(0.5, index=agg_rsrs.index)
    ef[agg_rsrs < theta_off] = 0.0
    ef[agg_rsrs >= theta_on] = 1.0
    return ef


def _equity_frac_from_regime(regime_panel, off_cells: set[int], full_cells: set[int],
                              state_col: str = "regime_state_2"):
    """Map regime cell to equity fraction.

    off_cells -> 0.0 (full risk-off / defensive)
    full_cells -> 1.0 (full equity)
    others -> 0.5 (half-half)
    """
    s = regime_panel[state_col]
    ef = pd.Series(0.5, index=s.index)
    ef[s.isin(off_cells)] = 0.0
    ef[s.isin(full_cells)] = 1.0
    return ef


def to_row(round_n, label, params, extras, metrics):
    row = {"round": round_n, "label": label, **params}
    for k, v in extras.items():
        if k in ("universe_df", "regime_panel", "macro"):
            continue
        row[k] = v if not isinstance(v, (list, tuple, dict)) else str(v)
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

    # Load best R6 params
    p = json.loads((OUT / "best_params_is.json").read_text())
    p = {k: v for k, v in p.items() if k not in ("v2_extras", "v3_label")}
    p = expand_param(p)
    print(f"R6 seed: {p}")

    # Build base signals
    rsrs, mom, base_score, elig, agg_rsrs = _build_signals(panels, p)
    base_topk = _topk_equal_weight(base_score, elig, p["top_k"])

    # Load macro & build regime panel using CSI300
    print("\n[setup] loading macro + building regime panel...")
    macro = fetch_all_macro()
    bench = panels["close"][BENCHMARK_SYMBOL]
    regime_panel = build_regime_panel(bench, macro=macro, ma_window=200, vol_window=60)
    print(f"  regime_panel shape={regime_panel.shape}")
    print(f"  regime_state_2 dist:\n{regime_panel['regime_state_2'].value_counts().sort_index()}")
    print(f"  regime_state_3 dist:\n{regime_panel['regime_state_3'].value_counts().sort_index()}")

    # Available defensives in panel
    defensive_in_panel = [s for s in DEFENSIVE_SYMBOLS if s in panels["close"].columns]
    def_returns = build_defensive_returns(panels["close"], defensive_in_panel)
    print(f"  defensive symbols available: {defensive_in_panel}")

    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)
    rows = []

    # ================================================================
    # ROUND 19 — 4-cell regime (trend × vol) + IS-best defensive routing
    # ================================================================
    print("\n=== R19: 4-cell regime + per-regime best defensive ===")
    map_2 = best_defensive_per_regime(regime_panel["regime_state_2"], def_returns)
    print(f"  IS-best defensive per regime: {map_2}")
    def_w = regime_routed_defensive_weights(regime_panel["regime_state_2"], map_2,
                                              list(panels["close"].columns))

    # Try multiple "off" cell choices
    candidates_off = [
        ({0, 1}, {2, 3}, "off=down,*; full=up,*"),    # trend down -> off
        ({0, 1, 3}, {2}, "off=down,*|up,high; full=up,low"),  # +high vol off
        ({1, 3}, {2}, "off=down,high|up,high; full=up,low"),  # high-vol = off
        ({0, 1}, {2}, "off=down,*; mid=up,high; full=up,low"),
    ]
    for off_set, full_set, desc in candidates_off:
        ef = _equity_frac_from_regime(regime_panel, off_set, full_set, "regime_state_2")
        w = assemble_weights(base_topk, def_w, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        sh = res.metrics["sharpe"]
        rows.append(to_row(19, f"r2 {desc}", p,
                            {"off": str(sorted(off_set)), "full": str(sorted(full_set))},
                            res.metrics))
        print(f"  {desc:55s}  Sharpe={sh:.3f}  Ret={res.metrics['ann_ret']*100:5.2f}%  DD={res.metrics['max_dd']*100:6.2f}%")

    # ================================================================
    # ROUND 20 — 8-cell regime (trend × vol × PMI growth)
    # ================================================================
    print("\n=== R20: 8-cell regime + per-regime best defensive ===")
    map_3 = best_defensive_per_regime(regime_panel["regime_state_3"], def_returns)
    print(f"  IS-best defensive per regime (8-cell): {map_3}")
    def_w_3 = regime_routed_defensive_weights(regime_panel["regime_state_3"], map_3,
                                                list(panels["close"].columns))

    # 8-cell labels: state = trend*4 + vol*2 + growth
    # off: trend down OR (high vol AND contracting)
    candidates_off_3 = [
        ({0,1,2,3}, {6,7}, "off=down,*; full=up,low"),
        ({0,1,2,3,5,7}, {6}, "off=down or high-vol-contract; full=up,low,exp"),
        ({0,1,2,3}, {4,5,6,7}, "binary trend"),
        ({0,1,2,3,5}, {4,6,7}, "off=down,*|up,high,contract"),
    ]
    for off_set, full_set, desc in candidates_off_3:
        ef = _equity_frac_from_regime(regime_panel, off_set, full_set, "regime_state_3")
        w = assemble_weights(base_topk, def_w_3, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        rows.append(to_row(20, f"r3 {desc}", p,
                            {"off": str(sorted(off_set)), "full": str(sorted(full_set))},
                            res.metrics))
        print(f"  {desc:55s}  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:5.2f}%")

    # ================================================================
    # ROUND 21 — Macro tilt: blend macro into score
    # ================================================================
    print("\n=== R21: macro tilt blended into composite score ===")
    # idea: when CPI is high, tilt toward gold + cyclicals (real-asset basket)
    #       when M2 is rising, tilt toward growth (科技 / 大消费)
    #       when PMI < 50, tilt toward defensive + bonds
    # We synthesize a per-day macro_tilt for each ETF based on its bucket.
    bucket_map = dict(zip(universe_df["symbol"].astype(str), universe_df["bucket"]))

    def macro_tilt(close: pd.DataFrame, regime_panel: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(0.0, index=close.index, columns=close.columns)
        cpi = regime_panel["cpi_yoy"]
        m2 = regime_panel["m2_yoy"]
        pmi = regime_panel["pmi"]
        # standardize macro to z-scores over rolling 5-yr
        cpi_z = (cpi - cpi.rolling(252*3, min_periods=120).mean()) / cpi.rolling(252*3, min_periods=120).std()
        m2_z = (m2 - m2.rolling(252*3, min_periods=120).mean()) / m2.rolling(252*3, min_periods=120).std()
        pmi_z = (pmi - 50) / 5.0  # PMI is centered at 50 with ~5 unit dispersion

        cyclical_buckets = {"周期", "地产链"}
        growth_buckets = {"科技", "大消费", "新能源"}
        defensive_buckets = {"红利", "债", "现金"}
        commodity_buckets = {"商品"}

        for sym in close.columns:
            b = bucket_map.get(str(sym), "")
            if b in growth_buckets:
                out[sym] = m2_z.fillna(0).reindex(close.index, method="ffill")
            elif b in cyclical_buckets:
                out[sym] = cpi_z.fillna(0).reindex(close.index, method="ffill")
            elif b in commodity_buckets:
                out[sym] = cpi_z.fillna(0).reindex(close.index, method="ffill")
            elif b in defensive_buckets:
                out[sym] = (-pmi_z.fillna(0)).reindex(close.index, method="ffill")
        return out.fillna(0)

    macro_score = macro_tilt(panels["close"], regime_panel)
    # search blend weight
    best_r21 = (-1e9, None)
    for w_macro in [0.0, 0.10, 0.20, 0.30, 0.40, 0.50]:
        score = base_score * (1 - w_macro) + macro_score * w_macro
        topk = _topk_equal_weight(score, elig, p["top_k"])
        # use R19 best regime routing
        best_r19_row = pd.DataFrame(rows)
        best_r19_row = best_r19_row[best_r19_row["round"] == 19].sort_values("sharpe_net", ascending=False).iloc[0]
        off_set = eval(best_r19_row["off"])  # noqa: S307
        full_set = eval(best_r19_row["full"])  # noqa: S307
        ef = _equity_frac_from_regime(regime_panel, set(off_set), set(full_set), "regime_state_2")
        w = assemble_weights(topk, def_w, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        rows.append(to_row(21, f"macro_blend w={w_macro}", p, {"w_macro": w_macro}, res.metrics))
        print(f"  w_macro={w_macro:.2f}  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:5.2f}%")
        if res.metrics["sharpe"] > best_r21[0]:
            best_r21 = (res.metrics["sharpe"], w_macro)

    # ================================================================
    # ROUND 22 — Yield-curve / spread additional gate
    # ================================================================
    print("\n=== R22: yield-curve spread gate ===")
    # When cn_10y_2y_spread is very low / negative => recession risk => more defensive
    # When us_cn_10y_spread > X => USD outflow risk => more defensive
    spread_cn = regime_panel["cn_10_2_spread"]
    # compute rolling 30th/70th pct of spread
    sp_lo = spread_cn.rolling(504, min_periods=120).quantile(0.30)
    sp_hi = spread_cn.rolling(504, min_periods=120).quantile(0.70)
    yield_gate_off = spread_cn < sp_lo
    yield_gate_full = spread_cn >= sp_hi

    # Combine with R19 best regime routing
    best_r19_row = pd.DataFrame(rows)
    best_r19_row = best_r19_row[best_r19_row["round"] == 19].sort_values("sharpe_net", ascending=False).iloc[0]
    off_set19 = set(eval(best_r19_row["off"]))  # noqa: S307
    full_set19 = set(eval(best_r19_row["full"]))  # noqa: S307

    for use_yield in [False, True]:
        ef = _equity_frac_from_regime(regime_panel, off_set19, full_set19, "regime_state_2")
        if use_yield:
            ef = ef.where(~yield_gate_off, 0.0)
            ef = ef.mask(yield_gate_full, 1.0)
        w = assemble_weights(base_topk, def_w, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        rows.append(to_row(22, f"yield_gate={use_yield}", p, {"yield_gate": use_yield}, res.metrics))
        print(f"  yield_gate={use_yield}  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:5.2f}%")

    # ================================================================
    # ROUND 23 — Param search around best regime config
    # ================================================================
    print("\n=== R23: param search around best regime config ===")
    df_so_far = pd.DataFrame(rows)
    best_row = df_so_far.sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"  best so far: Sharpe={best_row['sharpe_net']:.3f}  round={int(best_row['round'])}  label={best_row['label']}")

    # Carry forward the regime config + iterate (mom_L, w_rsrs, top_k, rebal_threshold)
    # Use R19 best regime routing as the wrapper
    for mL in [120, 180, 252]:
        for wr in [0.20, 0.30, 0.40, 0.50]:
            for k in [3, 5, 7]:
                for rb in [0.0, 0.20, 0.40, 0.60]:
                    pp = dict(p); pp["mom_L"] = mL; pp["w_rsrs"] = wr; pp["top_k"] = k; pp["rebal_threshold"] = rb
                    rsrs2, mom2, score2, elig2, agg2 = _build_signals(panels, pp)
                    topk2 = _topk_equal_weight(score2, elig2, k)
                    ef = _equity_frac_from_regime(regime_panel, off_set19, full_set19, "regime_state_2")
                    w = assemble_weights(topk2, def_w, ef, rb)
                    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
                    rows.append(to_row(23, f"refine L={mL} wr={wr} k={k} rb={rb}",
                                        pp, {"off": str(sorted(off_set19)), "full": str(sorted(full_set19))},
                                        res.metrics))

    df_now = pd.DataFrame(rows)
    best23 = df_now[df_now["round"] == 23].sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"  R23 best: Sharpe={best23['sharpe_net']:.3f}  L={best23['mom_L']} wr={best23['w_rsrs']} k={best23['top_k']} rb={best23['rebal_threshold']}")

    # ================================================================
    # ROUND 24 — Final stack: regime + macro tilt + best params
    # ================================================================
    print("\n=== R24: final stack — regime + macro + best R23 params ===")
    pf = expand_param({
        "rsrs_N": int(best23["rsrs_N"]), "rsrs_M": int(best23["rsrs_M"]),
        "mom_L": int(best23["mom_L"]),
        "lambda_s": float(best23["lambda_s"]), "lambda_k": float(best23["lambda_k"]),
        "w_rsrs": float(best23["w_rsrs"]), "top_k": int(best23["top_k"]),
        "theta_off": float(best23["theta_off"]), "theta_on": float(best23["theta_on"]),
        "rebal_threshold": float(best23["rebal_threshold"]),
    })
    pf["rsrs_form"] = "rsrs_skew"

    rsrsf, momf, score_f, elig_f, agg_f = _build_signals(panels, pf)
    macro_score_f = macro_tilt(panels["close"], regime_panel)
    for w_macro in [0.0, 0.10, 0.20, 0.30]:
        for use_yield in [False, True]:
            score = score_f * (1 - w_macro) + macro_score_f * w_macro
            topk = _topk_equal_weight(score, elig_f, pf["top_k"])
            ef = _equity_frac_from_regime(regime_panel, off_set19, full_set19, "regime_state_2")
            if use_yield:
                ef = ef.where(~yield_gate_off, 0.0)
                ef = ef.mask(yield_gate_full, 1.0)
            w = assemble_weights(topk, def_w, ef, pf["rebal_threshold"])
            res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
            rows.append(to_row(24, f"final w_macro={w_macro} yield={use_yield}",
                                pf, {"w_macro": w_macro, "yield_gate": use_yield,
                                      "off": str(sorted(off_set19)), "full": str(sorted(full_set19))},
                                res.metrics))
            print(f"  w_macro={w_macro:.2f} yield={use_yield}  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:5.2f}%")

    # ---- Persist ----
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "all_candidates_v4.csv", index=False)

    winner = df.sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"\n=== R19-R24 overall best: round={int(winner['round'])} Sharpe={winner['sharpe_net']:.3f} ===")
    print(f"  label: {winner['label']}")
    print(f"  ann_ret={winner['ann_ret']*100:.2f}%  DD={winner['max_dd']*100:.2f}%  Calmar={winner['calmar']:.2f}")

    R6_best = 0.878
    if winner["sharpe_net"] > R6_best:
        print(f"\n*** IMPROVED Sharpe {R6_best:.3f} -> {winner['sharpe_net']:.3f} ***")

        # Save winner artifacts
        win_p = expand_param({k: winner[k] for k in
                              ["rsrs_N","rsrs_M","mom_L","lambda_s","lambda_k",
                               "w_rsrs","top_k","theta_off","theta_on","rebal_threshold"]
                              if k in winner.index and not pd.isna(winner[k])})
        win_p["rsrs_form"] = "rsrs_skew"
        win_p["v4_label"] = winner["label"]
        win_p["v4_off_set"] = sorted(off_set19)
        win_p["v4_full_set"] = sorted(full_set19)
        win_p["v4_defensive_map"] = {int(k): v for k, v in map_2.items()}
        if "w_macro" in winner.index:
            win_p["v4_w_macro"] = float(winner["w_macro"]) if not pd.isna(winner["w_macro"]) else 0.0
        if "yield_gate" in winner.index:
            win_p["v4_yield_gate"] = bool(winner["yield_gate"]) if not pd.isna(winner["yield_gate"]) else False

        (OUT / "best_params_is.json").write_text(
            json.dumps(win_p, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

        # Save per-year + equity for the winner — re-run
        if int(winner["round"]) == 24:
            w_macro = float(winner["w_macro"]) if "w_macro" in winner.index and not pd.isna(winner["w_macro"]) else 0.0
            use_yield = bool(winner["yield_gate"]) if "yield_gate" in winner.index and not pd.isna(winner["yield_gate"]) else False
            score = score_f * (1 - w_macro) + macro_score_f * w_macro
            topk = _topk_equal_weight(score, elig_f, win_p["top_k"])
            ef = _equity_frac_from_regime(regime_panel, off_set19, full_set19, "regime_state_2")
            if use_yield:
                ef = ef.where(~yield_gate_off, 0.0).mask(yield_gate_full, 1.0)
            w = assemble_weights(topk, def_w, ef, win_p["rebal_threshold"])
            res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
            res.equity.to_csv(OUT / "v4_winner_equity.csv", header=["equity"])
            per_year_metrics(res.pnl_net).to_csv(OUT / "v4_winner_per_year.csv")
            print(f"  saved v4_winner_equity.csv and v4_winner_per_year.csv")
    else:
        print(f"\n(no improvement vs R6 best {R6_best:.3f})")

    print("\nPer-round R19-R24 distribution:")
    print(df.groupby("round")["sharpe_net"].describe().round(3).to_string())
    print(f"\nWall-clock: {time.time()-t0:.1f}s")
    print(f"Saved {OUT / 'all_candidates_v4.csv'}")


if __name__ == "__main__":
    main()
