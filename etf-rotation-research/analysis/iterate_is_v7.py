"""V7: gold-conditioning overlay on top of R30 (regime × CN_CPI) routing.

User insight: 黄金 strongly correlates with US CPI and USD strength.
Strategy: keep R30's routing (which already picks gold for some cells)
          but apply a gold-conditioning overlay using US real rate + DXY:

  - When R30 picks gold AND US real rate > +1% AND DXY strong → fall back to second-best
  - When R30 doesn't pick gold AND US real rate < 0 AND DXY weak (60d mom < -2%)
    → switch to gold

R37: simple gold conditioning (binary triggers)
R38: continuous gold-tilt weight blending two best defensives
R39: param refine
R40: final gate exploration
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
GOLD = "518880"
GOLD_FALLBACK = "511260"  # 国开 — second-best defensive when gold conditions unfavorable


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


def gold_conditioned_router(base_mapping_series: pd.Series,
                              regime_panel: pd.DataFrame,
                              real_rate_pos_thresh: float = 1.0,
                              real_rate_neg_thresh: float = 0.0,
                              dxy_mom_thresh: float = -0.02,
                              dxy_strong_required: bool = True,
                              fallback_when_gold_bad: str = GOLD_FALLBACK,
                              ) -> pd.Series:
    """Apply gold conditioning overlay on top of an existing per-day mapping.

    base_mapping_series : daily Series of defensive symbol (from R30 routing)
    Returns a new daily Series of defensive symbol with surgical gold edits.
    """
    out = base_mapping_series.copy()
    us_real = regime_panel.get("us_real_rate")
    dxy_mom = regime_panel.get("dxy_mom_60")
    dxy_strong = regime_panel.get("dxy_strong", pd.Series(0, index=regime_panel.index)).fillna(0).astype(int)

    if us_real is None or dxy_mom is None:
        return out

    # Gold-disfavoring: real rate > +1% AND DXY strong
    bad_for_gold = (us_real > real_rate_pos_thresh) & (dxy_strong == 1)
    # Gold-favoring: real rate < 0 AND DXY momentum negative
    good_for_gold = (us_real < real_rate_neg_thresh) & (dxy_mom < dxy_mom_thresh)

    # Switch out of gold when conditions bad
    is_gold = out == GOLD
    out[is_gold & bad_for_gold] = fallback_when_gold_bad
    # Switch into gold when conditions strongly favorable AND not already cash
    # (don't take cash days away — those are deliberately defensive)
    not_gold = out != GOLD
    not_cash = out != "511880"
    out[not_gold & not_cash & good_for_gold] = GOLD
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
    macro = fetch_all_macro()
    bench = panels["close"][BENCHMARK_SYMBOL]
    regime_panel = build_regime_panel(bench, macro=macro, ma_window=200, vol_window=60)

    p = json.loads((OUT / "best_params_is.json").read_text())
    p = {k: v for k, v in p.items() if not str(k).startswith(("v3_", "v4_", "v5_"))}
    p = expand_param(p)

    rsrs, score, elig = _build_signals(panels, p)
    base_topk = _topk_equal_weight(score, elig, p["top_k"])

    defensive_pool = [s for s in EXPANDED_DEFENSIVE if s in panels["close"].columns]
    def_returns = build_defensive_returns(panels["close"], defensive_pool)

    # R30 winner gate + (regime × CN CPI) base routing
    off_set = {0, 1, 3}; full_set = {2}
    ef = _equity_frac(regime_panel, off_set, full_set, "regime_state_2")
    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)

    cn_cpi_state = pd.cut(regime_panel["cpi_yoy"], [-np.inf, 1.0, 3.0, np.inf],
                            labels=["low", "mid", "high"]).astype(str)
    base_map = per_regime_per_macro_best(regime_panel["regime_state_2"], cn_cpi_state,
                                            def_returns, metric="sharpe_min_vol")

    # Build per-day base defensive choice from R30 mapping
    def base_daily_defensive():
        out = pd.Series("511880", index=regime_panel.index)
        for dt in regime_panel.index:
            r = regime_panel.at[dt, "regime_state_2"]
            ms = cn_cpi_state.at[dt]
            if pd.isna(r):
                continue
            r = int(r)
            sym = base_map.get((r, str(ms)))
            if sym:
                out.at[dt] = sym
        return out

    daily_base = base_daily_defensive()
    print(f"R30 base daily defensive distribution:\n{daily_base.value_counts().to_dict()}")

    rows = []
    all_symbols = list(panels["close"].columns)

    # Sanity: reproduce R30 winner
    def_w_base = pd.DataFrame(0.0, index=daily_base.index, columns=all_symbols)
    for dt, sym in daily_base.items():
        if sym in def_w_base.columns:
            def_w_base.at[dt, sym] = 1.0
    w_base = assemble(base_topk, def_w_base, ef, p["rebal_threshold"])
    res_base = run_backtest(w_base, panels["close"], panels["open"], panels["amount"], cost_cfg)
    print(f"R30 reproduction: Sharpe={res_base.metrics['sharpe']:.3f} (target 1.457)")

    # ========= R37: gold-conditioning overlay =========
    print("\n=== R37: gold-conditioning overlay ===")
    grids = [
        # (rr_pos, rr_neg, dxy_mom, fallback)
        (1.0, 0.0, -0.02, GOLD_FALLBACK),
        (0.5, -0.5, -0.02, GOLD_FALLBACK),
        (1.5, -1.0, -0.05, GOLD_FALLBACK),
        (1.0, 0.0, -0.02, "511010"),     # fallback to 国债
        (1.0, 0.0, -0.02, "515080"),     # fallback to 红利低波
        (2.0, -2.0, -0.05, GOLD_FALLBACK),  # very strict
    ]
    best_r37 = (-1e9, None, None)
    for rr_pos, rr_neg, dmom, fb in grids:
        daily_cond = gold_conditioned_router(daily_base, regime_panel,
                                                real_rate_pos_thresh=rr_pos,
                                                real_rate_neg_thresh=rr_neg,
                                                dxy_mom_thresh=dmom,
                                                fallback_when_gold_bad=fb)
        def_w = pd.DataFrame(0.0, index=daily_cond.index, columns=all_symbols)
        for dt, sym in daily_cond.items():
            if sym in def_w.columns:
                def_w.at[dt, sym] = 1.0
        w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        sh = res.metrics["sharpe"]
        # Show how many days changed
        n_changed = (daily_cond != daily_base).sum()
        gold_added = ((daily_cond == GOLD) & (daily_base != GOLD)).sum()
        gold_removed = ((daily_cond != GOLD) & (daily_base == GOLD)).sum()
        rows.append(to_row(37,
                            f"gold_cond rr_pos={rr_pos} rr_neg={rr_neg} dxy={dmom} fb={fb}",
                            p, {"rr_pos": rr_pos, "rr_neg": rr_neg, "dxy_mom": dmom,
                                 "fallback": fb, "n_changed": int(n_changed),
                                 "gold_added": int(gold_added), "gold_removed": int(gold_removed)},
                            res.metrics))
        print(f"  rr_pos={rr_pos:4.1f} rr_neg={rr_neg:4.1f} dxy_mom<{dmom:.2f} fb={fb}  "
              f"gold +{gold_added}/-{gold_removed}  Sharpe={sh:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%")
        if sh > best_r37[0]:
            best_r37 = (sh, daily_cond, (rr_pos, rr_neg, dmom, fb))

    # ========= R38: gold-favoring continuous tilt (blend gold and base) =========
    print("\n=== R38: continuous gold tilt (50/50 blend on favorable days) ===")
    us_real = regime_panel["us_real_rate"]
    dxy_mom = regime_panel["dxy_mom_60"]
    # gold_bias score: high when US real rate low AND DXY weak
    gold_bias = (-us_real.fillna(0)) * 0.3 + (-dxy_mom.fillna(0)) * 5.0
    gold_bias_z = (gold_bias - gold_bias.rolling(252, min_periods=60).mean()) / gold_bias.rolling(252, min_periods=60).std()

    # Blend: 50% gold + 50% base when bias is in top quintile
    for q in [0.6, 0.7, 0.8]:
        for blend in [0.3, 0.5, 0.7, 1.0]:
            daily_blend_def = daily_base.copy()
            thr = gold_bias_z.rolling(504, min_periods=120).quantile(q)
            favor_gold = gold_bias_z > thr
            def_w = pd.DataFrame(0.0, index=daily_base.index, columns=all_symbols)
            for dt, sym in daily_base.items():
                if pd.isna(favor_gold.get(dt, False)):
                    if sym in def_w.columns:
                        def_w.at[dt, sym] = 1.0
                elif favor_gold.at[dt]:
                    # blend
                    if sym in def_w.columns:
                        def_w.at[dt, sym] = 1 - blend
                    if GOLD in def_w.columns:
                        def_w.at[dt, GOLD] = def_w.at[dt, GOLD] + blend
                else:
                    if sym in def_w.columns:
                        def_w.at[dt, sym] = 1.0
            w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
            res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
            rows.append(to_row(38, f"tilt q={q} blend={blend}", p,
                                {"q": q, "blend": blend}, res.metrics))
            print(f"  q={q} blend={blend}  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%")

    # ========= R39: param refine on best of R37/R38 =========
    df_so_far = pd.DataFrame(rows)
    win_so_far = df_so_far.sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"\n=== R39: param refine (best so far Sharpe={win_so_far['sharpe_net']:.3f} R{int(win_so_far['round'])}) ===")
    if int(win_so_far["round"]) == 37:
        # rebuild best_def_w from best R37 settings
        rr_pos, rr_neg, dmom, fb = best_r37[2]
        daily_best = gold_conditioned_router(daily_base, regime_panel,
                                                real_rate_pos_thresh=rr_pos,
                                                real_rate_neg_thresh=rr_neg,
                                                dxy_mom_thresh=dmom,
                                                fallback_when_gold_bad=fb)
        best_def_w = pd.DataFrame(0.0, index=daily_best.index, columns=all_symbols)
        for dt, sym in daily_best.items():
            if sym in best_def_w.columns:
                best_def_w.at[dt, sym] = 1.0
    else:
        best_def_w = def_w_base  # fall back to R30 base

    for k in [3, 5, 7]:
        for wr in [0.20, 0.30, 0.40]:
            for mL in [120, 180, 252]:
                for rb in [0.0, 0.20, 0.40, 0.60]:
                    pp = dict(p); pp["top_k"]=k; pp["w_rsrs"]=wr; pp["mom_L"]=mL; pp["rebal_threshold"]=rb
                    rsrs2, score2, elig2 = _build_signals(panels, pp)
                    topk2 = _topk_equal_weight(score2, elig2, k)
                    w = assemble(topk2, best_def_w, ef, rb)
                    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
                    rows.append(to_row(39, f"refine k={k} wr={wr} L={mL} rb={rb}",
                                        pp, {}, res.metrics))

    # ========= R40: final gate exploration =========
    df_now = pd.DataFrame(rows)
    win = df_now.sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"\n=== R40: final gate (best so far Sharpe={win['sharpe_net']:.3f}) ===")
    for off_alt, full_alt in [({1, 3}, {2}), ({0, 1, 3}, {2}), ({1, 3}, {2, 0}), ({0, 1, 3}, {2, 3})]:
        ef_alt = _equity_frac(regime_panel, off_alt, full_alt, "regime_state_2")
        pp = expand_param({k: float(win[k]) if k not in ("rsrs_N","rsrs_M","mom_L","top_k") else int(win[k])
                            for k in ["rsrs_N","rsrs_M","mom_L","lambda_s","lambda_k",
                                        "w_rsrs","top_k","theta_off","theta_on","rebal_threshold"]
                            if k in win.index and not pd.isna(win[k])})
        pp["rsrs_form"] = "rsrs_skew"
        rsrs2, score2, elig2 = _build_signals(panels, pp)
        topk2 = _topk_equal_weight(score2, elig2, pp["top_k"])
        w = assemble(topk2, best_def_w, ef_alt, pp["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        rows.append(to_row(40, f"gate off={sorted(off_alt)} full={sorted(full_alt)}",
                            pp, {"off": str(sorted(off_alt)), "full": str(sorted(full_alt))},
                            res.metrics))
        print(f"  off={sorted(off_alt)} full={sorted(full_alt)}  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%")

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "all_candidates_v7.csv", index=False)

    winner = df.sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"\n=== R37-R40 overall best: round={int(winner['round'])} Sharpe={winner['sharpe_net']:.3f} ===")
    print(f"  label: {winner['label']}")
    print(f"  ann_ret={winner['ann_ret']*100:.2f}%  DD={winner['max_dd']*100:.2f}%  Calmar={winner['calmar']:.2f}  Turn={winner['ann_turnover']:.1f}x")

    R30_best = 1.457
    if winner["sharpe_net"] > R30_best:
        print(f"\n*** IMPROVED Sharpe {R30_best:.3f} -> {winner['sharpe_net']:.3f} ***")
    else:
        print(f"\n(no improvement vs R30 best {R30_best:.3f})")

    print("\nTop 10 across R37-R40:")
    print(df.sort_values("sharpe_net", ascending=False).head(10)[
        ["round","label","sharpe_net","ann_ret","ann_vol","max_dd","calmar","ann_turnover"]
    ].to_string(index=False))

    print("\nPer-round R37-R40 distribution:")
    print(df.groupby("round")["sharpe_net"].describe().round(3).to_string())
    print(f"\nWall-clock: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
