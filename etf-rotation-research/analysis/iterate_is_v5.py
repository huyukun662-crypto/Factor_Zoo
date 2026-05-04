"""V5 continuation: R25-R30 — diversified defensive routing by macro environment.

R25 Expanded defensive pool, per-regime SHARPE-MIN-VOL (excludes cash from auto-winning)
R26 Per-regime ANN-RETURN argmax (highest absolute return)
R27 Macro IF-THEN rule router (CPI+PMI+vol -> {gold, bonds, dividend, coal, cash})
R28 Per (regime × CPI level) — 8 buckets, find best defensive
R29 Param search around best defensive routing
R30 Final stack

# [GUARDRAIL] IS_END=2023-12-31. Pure IS optimization.
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
from strategy.backtest import CostConfig, run_backtest, per_year_metrics  # noqa: E402
from strategy.defensive import (  # noqa: E402
    EXPANDED_DEFENSIVE, macro_rule_router, per_regime_best,
    per_regime_per_macro_best, routed_defensive_weights,
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


def _equity_frac(regime_panel, off_set, full_set, state_col="regime_state_2"):
    s = regime_panel[state_col]
    ef = pd.Series(0.5, index=s.index)
    ef[s.isin(off_set)] = 0.0
    ef[s.isin(full_set)] = 1.0
    return ef


def assemble(equity_w, defensive_w, equity_frac, rebal_thresh):
    cols = sorted(set(equity_w.columns) | set(defensive_w.columns))
    eq = equity_w.reindex(columns=cols, fill_value=0.0)
    de = defensive_w.reindex(columns=cols, fill_value=0.0)
    out = eq.mul(equity_frac, axis=0).add(de.mul(1 - equity_frac, axis=0), fill_value=0.0)
    if rebal_thresh and rebal_thresh > 0:
        out = _apply_rebal_threshold(out, rebal_thresh)
    return out


def to_row(round_n, label, params, extras, metrics):
    row = {"round": round_n, "label": label, **params}
    for k, v in extras.items():
        if k in ("regime_panel", "macro", "panels", "universe_df"):
            continue
        row[k] = v if not isinstance(v, (list, tuple, dict, set)) else str(v)
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
    macro = fetch_all_macro()
    bench = panels["close"][BENCHMARK_SYMBOL]
    regime_panel = build_regime_panel(bench, macro=macro, ma_window=200, vol_window=60)

    # Load R23 best params (current best)
    p = json.loads((OUT / "best_params_is.json").read_text())
    p = {k: v for k, v in p.items() if not str(k).startswith("v4_") and k != "v3_label"}
    p = expand_param(p)
    print(f"R23 seed: {p}")

    # Build base signals + topk
    rsrs, score, elig = _build_signals(panels, p)
    base_topk = _topk_equal_weight(score, elig, p["top_k"])

    # Expanded defensive pool
    defensive_pool = [s for s in EXPANDED_DEFENSIVE if s in panels["close"].columns]
    print(f"defensive pool ({len(defensive_pool)}): {defensive_pool}")
    def_returns = build_defensive_returns(panels["close"], defensive_pool)
    print(f"defensive returns shape: {def_returns.shape}")

    # Inception summary for defensives
    inception = {s: panels["close"][s].first_valid_index() for s in defensive_pool}
    print("defensive inception dates:")
    for s, dt in inception.items():
        print(f"  {s}: {dt.date() if dt else 'None'}")

    # Reuse the R23 regime gate (off={1,3}, full={2})
    off_set = {1, 3}; full_set = {2}
    ef = _equity_frac(regime_panel, off_set, full_set, "regime_state_2")
    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)

    rows = []
    all_symbols = list(panels["close"].columns)

    # ========= ROUND 25: per-regime sharpe-min-vol & sortino =========
    print("\n=== R25: expanded pool, sharpe-min-vol per regime ===")
    for metric in ["sharpe", "sharpe_min_vol", "sortino", "annret"]:
        m = per_regime_best(regime_panel["regime_state_2"], def_returns, metric=metric)
        print(f"  metric={metric:18s}  mapping={m}")
        def_w = routed_defensive_weights(regime_panel["regime_state_2"], m, all_symbols)
        w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        sh = res.metrics["sharpe"]
        rows.append(to_row(25, f"per-regime {metric}", p,
                            {"metric": metric, "mapping": m}, res.metrics))
        print(f"    Sharpe={sh:.3f}  Ret={res.metrics['ann_ret']*100:5.2f}%  DD={res.metrics['max_dd']*100:6.2f}%")

    # ========= ROUND 26: macro IF-THEN rule router =========
    print("\n=== R26: macro IF-THEN rule router ===")
    daily_def = macro_rule_router(regime_panel, defensive_pool=defensive_pool)
    daily_def_present = daily_def.dropna()
    print(f"  rule-based daily defensive distribution:")
    print(f"  {daily_def.value_counts().to_dict()}")
    def_w = routed_defensive_weights(regime_panel["regime_state_2"], daily_def, all_symbols)
    w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
    rows.append(to_row(26, "macro_rule_router", p, {"router": "macro_rule"}, res.metrics))
    print(f"  macro_rule  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%")

    # ========= ROUND 27: per (regime × CPI bucket) =========
    print("\n=== R27: per (regime × CPI bucket) ===")
    cpi = regime_panel["cpi_yoy"]
    cpi_state = pd.cut(cpi, [-np.inf, 1.0, 3.0, np.inf],
                       labels=["low", "mid", "high"]).astype(str)
    print(f"  CPI bucket distribution: {cpi_state.value_counts().to_dict()}")
    for metric in ["sharpe_min_vol", "annret", "sortino"]:
        m_combo = per_regime_per_macro_best(regime_panel["regime_state_2"],
                                              cpi_state, def_returns, metric=metric)
        print(f"  metric={metric:18s}  combo size={len(m_combo)}")
        # Print mapping
        for (r, ms), sym in sorted(m_combo.items()):
            print(f"    regime={r} cpi={ms:5s} -> {sym}")
        def_w = routed_defensive_weights(regime_panel["regime_state_2"], m_combo,
                                          all_symbols, macro_state=cpi_state)
        w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        rows.append(to_row(27, f"reg×cpi {metric}", p,
                            {"metric": metric, "mapping": m_combo}, res.metrics))
        print(f"    Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:5.2f}%  DD={res.metrics['max_dd']*100:6.2f}%")

    # ========= ROUND 28: per (regime × PMI bucket) =========
    print("\n=== R28: per (regime × PMI bucket) ===")
    pmi = regime_panel["pmi"]
    pmi_state = pd.cut(pmi, [-np.inf, 49, 51, np.inf],
                       labels=["contract", "neutral", "expand"]).astype(str)
    print(f"  PMI bucket distribution: {pmi_state.value_counts().to_dict()}")
    for metric in ["sharpe_min_vol", "annret"]:
        m_combo = per_regime_per_macro_best(regime_panel["regime_state_2"],
                                              pmi_state, def_returns, metric=metric)
        for (r, ms), sym in sorted(m_combo.items()):
            print(f"    regime={r} pmi={ms:8s} -> {sym}")
        def_w = routed_defensive_weights(regime_panel["regime_state_2"], m_combo,
                                          all_symbols, macro_state=pmi_state)
        w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        rows.append(to_row(28, f"reg×pmi {metric}", p,
                            {"metric": metric, "mapping": m_combo}, res.metrics))
        print(f"    {metric:18s}  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:5.2f}%")

    # ========= ROUND 29: param search around current best =========
    df_so_far = pd.DataFrame(rows)
    best_row = df_so_far.sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"\n=== R29: param refine (best so far Sharpe={best_row['sharpe_net']:.3f} from R{int(best_row['round'])}) ===")
    # Reproduce the best defensive routing
    best_round_29 = int(best_row["round"])
    best_def_w = None
    if best_round_29 == 25:
        m = eval(best_row["mapping"])  # noqa: S307
        best_def_w = routed_defensive_weights(regime_panel["regime_state_2"], m, all_symbols)
    elif best_round_29 == 26:
        best_def_w = routed_defensive_weights(regime_panel["regime_state_2"],
                                                macro_rule_router(regime_panel, defensive_pool=defensive_pool),
                                                all_symbols)
    elif best_round_29 == 27:
        m = eval(best_row["mapping"])  # noqa: S307
        best_def_w = routed_defensive_weights(regime_panel["regime_state_2"], m,
                                                all_symbols, macro_state=cpi_state)
    elif best_round_29 == 28:
        m = eval(best_row["mapping"])  # noqa: S307
        best_def_w = routed_defensive_weights(regime_panel["regime_state_2"], m,
                                                all_symbols, macro_state=pmi_state)
    else:
        # fallback to single-pick R25 sharpe-min-vol mapping
        m = per_regime_best(regime_panel["regime_state_2"], def_returns, metric="sharpe_min_vol")
        best_def_w = routed_defensive_weights(regime_panel["regime_state_2"], m, all_symbols)

    # Param grid over (top_k, w_rsrs, mom_L, rebal_threshold)
    for k in [3, 5, 7]:
        for wr in [0.20, 0.30, 0.40, 0.50]:
            for mL in [120, 180, 252]:
                for rb in [0.0, 0.20, 0.40, 0.60]:
                    pp = dict(p); pp["top_k"]=k; pp["w_rsrs"]=wr; pp["mom_L"]=mL; pp["rebal_threshold"]=rb
                    rsrs2, score2, elig2 = _build_signals(panels, pp)
                    topk2 = _topk_equal_weight(score2, elig2, k)
                    w = assemble(topk2, best_def_w, ef, rb)
                    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
                    rows.append(to_row(29, f"refine k={k} wr={wr} L={mL} rb={rb}",
                                        pp, {"defensive_round": best_round_29}, res.metrics))

    # ========= ROUND 30: Final stack (best of R25-R29 with refined params + small macro tilt) =========
    print("\n=== R30: final stack ===")
    df_now = pd.DataFrame(rows)
    win = df_now.sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"  best so far: Sharpe={win['sharpe_net']:.3f}  round={int(win['round'])}  label={win['label']}")
    # Try a tiny grid of theta_off/theta_on around the regime gate
    for off_alt, full_alt in [({1, 3}, {2}), ({0, 1, 3}, {2}), ({1, 3}, {2, 0})]:
        ef_alt = _equity_frac(regime_panel, off_alt, full_alt, "regime_state_2")
        # use winner's params
        pp = expand_param({k: float(win[k]) if k not in ("rsrs_N","rsrs_M","mom_L","top_k") else int(win[k])
                            for k in ["rsrs_N","rsrs_M","mom_L","lambda_s","lambda_k",
                                       "w_rsrs","top_k","theta_off","theta_on","rebal_threshold"]
                            if k in win.index and not pd.isna(win[k])})
        pp["rsrs_form"] = "rsrs_skew"
        rsrs2, score2, elig2 = _build_signals(panels, pp)
        topk2 = _topk_equal_weight(score2, elig2, pp["top_k"])
        w = assemble(topk2, best_def_w, ef_alt, pp["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        rows.append(to_row(30, f"gate off={sorted(off_alt)} full={sorted(full_alt)}",
                            pp, {"off": str(sorted(off_alt)), "full": str(sorted(full_alt))},
                            res.metrics))
        print(f"  off={sorted(off_alt)} full={sorted(full_alt)}  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%")

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "all_candidates_v5.csv", index=False)

    winner = df.sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"\n=== R25-R30 overall best: round={int(winner['round'])} Sharpe={winner['sharpe_net']:.3f} ===")
    print(f"  label: {winner['label']}")
    print(f"  ann_ret={winner['ann_ret']*100:.2f}%  DD={winner['max_dd']*100:.2f}%  Calmar={winner['calmar']:.2f}  Turn={winner['ann_turnover']:.1f}x")

    R23_best = 1.170
    if winner["sharpe_net"] > R23_best:
        print(f"\n*** IMPROVED Sharpe {R23_best:.3f} -> {winner['sharpe_net']:.3f} ***")
    else:
        print(f"\n(no improvement vs R23 best {R23_best:.3f})")

    # Print top 10
    print("\nTop 10 across R25-R30:")
    print(df.sort_values("sharpe_net", ascending=False).head(10)[
        ["round","label","sharpe_net","ann_ret","ann_vol","max_dd","calmar","ann_turnover"]
    ].to_string(index=False))

    print("\nPer-round R25-R30 distribution:")
    print(df.groupby("round")["sharpe_net"].describe().round(3).to_string())
    print(f"\nWall-clock: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
