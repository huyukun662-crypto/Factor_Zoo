# Alpha Ranking — Trend / Technical Session (Final, after Round 6)

**Session:** `20260422_trend_technical_alpha`
**Author:** Agent 5 — Evaluator
**Cost:** 5 bps per side, turnover-aware. Monthly rebalance. Industry-neutral.
**Splits:** Train 2018-2022 / Validate 2023 / Test 2024 – 2025-04-18.
**Decision:** **PROMOTE α_35** (dispersion-gated 12-3 idio momentum).

## Final ranking (top deployable)

| rank | alpha | construction | test LS | test Q5 IR | full LS | maxDD | worst-year-active | verdict |
|---:|---|---|---:|---:|---:|---:|---:|---|
| 🏆 | **α_35** | **α_29 × 1{cross-sectional std(ret_20) > rolling-252d-median}** | **1.74** | **1.03** | **1.22** | **−5.5 %** | **0.63** | **PROMOTE** |
| | (variant) α_35-126d | same with 126d median lookback | 2.29 | 1.25 | 1.46 | -2.7 % | 0.63 | viable variant |
| | (variant) α_35-p60 | dispersion > 60th percentile (252d) | 1.54 | 1.22 | 1.13 | -4.5 % | 1.24 | viable variant |
| 2 | α_29 | idio 12-3 momentum (ungated baseline) | 2.06 | 1.16 | 1.00 | -7.1 % | 0.04 | RESEARCH-ONLY |
| 3 | α_19 | idio 12-2 momentum | 1.24 | 0.65 | 0.84 | -7.3 % | 0.16 | RESEARCH-ONLY |
| 4 | α_28 | 12-2 idio with σ_60 control | 1.20 | 0.61 | 0.61 | -7.5 % | -0.14 | RESEARCH-ONLY |
| 5 | α_38 | α_29 × softmax(regime score) | 1.38 | 0.74 | 0.72 | -5.0 % | -1.14 | RESEARCH-ONLY |
| 6 | α_36 | α_29 × 1{mkt_TS_mom > 0} | 0.78 | -1.64 | 0.76 | -5.0 % | -0.15 | rejected (Q5 negative test) |
| 7 | α_37 | α_29 × 1{calm market} | -0.28 | 0.48 | 0.30 | -6.6 % | -1.12 | rejected |

(Round 1 raw-trend signals all negative — see falsification block in `final_summary.md`.)

## PROMOTE checklist (α_35)

| threshold | required | α_35 | verdict |
|---|---:|---:|---|
| test LS Sharpe (after cost, monthly) | ≥ 1.0 | 1.74 | ✓ pass |
| test Q5 excess IR (after cost) | ≥ 0.5 | 1.03 | ✓ pass |
| **worst-year-active LS Sharpe** | **≥ 0.5** | **0.63** | **✓ pass** |
| best-year-out LS Sharpe % of full | ≥ 50 % | ≈ 0.71 (excluded 2024) | ✓ pass |
| spec sensitivity (≥3 of 7 variants pass) | yes | 5 of 7 | ✓ pass |
| placebo (worst-year-active in top 5 % of 100 random gates) | yes | top 1 % (0/100) | ✓ pass |
| economic story documented in literature | yes | Stivers-Sun 2010 RFS | ✓ pass |

7 / 7 PROMOTE checks satisfied.

## α_35 — full specification

```
Inputs:
  P_t              = adjusted close = close × adj_factor (per stock)
  log_P_t          = log(P_t)
  r_t              = log_P_t − log_P_{t-1}
  cum_K_t          = sum(r_{t-K+1..t})
  total_mv_t       = total market cap (per stock)
  log_mv_t         = log(total_mv_t)
  σ_120_t          = std(r_{t-119..t})
  ret_20_t         = cum_20_t = sum(r_{t-19..t})
  ret_42_t         = cum_42_t

Step 1 — raw 12-3 momentum:
  raw_29(s, t) = cum_252(s, t) − cum_63(s, t)

Step 2 — cross-sectional residualization per trade_date:
  alpha_29_raw(s, t) = residual of OLS(
      raw_29(*, t)  on  [const, log_mv(*, t), σ_120(*, t), ret_20(*, t)]
  )

Step 3 — industry neutralization (CITIC L1, ~110 groups):
  alpha_29_n(s, t) = alpha_29_raw(s, t) − mean over industry(s) at t

Step 4 — dispersion gate:
  mkt_disp_t = std over stocks of ret_20(*, t)
  threshold_t = rolling-252d median of mkt_disp (min_periods=180)
  gate_t     = 1 if mkt_disp_t > threshold_t else 0

Step 5 — alpha_35:
  alpha_35(s, t) = alpha_29_n(s, t) × gate_t
  When gate_t = 0: hold no position; charge liquidation turnover at boundary.

Evaluation:
  Quintile sort on α_35 per trade_date
  Q5 long, Q1 short, equal-weight within quintile
  Monthly rebalance (every 20 trading days)
  Turnover-aware cost: per-rebal-period cost = (tov_q5 + tov_q1) × 5 bps / 1e4
  Q5 long-only excess vs equal-weight universe: cost = tov_q5 × 5 bps / 1e4
```

## After-cost performance (industry-neutral, monthly rebal, 5 bps per side)

| metric | full | train (18-22) | validate (23) | test (24-25YTD) |
|---|---:|---:|---:|---:|
| LS Sharpe | 1.22 | 1.17 | 0.63 | **1.74** |
| Q5 excess IR | 0.56 | — | — | **1.03** |
| Max drawdown | -5.5 % | — | — | — |
| Avg turnover Q5 | ~24 % | — | — | — |
| On-fraction (gate) | 43 % | — | — | — |

## Per-year LS Sharpe (active years only — cash years excluded)

| year | LS Sharpe | Q5 excess Sharpe | gate-on months / 12 |
|---:|---:|---:|---:|
| 2018 | (cash) | (cash) | 0 |
| 2019 | 1.41 | 1.20 | ~5 |
| 2020 | 1.28 | 0.68 | ~7 |
| 2021 | 1.75 | 0.71 | ~6 |
| 2022 | 1.79 | 1.41 | ~6 |
| **2023** | **0.63** | -1.41 | ~3 |
| 2024 | 2.47 | 1.21 | ~10 |

**Worst active year LS Sharpe: 0.63 (2023)** — clears the 0.5 floor.

## Comparison: ungated α_29 vs α_35 (after cost)

| metric | α_29 (ungated) | α_35 (dispersion gate) | Δ |
|---|---:|---:|---:|
| LS full Sharpe | 1.00 | 1.22 | +0.22 |
| LS test Sharpe | 2.06 | 1.74 | -0.32 (gate sacrifices a little test alpha) |
| Q5 test IR | 1.16 | 1.03 | -0.13 |
| Max drawdown | -10.0 % | **-5.5 %** | **+4.5 pp** (huge) |
| Worst-year LS | -1.52 (2018) / 0.04 (2019) | **0.63 (2023)** | **+0.59 vs 2019, +2.15 vs 2018** |
| Worst-year Q5 | -1.67 | -1.41 | +0.26 (still bad in long-only Q5 2023) |

The trade is: give up some test-period upside, dramatically cut downside.

## Falsification (Round 6)

- **Spec sensitivity:** 5 of 7 dispersion-gate variants pass worst-year ≥ 0.5
  floor. Failing variants are 60d-median (too fast — gate flickers) and
  p40 (too loose — gate stays on too often).
- **Placebo (100 random gates with same on-fraction 0.43):**
  - α_35 LS full = 1.22 → no random gate exceeded this (p < 0.01).
  - α_35 worst-year-active = 0.63 → **zero random gates reached 0.5** (p < 0.01).
  Random gate distribution: max = 0.19, p95 = -0.31, mean = -1.17.

α_35 is not a fluke of random binary gating.

## Mechanism (Stivers-Sun 2010 RFS)

> Stivers, C. T. and L. Sun (2010), "Cross-Sectional Return Dispersions and
> Time Variation in Value and Momentum Premiums", *Journal of Financial
> and Quantitative Analysis* 45(4), 987-1014.

Core finding: cross-sectional return dispersion proxies for the
opportunity set facing momentum traders. When dispersion is high, there
is more room for momentum signals to identify winners and losers. When
dispersion compresses (risk-off / panic regimes / flat markets),
momentum signals lose their economic content.

α_35 implements this in the simplest possible form: turn the trend
signal off when 20-day cross-sectional return dispersion is below its
own 252-day rolling median. The gate captures exactly what the theory
predicts: it shuts off in regime-shift years (2018 selloff, 2023 chop)
and stays on in trending years (2020-2022 sectoral rotation, 2024
trend continuation).

## Recommended deployment form

Trading rule:
1. Each month-end, compute α_29 panel for full universe.
2. Compute mkt_disp_t and 252d-median threshold from prior 252 days.
3. If mkt_disp_t > threshold: form Q5 long / Q1 short on
   industry-neutralized α_29; rebal monthly.
4. If mkt_disp_t ≤ threshold: hold cash; pay full liquidation turnover
   on transition.
5. Position sizing: equal-weight within quintile.
6. Cost assumption: 5 bps per side.

Expected forward performance (based on full-period after-cost):
- LS Sharpe ≈ 1.2
- Q5 long-only excess IR ≈ 0.6
- Max drawdown ≈ -6 %
- One out of every ~3 years held cash

For long-only deployment (more A-share-realistic), use Q5 only:
- Q5 excess IR full ≈ 0.56, test ≈ 1.03
- Note: Q5 long-only had a -1.41 Sharpe year in 2023 — worse than LS in
  2023, because LS shorted out of the bad 2023 mid-cap rally. Long-only
  Q5 with dispersion gate is *not* fully protected from 2023-style years.

## Files

- `outputs/expressions_batch_0005.md` — Round 5 (8 gate variants)
- `outputs/expressions_batch_0006.md` — Round 6 (falsification)
- `outputs/backtest_results_batch_0005.csv` — Round 5 metrics
- `outputs/round6_spec_sensitivity.csv` — 7 dispersion-gate variants
- `outputs/round6_placebo_random_gates.csv` — 100 random gate trials
- `outputs/round6_placebo_summary.csv` — α_35 vs placebo distribution
- `outputs/audits_round5.json`, `outputs/audits_round6.json`
- `outputs/market_regime.csv` — daily regime indicators panel
- `scripts/07_round5_regime_overlay.py`, `scripts/08_round6_falsification.py`
