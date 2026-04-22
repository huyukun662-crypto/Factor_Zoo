# Expressions Batch 0003 — Idio Trend, Robustness Variants

**Session:** `20260422_trend_technical_alpha`
**Author:** Agent 3 — Alpha Builder

Round 2 established that **idiosyncratic momentum exists** in A-share once
{log_mv, σ_120, ret_20} are stripped. α_15 (idio 12-1) had IC +0.022,
t-stat 8.6, test LS Sharpe 0.88 — but worst year -0.10 fails the 0.5 floor.
α_12 (idio MA-crossover) had LS 1.02 full but worst year 0.40, also failing.

Round 3 tests whether targeted modifications can lift either alpha above the
audit floor: universe filter, industry-relative momentum, skip length,
horizon length, combos.

All expressions are residualized cross-sectionally per `trade_date` against
{log_mv, σ_120, ret_20} unless otherwise noted, then industry-neutralized at
evaluation. Same 5-bps turnover-aware cost, monthly rebalance.

## α_17 — large-cap idio_12_1
α_15 evaluated on the universe filtered to `total_mv ≥ median(total_mv per date)`.
Tests whether the worst-year drag was driven by micro-cap reversal noise.

## α_18 — industry-relative idio_12_1
For each (stock, date), `ret_252_ind = ret_252 - mean(ret_252 within industry, date)`,
then `ind_skip = ret_252_ind − ret_20_ind`, then cs-residualize vs
{log_mv, σ_120, ret_20}. Tests whether industry-relative momentum is the
true signal vs stock-level momentum.

## α_19 — longer skip (12-2 momentum)
`raw_19 = cum_252 − cum_42` (skip 42 days instead of 21), then cs-residualize
vs {log_mv, σ_120, ret_42}. Tests whether a longer skip-window removes more
short-term reversal contamination.

## α_20 — long-window momentum (24-1)
`raw_20 = cum_504 − cum_21` (2-year minus 1-month), then cs-residualize vs
{log_mv, σ_120, ret_20}. Tests whether multi-year momentum is more robust to
1-year regime cycles.

## α_21 — combo (z-mean of α_12 + α_15)
Per date, equal-weighted z-score average of α_12 and α_15.

## α_22 — combo (33/33/33 z-mean of α_11 + α_12 + α_15)
Per date, equal-weighted z-score average of three positive-IC idio signals.

## α_23 — 6-1 momentum idio
`raw_23 = cum_126 − cum_21` (6-month minus 1-month), cs-residualize vs
{log_mv, σ_120, ret_20}. Shorter horizon than 12-1.

## α_24 — 9-1 momentum idio
`raw_24 = cum_189 − cum_21` (9-month minus 1-month), cs-residualize. Halfway
between 6-1 and 12-1.

## Decision logic
- If any α_17..α_24 achieves test LS Sharpe ≥ 1.0 AND worst-year ≥ 0.5 AND
  test q5_excess IR ≥ 0.5 AND residual IC ≥ 30 % of raw IC: candidate for
  PROMOTE. Otherwise full-family RESEARCH-ONLY.
- Honest reporting: any improvement vs Round 2 is logged, even if below
  PROMOTE thresholds.
