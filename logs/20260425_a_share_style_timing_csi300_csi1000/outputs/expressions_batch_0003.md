# Expressions Batch 0003 (R3) — Agent 3 (Alpha Builder)

**Mechanism family**: M3_turnover_acceleration_momentum (pivot from R2 anti-thesis finding)
**Declared horizon**: 5 trading days
**Thesis sign of IC vs forward 5d spread return**: +1
**Standardization**: 252d rolling z-score, deadband 0.5 (engine).
**Negation at source**: every expression returns `-z(...)` so positive
score = "expect favour 300", consistent with the convention since R1.
**Rule of 8**: 8 expressions submitted ✓
**Anti-clone vs R1 vol-spread**: max |corr| = 0.227 ✓ (< 0.85)
**Anti-clone vs R2 E1 (level cluster)**: max |corr| = 0.339 ✓ (< 0.85)

| # | Name | Construction | Distinct dimension |
|---|---|---|---|
| 1 | `r3_e1_amt_accel_5_20_neg`           | `-z(log(MA5/MA20)(amt_1000))`             | fast / fast baseline |
| 2 | `r3_e2_amt_accel_5_60_neg`           | `-z(log(MA5/MA60)(amt_1000))`             | **R2 E3 negated** — primary lead |
| 3 | `r3_e3_amt_accel_10_60_neg`          | `-z(log(MA10/MA60)(amt_1000))`            | slower numerator |
| 4 | `r3_e4_amt_accel_5_120_neg`          | `-z(log(MA5/MA120)(amt_1000))`            | longest baseline (~5mo) |
| 5 | `r3_e5_amt_accel_spread_5_20_neg`    | `-z((MA5/MA20)(amt_1000) − same(amt_300))`| spread, fast |
| 6 | `r3_e6_amt_accel_spread_5_60_neg`    | `-z((MA5/MA60)(amt_1000) − same(amt_300))`| spread, medium |
| 7 | `r3_e7_vol_accel_spread_5_60_neg`    | `-z((MA5/MA60)(vol_1000) − same(vol_300))`| **VOLUME-derived** spread |
| 8 | `r3_e8_accel_high_vol_regime`        | `-z(log(MA5/MA60)(amt_1000))` gated by `R1 vol_spread_z > 0` | **regime-conditioned** |

## Sanity-check matrix (TRAIN, 906-967 days depending on min_periods)

### Anti-clone vs R1 vol-spread (raw construction, NOT R1 E1's negated form)

| Expr | corr |
|---|---:|
| r3_e1 | +0.227 |
| r3_e2 | +0.169 |
| r3_e3 | +0.143 |
| r3_e4 | −0.016 |
| r3_e5 | +0.032 |
| r3_e6 | −0.140 |
| r3_e7 | −0.208 |
| r3_e8 | +0.165 |

All clear `< 0.85`. The spread variants (E5-E7) and the long-baseline E4
are most decorrelated.

### Anti-clone vs R2 E1 (turnover-level cluster)

| Expr | corr |
|---|---:|
| r3_e1 | +0.086 |
| r3_e2 | −0.004 |
| r3_e3 | −0.023 |
| r3_e4 | −0.237 |
| r3_e5 | +0.001 |
| r3_e6 | −0.339 |
| r3_e7 | −0.281 |
| r3_e8 | −0.026 |

All clear `< 0.85`. R3 is genuinely orthogonal to the R2 level cluster.

### R3-internal pairwise correlation

| | E1 | E2 | E3 | E4 | E5 | E6 | E7 | E8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **E1** | 1.00 | 0.74 | 0.57 | 0.56 | 0.29 | 0.14 | -0.01 | 0.40 |
| **E2** |  | 1.00 | 0.96 | 0.87 | 0.23 | 0.20 |  0.03 | 0.67 |
| **E3** |  |  | 1.00 | 0.86 | 0.21 | 0.21 |  0.05 | 0.66 |
| **E4** |  |  |  | 1.00 | 0.24 | 0.31 |  0.14 | 0.56 |
| **E5** |  |  |  |  | 1.00 | 0.77 |  0.70 | 0.16 |
| **E6** |  |  |  |  |  | 1.00 |  0.92 | 0.17 |
| **E7** |  |  |  |  |  |  |  1.00 | 0.03 |
| **E8** |  |  |  |  |  |  |  | 1.00 |

Three sub-groups visible:
- **Single-leg amount accel**: E1, E2, E3, E4 (corr 0.56-0.96)
- **Spread-of-accel cluster**: E5, E6, E7 (corr 0.70-0.92), with E7
  being the volume-derived sibling of E6
- **Regime-conditioned**: E8 — correlated with E2/E3 single-leg
  cluster (~0.67) but ~0 with the spread cluster

E8 active fraction (`gate > 0`): 44.78% of TRAIN days — close to the
expected ~50% from a zero-mean rolling-z regime indicator.

## Rationale per expression (one-paragraph each)

### E1 `r3_e1_amt_accel_5_20_neg`
Faster baseline (20d) than the R2 E3 it replaces. Tests whether tightening
the reference window preserves the momentum signal. Expected to react more
to short-term attention bursts; may have higher turnover.

### E2 `r3_e2_amt_accel_5_60_neg`
**Primary R3 lead**: this is exactly R2 E3 with the score negated.
R2 E3 had TRAIN IC = −0.196, t = −5.93; if the relationship is real
and stable, E2 should have +0.196 IC on TRAIN with the same magnitude.

### E3 `r3_e3_amt_accel_10_60_neg`
Slower numerator (10d MA instead of 5d). Trades off responsiveness for
noise reduction. Expected IC slightly lower than E2 if M3 mechanism is
truly fast.

### E4 `r3_e4_amt_accel_5_120_neg`
Longest baseline (~5 months). Tests the regime baseline at the limit
of "still meaningful for a 5d momentum signal". Risk: too-long baseline
washes out faster regime shifts.

### E5 `r3_e5_amt_accel_spread_5_20_neg`
Spread of accelerations (1000−300) on the fast windows. Removes any
market-wide attention regime (e.g. holiday lulls). Most-decorrelated
with R1 vol-spread (corr +0.032).

### E6 `r3_e6_amt_accel_spread_5_60_neg`
Spread version on E2's windows. The cleanest "small-cap-specific
attention acceleration" signal.

### E7 `r3_e7_vol_accel_spread_5_60_neg`
Volume (shares traded) instead of amount (CNY). Tests whether the M3
signal is in CNY-flow (price × shares) or in raw share volume. CNY-flow
embeds price information; share volume is closer to "number of trades".

### E8 `r3_e8_accel_high_vol_regime`
Regime-conditional: takes the E2 acceleration signal but gates it to
zero whenever the R1 raw vol-spread z-score is ≤ 0. Tests whether the
acceleration signal is concentrated in elevated-vol regimes (which
would explain why R1 E4's stable test years aligned with elevated-vol
2024 episodes).

## Expected turnover direction

E1, E5: higher turnover (faster windows).
E4: lower turnover (longest baseline).
E8: lower non-zero fraction (~45%) but normal turnover when active.
Others: moderate.

## Fragility notes

- E2, E3 share MA60 baseline — both fail if 60d MA estimator has a bug.
- E5, E6, E7 share the spread-of-accel form — sensitive to single-day
  amount/vol spikes on either leg.
- E8 depends on the R1 vol-spread construction; if R1 E1's raw form
  has a bug it propagates here. (E1's raw is reproduced fresh inside
  E8's _gen, not imported, to keep independence.)
- E1 is the most independent from the rest of the batch (its 5/20
  windows differ from everyone else's 5/60 or 5/120).

## Pre-registered honesty bar (per session_metadata.yml round_0003)

This is the THIRD round on the same TEST window. Multiple comparisons
across 24 expressions on the same test set inflates false-positive
risk. Stage 5 R3 PROMOTE-eligibility is pre-registered with TIGHTER
floors than R1/R2:

- test IC t-stat ≥ **3.5** (vs standard 3.0)
- worst-year Sharpe ≥ **0.7** (vs standard 0.5)
- economic story consistent with both R1 and R2 findings

These are committed BEFORE Stage 4 runs, in
`outputs/session_metadata.yml#round_0003.multiple_comparisons_bar`.
