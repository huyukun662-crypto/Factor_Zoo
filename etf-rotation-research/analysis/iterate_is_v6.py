"""V6 continuation: R31-R36 — gold-aware routing using US CPI + DXY + USD/CNY.

R31 (regime × DXY trend) defensive routing
R32 (regime × US real rate sign) — gold favored when US real rate < 0
R33 (regime × CN_CPI × DXY) 27-cell  — combined CN/US macro
R34 Hand-crafted gold-aware rule router
R35 Param search around best R31-R34
R36 Final stack

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


def gold_aware_rule_router(regime_panel: pd.DataFrame, defensive_pool: list[str]
                             ) -> pd.Series:
    """Hand-crafted rule using both CN and US macro:

    Priority:
      1. US real rate < 0 OR DXY trending down (60d) -> 518880 黄金
      2. CPI(CN) >= 3.0 AND PMI < 50 -> 518880 黄金 (inflation+slowdown)
      3. CPI(CN) >= 3.0 AND PMI >= 50 -> 515220 煤炭 (inflation+expand)
      4. CPI(CN) < 1.0 AND PMI < 50 -> 511010 国债 (deflation+recession)
      5. CPI(CN) < 1.0 AND PMI >= 50 -> 515080 红利低波 (low-infl+growth)
      6. mid CPI + DXY strong -> 511010 国债 (USD strength = CNY weakness; bonds in CNY)
      7. mid CPI + PMI >= 52 -> 515080 红利低波
      8. default -> 511880 货币
    """
    out = pd.Series("511880", index=regime_panel.index)
    cpi = regime_panel.get("cpi_yoy")
    pmi = regime_panel.get("pmi")
    us_real = regime_panel.get("us_real_rate")
    dxy_mom = regime_panel.get("dxy_mom_60")
    dxy_strong = regime_panel.get("dxy_strong", pd.Series(0, index=regime_panel.index)).fillna(0).astype(int)

    high_inflation = cpi >= 3.0
    low_inflation = cpi < 1.0
    pmi_expand = pmi >= 50.0
    pmi_strong = pmi >= 52.0

    # 6: mid CPI + DXY strong -> 国债
    out[(~high_inflation) & (~low_inflation) & (dxy_strong == 1)] = "511010"
    # 7: mid CPI + PMI >= 52 -> 红利低波
    out[(~high_inflation) & (~low_inflation) & (pmi_strong) & (dxy_strong == 0)] = "515080"
    # 5: low CPI + PMI expand -> 红利低波
    out[(low_inflation) & (pmi_expand)] = "515080"
    # 4: low CPI + PMI contract -> 国债
    out[(low_inflation) & (~pmi_expand)] = "511010"
    # 3: high CPI + PMI expand -> 煤炭
    out[(high_inflation) & (pmi_expand)] = "515220"
    # 2: high CPI + PMI contract -> 黄金
    out[(high_inflation) & (~pmi_expand)] = "518880"
    # 1: gold-favorable conditions OVERRIDE all (highest priority)
    gold_cond = pd.Series(False, index=regime_panel.index)
    if us_real is not None:
        gold_cond = gold_cond | (us_real < 0)
    if dxy_mom is not None:
        gold_cond = gold_cond | (dxy_mom < -0.02)
    out[gold_cond] = "518880"

    out = out.where(out.isin(defensive_pool), other="511880")
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
    print(f"regime_panel cols: {list(regime_panel.columns)}")
    print(f"  us_cpi range: {regime_panel['us_cpi_yoy'].min():.2f} .. {regime_panel['us_cpi_yoy'].max():.2f}")
    print(f"  us_real_rate range: {regime_panel['us_real_rate'].min():.2f} .. {regime_panel['us_real_rate'].max():.2f}")
    print(f"  dxy range: {regime_panel['dxy'].min():.1f} .. {regime_panel['dxy'].max():.1f}")
    print(f"  dxy_strong dist: {regime_panel['dxy_strong'].value_counts(dropna=False).to_dict()}")

    p = json.loads((OUT / "best_params_is.json").read_text())
    p = {k: v for k, v in p.items() if not str(k).startswith(("v3_", "v4_", "v5_"))}
    p = expand_param(p)

    # Build base signals
    rsrs, score, elig = _build_signals(panels, p)
    base_topk = _topk_equal_weight(score, elig, p["top_k"])

    defensive_pool = [s for s in EXPANDED_DEFENSIVE if s in panels["close"].columns]
    def_returns = build_defensive_returns(panels["close"], defensive_pool)

    off_set = {0, 1, 3}; full_set = {2}  # R30 winner gate
    ef = _equity_frac(regime_panel, off_set, full_set, "regime_state_2")
    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)

    rows = []
    all_symbols = list(panels["close"].columns)

    # ========= R31: (regime × DXY trend) defensive =========
    print("\n=== R31: (regime × DXY trend) ===")
    dxy_state = regime_panel["dxy_strong"].fillna(0).astype(int).map({0: "weak", 1: "strong"})
    print(f"  DXY state dist: {dxy_state.value_counts().to_dict()}")
    for metric in ["sharpe_min_vol", "annret"]:
        m = per_regime_per_macro_best(regime_panel["regime_state_2"], dxy_state,
                                        def_returns, metric=metric)
        for (r, ms), sym in sorted(m.items()):
            print(f"    regime={r} dxy={ms:6s} -> {sym}")
        def_w = routed_defensive_weights(regime_panel["regime_state_2"], m, all_symbols,
                                            macro_state=dxy_state)
        w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        rows.append(to_row(31, f"reg×dxy {metric}", p,
                            {"metric": metric, "mapping": m}, res.metrics))
        print(f"    {metric:18s}  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%")

    # ========= R32: (regime × US real rate sign) =========
    print("\n=== R32: (regime × US real rate sign) ===")
    us_real = regime_panel["us_real_rate"]
    us_real_state = pd.Series("neg", index=us_real.index)
    us_real_state[us_real >= 0] = "pos"
    us_real_state[us_real.isna()] = "unk"
    print(f"  US real rate state dist: {us_real_state.value_counts().to_dict()}")
    for metric in ["sharpe_min_vol", "annret"]:
        m = per_regime_per_macro_best(regime_panel["regime_state_2"], us_real_state,
                                        def_returns, metric=metric)
        for (r, ms), sym in sorted(m.items()):
            print(f"    regime={r} us_real={ms:5s} -> {sym}")
        def_w = routed_defensive_weights(regime_panel["regime_state_2"], m, all_symbols,
                                            macro_state=us_real_state)
        w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
        rows.append(to_row(32, f"reg×us_real {metric}", p,
                            {"metric": metric, "mapping": m}, res.metrics))
        print(f"    {metric:18s}  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%")

    # ========= R33: (regime × CN_CPI × DXY) — fine-grained 3-axis =========
    print("\n=== R33: (regime × CN_CPI × DXY) — combined 3-axis ===")
    cn_cpi = regime_panel["cpi_yoy"]
    cn_cpi_state = pd.cut(cn_cpi, [-np.inf, 1.0, 3.0, np.inf],
                           labels=["low", "mid", "high"]).astype(str)
    combined = cn_cpi_state.astype(str) + "_" + dxy_state.astype(str)
    print(f"  combined state dist (top 6): {combined.value_counts().head(6).to_dict()}")
    m = per_regime_per_macro_best(regime_panel["regime_state_2"], combined,
                                    def_returns, metric="sharpe_min_vol")
    for (r, ms), sym in sorted(m.items()):
        print(f"    regime={r} cpi×dxy={ms:13s} -> {sym}")
    def_w = routed_defensive_weights(regime_panel["regime_state_2"], m, all_symbols,
                                        macro_state=combined)
    w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
    rows.append(to_row(33, "reg×cpi×dxy sharpe_min_vol", p, {"mapping": m}, res.metrics))
    print(f"  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%")

    # ========= R34: hand-crafted gold-aware rule router =========
    print("\n=== R34: hand-crafted gold-aware rule router ===")
    daily_def = gold_aware_rule_router(regime_panel, defensive_pool=defensive_pool)
    print(f"  rule-based daily defensive distribution: {daily_def.value_counts().to_dict()}")
    def_w = routed_defensive_weights(regime_panel["regime_state_2"], daily_def, all_symbols)
    w = assemble(base_topk, def_w, ef, p["rebal_threshold"])
    res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
    rows.append(to_row(34, "gold_aware_rule", p, {}, res.metrics))
    print(f"  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%")

    # ========= R35: param refine around best of R31-R34 =========
    df_so_far = pd.DataFrame(rows)
    win_so_far = df_so_far.sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"\n=== R35: param refine (best so far Sharpe={win_so_far['sharpe_net']:.3f} R{int(win_so_far['round'])}) ===")
    bw_round = int(win_so_far["round"])
    if bw_round == 31:
        m = eval(win_so_far["mapping"])  # noqa: S307
        best_def_w = routed_defensive_weights(regime_panel["regime_state_2"], m, all_symbols, macro_state=dxy_state)
    elif bw_round == 32:
        m = eval(win_so_far["mapping"])  # noqa: S307
        best_def_w = routed_defensive_weights(regime_panel["regime_state_2"], m, all_symbols, macro_state=us_real_state)
    elif bw_round == 33:
        m = eval(win_so_far["mapping"])  # noqa: S307
        best_def_w = routed_defensive_weights(regime_panel["regime_state_2"], m, all_symbols, macro_state=combined)
    elif bw_round == 34:
        best_def_w = routed_defensive_weights(regime_panel["regime_state_2"],
                                                gold_aware_rule_router(regime_panel, defensive_pool=defensive_pool),
                                                all_symbols)
    else:
        best_def_w = None

    if best_def_w is not None:
        for k in [3, 5, 7]:
            for wr in [0.20, 0.30, 0.40]:
                for mL in [120, 180, 252]:
                    for rb in [0.0, 0.20, 0.40, 0.60]:
                        pp = dict(p); pp["top_k"]=k; pp["w_rsrs"]=wr; pp["mom_L"]=mL; pp["rebal_threshold"]=rb
                        rsrs2, score2, elig2 = _build_signals(panels, pp)
                        topk2 = _topk_equal_weight(score2, elig2, k)
                        w = assemble(topk2, best_def_w, ef, rb)
                        res = run_backtest(w, panels["close"], panels["open"], panels["amount"], cost_cfg)
                        rows.append(to_row(35, f"refine k={k} wr={wr} L={mL} rb={rb}",
                                            pp, {"defensive_round": bw_round}, res.metrics))

    # ========= R36: final gate exploration =========
    df_now = pd.DataFrame(rows)
    win = df_now.sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"\n=== R36: final gate (best so far Sharpe={win['sharpe_net']:.3f}) ===")
    if best_def_w is not None:
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
            rows.append(to_row(36, f"gate off={sorted(off_alt)} full={sorted(full_alt)}",
                                pp, {"off": str(sorted(off_alt)), "full": str(sorted(full_alt))},
                                res.metrics))
            print(f"  off={sorted(off_alt)} full={sorted(full_alt)}  Sharpe={res.metrics['sharpe']:.3f}  Ret={res.metrics['ann_ret']*100:.2f}%  DD={res.metrics['max_dd']*100:.2f}%")

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "all_candidates_v6.csv", index=False)

    winner = df.sort_values("sharpe_net", ascending=False).iloc[0]
    print(f"\n=== R31-R36 overall best: round={int(winner['round'])} Sharpe={winner['sharpe_net']:.3f} ===")
    print(f"  label: {winner['label']}")
    print(f"  ann_ret={winner['ann_ret']*100:.2f}%  DD={winner['max_dd']*100:.2f}%  Calmar={winner['calmar']:.2f}  Turn={winner['ann_turnover']:.1f}x")

    R30_best = 1.457
    if winner["sharpe_net"] > R30_best:
        print(f"\n*** IMPROVED Sharpe {R30_best:.3f} -> {winner['sharpe_net']:.3f} ***")
    else:
        print(f"\n(no improvement vs R30 best {R30_best:.3f})")

    print("\nTop 10 across R31-R36:")
    print(df.sort_values("sharpe_net", ascending=False).head(10)[
        ["round","label","sharpe_net","ann_ret","ann_vol","max_dd","calmar","ann_turnover"]
    ].to_string(index=False))

    print("\nPer-round R31-R36 distribution:")
    print(df.groupby("round")["sharpe_net"].describe().round(3).to_string())
    print(f"\nWall-clock: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
