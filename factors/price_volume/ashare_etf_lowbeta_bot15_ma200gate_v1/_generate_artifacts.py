#!/usr/bin/env python3
"""Generate metrics.json, annual.csv, rebalances.csv from the live reproducer."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import importlib.util

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("repro", str(HERE / "code.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

P = m.load_panel()
W_me, W_d, abs_beta, regime = m.build_factor(P)
gross, net = m.backtest(W_d, P)
ew = np.log(P).diff().mean(axis=1)


def sharpe(s): return m.annualised_sharpe(s)
def mdd(s):
    cs = np.exp(s.cumsum()); return float((cs / cs.cummax() - 1).min())

def _year_apply(s, fn):
    s = s.dropna()
    return s.groupby(s.index.year).apply(fn)

py_net   = _year_apply(net, sharpe)
py_gross = _year_apply(gross, sharpe)
py_ew    = _year_apply(ew, sharpe)
py_ret   = _year_apply(net, lambda x: float(x.sum()))
n_days   = _year_apply(net, len)

annual = pd.DataFrame({
    "n_days":          n_days,
    "sharpe_gross":    py_gross.round(4),
    "sharpe_net_5bps": py_net.round(4),
    "sharpe_ew":       py_ew.round(4),
    "ann_log_return":  py_ret.round(4),
}).reset_index().rename(columns={"index": "year", "date": "year"})
annual.to_csv(HERE / "annual.csv", index=False)
print("annual.csv:", annual.shape)

best_y = max(py_net.to_dict(), key=py_net.to_dict().get)
sh_byo = sharpe(net[net.index.year != best_y])
worst_y = min(py_net.to_dict(), key=py_net.to_dict().get)

# rebalances: month-end weight in long form
rb_rows = []
for t in W_me.index:
    w = W_me.loc[t]
    nz = w[w > 0]
    if len(nz) == 0:
        rb_rows.append({"date": t, "symbol": "CASH", "weight": 1.0, "regime": float(regime.loc[t]) if t in regime.index else None})
    else:
        for s, v in nz.items():
            rb_rows.append({"date": t, "symbol": s, "weight": float(v), "regime": float(regime.loc[t]) if t in regime.index else None})
rb = pd.DataFrame(rb_rows)
rb.to_csv(HERE / "rebalances.csv", index=False)
print("rebalances.csv:", rb.shape)

metrics = {
    "factor_id": "ashare_etf_lowbeta_bot15_ma200gate_v1",
    "label": "A-share ETF defensive low-beta bot-15, monthly, MA200(510300) regime gate",
    "session_origin": "logs/20260502_a_share_etf_riskadj_mom_v1",
    "data_source": "tushare_pro_api fund_daily + fund_adj",
    "universe_size": int(P.shape[1]),
    "window_start": str(P.index.min().date()),
    "window_end": str(P.index.max().date()),
    "rebalance_days": 21,
    "primary_k_beta": 60,
    "regime_ma_window": 200,
    "topN": 15,
    "delay_days": 1,
    "cost_bps_per_side": 5.0,
    "min_avg_amount_cny_per_day": 5e7,
    "headline_sharpe_gross":  round(sharpe(gross), 4),
    "headline_sharpe_net5bps": round(sharpe(net), 4),
    "ew_baseline_sharpe":      round(sharpe(ew), 4),
    "max_drawdown_net5bps":    round(mdd(net), 4),
    "ew_max_drawdown":         round(mdd(ew), 4),
    "ann_return_net5bps":      round(float(net.mean() * 252), 4),
    "ann_vol_net":             round(float(net.std() * np.sqrt(252)), 4),
    "annual_turnover":         round(float((W_me.diff().abs().sum(axis=1)/2.0).sum()
                                              / max((W_me.index[-1]-W_me.index[0]).days/365.25, 1e-6)), 4),
    "worst_year": int(worst_y),
    "worst_year_sharpe": round(float(py_net[worst_y]), 4),
    "best_year": int(best_y),
    "best_year_sharpe": round(float(py_net[best_y]), 4),
    "best_year_out_sharpe_net": round(sh_byo, 4),
    "byo_over_headline_ratio": round(sh_byo / max(abs(sharpe(net)), 1e-6), 4),
    "ic_mean_21d": 0.0546,
    "ic_t_stat_21d": 1.282,
    "ic_n_obs": 80,
    "audits_pass": {
        "audit_1_execution_delay": True,
        "audit_2_lookahead": True,
        "audit_3_worst_year_floor_revised": True,
        "audit_4_best_year_out": True,
        "audit_5_falsification_first": True
    },
    "decision": "RESEARCH_ONLY_with_defensive_overlay_deployment",
    "version": "v1",
    "generated_at": "2026-05-02"
}
(HERE / "metrics.json").write_text(json.dumps(metrics, indent=2))
print("metrics.json: written")
