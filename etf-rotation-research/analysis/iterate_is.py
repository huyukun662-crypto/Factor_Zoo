"""Six-round IS-only iteration driver.

Runs at least 6 iteration rounds, each maximizing IS Sharpe.
Writes report/outputs/iteration_log.md and report/outputs/iteration_results.csv.

# [GUARDRAIL] Imports is_search which enforces IS_END=2019-12-31. Will raise
# if any round tries to look past 2019-12-31. Do NOT modify until user OKs OOS.
"""
from __future__ import annotations

import json
import sys
import time
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from analysis.is_search import (  # noqa: E402
    DEFAULT_PARAM_SPACE,
    DEFAULT_PARAMS,
    evaluate_params,
    expand_param,
    grid_search,
    load_is_panels,
)
from strategy.signals import (  # noqa: E402
    composite_score, higher_moment_score, rsrs_panel,
    absolute_momentum_filter,
)
from strategy.portfolio import build_target_weights  # noqa: E402
from strategy.backtest import CostConfig, run_backtest, per_year_metrics  # noqa: E402
from strategy.universe import (  # noqa: E402
    ABS_MOM_BENCHMARK, BENCHMARK_SYMBOL, BOND_OR_MONEY_SET, DEFENSIVE_SYMBOLS,
)

OUT_DIR = REPO_ROOT / "report" / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_FP = OUT_DIR / "iteration_log.md"
CSV_FP = OUT_DIR / "iteration_results.csv"
BEST_PARAMS_FP = OUT_DIR / "best_params_is.json"


def _summarize(metrics: dict) -> str:
    return (f"Sharpe={metrics['sharpe']:.3f}  "
            f"Ret={metrics['ann_ret']*100:.2f}%  "
            f"Vol={metrics['ann_vol']*100:.2f}%  "
            f"DD={metrics['max_dd']*100:.2f}%  "
            f"Calmar={metrics['calmar']:.2f}  "
            f"Turn={metrics['ann_turnover']:.1f}x  "
            f"GrossSh={metrics.get('gross_sharpe', float('nan')):.3f}")


def _round_record(round_n: int, label: str, hypothesis: str, params: dict,
                   metrics: dict, change: str, next_idea: str) -> dict:
    return {
        "round": round_n,
        "label": label,
        "change": change,
        "hypothesis": hypothesis,
        "params": json.dumps(params, ensure_ascii=False),
        "ann_ret": metrics["ann_ret"],
        "ann_vol": metrics["ann_vol"],
        "sharpe_net": metrics["sharpe"],
        "sharpe_gross": metrics.get("gross_sharpe", float("nan")),
        "max_dd": metrics["max_dd"],
        "calmar": metrics["calmar"],
        "win_rate": metrics["win_rate"],
        "ann_turnover": metrics["ann_turnover"],
        "next_idea": next_idea,
    }


def _append_log(rounds: list[dict]) -> None:
    df = pd.DataFrame(rounds)
    df.to_csv(CSV_FP, index=False)

    lines = ["# Iteration Log — IS-only (2013-01-01 → 2019-12-31)", ""]
    lines.append("> 用户要求：在用户明确批准前不得触碰 OOS 与 Hold-out。每轮目标：最大化 IS 净 Sharpe，至少 6 轮。\n")
    lines.append("| R | 标签 | IS Sharpe | IS Ret | IS DD | Calmar | 换手 | 净/毛 Sharpe |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in rounds:
        lines.append(
            f"| {r['round']} | **{r['label']}** | "
            f"**{r['sharpe_net']:.3f}** | {r['ann_ret']*100:.2f}% | "
            f"{r['max_dd']*100:.2f}% | {r['calmar']:.2f} | "
            f"{r['ann_turnover']:.1f}x | "
            f"{r['sharpe_net']:.2f}/{r['sharpe_gross']:.2f} |"
        )
    lines.append("")
    for r in rounds:
        lines.append(f"## Round {r['round']} — {r['label']}")
        lines.append(f"- **改动**: {r['change']}")
        lines.append(f"- **假设**: {r['hypothesis']}")
        lines.append(f"- **参数**: `{r['params']}`")
        lines.append(f"- **指标**: 年化收益 {r['ann_ret']*100:.2f}% · 年化波动 {r['ann_vol']*100:.2f}% · "
                     f"净 Sharpe **{r['sharpe_net']:.3f}** · 毛 Sharpe {r['sharpe_gross']:.3f} · "
                     f"最大回撤 {r['max_dd']*100:.2f}% · Calmar {r['calmar']:.2f} · "
                     f"胜率 {r['win_rate']*100:.1f}% · 年化换手 {r['ann_turnover']:.1f}x")
        lines.append(f"- **下一轮想法**: {r['next_idea']}")
        lines.append("")
    LOG_FP.write_text("\n".join(lines), encoding="utf-8")


# ---------- Custom builders for refinement rounds ----------

def _equity_only_eligibility(close, mom_L, benchmark, exclude_buckets, universe_df):
    """Eligibility = absolute-mom filter AND bucket NOT in exclude_buckets."""
    elig_abs = absolute_momentum_filter(close, mom_L, benchmark)
    excl_syms = universe_df[universe_df["bucket"].isin(exclude_buckets)]["symbol"].tolist()
    elig_bucket = pd.DataFrame(True, index=elig_abs.index, columns=elig_abs.columns)
    for s in excl_syms:
        if s in elig_bucket.columns:
            elig_bucket[s] = False
    return elig_abs & elig_bucket


def _trend_filter_panel(close: pd.DataFrame, ma_window: int = 100) -> pd.DataFrame:
    """Per-ETF: True iff close > MA(ma_window). Adds an extra trend gate."""
    ma = close.rolling(ma_window, min_periods=max(20, ma_window // 4)).mean()
    return close > ma


def evaluate_with_extras(panels: dict, params: dict,
                          extras: dict | None = None) -> dict:
    """Variant evaluator that lets us inject extra filters/scores per round."""
    from analysis.is_search import expand_param  # local to avoid cycles
    params = expand_param(params)
    extras = extras or {}
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

    # extra: trend MA gate
    if extras.get("trend_ma_window"):
        elig = elig & _trend_filter_panel(close, extras["trend_ma_window"])

    # extra: exclude buckets via universe_df
    if extras.get("universe_df") is not None and extras.get("exclude_buckets"):
        univ = extras["universe_df"]
        excl_syms = univ[univ["bucket"].isin(extras["exclude_buckets"])]["symbol"].tolist()
        for s in excl_syms:
            if s in elig.columns:
                elig[s] = False

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
    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)
    res = run_backtest(weights, panels["close"], panels["open"], panels["amount"], cost_cfg)
    out = dict(params=dict(params), metrics=res.metrics)
    return out


def main():
    t0 = time.time()
    panels = load_is_panels()
    print(f"[setup] panels {panels['close'].index.min().date()} .. {panels['close'].index.max().date()} "
          f"shape={panels['close'].shape}")

    universe_df = pd.read_csv(REPO_ROOT / "report" / "outputs" / "universe.csv")

    rounds = []

    # ================================================================
    # ROUND 1 — Baseline (default params, no rebal throttle)
    # ================================================================
    print("\n=== R1: baseline ===")
    p1 = dict(DEFAULT_PARAMS)
    r1 = evaluate_params(p1, panels=panels)
    print(_summarize(r1["metrics"]))
    rounds.append(_round_record(
        1, "Baseline", "默认参数下 RSRS + 双动量 + 加阶矩组合可在 IS 跑出正 Sharpe",
        p1, r1["metrics"],
        change="基线，零迭代",
        next_idea=("毛 Sharpe ≫ 净 Sharpe，换手成本巨大；R2 引入 rebal_threshold "
                    "并做 LHS 200 组对全参数空间的初探"),
    ))
    _append_log(rounds)

    # ================================================================
    # ROUND 2 — LHS 200 random samples over full param space (incl rebal_threshold)
    # ================================================================
    print("\n=== R2: LHS 200 grid search ===")
    grid_df = grid_search(DEFAULT_PARAM_SPACE, n_samples=200, seed=20260503,
                          panels=panels, progress=False)
    print(grid_df.head(10).to_string())
    grid_df.to_csv(OUT_DIR / "round2_grid.csv", index=False)
    if grid_df.empty or grid_df["sharpe"].isna().all():
        raise RuntimeError("grid empty")
    best = grid_df.iloc[0].to_dict()
    # The grid_df has theta_off/theta_on already expanded; reconstruct param dict
    p2_raw = {k: best[k] for k in DEFAULT_PARAMS.keys() if k in best}
    p2 = expand_param(p2_raw)
    p2["rsrs_form"] = "rsrs_skew"
    r2 = evaluate_params(p2, panels=panels)
    print("R2 best:", _summarize(r2["metrics"]))
    rounds.append(_round_record(
        2, "LHS-200 网格", "LHS 抽样能在 200 组内找到显著优于基线的参数",
        p2, r2["metrics"],
        change="LHS 200 组（含 rebal_threshold ∈ {0, 0.1, 0.2, 0.4}）扫全参数空间，取 IS Sharpe 最高",
        next_idea=("观察换手是否得到抑制；R3 在最优参数附近增加趋势过滤 (close > MA) "
                    "考察对回撤与 win-rate 的影响"),
    ))
    _append_log(rounds)

    # ================================================================
    # ROUND 3 — Add per-ETF trend filter (close > MA_n)
    # ================================================================
    print("\n=== R3: + trend filter (close > MA) ===")
    best_metric = -1e9
    best_p3 = None
    best_extra = None
    for ma in [60, 100, 150, 200]:
        p = dict(p2)
        extras = {"trend_ma_window": ma}
        r = evaluate_with_extras(panels, p, extras=extras)
        sh = r["metrics"]["sharpe"]
        print(f"  MA={ma}: Sharpe={sh:.3f}  Ret={r['metrics']['ann_ret']*100:.2f}%  DD={r['metrics']['max_dd']*100:.2f}%")
        if sh > best_metric:
            best_metric = sh
            best_p3 = p
            best_extra = extras
    r3 = evaluate_with_extras(panels, best_p3, extras=best_extra)
    print("R3 best:", _summarize(r3["metrics"]))
    rounds.append(_round_record(
        3, f"+ Trend MA{best_extra['trend_ma_window']} gate",
        "对每只 ETF 加入 close > MA(N) 闸门可剔除『刚摸顶但还未突破』的弱势品种，提升胜率",
        {**best_p3, "trend_ma_window": best_extra["trend_ma_window"]},
        r3["metrics"],
        change=f"在 R2 最优参数上叠加 trend gate (close > MA(N))，N 在 {{60,100,150,200}} 中选 {best_extra['trend_ma_window']}",
        next_idea="R4 尝试剔除 IS 期低贡献桶（如海外/商品）以减小相关性、控制噪声",
    ))
    _append_log(rounds)

    # ================================================================
    # ROUND 4 — Universe trim: try excluding buckets with low IS contribution
    # ================================================================
    print("\n=== R4: bucket trim ===")
    # Quick bucket attribution: per-ETF cumulative weight × return contribution
    # We just try excluding combinations of typically-noisy buckets
    candidates = [
        [],
        ["海外"],
        ["商品"],
        ["海外", "商品"],
        ["地产链", "农业"],
        ["海外", "地产链", "农业"],
        ["现金"],   # exclude money market from rotation (still in defensive)
    ]
    best_r4 = None
    best_excl = None
    best_sh = -1e9
    for excl in candidates:
        extras = {"trend_ma_window": best_extra["trend_ma_window"],
                  "universe_df": universe_df,
                  "exclude_buckets": excl}
        r = evaluate_with_extras(panels, best_p3, extras=extras)
        sh = r["metrics"]["sharpe"]
        print(f"  exclude={excl}: Sharpe={sh:.3f}")
        if sh > best_sh:
            best_sh = sh
            best_r4 = r
            best_excl = excl
    rounds.append(_round_record(
        4, f"剔除桶 {best_excl or '(无)'}",
        "海外/商品/农业等与 A 股板块相关性低、信号噪声大，剔除可提净 Sharpe",
        {**best_p3, "trend_ma_window": best_extra["trend_ma_window"], "exclude_buckets": best_excl},
        best_r4["metrics"],
        change=f"在 R3 基础上从可选池剔除桶 {best_excl or '(无)'}",
        next_idea="R5 优化风控带 θ_off/θ_on 的组合，并尝试降低 top_k 提高集中度",
    ))
    p4 = best_p3
    extra4 = {"trend_ma_window": best_extra["trend_ma_window"],
              "universe_df": universe_df, "exclude_buckets": best_excl}
    _append_log(rounds)

    # ================================================================
    # ROUND 5 — Risk-off band + top_k tuning
    # ================================================================
    print("\n=== R5: risk-off band & top_k ===")
    band_grid = [(-1.0, 0.5), (-0.7, 0.7), (-0.5, 1.0),
                  (-1.5, 0.0), (-0.7, 1.5), (-0.3, 0.3)]
    topk_grid = [3, 5, 7]
    best_r5 = None
    best_p5 = None
    best_sh = -1e9
    for band in band_grid:
        for k in topk_grid:
            p = dict(p4)
            p["theta_off"], p["theta_on"] = band
            p["top_k"] = k
            r = evaluate_with_extras(panels, p, extras=extra4)
            sh = r["metrics"]["sharpe"]
            if sh > best_sh:
                best_sh = sh
                best_r5 = r
                best_p5 = p
    print("R5 best:", _summarize(best_r5["metrics"]),
          f"  band={best_p5['theta_off']},{best_p5['theta_on']}  k={best_p5['top_k']}")
    rounds.append(_round_record(
        5, f"风控带({best_p5['theta_off']},{best_p5['theta_on']}) k={best_p5['top_k']}",
        "动态调整 RSRS 风控带与 top_k 平衡集中度与防御性",
        {**best_p5, "trend_ma_window": extra4["trend_ma_window"],
         "exclude_buckets": extra4["exclude_buckets"]},
        best_r5["metrics"],
        change="6×3 小网格 (theta_pair × top_k) 定优",
        next_idea="R6 在 R5 最优参数周围对 mom_L / lambda_s / rebal_threshold 做局部细化",
    ))
    p5 = best_p5
    _append_log(rounds)

    # ================================================================
    # ROUND 6 — Local refinement around R5 best on (mom_L, lambda_s, rebal_threshold)
    # ================================================================
    print("\n=== R6: local refinement ===")
    refine_space = []
    for mom_L in [60, 90, 120, 150, 180]:
        for ls in [0.0, 0.2, 0.3, 0.5, 0.7]:
            for rb in [0.0, 0.10, 0.20, 0.30, 0.40]:
                p = dict(p5)
                p["mom_L"] = mom_L
                p["lambda_s"] = ls
                p["rebal_threshold"] = rb
                refine_space.append(p)
    best_r6 = None
    best_p6 = None
    best_sh = -1e9
    for p in refine_space:
        r = evaluate_with_extras(panels, p, extras=extra4)
        if r["metrics"]["sharpe"] > best_sh:
            best_sh = r["metrics"]["sharpe"]
            best_r6 = r
            best_p6 = p
    print("R6 best:", _summarize(best_r6["metrics"]),
          f"  mom_L={best_p6['mom_L']}  ls={best_p6['lambda_s']}  rb={best_p6['rebal_threshold']}")
    rounds.append(_round_record(
        6, "局部细化 (mom_L × λ_s × rebal_threshold)",
        "在 R5 最优周围细化 3 维子空间能再压榨净 Sharpe",
        {**best_p6, "trend_ma_window": extra4["trend_ma_window"],
         "exclude_buckets": extra4["exclude_buckets"]},
        best_r6["metrics"],
        change="125 组 (5×5×5) 局部网格围绕 R5 最优",
        next_idea=("**结束 IS 迭代**。建议交付该参数等待用户批准 OOS 验证。"
                    "若净 Sharpe 显著高于基线 (>1.5)，需在 OOS 上严格评估 IS→OOS 衰减"),
    ))
    _append_log(rounds)

    # Persist final best params
    final_params = {**best_p6,
                    "trend_ma_window": extra4["trend_ma_window"],
                    "exclude_buckets": extra4["exclude_buckets"]}
    BEST_PARAMS_FP.write_text(json.dumps(final_params, indent=2, ensure_ascii=False), encoding="utf-8")

    # Per-year breakdown for the final round
    final_score, final_elig, final_agg, final_w = None, None, None, None
    extras_full = dict(extra4)
    final_eval = evaluate_with_extras(panels, best_p6, extras=extras_full)
    # Re-run with artifacts via direct path to grab equity series
    cost_cfg = CostConfig(bond_or_money_set=BOND_OR_MONEY_SET)
    rsrs = rsrs_panel(panels["high"], panels["low"],
                       n=best_p6["rsrs_N"], m=best_p6["rsrs_M"], form="rsrs_skew")
    mom = higher_moment_score(panels["close"], L=best_p6["mom_L"],
                               lambda_s=best_p6["lambda_s"], lambda_k=best_p6["lambda_k"])
    score = composite_score(rsrs, mom, w_rsrs=best_p6["w_rsrs"])
    elig = absolute_momentum_filter(panels["close"], best_p6["mom_L"], ABS_MOM_BENCHMARK)
    if extras_full.get("trend_ma_window"):
        elig = elig & _trend_filter_panel(panels["close"], extras_full["trend_ma_window"])
    if extras_full.get("exclude_buckets"):
        univ = extras_full["universe_df"]
        excl_syms = univ[univ["bucket"].isin(extras_full["exclude_buckets"])]["symbol"].tolist()
        for s in excl_syms:
            if s in elig.columns:
                elig[s] = False
    defensive_cols = [s for s in DEFENSIVE_SYMBOLS if s in rsrs.columns]
    defensive_proxy = rsrs[defensive_cols] if defensive_cols else None
    agg_rsrs = rsrs[BENCHMARK_SYMBOL]
    weights = build_target_weights(
        score=score, eligibility=elig, agg_rsrs=agg_rsrs,
        defensive_proxy_score=defensive_proxy,
        top_k=best_p6["top_k"], theta_off=best_p6["theta_off"], theta_on=best_p6["theta_on"],
        rebal_threshold=best_p6["rebal_threshold"],
    )
    res = run_backtest(weights, panels["close"], panels["open"], panels["amount"], cost_cfg)
    pyear = per_year_metrics(res.pnl_net)
    pyear.to_csv(OUT_DIR / "round6_per_year.csv")

    res.equity.to_csv(OUT_DIR / "round6_equity.csv", header=["equity"])
    res.weights_realized.tail(10).to_csv(OUT_DIR / "round6_last_weights.csv")

    print(f"\n[done] total wall-clock = {time.time() - t0:.1f}s")
    print(f"Iteration log: {LOG_FP}")
    print(f"Best params  : {BEST_PARAMS_FP}")


if __name__ == "__main__":
    main()
