# Expressions Batch 0002 — Idiosyncratic Trend (Residualized)

**Session:** `20260422_trend_technical_alpha`
**Author:** Agent 3 — Alpha Builder
**Mechanism:** idiosyncratic momentum (Blitz-Huij-Martens 2011 JEF)
**Falsification result from Batch 0001:** all 8 raw trend signals were
*wrong-signed*, with rank-IC t-stats between |6| and |25|. The A-share return
process is reversal-dominated. Batch 2 asks the residual question: after
stripping the *known* anti-momentum drivers from each trend signal, does any
true trend predict forward returns?

Controls used in cross-sectional residualization (per `trade_date`):
1. `log_mv` — log of total market cap (size effect)
2. `sigma_120` — std of past-120-day daily log returns (lottery / σ effect)
3. `ret_20` — past-20-day cumulative log return (short-term reversal)

For each trend signal X in {α_01..α_08} we compute, per date:
```
X_idio(t) = residual of OLS(X(t) on [const, log_mv(t), σ_120(t), ret_20(t)])
```
where the regression is run cross-sectionally across all stocks at date `t`,
using only data available up to `t` (no peeking). Cross-sectional
residualization is **walk-forward-safe by construction** because each date is
solved independently.

---

## α_09 — idio_HZZ_trend
Residual of α_01 vs {log_mv, σ_120, ret_20}.

## α_10 — idio_tstat_60d
Residual of α_02 vs {log_mv, σ_120, ret_20}.

## α_11 — idio_tstat_120d
Residual of α_03 vs {log_mv, σ_120, ret_20}.

## α_12 — idio_MA_crossover
Residual of α_04 vs {log_mv, σ_120, ret_20}.

## α_13 — idio_52w_proximity
Residual of α_05 vs {log_mv, σ_120, ret_20}.

## α_14 — idio_trend_Sharpe
Residual of α_07 vs {log_mv, σ_120, ret_20}.

## α_15 — idio_12_1_momentum
Residual of α_08 vs {log_mv, σ_120, ret_20}.

## α_16 — idio_combo
Equal-weighted z-score average of α_09 and α_15 per `trade_date`. This tests
whether *combining* two complementary idio-trend signals (Han-Zhou-Zhu shape
+ classical 12-1) produces a stronger composite, the way classical
multi-style books work.

## Notes for Agent 4
- All residualizations done per-date via `numpy.linalg.lstsq`, batched to
  vectorize across dates.
- Industry-neutralization is applied **after** residualization at evaluation
  time, same as batch 1.
- Same backtest pipeline: monthly rebal, 5 bps per side turnover-aware cost,
  Q5 long-only excess + LS metrics.
- If any α_09..α_16 has positive LS Sharpe ≥ 1.0 AND worst-year ≥ 0.5 AND
  residual IC ≥ 30 % of raw IC after additionally regressing out industry,
  it is a PROMOTE candidate. Otherwise RESEARCH-ONLY and the family is
  declared dead.
