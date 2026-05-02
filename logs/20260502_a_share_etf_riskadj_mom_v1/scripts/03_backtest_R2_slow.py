#!/usr/bin/env python3
"""Agent 4 — Round 2.

R1 finding: at 21d horizon all 8 R1 variants UNDERPERFORM EW (excess Sharpe < 0).
The only positive-IC variant was m3 (120d riskadj-mom) at +0.025. Hypothesis
update: A-share ETF cross-section has predictability only at LONGER horizons
(quarterly+) and TOP-N must be wider than 5/3 to dampen rank noise.

R2 batch:
  m1_R2: riskadj_mom_120_top20
  m2_R2: riskadj_mom_180_top20
  m3_R2: riskadj_mom_252_top20  (12-month classical)
  m4_R2: plain_mom_120_top20
  m5_R2: plain_mom_252_top20
  m6_R2: plain_mom_252_skip20_top20  (JT 12-2)
  m7_R2: riskadj_mom_252_top20_ma200_gate
  m8_R2: ew_baseline_all  (control: equal-weight all liquid ETFs)

Rebalance: monthly. Cost: 5 bps/side. Universe: liquidity-filtered Tushare panel.
"""
import json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent))

ROOT = Path("/home/user/Factor_Zoo")
SESSION = ROOT / "logs/20260502_a_share_etf_riskadj_mom_v1"
OUT = SESSION / "outputs"
WORK = SESSION / "working"
DATA = ROOT / "logs/_shared_cache/etf_daily_tushare.parquet"

DELAY = 1
COST_BPS = 5e-4
HOLD_DAYS = 21
RNG_SEED = 20260502
np.random.seed(RNG_SEED)

# Reuse helpers from script 02 by importing
import importlib.util
spec = importlib.util.spec_from_file_location(
    "rmod", str(SESSION / "scripts" / "02_backtest_riskadj_mom.py"))
rmod = importlib.util.module_from_spec(spec); spec.loader.exec_module(rmod)
load_panel        = rmod.load_panel
signal_riskadj    = rmod.signal_riskadj
regime_mask_ma50  = rmod.regime_mask_ma50
make_weights      = rmod.make_weights
backtest          = rmod.backtest
annualised_sharpe = rmod.annualised_sharpe
per_year_sharpe   = rmod.per_year_sharpe
equal_weight_universe_return = rmod.equal_weight_universe_return
info_coefficient  = rmod.info_coefficient
gates             = rmod.gates


def main():
    # Stricter liquidity floor for R2: avg daily amount >= 5e4 (~50M CNY/day)
    P, raw, kept, A = load_panel(min_bars=1500, min_avg_amount=5e4)
    print(f"[load R2] symbols kept: {len(kept)}, dates: {P.shape[0]}, "
          f"{P.index.min().date()} → {P.index.max().date()}")

    BENCH = "510300.SH" if "510300.SH" in P.columns else (
        next((c for c in P.columns if c.startswith("510")), P.columns[0]))
    print(f"[bench] using {BENCH}")
    ma50_mask  = regime_mask_ma50(P, bench=BENCH, n=50)
    ma200_mask = regime_mask_ma50(P, bench=BENCH, n=200)

    EXPRS = [
        dict(id="m1_R2_riskadj_mom_120_top20",         k=120, vw=120, vk="std_log_ret", skip=0,  topN=20, gate=None),
        dict(id="m2_R2_riskadj_mom_180_top20",         k=180, vw=180, vk="std_log_ret", skip=0,  topN=20, gate=None),
        dict(id="m3_R2_riskadj_mom_252_top20",         k=252, vw=252, vk="std_log_ret", skip=0,  topN=20, gate=None),
        dict(id="m4_R2_plain_mom_120_top20",           k=120, vw=None,vk="none",        skip=0,  topN=20, gate=None),
        dict(id="m5_R2_plain_mom_252_top20",           k=252, vw=None,vk="none",        skip=0,  topN=20, gate=None),
        dict(id="m6_R2_plain_mom_252_skip20_top20",    k=252, vw=None,vk="none",        skip=20, topN=20, gate=None),
        dict(id="m7_R2_riskadj_mom_252_top20_ma200",   k=252, vw=252, vk="std_log_ret", skip=0,  topN=20, gate="MA200"),
        dict(id="m8_R2_ew_baseline_all",               k=None,vw=None,vk=None,          skip=0,  topN=None,gate=None),
    ]

    ew_log = equal_weight_universe_return(P)
    ew_sh  = annualised_sharpe(ew_log)
    print(f"[bench] EW universe Sharpe (gross) = {ew_sh:.3f}")

    results, py_rows, cost_rows, gates_all = [], [], [], {}

    for e in EXPRS:
        if e["id"].endswith("_ew_baseline_all"):
            # equal-weight all valid each day (no rebalance cost approximation)
            valid = (~P.isna()).astype(float)
            wsum = valid.sum(axis=1)
            W_d = valid.div(wsum.replace(0, np.nan), axis=0).fillna(0)
            W_me = W_d.copy()
            sig = pd.DataFrame(0.0, index=P.index, columns=P.columns)
        else:
            sig = signal_riskadj(P, k=e["k"], vol_window=e["vw"] or e["k"],
                                 vol_kind=e["vk"], skip=e["skip"])
            gate = ma200_mask if e["gate"] == "MA200" else (
                   ma50_mask if e["gate"] == "MA50" else None)
            W_d, W_me, _ = make_weights(sig, P, topN=e["topN"], regime_mask=gate)

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

        if e["id"].endswith("_ew_baseline_all"):
            ic_mean, ic_t, ic_n = float("nan"), float("nan"), 0
        else:
            ic_mean, ic_t, ic_n = info_coefficient(sig, P, horizon=HOLD_DAYS)

        row = dict(
            expression=e["id"],
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
            py_rows.append(dict(expression=e["id"], year=y, sharpe_net=round(v, 3)))
        for cb in [0, 5, 10, 20]:
            _, n_cb, _ = backtest(W_d, P, cost_bps=cb * 1e-4)
            cost_rows.append(dict(expression=e["id"], cost_bps=cb,
                                  sharpe=round(annualised_sharpe(n_cb), 3),
                                  ann_return=round(float(n_cb.mean()*252), 4)))

        if e["topN"] is not None and not e["id"].endswith("_ew_baseline_all"):
            g = gates(W_me, P, sig, net, gross, e["id"], e["topN"])
        else:
            g = {"name": e["id"], "G2_runs_e2e": True, "G3_pass": True, "G4_pass": True, "overall_pass": True, "note": "ew baseline — gates skipped"}
        gates_all[e["id"]] = g
        print(f"[{e['id']:<42}] Sgross={sh_g:5.2f} Snet={sh_n:5.2f}  "
              f"vsEW={sh_e:+5.2f}  worstY={row['worst_year_sharpe']}  "
              f"BYO={sh_byo:5.2f}  IC={(ic_mean if not math.isnan(ic_mean) else 0):.3f}  "
              f"TO={annual_turn*100:6.1f}%  G3={g.get('G3_pass')} G4={g.get('G4_pass')}")

    df_summary = pd.DataFrame(results)
    df_summary.to_csv(OUT / "r2_summary_batch_0002.csv", index=False)
    df_py = pd.DataFrame(py_rows).sort_values(["expression","year"])
    df_py.to_csv(OUT / "r2_per_year_batch_0002.csv", index=False)
    df_cost = pd.DataFrame(cost_rows)
    df_cost.to_csv(OUT / "r2_cost_sensitivity_batch_0002.csv", index=False)
    (OUT / "r2_validation_gates_batch_0002.json").write_text(json.dumps(gates_all, indent=2))

    md = ["# Backtest Results — Batch 0002 (R2) — Slow Risk-Adjusted Momentum",
          "",
          f"- Universe: {len(kept)} ETFs (≥1500 bars, ≥50M CNY/day avg amount)",
          f"- EW-universe Sharpe (gross) = {ew_sh:.3f}  (this is the bar to beat)",
          "",
          "## Headline metrics", "",
          df_summary.to_markdown(index=False),
          "", "## Per-year Sharpe (net)", "",
          df_py.pivot(index="year", columns="expression", values="sharpe_net").round(2).to_markdown(),
          "", "## Cost sensitivity", "",
          df_cost.pivot(index="cost_bps", columns="expression", values="sharpe").round(2).to_markdown(),
          ""]
    (OUT / "backtest_results_batch_0002.md").write_text("\n".join(md))
    print(f"[done] R2 artifacts written. universe={len(kept)} EW={ew_sh:.3f}")


if __name__ == "__main__":
    main()
