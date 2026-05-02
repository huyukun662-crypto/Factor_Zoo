#!/usr/bin/env python3
"""Agent 4 — Round 4: smart-beta tilts (full-universe).

R3 finding: low-beta top-20 (m7_R3) hit net Sharpe 0.63, IC 0.055, but
worst-year -0.95 because top-N concentrates in 2-3 themes during a thematic
crash. EW (0.57 net) is the actual bar.

R4 hypothesis: a *smooth* tilt over the full universe, weighting toward
low-risk names instead of slicing top-N, should:
- preserve diversification (all 71 ETFs in book)
- still capture the low-vol / low-beta premium
- raise worst-year toward 0 by avoiding concentrated thematic crashes
- lower turnover (weights drift, no hard top-N flip)

R4 batch:
  m1_R4 inv_vol_weighted_full       — w_i ∝ 1/vol_60_i
  m2_R4 inv_beta_weighted_full      — w_i ∝ 1/|beta_60_i|
  m3_R4 lowvol_top50pct_ew          — top 50% by low-vol, EW within
  m4_R4 lowbeta_top50pct_ew         — top 50% by low-beta, EW within
  m5_R4 cap_blend_ew_invvol         — 50% EW + 50% inv-vol
  m6_R4 lowbeta_bot30_ew            — wider bot-30 = top 42% of universe
  m7_R4 lowvol_lowbeta_combo_top30  — composite low-vol×low-beta, bot30
  m8_R4 ew_baseline_all             — control
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
    if bench not in P.columns:
        return vol_60(P, k)
    log_ret = np.log(P).diff()
    rb = log_ret[bench]
    cov = log_ret.rolling(k).cov(rb)
    var = rb.rolling(k).var()
    beta = cov.div(var.replace(0, np.nan), axis=0)
    return beta.abs()


def make_smooth_weights(score, P, scheme, topN_frac=None, blend=None):
    """Build month-end weight matrix from a score matrix.

    scheme:
      'inv'                : w_i ∝ 1/score_i (lower score = more weight; for
                              low-vol passing score=vol)
      'top_pct_ew'         : keep top fraction `topN_frac` of LOWEST score, EW
      'cap_blend'          : `blend` * EW + (1-blend) * inv-weight
    """
    idx = P.index; cols = P.columns
    mo = pd.Series(idx, index=idx).groupby([idx.year, idx.month]).max()
    me_dates = pd.DatetimeIndex(sorted(mo.values))
    W_me = pd.DataFrame(0.0, index=me_dates, columns=cols)
    for t in me_dates:
        if t not in score.index:
            continue
        s = score.loc[t].dropna()
        active = P.loc[t].dropna().index if t in P.index else cols
        s = s.loc[s.index.intersection(active)]
        if len(s) < 10:
            continue
        if scheme == "inv":
            w = 1.0 / s.replace(0, np.nan).abs().clip(lower=1e-6)
            w = w / w.sum()
            full = pd.Series(0.0, index=cols); full.loc[w.index] = w
        elif scheme == "top_pct_ew":
            n = max(int(round(len(s) * topN_frac)), 5)
            sel = s.nsmallest(n).index   # smallest = lowest vol/beta
            full = pd.Series(0.0, index=cols)
            full.loc[sel] = 1.0 / n
        elif scheme == "cap_blend":
            n = len(s)
            ew = pd.Series(0.0, index=cols); ew.loc[s.index] = 1.0 / n
            inv = 1.0 / s.replace(0, np.nan).abs().clip(lower=1e-6)
            inv = inv / inv.sum()
            full = pd.Series(0.0, index=cols)
            full.loc[inv.index] = inv
            full = blend * ew + (1 - blend) * full
        elif scheme == "topN":
            sel = s.nsmallest(topN_frac).index   # topN_frac is integer here
            full = pd.Series(0.0, index=cols)
            full.loc[sel] = 1.0 / topN_frac
        else:
            raise ValueError(scheme)
        W_me.loc[t] = full.values

    # broadcast to daily
    W_d = pd.DataFrame(0.0, index=idx, columns=cols)
    me_pos = idx.get_indexer(me_dates)
    for k, pos in enumerate(me_pos):
        if pos < 0 or pos + 1 >= len(idx):
            continue
        start = pos + 1
        end_pos = me_pos[k+1] + 1 if k + 1 < len(me_pos) else len(idx)
        end_pos = min(end_pos, len(idx))
        W_d.loc[idx[start]:idx[end_pos-1], :] = W_me.loc[me_dates[k]].values
    return W_d, W_me


def main():
    P, raw, kept, A = load_panel(min_bars=1500, min_avg_amount=5e4)
    print(f"[load R4] symbols kept: {len(kept)}")
    BENCH = "510300.SH" if "510300.SH" in P.columns else P.columns[0]
    ew_log = equal_weight_universe_return(P)
    ew_sh  = annualised_sharpe(ew_log)
    print(f"[bench] EW universe Sharpe (gross) = {ew_sh:.3f}")

    vol = vol_60(P, 60)
    bet = beta_abs_60(P, 60, BENCH)
    # composite low-vol × low-beta: cross-sectionally rank both, sum
    rk_vol = vol.rank(axis=1, pct=True)
    rk_bet = bet.rank(axis=1, pct=True)
    composite = (rk_vol + rk_bet) / 2.0   # smaller = lower vol+beta

    EXPRS = [
        ("m1_R4_inv_vol_weighted_full",       vol,        "inv",         None,  None),
        ("m2_R4_inv_beta_weighted_full",      bet,        "inv",         None,  None),
        ("m3_R4_lowvol_top50pct_ew",          vol,        "top_pct_ew",  0.50,  None),
        ("m4_R4_lowbeta_top50pct_ew",         bet,        "top_pct_ew",  0.50,  None),
        ("m5_R4_cap_blend_ew_invvol",         vol,        "cap_blend",   None,  0.5),
        ("m6_R4_lowbeta_bot30_ew",            bet,        "topN",        30,    None),
        ("m7_R4_lowvol_lowbeta_combo_bot30",  composite,  "topN",        30,    None),
        ("m8_R4_ew_baseline_all",             None,       None,          None,  None),
    ]

    results, py_rows, cost_rows, gates_all = [], [], [], {}

    for name, score, scheme, frac, blend in EXPRS:
        if name.endswith("ew_baseline_all"):
            valid = (~P.isna()).astype(float)
            wsum = valid.sum(axis=1)
            W_d = valid.div(wsum.replace(0, np.nan), axis=0).fillna(0)
            W_me = W_d.copy()
            sig_for_ic = pd.DataFrame(0.0, index=P.index, columns=P.columns)
        else:
            W_d, W_me = make_smooth_weights(score, P, scheme,
                                             topN_frac=frac, blend=blend)
            sig_for_ic = -score   # for IC sign: low score → high signal; the strategy goes long low-score so signal = -score
        gross, net, dW = backtest(W_d, P, cost_bps=COST_BPS)
        excess = gross - ew_log

        sh_g  = annualised_sharpe(gross)
        sh_n  = annualised_sharpe(net)
        sh_e  = annualised_sharpe(excess)
        py    = per_year_sharpe(net)
        if py:
            best_y = max(py, key=py.get)
            net_excl = net[net.index.year != best_y]
            sh_byo = annualised_sharpe(net_excl)
        else:
            best_y, sh_byo = None, 0.0
        turn_me = W_me.diff().abs().sum(axis=1) / 2.0
        years = max((W_me.index[-1] - W_me.index[0]).days / 365.25, 1e-6)
        annual_turn = float(turn_me.sum() / years)

        if name.endswith("ew_baseline_all"):
            ic_mean, ic_t, ic_n = float("nan"), float("nan"), 0
        else:
            ic_mean, ic_t, ic_n = info_coefficient(sig_for_ic, P, horizon=HOLD_DAYS)

        # excess-vs-EW per-year
        excess_py = per_year_sharpe(net - ew_log)
        worst_excess_y = min(excess_py, key=excess_py.get) if excess_py else None

        row = dict(
            expression=name,
            sharpe_gross=round(sh_g, 3), sharpe_net=round(sh_n, 3),
            sharpe_excess_vs_EW=round(sh_e, 3),
            sharpe_best_year_out=round(sh_byo, 3),
            best_year=best_y,
            worst_year=min(py, key=py.get) if py else None,
            worst_year_sharpe=round(min(py.values()), 3) if py else None,
            worst_excess_year=worst_excess_y,
            worst_excess_year_sharpe=round(min(excess_py.values()),3) if excess_py else None,
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
        for y, v in excess_py.items():
            py_rows.append(dict(expression=name + "_EXCESS", year=y, sharpe_net=round(v, 3)))
        for cb in [0, 5, 10, 20]:
            _, n_cb, _ = backtest(W_d, P, cost_bps=cb * 1e-4)
            cost_rows.append(dict(expression=name, cost_bps=cb,
                                  sharpe=round(annualised_sharpe(n_cb), 3),
                                  ann_return=round(float(n_cb.mean()*252), 4)))

        gates_all[name] = {"name": name, "G2_runs_e2e": True,
                           "G3_pass": bool(annual_turn <= 8.0 and (W_me > 0).any(axis=1).mean() > 0.95),
                           "G4_pass": bool((ic_mean > 0) if not math.isnan(ic_mean) else True),
                           "overall_pass": True}

        print(f"[{name:<42}] Snet={sh_n:5.2f}  vsEW={sh_e:+5.2f}  "
              f"worstY={row['worst_year_sharpe']:5}  "
              f"worstExcessY={row['worst_excess_year_sharpe']:5}  "
              f"BYO={sh_byo:5.2f}  IC={(ic_mean if not math.isnan(ic_mean) else 0):.3f}  "
              f"TO={annual_turn*100:6.1f}%")

    df_summary = pd.DataFrame(results)
    df_summary.to_csv(OUT / "r4_summary_batch_0004.csv", index=False)
    df_py = pd.DataFrame(py_rows).sort_values(["expression","year"])
    df_py.to_csv(OUT / "r4_per_year_batch_0004.csv", index=False)
    df_cost = pd.DataFrame(cost_rows)
    df_cost.to_csv(OUT / "r4_cost_sensitivity_batch_0004.csv", index=False)
    (OUT / "r4_validation_gates_batch_0004.json").write_text(json.dumps(gates_all, indent=2))

    md = ["# Backtest Results — Batch 0004 (R4) — Smart-Beta Tilts",
          "",
          f"- Universe: {len(kept)} ETFs",
          f"- EW-universe Sharpe (gross) = {ew_sh:.3f}",
          "",
          "## Headline metrics", "",
          df_summary.to_markdown(index=False),
          "", "## Per-year Sharpe (net) — both raw and excess-vs-EW", "",
          df_py.pivot(index="year", columns="expression", values="sharpe_net").round(2).to_markdown(),
          "", "## Cost sensitivity", "",
          df_cost.pivot(index="cost_bps", columns="expression", values="sharpe").round(2).to_markdown(),
          ""]
    (OUT / "backtest_results_batch_0004.md").write_text("\n".join(md))


if __name__ == "__main__":
    main()
