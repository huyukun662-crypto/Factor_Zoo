# Expressions Batch 0002 (R2) — Agent 3 (Alpha Builder)

**Mechanism family**: M2_turnover_divergence (pivot from R1 M1)
**Declared horizon**: 5 trading days
**Thesis sign of IC vs forward 5d spread return**: +1 (high small-cap turnover share → favour 300)
**Rule of 8**: 8 expressions submitted ✓
**Standardization convention**: same as R1 — each expression outputs a 252d
rolling z-score; engine deadband=0.5.
**Anti-clone vs R1**: build directive required `|corr| < 0.85` with the
R1 vol-spread. **All 8 R2 expressions clear this with |corr| ≤ 0.48 on TRAIN**
(table below). M2 is not just M1 in disguise.

| # | Name | Construction | Distinct dimension |
|---|---|---|---|
| 1 | `r2_e1_log_amount_ratio_20d`     | `z(MA20(log(amt1000/amt300)))` | level, smoothed |
| 2 | `r2_e2_log_amount_ratio_5d`      | `z(MA5(log(amt1000/amt300)))` | faster level |
| 3 | `r2_e3_abnormal_amount_1000`     | `z(log(MA5(amt1000)/MA60(amt1000)))` | small-cap acceleration only |
| 4 | `r2_e4_abnormal_amount_spread`   | `z(abnormal(1000) − abnormal(300))` | acceleration spread |
| 5 | `r2_e5_log_amount_ratio_z504`    | same raw as E1, z over 504d | longer regime baseline |
| 6 | `r2_e6_amount_resid_vs_vol_spread` | `z(MA20(resid log_amt | log_vol))_1000 − same_300` | flow net of mechanical vol-driven trading |
| 7 | `r2_e7_log_amount_accel_spread`  | `z((MA5−MA20)(log_amt_1000) − same_300)` | second-derivative (accel) spread |
| 8 | `r2_e8_amount_share_1000`        | `z(MA20(amt1000/(amt1000+amt300)))` | flow share, bounded [0,1] |

## Sanity-check matrix (TRAIN, 906 days)

### Anti-clone vs R1 raw vol-spread

| Expr | corr(score, vol_spread_z) | Status |
|---|---:|:-:|
| r2_e1 | +0.47 | ✓ |
| r2_e2 | +0.42 | ✓ |
| r2_e3 | −0.17 | ✓ (most independent of vol) |
| r2_e4 | +0.14 | ✓ |
| r2_e5 | +0.48 | ✓ |
| r2_e6 | +0.35 | ✓ (residualization works) |
| r2_e7 | −0.01 | ✓ (orthogonal) |
| r2_e8 | +0.47 | ✓ |

E3 and E7 are nearly orthogonal to vol-spread → these are the cleanest
M2-only signals. E6 (residualized) sits between, as expected.

### R2-internal pairwise correlation

| | E1 | E2 | E3 | E4 | E5 | E6 | E7 | E8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **E1** | 1.00 | 0.88 | 0.03 | 0.37 | 0.92 | 0.83 | 0.02 | 1.00 |
| **E2** |  | 1.00 | 0.13 | 0.66 | 0.79 | 0.77 | 0.47 | 0.88 |
| **E3** |  |  | 1.00 | 0.16 | -0.01 | 0.23 | 0.21 | 0.03 |
| **E4** |  |  |  | 1.00 | 0.22 | 0.50 | 0.78 | 0.37 |
| **E5** |  |  |  |  | 1.00 | 0.67 | -0.04 | 0.91 |
| **E6** |  |  |  |  |  | 1.00 | 0.13 | 0.83 |
| **E7** |  |  |  |  |  |  | 1.00 | 0.02 |
| **E8** |  |  |  |  |  |  |  | 1.00 |

Three clusters visible:
- **Level cluster**: E1, E5, E8 (and weakly E2, E6) — corr ≥ 0.83
- **Acceleration cluster**: E4, E7 (corr 0.78); E3 sits adjacent (corr 0.16-0.21)
- **Residualized**: E6 spans both clusters (0.83 with E1, 0.50 with E4)

E8 ≈ E1 (corr 1.00) by construction: `share = ratio/(1+ratio)` is a
near-monotone bijection in the observed range. Kept as a robustness
sanity-check pair rather than dropped.

## Rationale per expression (one-paragraph each)

### E1 `r2_e1_log_amount_ratio_20d`
Cleanest expression of M2: ratio of CNY-amounts traded on the small-cap
index vs large-cap index, log-transformed for symmetric handling, smoothed
over 20d, z-scored over 252d. Positive z = small-cap is consuming an
unusually large share of broad-base trading flow vs the past year.

### E2 `r2_e2_log_amount_ratio_5d`
Same as E1 with 5d smoothing instead of 20d. Faster, noisier. Tests
whether fast attention shifts predict the 5d horizon better than the
month-scale level.

### E3 `r2_e3_abnormal_amount_1000`
Small-cap acceleration only: `log(MA5/MA60)` of `amount_1000`.
Captures whether small-cap trading is accelerating relative to its own
2-month baseline, ignoring large-cap entirely. Most-orthogonal to
vol-spread (corr −0.17), so this is M2 in its purest form.

### E4 `r2_e4_abnormal_amount_spread`
Acceleration spread: same as E3 but for both legs, then take
1000-minus-300 difference. Removes any market-wide flow regime
(e.g. holiday weeks where ALL turnover is low).

### E5 `r2_e5_log_amount_ratio_z504`
Same raw signal as E1 but z over 504d (~2y) instead of 252d. Captures
*longer* regime shifts in style-flow concentration; less sensitive to
recent-year noise.

### E6 `r2_e6_amount_resid_vs_vol_spread`
Flow net of mechanical vol-driven trading. Rolling beta-residualizes
log(amount) vs log(realized_vol(20d)) for each leg, then takes the
spread of residual log-amounts. This is the audit-cleanest answer to
"is M2 just M1 in disguise?": it strips out the linear vol component
before computing the spread.

### E7 `r2_e7_log_amount_accel_spread`
Second-derivative cross: `(MA5 − MA20)` of log-amount on each leg,
then 1000-minus-300. Most decorrelated from vol-spread (corr −0.01).

### E8 `r2_e8_amount_share_1000`
Flow share: `amount_1000 / (amount_1000 + amount_300)`. Bounded [0,1],
interpretable as fraction of broad-base trading captured by small-cap.
Empirically near-identical to E1 in z-score space (corr 1.00 on
TRAIN); kept as robustness check on the ratio formulation.

## Expected turnover direction

Same as R1: with deadband=0.5 on rolling-z-score signals, most
expressions will sit at zero ~60% of trading days. Expected annual
turnover 50%-300%, well within the [10%, 2000%] G3 budget.

## Fragility notes

- E1, E5, E8 share the same numerator (log ratio) — one bug, three fail.
- E3, E4, E7 are all "acceleration" variants — sensitive to MA window
  choice; if MA5 is too short, signal dominated by single-day amount
  spikes.
- E6 depends on the residualization regression being well-conditioned;
  during very low-vol periods the regression is near-singular and
  residuals become noisy. min_periods=60 on the rolling window
  guards against this but does not eliminate it.
