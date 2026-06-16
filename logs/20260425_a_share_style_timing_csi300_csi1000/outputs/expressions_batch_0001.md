# Expressions Batch 0001 — Agent 3 (Alpha Builder)

**Mechanism family**: M1_volatility_regime
**Declared horizon**: 5 trading days
**Thesis sign of IC vs forward 5d spread return**: +1
**Rule of 8**: 8 expressions submitted ✓
**Standardization convention**: each expression outputs a 252-day rolling
z-score; the engine maps `z > +0.5 → +1`, `z < −0.5 → −1`, else `0`. This
keeps turnover comparable across the 8 variants and avoids day-to-day
churn on noise.

| # | Name | Construction | Distinct dimension |
|---|---|---|---|
| 1 | `r1_e1_volspread_20d` | `z(σ20(r1000) − σ20(r300))` | baseline |
| 2 | `r1_e2_volratio_20d` | `z(σ20(r1000)/σ20(r300) − 1)` | scale-free ratio |
| 3 | `r1_e3_logvolratio_20d` | `z(log σ20(r1000)/σ20(r300))` | symmetric in log |
| 4 | `r1_e4_volspread_10d` | `z(σ10(r1000) − σ10(r300))` | faster window |
| 5 | `r1_e5_volspread_20d_z504` | same raw as E1, z over 504d | longer regime baseline |
| 6 | `r1_e6_downvolspread_20d` | `z(σ20⁻(r1000) − σ20⁻(r300))` | downside-only (panic) |
| 7 | `r1_e7_vol_accel_spread` | `z((σ5−σ20)(r1000) − (σ5−σ20)(r300))` | vol acceleration spread |
| 8 | `r1_e8_volspread_longbaseline` | `z((σ20(r1000)−σ20(r300))/mean252(σ20(r300)))` | spread vs long-run baseline |

`σN(·) = rolling realized vol of daily log returns over N days`.
`σN⁻(·) = downside vol (returns clipped at 0)`.
`z(·) = (x − rolling_mean(x, 252)) / rolling_std(x, 252)`, with
`min_periods=60` to allow signal during the warm-up window.

---

## Rationale per expression (one paragraph each)

### E1 `r1_e1_volspread_20d`
Cleanest expression of M1: take 20-day realized vol of each leg, take the
difference, z-score over a 252-day rolling window. Positive z means the
small-cap leg is unusually more volatile than the large-cap leg
*relative to the recent year* — the regime-relative trigger for
risk-off rotation. Expected turnover: moderate (z swings through ±0.5
band a few times per year).

### E2 `r1_e2_volratio_20d`
Scale-free version: `(σ20_1000 / σ20_300) − 1`. Useful when absolute vol
levels drift over the cycle (e.g. 2018 vs 2024). The minus-1 centres the
ratio at zero. Expected turnover: similar to E1.

### E3 `r1_e3_logvolratio_20d`
Same as E2 but in log space → symmetric handling of "1000 is 50% more
volatile than 300" vs "300 is 50% more volatile than 1000". Should
produce IC very close to E2 for moderate spreads but diverge in tail
events. Expected turnover: similar to E2.

### E4 `r1_e4_volspread_10d`
Faster vol window (10d). Two effects: (a) reacts to vol shocks within
~5 trading days vs ~10 for E1, (b) higher day-to-day noise → likely
higher turnover. The 10d horizon is closer to the 5d declared horizon —
if M1 is real and mean-reverts on a 1-2 week clock, E4 may have the
strongest IC. Expected turnover: higher than E1.

### E5 `r1_e5_volspread_20d_z504`
Same raw spread as E1 but z-scored over 504 days (~2 years). Captures
*longer* regime shifts and is less sensitive to recent-year noise. If
the 2024-Q1 micro-cap panic was a regime change, E5 will register it as
extreme; if it was just noise within the long-run distribution, it
won't. Expected turnover: lower than E1 (smoother z).

### E6 `r1_e6_downvolspread_20d`
Asymmetric: only the downside semivariance is used. The thesis is that
risk-off rotation is triggered by *down-side* small-cap vol, not by
upside. Expected to outperform E1 in panic regimes (2018Q4, 2020Q1,
2024Q1) and underperform in choppy bidirectional regimes. Expected
turnover: similar to E1.

### E7 `r1_e7_vol_accel_spread`
Vol acceleration: `(σ5 − σ20)(1000) − (σ5 − σ20)(300)`. Positive when
small-cap vol is rising faster than large-cap vol, *relative to its own
20d trend*. This is essentially a second-derivative signal — orthogonal
to E1 by construction (correlation ~0 on training data confirms). If
the M1 mechanism works through vol *change* rather than vol *level*,
E7 will outperform; if through level, it will underperform.

### E8 `r1_e8_volspread_longbaseline`
Spread normalized by the long-run baseline of large-cap vol:
`(σ20_1000 − σ20_300) / mean252(σ20_300)`. Distinguishes "absolute
spread that is large vs typical market vol regime" from "spread that is
relatively large given current contemporary vol level" (which E2/E3
test). Expected turnover: similar to E1.

---

## Pairwise correlation on TRAIN

| | E1 | E2 | E3 | E4 | E5 | E6 | E7 | E8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **E1** | 1.00 | 0.89 | 0.91 | 0.76 | 0.96 | 0.84 | -0.02 | 0.99 |
| **E2** | | 1.00 | 0.99 | 0.67 | 0.85 | 0.71 | -0.04 | 0.88 |
| **E3** | | | 1.00 | 0.69 | 0.87 | 0.73 | -0.04 | 0.90 |
| **E4** | | | | 1.00 | 0.72 | 0.68 | 0.33 | 0.76 |
| **E5** | | | | | 1.00 | 0.80 | -0.03 | 0.96 |
| **E6** | | | | | | 1.00 | 0.02 | 0.82 |
| **E7** | | | | | | | 1.00 | -0.01 |
| **E8** | | | | | | | | 1.00 |

E7 (vol acceleration) is the most decorrelated of the batch — it tests a
fundamentally different M1 sub-mechanism (vol *change* vs vol *level*).
E1/E5/E8 cluster tightly (corr ≥ 0.96) — they probe the same basic
"absolute vol-level spread" with different normalizations. E2/E3 cluster
(corr 0.99) — log vs ratio in the same baseline. This batch is
construction-distinct (8 different math ops) but signal-clustered into
~3 groups; Agent 5 should weight cluster diversity when interpreting
TVT scores.

## Expected turnover direction

All eight: lower than a no-deadband momentum factor on the same data,
because the |z| > 0.5 deadband forces the position to remain at zero
~60% of trading days during normal regimes. We expect annual turnover
in the 50%-300% range across the batch — comfortably inside the [10%,
2000%] G3 budget.

## Fragility notes per expression

- E1, E5, E8 share the same raw signal up to normalization → if the raw
  signal has a bug, three expressions fail together.
- E2, E3 share the ratio numerator → if the small-cap vol estimator is
  biased (e.g. by a market halt day), both fail.
- E7 is the only expression that may have a peak |IC| at h=1 rather
  than h=5 (acceleration signals tend to be faster). If G5 fails because
  4+ expressions peak at h=1, escalate to Agent 2 for horizon revision.
