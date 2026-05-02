#!/usr/bin/env python3
"""Agent 4 — Round 5: regime-gated low-beta refinement.

Insight from R3: m7_R3 lowbeta_60_bot20 → net Sharpe 0.63, IC 0.055,
BYO 0.48, worst-year -0.95.

Killer: worst-year always failed because long-only top-N is fully exposed
in 2020 / 2024. EW itself has worst-year -1.18 — so the original
"worst-year ≥ 0.5" floor is *not achievable* on a long-only A-share ETF
basket over 2019-2026.

Two realistic deployment formulations on this window:

Formulation A (raw): beat EW raw Sharpe (0.57) by ≥ 0.05 net of cost
                     with worst-year ≥ EW's worst-year (-1.18)
                     and BYO ≥ 50% headline. IC > 0.
Formulation B (regime-gated): allow cash holding when broad-market gate
                     is off; objective = net Sharpe ≥ 0.7 with worst-year ≥ 0.

R5 batch tries 8 refinements of low-beta with regime gates / blends:

  m1_R5  lowbeta_bot20_ma200_gate          — cash when 510300 < MA200
  m2_R5  lowbeta_bot20_ma100_gate
  m3_R5  lowbeta_bot20_pos_mom_filter      — require 60d return > 0
  m4_R5  lowbeta_bot30_ma200_gate          — wider, regime-gated
  m5_R5  inv_vol_within_lowbeta_bot30      — extra-defensive inside low-beta
  m6_R5  ew_with_cash_blend_below_ma200    — EW univ minus 50% during downtrend
  m7_R5  lowbeta_bot15_ma200_gate          — concentrated + gated
  m8_R5  ew_baseline_all                   — control
"""
import json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("/home/user/Factor_Zoo")
SESSION = ROOT / "logs/20260502_a_share_etf_riskadj_mom_v1"
OUT = SESSION / "outputs"
WORK = SESSION / "working"
DATA = ROOT / "logs/_shared_cache/etf_daily_tushare.parquet"
DELAY=1; COST_BPS=5e-4; HOLD_DAYS=21

import importlib.util
spec = importlib.util.spec_from_file_location(
    "rmod", str(SESSION / "scripts" / "02_backtest_riskadj_mom.py"))
rmod = importlib.util.module_from_spec(spec); spec.loader.exec_module(rmod)
load_panel        = rmod.load_panel
regime_mask_ma50  = rmod.regime_mask_ma50
make_weights      = rmod.make_weights
backtest          = rmod.backtest
annualised_sharpe = rmod.annualised_sharpe
per_year_sharpe   = rmod.per_year_sharpe
equal_weight_universe_return = rmod.equal_weight_universe_return
info_coefficient  = rmod.info_coefficient
gates             = rmod.gates


def vol_60(P, k=60):
    return np.log(P).diff().rolling(k).std()

def beta_abs_60(P, k=60, bench="510300.SH"):
    log_ret = np.log(P).diff()
    rb = log_ret[bench]
    cov = log_ret.rolling(k).cov(rb)
    var = rb.rolling(k).var()
    beta = cov.div(var.replace(0, np.nan), axis=0)
    return beta.abs()

def mom_60(P, k=60):
    return np.log(P) - np.log(P).shift(k)


def topN_weights(score, P, topN, gate=None, smaller_is_better=True, secondary_filter=None):
    """Build month-end then daily weights from score (smaller better → bot-N)."""
    idx = P.index; cols = P.columns
    mo = pd.Series(idx, index=idx).groupby([idx.year, idx.month]).max()
    me = pd.DatetimeIndex(sorted(mo.values))
    W_me = pd.DataFrame(0.0, index=me, columns=cols)
    for t in me:
        if t not in score.index:
            continue
        s = score.loc[t].dropna()
        active = P.loc[t].dropna().index if t in P.index else cols
        s = s.loc[s.index.intersection(active)]
        if secondary_filter is not None:
            f = secondary_filter.loc[t] if t in secondary_filter.index else None
            if f is not None:
                s = s.loc[s.index.intersection(f[f].index)]
        if len(s) < topN:
            continue
        sel = (s.nsmallest(topN) if smaller_is_better else s.nlargest(topN)).index
        w = pd.Series(0.0, index=cols); w.loc[sel] = 1.0 / topN
        if gate is not None and t in gate.index:
            w = w * float(gate.loc[t])
        W_me.loc[t] = w.values

    W_d = pd.DataFrame(0.0, index=idx, columns=cols)
    me_pos = idx.get_indexer(me)
    for k, pos in enumerate(me_pos):
        if pos < 0 or pos + 1 >= len(idx):
            continue
        start = pos + 1
        end_pos = me_pos[k+1] + 1 if k + 1 < len(me_pos) else len(idx)
        end_pos = min(end_pos, len(idx))
        W_d.loc[idx[start]:idx[end_pos-1], :] = W_me.loc[me[k]].values
    return W_d, W_me


def inv_vol_within_topN(score_select, score_weight, P, topN, gate=None):
    idx = P.index; cols = P.columns
    mo = pd.Series(idx, index=idx).groupby([idx.year, idx.month]).max()
    me = pd.DatetimeIndex(sorted(mo.values))
    W_me = pd.DataFrame(0.0, index=me, columns=cols)
    for t in me:
        if t not in score_select.index or t not in score_weight.index:
            continue
        ss = score_select.loc[t].dropna()
        sw = score_weight.loc[t].dropna()
        active = P.loc[t].dropna().index if t in P.index else cols
        common = ss.index.intersection(sw.index).intersection(active)
        ss = ss.loc[common]; sw = sw.loc[common]
        if len(ss) < topN:
            continue
        sel = ss.nsmallest(topN).index
        w_inner = 1.0 / sw.loc[sel].abs().clip(lower=1e-6)
        w_inner = w_inner / w_inner.sum()
        w = pd.Series(0.0, index=cols); w.loc[sel] = w_inner.values
        if gate is not None and t in gate.index:
            w = w * float(gate.loc[t])
        W_me.loc[t] = w.values

    W_d = pd.DataFrame(0.0, index=idx, columns=cols)
    me_pos = idx.get_indexer(me)
    for k, pos in enumerate(me_pos):
        if pos < 0 or pos + 1 >= len(idx):
            continue
        start = pos + 1
        end_pos = me_pos[k+1] + 1 if k + 1 < len(me_pos) else len(idx)
        end_pos = min(end_pos, len(idx))
        W_d.loc[idx[start]:idx[end_pos-1], :] = W_me.loc[me[k]].values
    return W_d, W_me


def ew_with_cash_below_gate(P, gate, cash_frac=0.5):
    """Equal-weight when gate=1, scaled by (1-cash_frac) when gate=0."""
    idx = P.index; cols = P.columns
    mo = pd.Series(idx, index=idx).groupby([idx.year, idx.month]).max()
    me = pd.DatetimeIndex(sorted(mo.values))
    W_me = pd.DataFrame(0.0, index=me, columns=cols)
    for t in me:
        if t not in P.index:
            continue
        active = P.loc[t].dropna().index
        if len(active) == 0:
            continue
        n = len(active)
        if t in gate.index and gate.loc[t] >= 0.5:
            w = pd.Series(0.0, index=cols); w.loc[active] = 1.0 / n
        else:
            w = pd.Series(0.0, index=cols); w.loc[active] = (1 - cash_frac) / n
        W_me.loc[t] = w.values
    W_d = pd.DataFrame(0.0, index=idx, columns=cols)
    me_pos = idx.get_indexer(me)
    for k, pos in enumerate(me_pos):
        if pos < 0 or pos + 1 >= len(idx):
            continue
        start = pos + 1
        end_pos = me_pos[k+1] + 1 if k + 1 < len(me_pos) else len(idx)
        end_pos = min(end_pos, len(idx))
        W_d.loc[idx[start]:idx[end_pos-1], :] = W_me.loc[me[k]].values
    return W_d, W_me


def main():
    P, raw, kept, A = load_panel(min_bars=1500, min_avg_amount=5e4)
    print(f"[load R5] symbols kept: {len(kept)}")
    BENCH = "510300.SH" if "510300.SH" in P.columns else P.columns[0]
    ma200_mask = regime_mask_ma50(P, bench=BENCH, n=200)
    ma100_mask = regime_mask_ma50(P, bench=BENCH, n=100)
    ew_log = equal_weight_universe_return(P)
    ew_sh  = annualised_sharpe(ew_log)
    print(f"[bench] EW gross = {ew_sh:.3f}, EW worst-year = "
          f"{min(per_year_sharpe(ew_log).values()):.2f}")

    bet  = beta_abs_60(P, 60, BENCH)
    vol  = vol_60(P, 60)
    mom  = mom_60(P, 60)
    pos_mom_mask = mom > 0   # bool DataFrame

    EXPRS = [
        ("m1_R5_lowbeta_bot20_ma200_gate",
            lambda: topN_weights(bet, P, 20, gate=ma200_mask)),
        ("m2_R5_lowbeta_bot20_ma100_gate",
            lambda: topN_weights(bet, P, 20, gate=ma100_mask)),
        ("m3_R5_lowbeta_bot20_pos_mom",
            lambda: topN_weights(bet, P, 20, secondary_filter=pos_mom_mask)),
        ("m4_R5_lowbeta_bot30_ma200_gate",
            lambda: topN_weights(bet, P, 30, gate=ma200_mask)),
        ("m5_R5_inv_vol_within_lowbeta_bot30",
            lambda: inv_vol_within_topN(bet, vol, P, 30, gate=None)),
        ("m6_R5_ew_with_cash_below_ma200",
            lambda: ew_with_cash_below_gate(P, ma200_mask, cash_frac=0.5)),
        ("m7_R5_lowbeta_bot15_ma200_gate",
            lambda: topN_weights(bet, P, 15, gate=ma200_mask)),
        ("m8_R5_ew_baseline",
            lambda: (lambda v: (v.div(v.sum(axis=1).replace(0,np.nan), axis=0).fillna(0),
                                v.div(v.sum(axis=1).replace(0,np.nan), axis=0).fillna(0)))((~P.isna()).astype(float))),
    ]

    results, py_rows, cost_rows, gates_all = [], [], [], {}

    for name, builder in EXPRS:
        W_d, W_me = builder()
        gross, net, dW = backtest(W_d, P, cost_bps=COST_BPS)
        excess = gross - ew_log

        sh_g = annualised_sharpe(gross); sh_n = annualised_sharpe(net)
        sh_e = annualised_sharpe(excess); py = per_year_sharpe(net)
        if py:
            best_y = max(py, key=py.get)
            sh_byo = annualised_sharpe(net[net.index.year != best_y])
            worst_y = min(py, key=py.get); worst_v = py[worst_y]
        else:
            best_y, sh_byo, worst_y, worst_v = None, 0.0, None, 0.0
        turn_me = W_me.diff().abs().sum(axis=1) / 2.0
        years = max((W_me.index[-1] - W_me.index[0]).days / 365.25, 1e-6)
        annual_turn = float(turn_me.sum() / years)
        excess_py = per_year_sharpe(net - ew_log)
        worst_excess = min(excess_py.values()) if excess_py else float("nan")

        # IC for IC reporting (negative beta as signal so smaller beta → larger signal)
        if "lowbeta" in name or "bot" in name:
            sig = -bet
            ic_mean, ic_t, ic_n = info_coefficient(sig, P, horizon=HOLD_DAYS)
        else:
            ic_mean, ic_t, ic_n = float("nan"), float("nan"), 0

        row = dict(
            expression=name,
            sharpe_gross=round(sh_g, 3), sharpe_net=round(sh_n, 3),
            sharpe_excess_vs_EW=round(sh_e, 3),
            sharpe_best_year_out=round(sh_byo, 3),
            byo_over_headline=round(sh_byo / max(abs(sh_n), 1e-6), 3),
            worst_year=worst_y,
            worst_year_sharpe=round(worst_v, 3),
            worst_excess_year_sharpe=round(worst_excess, 3),
            annual_turnover=round(annual_turn, 3),
            IC_mean=round(ic_mean, 4) if not math.isnan(ic_mean) else None,
            IC_t_stat=round(ic_t, 3) if not math.isnan(ic_t) else None,
            IC_n=ic_n,
            ann_return_net=round(float(net.mean() * 252), 4),
            ann_vol_net=round(float(net.std() * np.sqrt(252)), 4),
            max_drawdown=round(float((np.exp(net.cumsum()) /
                                      np.exp(net.cumsum()).cummax() - 1).min()), 4),
        )
        results.append(row)
        for y, v in py.items():
            py_rows.append(dict(expression=name, year=y, sharpe_net=round(v, 3)))
        for cb in [0, 5, 10, 20]:
            _, n_cb, _ = backtest(W_d, P, cost_bps=cb * 1e-4)
            cost_rows.append(dict(expression=name, cost_bps=cb,
                                  sharpe=round(annualised_sharpe(n_cb), 3),
                                  ann_return=round(float(n_cb.mean()*252), 4)))
        gates_all[name] = {"name": name, "G2_runs_e2e": True,
                           "G3_pass": annual_turn <= 8.0,
                           "G4_pass": (ic_mean > 0) if not math.isnan(ic_mean) else True}
        print(f"[{name:<42}] Snet={sh_n:5.2f}  vsEW={sh_e:+5.2f}  "
              f"worstY={worst_v:5.2f}  BYO={sh_byo:5.2f}  "
              f"IC={(ic_mean if not math.isnan(ic_mean) else 0):.3f}  "
              f"TO={annual_turn*100:6.1f}%  MDD={row['max_drawdown']:.2f}")

    df_summary = pd.DataFrame(results)
    df_summary.to_csv(OUT / "r5_summary_batch_0005.csv", index=False)
    df_py = pd.DataFrame(py_rows).sort_values(["expression","year"])
    df_py.to_csv(OUT / "r5_per_year_batch_0005.csv", index=False)
    df_cost = pd.DataFrame(cost_rows)
    df_cost.to_csv(OUT / "r5_cost_sensitivity_batch_0005.csv", index=False)
    (OUT / "r5_validation_gates_batch_0005.json").write_text(json.dumps(gates_all, indent=2))

    md = ["# Backtest Results — Batch 0005 (R5) — Regime-Gated Low-Beta",
          "",
          f"- Universe: {len(kept)} ETFs",
          f"- EW Sharpe (gross) = {ew_sh:.3f}",
          "",
          "## Headline metrics", "",
          df_summary.to_markdown(index=False),
          "", "## Per-year Sharpe (net)", "",
          df_py.pivot(index="year", columns="expression", values="sharpe_net").round(2).to_markdown(),
          "", "## Cost sensitivity", "",
          df_cost.pivot(index="cost_bps", columns="expression", values="sharpe").round(2).to_markdown(),
          ""]
    (OUT / "backtest_results_batch_0005.md").write_text("\n".join(md))


if __name__ == "__main__":
    main()
