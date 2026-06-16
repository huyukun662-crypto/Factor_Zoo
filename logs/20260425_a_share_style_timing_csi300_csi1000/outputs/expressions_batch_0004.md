# Expressions Batch 0004 (R4) — Agent 3 (Alpha Builder)

**Mechanism family**: M3_regime_conditioned (refinement of R3 E4)
**Declared horizon**: 20 trading days
**Thesis sign**: +1 (regime-weighted M3 momentum after negation)
**Rule of 8**: 8 expressions submitted ✓
**Anti-clone vs R1 vol-spread**: max |corr| = 0.21 ✓
**Anti-clone vs R2 E1 (level cluster)**: max |corr| = 0.39 ✓
**Correlation with R3 E4 (base mechanism)**: NOT capped — regime-conditioned variants of R3 E4 by design. The test of value-add is whether R4 winner's worst-year Sharpe (esp. 2025) exceeds R3 E4's −1.19.

| # | Name | Construction | Distinct dimension |
|---|---|---|---|
| 1 | `r4_e1_e4_x_volgate_tanh_t1` | E4 × tanh(vol_spread_z / 1.0) | smooth two-sided gate, T=1 |
| 2 | `r4_e2_e4_x_volgate_tanh_t2` | E4 × tanh(vol_spread_z / 2.0) | softer gate, T=2 |
| 3 | `r4_e3_e4_x_turnoverlevel_tanh` | E4 × tanh(R2_turnover_z / 1.5) | turnover-level as regime |
| 4 | `r4_e4_e4_x_volgate_oneside` | E4 × max(0, tanh(vol_spread_z)) | **one-sided gate** (never flips) |
| 5 | `r4_e5_e4_x_composite_regime` | E4 × tanh((vol_z + turnover_z)/2 / 1.5) | composite vol+turnover regime |
| 6 | `r4_e6_e2_x_volgate_tanh_t1` | E2 × tanh(vol_spread_z / 1.0) | gate on E2 (5/60) base, robustness |
| 7 | `r4_e7_e4_monthly_rebalance` | E4 with 20d signal-discretization | **rebalance-frequency variant** (monthly) |
| 8 | `r4_e8_e4_x_market_60d_gate` | E4 × tanh(z(60d log-return idx1000)) | bull/bear market regime gate |

## Pre-registered honesty bars (from session_metadata.yml round_0004)

This is the **fourth** round on the same TEST window. Multiple-comparisons
risk now spans 32 expressions. R4 PROMOTE bar pre-registered TIGHTER than R3:

- test IC t-stat ≥ **4.0** (vs R3's 3.5, R1/R2's 3.0)
- worst-year Sharpe ≥ **0.7**
- economic story coherent with R1+R2+R3 findings (regime-conditional momentum)
- **R4 winner test Sharpe must exceed R3 E4's +0.58** (raw improvement, not just survive audits)

## Sanity-check matrix (TRAIN, ~870-892 days)

### Anti-clone vs R1 raw vol-spread

| Expr | corr |
|---|---:|
| r4_e1 | +0.04 |
| r4_e2 | +0.03 |
| r4_e3 | −0.09 |
| r4_e4 | +0.02 |
| r4_e5 | −0.02 |
| r4_e6 | +0.08 |
| r4_e7 | −0.21 |
| r4_e8 | +0.05 |

All easily clear `< 0.85`.

### Anti-clone vs R2 E1 (level cluster)

| Expr | corr |
|---|---:|
| r4_e1 | −0.03 |
| r4_e2 | −0.02 |
| r4_e3 | +0.16 |
| r4_e4 | −0.14 |
| r4_e5 | +0.11 |
| r4_e6 | −0.02 |
| r4_e7 | −0.39 |
| r4_e8 | +0.04 |

All clear `< 0.85`. R4 is genuinely orthogonal to R1+R2 levels.

### Correlation with R3 E4 (base, expected high for non-discretized variants)

| Expr | corr | Interpretation |
|---|---:|---|
| r4_e1 | −0.18 | smooth two-sided gate FLIPS sign in calm regimes → low overall corr |
| r4_e2 | −0.18 | softer gate, similar pattern |
| r4_e3 | +0.20 | turnover-z gate: aligned with E4 in turnover-rising regimes |
| r4_e4 | +0.56 | one-sided gate: E4 dampened, never flipped |
| r4_e5 | −0.03 | composite gate flips/dampens, low overall corr |
| r4_e6 | −0.14 | E2 base differs from E4 base, plus gate |
| r4_e7 | **+0.76** | monthly rebalance: same signal held for 20d at a time |
| r4_e8 | +0.43 | market-return gate aligned with E4 in trending markets |

Note: low corr with R3 E4 for E1/E2/E5 is BY DESIGN — the smooth gate
flips the sign in low-vol regimes. The correlation drop is the visible
sign that the regime-conditioning is functional.

E7 (monthly rebalance) signal-change count on TRAIN: 42 over 853 days =
~1 change per 20 days, matching the 20d discretization period exactly.

## Rationale per expression

### E1 `r4_e1_e4_x_volgate_tanh_t1`
**Primary R4 lead**. Smooth tanh gate on R1 vol-spread z with
temperature 1.0. When small-cap vol is unusually elevated (z > 0,
"high-attention" regime), the M3 momentum signal is amplified.
When small-cap is calm relative to large-cap (z < 0), the signal
flips toward the M2 mean-reversion direction. Tests whether 2025's
M3 failure was specifically a calm-regime event.

### E2 `r4_e2_e4_x_volgate_tanh_t2`
Softer version of E1 (temperature 2.0). Less aggressive flipping;
relies more on the M3 base signal across regimes. Tests
gate-temperature sensitivity.

### E3 `r4_e3_e4_x_turnoverlevel_tanh`
Same gate STRUCTURE as E1 but uses R2's turnover-level z as the
regime indicator instead of R1's vol-spread z. Tests whether
turnover-level (R2 narrative) or vol-state (R1 narrative) is the
better regime indicator for M3.

### E4 `r4_e4_e4_x_volgate_oneside`
One-sided gate: amplifies E4 in elevated-vol regimes but does NOT
flip it in calm regimes (just dampens toward 0). Tests the
hypothesis that 2025's failure was a **flip** of M3 (rescue-able
by sign-flipping gate, E1 should help) vs a **shrinkage** of M3
(unrescuable; E4 one-sided would do better than E1).

### E5 `r4_e5_e4_x_composite_regime`
Composite regime: average of R1 vol-spread z and R2 turnover-level z.
Tests whether combining M1+M2 regime info gives a more robust gate
than either alone.

### E6 `r4_e6_e2_x_volgate_tanh_t1`
Same gate as E1 but on R3 E2 base (5/60 windows, more responsive
than 5/120). Tests whether the regime-conditioning effect is robust
across different M3 base specifications, or specific to E4.

### E7 `r4_e7_e4_monthly_rebalance`
**Rebalance-frequency variant**: R3 E4 signal sampled every 20d and
held. No regime gate. Tests purely whether matching the rebalance
frequency to the peak-IC horizon improves Sharpe via cost reduction
(daily ~150 bps/yr → monthly ~30 bps/yr at 5 bps/side × 2 legs).

### E8 `r4_e8_e4_x_market_60d_gate`
Bull/bear market regime gate. When trailing 60d log-return of CSI1000
is positive (uptrend), M3 momentum amplified; when negative (downtrend),
flipped. Tests whether market direction is the relevant regime axis.

## Fragility notes

- E1, E2, E5 share the vol-spread z computation — bug in vol-spread propagates to 3 expressions.
- E3, E5 share turnover-level z — same risk on that side.
- E7 is the ONLY expression that doesn't depend on regime indicators; if M3 mechanism itself isn't working, E7's monthly rebalance won't save it. E7 is the cleanest "is the signal real even with cost reduction?" test.
- All gated expressions (E1-E6, E8) have lower stdev than E4 base (~0.43-0.74 vs ~1.05 for E7). The gate compresses the signal; combined with deadband=0.5, this means MORE flat days. Need to verify G3 non-zero fraction stays above 30%.

## Expected gate-effect on 2025 specifically

R3 E4's 2025 Sharpe was −1.19. If the regime-conditioning works:
- E1 (two-sided tanh): expects 2025 to be IMPROVED (signal flips in calm regime, possibly catching mean-reversion right)
- E4 (one-sided): expects 2025 to be NEUTRAL/SLIGHTLY-LESS-NEGATIVE (signal dampened toward 0, not loss-making)
- E7 (monthly rebal): 2025 unchanged in direction, slightly less negative due to lower cost

If 2025 stays negative across ALL 8, the regime-flip hypothesis is wrong — the M3 mechanism just stopped working in 2025 across regimes.
