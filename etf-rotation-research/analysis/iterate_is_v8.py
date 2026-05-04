"""V8: R41-R44 — Double-pressure (USD strong + RMB weak) defensive override.

Findings from double_pressure_analysis.py:
  - 511260 国开债 dominates USD-strong/RMB-weak regimes (Sharpe 1.67-2.70)
  - 黄金 fails in strict double-pressure (Sharpe -0.40 to -3.55)

Strategy: keep R30 base routing, add double-pressure override:
  WHEN (dxy_mom_60 > X AND usdcny_mom_60 > Y) → force 511260 国开 (or pool)
  ELSE → use R30 (regime × CN_CPI) sharpe_min_vol mapping

R41 simple override → 511260 only
R42 override pool: blend 511260 + 货币 + 华宝油气
R43 + WFA test the override
R44 final stack with refined params

# [GUARDRAIL] All within IS_END=2023-12-31.
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


def _equity_frac(regime_panel, off_set, full_set):
    s = regime_panel["regime_state_2"]
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


def double_pressure_override(daily_base: pd.Series, regime_panel: pd.DataFrame,
                                dxy_thresh: float, rmb_thresh: float,
                                override_sym: str = "511260") -> pd.Series:
    """Force daily defensive to override_sym when (dxy_mom > X AND usdcny_mom > Y)."""
    out = daily_base.copy()
    dxy_mom = regime_panel.get("dxy_mom_60")
    rmb_mom = regime_panel.get("usdcny_mom_60")
    if dxy_mom is None or rmb_mom is None:
        return out
    pressure = (dxy_mom > dxy_thresh) & (rmb_mom > rmb_thresh)
    out[pressure.fillna(False)] = override_sym
    return out


def _daily_def_from_mapping(regime_labels, cpi_state, mapping, default="511880"):
    out = pd.Series(default, index=regime_labels.index)
    for dt in regime_labels.index:
        r = regime_labels.at[dt]
        if pd.isna(r):
            continue
        ms = cpi_state.at[dt] if dt in cpi_state.index else None
        sym = mapping.get((int(r), str(ms)))
        if sym is None:
            for k, v in mapping.items():
                if isinstance(k, tuple) and k[0] == int(r):
                    sym = v; break
        if sym:
            out.at[dt] = sym
    return out


def _def_w_from_daily(daily_def, all_symbols):
    out = pd.DataFrame(0.0, index=daily_def.index, columns=all_symbols)
    for dt, sym in daily_def.items():
        if sym in out.columns:
            out.at[dt, sym] = 1.0
    return out


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


def main():
    t0 = time.time()
    panels = load_is_panels()
    macro = fetch_all_macro()
    bench = panels["close"][BENCHMARK_SYMBOL]
    regime_panel = build_regime_panel(bench, macro=macro, ma_window=200, vol_window=60)

    p_r30 = expand_param({
        "rsrs_N": 30, "rsrs_M": 250, "mom_L": 180,
        "lambda_s": 0.2, "lambda_k": 0.0,
        "w_rsrs": 0.2, "top_k": 7,
        "theta_off": -0.7, "theta_on": 0.7,
        "rebal_threshold": 0.4,
    })
    p_r30["rsrs_form"] = "rsrs_skew"

    rsrs, score, elig = _build_signals(panels, p_r30)
    base_topk = _topk_equal_weight(score, elig, p_r30["top_k"])

    defensive_pool = [s for s in EXPANDED_DEFENSIVE if s in panels["close"].columns]
    def_returns = build_defensive_returns(panels["close"], defensive_pool)
    cn_cpi_state = pd.cut(regime_panel["cpi_yoy"], [-np.inf, 1.0, 3.0, np.inf],
                            labels=["low", "mid", "high"]).astype(str)

    # R30 base mapping (full IS sharpe_min_vol)
    base_map = per_regime_per_macro_best(regime_panel["regime_state_2"], cn_cpi_state,
                                            def_returns, metric="sharpe_min_vol")
    daily_base = _daily_def_from_mapping(regime_panel["regime_state_2"], cn_cpi_state, base_map)
    print(f"R30 base daily defensive: {daily_base.value_counts().to_dict()}")

    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)
    all_symbols = list(panels["close"].columns)
    off_set, full_set = {0, 1, 3}, {2}
    ef = _equity_frac(regime_panel, off_set, full_set)

    # Sanity: reproduce R30
    def_w_r30 = _def_w_from_daily(daily_base, all_symbols)
    w_r30 = assemble(base_topk, def_w_r30, ef, p_r30["rebal_threshold"])
    res_r30 = run_backtest(w_r30, panels["close"], panels["open"], panels["amount"], cost_cfg)
    print(f"R30 reproduction: Sharpe={res_r30.metrics['sharpe']:.3f} (target 1.457)")

    rows = []
    rows.append(to_row(0, "R30 baseline", p_r30, {"override": "none"}, res_r30.metrics))

    # ========= R41: simple override → 511260 国开 at various thresholds =========
    print("\n=== R41: double-pressure override → 511260 国开 ===")
    for dxy_t, rmb_t in [(0.0, 0.0), (0.01, 0.005), (0.02, 0.01), (0.04, 0.02), (0.06, 0.03)]:
        for sym in ["511260", "511880", "511010", "162411"]:
            daily_ovr = double_pressure_override(daily_base, regime_panel, dxy_t, rmb_t, sym)
            n_changed = int((daily_ovr != daily_base).sum())
            def_w = _def_w_from_daily(daily_ovr, all_symbols)
            w = assemble(base_topk, def_w, ef, p_r30["rebal_threshold"])
            res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
            rows.append(to_row(41, f"override→{sym} dxy>{dxy_t} rmb>{rmb_t}", p_r30,
                                {"override_sym": sym, "dxy_thresh": dxy_t, "rmb_thresh": rmb_t,
                                 "n_changed": n_changed}, res.metrics))
            print(f"  override→{sym}  dxy>{dxy_t:.2f} rmb>{rmb_t:.3f}  changed={n_changed:4d}d  "
                  f"Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:5.2f}%  "
                  f"DD={res.metrics['max_dd']*100:6.2f}%  Calmar={res.metrics['calmar']:.2f}")

    # ========= R42: override to dynamic basket (best-of-3 in pressure regime) =========
    print("\n=== R42: override → dynamic best-of-pool ===")
    # Use the IS-best per double-pressure subset
    pressure_pool_options = [
        ["511260"],
        ["511260", "511880"],
        ["511260", "162411"],
        ["511260", "511880", "162411"],  # bonds + cash + oil
    ]
    for dxy_t, rmb_t in [(0.02, 0.01), (0.04, 0.02)]:
        for pool in pressure_pool_options:
            daily_ovr = daily_base.copy()
            mask = (regime_panel["dxy_mom_60"] > dxy_t) & (regime_panel["usdcny_mom_60"] > rmb_t)
            mask = mask.fillna(False)
            # equal-weight pool on pressure days
            def_w = _def_w_from_daily(daily_ovr, all_symbols)
            # zero out original on pressure days, then put 1/n on each pool member
            for dt in regime_panel.index[mask]:
                # zero existing
                for sym in def_w.columns:
                    def_w.at[dt, sym] = 0.0
                eqw = 1.0 / len(pool)
                for s in pool:
                    if s in def_w.columns:
                        def_w.at[dt, s] = eqw
            w = assemble(base_topk, def_w, ef, p_r30["rebal_threshold"])
            res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
            n_changed = int(mask.sum())
            rows.append(to_row(42, f"pool {pool} dxy>{dxy_t} rmb>{rmb_t}", p_r30,
                                {"pool": str(pool), "dxy_thresh": dxy_t,
                                 "rmb_thresh": rmb_t, "n_changed": n_changed},
                                res.metrics))
            print(f"  pool={pool}  dxy>{dxy_t:.2f}  rmb>{rmb_t:.3f}  Sharpe={res.metrics['sharpe']:.3f}  "
                  f"Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%")

    # ========= R43: param refine around best of R41/R42 =========
    df_so_far = pd.DataFrame(rows)
    win = df_so_far[df_so_far["round"] > 0].sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"\n=== R43: param refine (best so far Sharpe={win['sharpe_net']:.3f} from R{int(win['round'])}) ===")

    # Reconstruct best override
    if int(win["round"]) == 41:
        ovr_sym = win["override_sym"]
        dxy_t = float(win["dxy_thresh"])
        rmb_t = float(win["rmb_thresh"])
        def_w_best = _def_w_from_daily(
            double_pressure_override(daily_base, regime_panel, dxy_t, rmb_t, ovr_sym),
            all_symbols,
        )
    else:
        # R42 winner — re-derive
        dxy_t = float(win["dxy_thresh"])
        rmb_t = float(win["rmb_thresh"])
        pool = eval(win["pool"])  # noqa: S307
        daily_ovr = daily_base.copy()
        mask = ((regime_panel["dxy_mom_60"] > dxy_t) &
                (regime_panel["usdcny_mom_60"] > rmb_t)).fillna(False)
        def_w_best = _def_w_from_daily(daily_ovr, all_symbols)
        for dt in regime_panel.index[mask]:
            for sym in def_w_best.columns:
                def_w_best.at[dt, sym] = 0.0
            eqw = 1.0 / len(pool)
            for s in pool:
                if s in def_w_best.columns:
                    def_w_best.at[dt, s] = eqw

    for k in [3, 5, 7]:
        for wr in [0.20, 0.30, 0.40]:
            for mL in [120, 180, 252]:
                for rb in [0.0, 0.20, 0.40]:
                    pp = dict(p_r30); pp["top_k"]=k; pp["w_rsrs"]=wr; pp["mom_L"]=mL; pp["rebal_threshold"]=rb
                    rsrs2, score2, elig2 = _build_signals(panels, pp)
                    topk2 = _topk_equal_weight(score2, elig2, k)
                    w = assemble(topk2, def_w_best, ef, rb)
                    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
                    rows.append(to_row(43, f"refine k={k} wr={wr} L={mL} rb={rb}",
                                        pp, {}, res.metrics))

    # ========= R44: final stack — best params + best override + gate exploration =========
    df_now = pd.DataFrame(rows)
    win = df_now[df_now["round"] > 0].sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"\n=== R44: final gate (best so far Sharpe={win['sharpe_net']:.3f}) ===")
    for off_alt, full_alt in [({1, 3}, {2}), ({0, 1, 3}, {2}), ({1, 3}, {2, 0})]:
        ef_alt = _equity_frac(regime_panel, off_alt, full_alt)
        pp = expand_param({k: float(win[k]) if k not in ("rsrs_N","rsrs_M","mom_L","top_k") else int(win[k])
                            for k in ["rsrs_N","rsrs_M","mom_L","lambda_s","lambda_k",
                                        "w_rsrs","top_k","theta_off","theta_on","rebal_threshold"]
                            if k in win.index and not pd.isna(win[k])})
        pp["rsrs_form"] = "rsrs_skew"
        rsrs2, score2, elig2 = _build_signals(panels, pp)
        topk2 = _topk_equal_weight(score2, elig2, pp["top_k"])
        w = assemble(topk2, def_w_best, ef_alt, pp["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        rows.append(to_row(44, f"gate off={sorted(off_alt)} full={sorted(full_alt)}",
                            pp, {"off": str(sorted(off_alt))}, res.metrics))
        print(f"  off={sorted(off_alt)} full={sorted(full_alt)}  Sharpe={res.metrics['sharpe']:.3f}  "
              f"Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%")

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "all_candidates_v8.csv", index=False)

    winner = df[df["round"] > 0].sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"\n=== R41-R44 overall best: round={int(winner['round'])} Sharpe={winner['sharpe_net']:.3f} ===")
    print(f"  label: {winner['label']}")
    print(f"  ann_ret={winner['ann_ret']*100:.2f}%  DD={winner['max_dd']*100:.2f}%  Calmar={winner['calmar']:.2f}  Turn={winner['ann_turnover']:.1f}x")

    R30_best = 1.457
    if winner["sharpe_net"] > R30_best:
        print(f"\n*** IMPROVED Sharpe {R30_best:.3f} -> {winner['sharpe_net']:.3f} ***")
    else:
        print(f"\n(no improvement vs R30 best {R30_best:.3f})")

    # Top 10
    print("\nTop 10:")
    print(df[df["round"] > 0].sort_values("sharpe_net", ascending=False).head(10)[
        ["round","label","sharpe_net","ann_ret","ann_vol","max_dd","calmar","ann_turnover"]
    ].to_string(index=False))

    # Per-year for the winner — re-run
    print(f"\nReproducing winner per-year...")
    if int(winner["round"]) in (41, 43, 44):
        # determine the override params
        win_params_only_p = {k: int(winner[k]) if k in ("rsrs_N","rsrs_M","mom_L","top_k") else float(winner[k])
                              for k in ["rsrs_N","rsrs_M","mom_L","lambda_s","lambda_k",
                                          "w_rsrs","top_k","theta_off","theta_on","rebal_threshold"]
                              if k in winner.index and not pd.isna(winner[k])}
        win_params = expand_param(win_params_only_p)
        win_params["rsrs_form"] = "rsrs_skew"
        rsrsf, scoref, eligf = _build_signals(panels, win_params)
        topkf = _topk_equal_weight(scoref, eligf, win_params["top_k"])
        # Use best override (from earlier R41/R42)
        if "override_sym" in winner.index and not pd.isna(winner.get("override_sym")):
            ovr_sym = winner["override_sym"]
            dxy_t = float(winner["dxy_thresh"])
            rmb_t = float(winner["rmb_thresh"])
            daily_w = double_pressure_override(daily_base, regime_panel, dxy_t, rmb_t, ovr_sym)
            def_w_winner = _def_w_from_daily(daily_w, all_symbols)
        else:
            # winner is R43/R44 inheriting from earlier
            def_w_winner = def_w_best
        # Use winner's gate
        if "off" in winner.index and not pd.isna(winner.get("off")):
            off_set_w = set(eval(winner["off"]))  # noqa: S307
        else:
            off_set_w = {0, 1, 3}
        ef_w = _equity_frac(regime_panel, off_set_w, {2})
        w_final = assemble(topkf, def_w_winner, ef_w, win_params["rebal_threshold"])
        res_final = run_backtest(w_final, panels["close"], panels["open"], panels["amount"], cost_cfg)
        py = per_year_metrics(res_final.pnl_net)
        py.to_csv(OUT / "v8_winner_per_year.csv")
        res_final.equity.to_csv(OUT / "v8_winner_equity.csv", header=["equity"])
        print(py.to_string())

    print(f"\nWall-clock: {time.time()-t0:.1f}s")
    print(f"\nPer-round R41-R44 distribution:")
    print(df[df["round"] > 0].groupby("round")["sharpe_net"].describe().round(3).to_string())


if __name__ == "__main__":
    main()
