#!/usr/bin/env python3
"""Agent 4 — Round 3: pivot to low-volatility.

R1: short-window risk-adjusted momentum FAILS on wide universe (negative IC).
R2: long-window momentum has correct sign (+IC) but cannot beat EW (Sharpe 0.57).

R3 hypothesis: A-share ETF cross-section is dominated by a *low-volatility*
anomaly — low-vol thematic ETFs out-deliver high-vol on a risk-adjusted basis.
This is the most-documented anomaly in Chinese A-shares (e.g. Eun-Huang-Lai
2008, Li-Liu-Wang 2020). At ETF level the story should still hold: high-vol
ETFs = thematic-lottery (semis, NEV, biotech) prone to bubble-and-crash;
low-vol = broad-index + dividend + defensive sector trackers.

R3 batch:
  m1_R3 lowvol_60_bot20            — long bottom-20 by 60d realised vol
  m2_R3 lowvol_120_bot20           — slower vol estimate
  m3_R3 lowvol_60_bot10            — concentrated low-vol
  m4_R3 lowvol_60_x_uptrend_bot20  — low-vol AND positive 120d return (composite)
  m5_R3 lowvol_60_bot20_ma200_gate — low-vol + broad-market regime
  m6_R3 high_vol_60_top20          — control: should under-perform if anomaly true
  m7_R3 lowbeta_60_bot20           — alt risk: low beta to bench instead of low vol
  m8_R3 ew_baseline_all            — control kept for reference
"""
import json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path("/home/user/Factor_Zoo")
SESSION = ROOT / "logs/20260502_a_share_etf_riskadj_mom_v1"
OUT = SESSION / "outputs"
WORK = SESSION / "working"
DATA = ROOT / "logs/_shared_cache/etf_daily_tushare.parquet"
DELAY = 1; COST_BPS = 5e-4; HOLD_DAYS = 21; RNG_SEED = 20260502
np.random.seed(RNG_SEED)

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


def signal_lowvol(P, k):
    log_ret = np.log(P).diff()
    vol = log_ret.rolling(k).std()
    return -vol  # bigger value = lower vol → top-N picks lowest vol

def signal_highvol(P, k):
    return -signal_lowvol(P, k)

def signal_lowbeta(P, k, bench):
    if bench not in P.columns:
        return signal_lowvol(P, k)
    log_ret = np.log(P).diff()
    rb = log_ret[bench]
    cov = log_ret.rolling(k).cov(rb)
    var = rb.rolling(k).var()
    beta = cov.div(var.replace(0, np.nan), axis=0)
    return -beta.abs()  # bigger value = lower |beta|

def signal_lowvol_x_uptrend(P, k_vol, k_mom):
    sig_lv = signal_lowvol(P, k_vol)
    logp = np.log(P)
    mom = logp - logp.shift(k_mom)
    # require mom > 0; among those, rank by low-vol
    return sig_lv.where(mom > 0)


def main():
    P, raw, kept, A = load_panel(min_bars=1500, min_avg_amount=5e4)
    print(f"[load R3] symbols kept: {len(kept)}, dates: {P.shape[0]}")
    BENCH = "510300.SH" if "510300.SH" in P.columns else P.columns[0]
    print(f"[bench] using {BENCH}")
    ma200_mask = regime_mask_ma50(P, bench=BENCH, n=200)
    ew_log = equal_weight_universe_return(P)
    ew_sh  = annualised_sharpe(ew_log)
    print(f"[bench] EW universe Sharpe (gross) = {ew_sh:.3f}")

    EXPRS = [
        ("m1_R3_lowvol_60_bot20",            lambda: signal_lowvol(P, 60),               20, None),
        ("m2_R3_lowvol_120_bot20",           lambda: signal_lowvol(P, 120),              20, None),
        ("m3_R3_lowvol_60_bot10",            lambda: signal_lowvol(P, 60),               10, None),
        ("m4_R3_lowvol_60_x_uptrend_bot20",  lambda: signal_lowvol_x_uptrend(P, 60, 120),20, None),
        ("m5_R3_lowvol_60_bot20_ma200_gate", lambda: signal_lowvol(P, 60),               20, "MA200"),
        ("m6_R3_high_vol_60_top20",          lambda: signal_highvol(P, 60),              20, None),
        ("m7_R3_lowbeta_60_bot20",           lambda: signal_lowbeta(P, 60, BENCH),       20, None),
        ("m8_R3_ew_baseline_all",            None,                                       None,None),
    ]

    results, py_rows, cost_rows, gates_all = [], [], [], {}

    for name, sigfn, topN, gate_kind in EXPRS:
        if name.endswith("ew_baseline_all"):
            valid = (~P.isna()).astype(float)
            wsum = valid.sum(axis=1)
            W_d = valid.div(wsum.replace(0, np.nan), axis=0).fillna(0)
            W_me = W_d.copy()
            sig = pd.DataFrame(0.0, index=P.index, columns=P.columns)
        else:
            sig  = sigfn()
            gate = ma200_mask if gate_kind == "MA200" else None
            W_d, W_me, _ = make_weights(sig, P, topN=topN, regime_mask=gate)

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
            ic_mean, ic_t, ic_n = info_coefficient(sig, P, horizon=HOLD_DAYS)

        row = dict(
            expression=name,
            sharpe_gross=round(sh_g, 3), sharpe_net=round(sh_n, 3),
            sharpe_excess_vs_EW=round(sh_e, 3),
            sharpe_best_year_out=round(sh_byo, 3),
            best_year=best_y,
            worst_year=min(py, key=py.get) if py else None,
            worst_year_sharpe=round(min(py.values()), 3) if py else None,
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

        if topN is not None:
            g = gates(W_me, P, sig, net, gross, name, topN)
        else:
            g = {"name": name, "G2_runs_e2e": True, "G3_pass": True, "G4_pass": True, "overall_pass": True}
        gates_all[name] = g
        print(f"[{name:<42}] Sgross={sh_g:5.2f} Snet={sh_n:5.2f}  "
              f"vsEW={sh_e:+5.2f}  worstY={row['worst_year_sharpe']}  "
              f"BYO={sh_byo:5.2f}  IC={(ic_mean if not math.isnan(ic_mean) else 0):.3f}  "
              f"TO={annual_turn*100:6.1f}%  G3={g.get('G3_pass')} G4={g.get('G4_pass')}")

    df_summary = pd.DataFrame(results)
    df_summary.to_csv(OUT / "r3_summary_batch_0003.csv", index=False)
    df_py = pd.DataFrame(py_rows).sort_values(["expression","year"])
    df_py.to_csv(OUT / "r3_per_year_batch_0003.csv", index=False)
    df_cost = pd.DataFrame(cost_rows)
    df_cost.to_csv(OUT / "r3_cost_sensitivity_batch_0003.csv", index=False)
    (OUT / "r3_validation_gates_batch_0003.json").write_text(json.dumps(gates_all, indent=2))

    md = ["# Backtest Results — Batch 0003 (R3) — Low-Volatility Pivot",
          "",
          f"- Universe: {len(kept)} ETFs (≥1500 bars, ≥50M CNY/day avg amount)",
          f"- EW-universe Sharpe (gross) = {ew_sh:.3f}  (bar to beat)",
          "",
          "## Headline metrics", "",
          df_summary.to_markdown(index=False),
          "", "## Per-year Sharpe (net)", "",
          df_py.pivot(index="year", columns="expression", values="sharpe_net").round(2).to_markdown(),
          "", "## Cost sensitivity", "",
          df_cost.pivot(index="cost_bps", columns="expression", values="sharpe").round(2).to_markdown(),
          ""]
    (OUT / "backtest_results_batch_0003.md").write_text("\n".join(md))
    print(f"[done R3] universe={len(kept)} EW={ew_sh:.3f}")


if __name__ == "__main__":
    main()
