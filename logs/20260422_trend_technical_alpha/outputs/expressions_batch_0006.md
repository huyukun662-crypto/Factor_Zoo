# Expressions Batch 0006 — Falsification of α_35

**Session:** `20260422_trend_technical_alpha`
**Author:** Agent 3 — Alpha Builder

Round 5 produced α_35 (= α_29 × dispersion gate) with all-active worst-year
LS Sharpe 0.63, the first alpha in this session to clear the 0.5 floor.
Round 6 stress-tests it before declaring PROMOTE.

## Spec sensitivity (7 dispersion-gate variants)

For each spec, compute `mkt_disp(t) = cross-sectional std of ret_20 across
stocks at t`. Gate on when `mkt_disp(t) > threshold(t)`. Test 7 thresholds:

| spec | threshold definition |
|---|---|
| baseline_252d_med | rolling 252d median of `mkt_disp` |
| 60d_med | rolling 60d median |
| 126d_med | rolling 126d median |
| 504d_med | rolling 504d median |
| 252d_p40 | 40th percentile over 252d window |
| 252d_p60 | 60th percentile over 252d window |
| 252d_p70 | 70th percentile over 252d window |

Pass criterion per spec: `worst_year_active ≥ 0.5` AND `ls_test ≥ 1.0` AND
`q5_test ≥ 0.5`.

## Placebo test

Generate 100 random binary gates with on-fraction matched to α_35 baseline
(0.43). For each, run the same gated backtest. Compare α_35 metrics against
the placebo distribution. Reject the dispersion mechanism if α_35 falls
within the 95th percentile of placebo metrics.

## Decision logic

PROMOTE α_35 only if:
1. ≥ 3 of 7 spec variants pass joint criteria (robustness)
2. α_35 baseline metrics fall in the top 5 % of placebo distribution
   for both `ls_full` and `worst_year_active`
3. The economic story (high dispersion → momentum premium) is documented
   in Stivers-Sun (2010 RFS) or equivalent — not a data-mined story
