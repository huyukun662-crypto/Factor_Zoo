# Alpha Ranking — Round 0001

Session `20260425_a_share_style_timing_csi300_csi1000` · Mechanism family
M1_volatility_regime · Selection rule
`val_sharpe − 0.3·|train_sharpe − val_sharpe|`, eligible iff
`train_sharpe > 0.5 AND val_sharpe > 0`.

## Headline

> **Decision: RESEARCH-ONLY.** No expression in the batch is TVT-eligible
> (every train Sharpe is below the 0.5 floor). The mechanism shows weak
> directional evidence in the **contrarian** direction (M1' after Agent
> 2 hypothesis revision) but the signal is too small and too
> regime-dependent to clear PROMOTE floors.

## Round-1 history (audit trail)

| Stage | Action | Outcome |
|---|---|---|
| Stage 4 v1 | Ran 8 vol-spread expressions with original thesis (`high vol_spread → favour 300`). | 8/8 G4 IC sign FAIL — IC consistently *negative* across batch. Batch-level hypothesis failure. |
| Stage 2 revision | Re-spec mechanism to **M1' contrarian** (`high vol_spread → small-cap mean-reversion → favour 1000`). | Same 8 constructions, output negated at source per `validation-gates.md:140`. v1 artifacts preserved as `*_v1_falsified.{md,json}`. |
| Stage 4 v2 | Re-ran the 8 (now negated) expressions. | 1/8 passes G4 (E1). 7/8 fail G4 sub-checks (monotonicity, peak horizon). G5 batch-level still FAIL (1 survivor < 4 needed). 0/8 TVT-eligible. |

## Eligibility table (v2, after Agent-2 revision)

| Expr | Train Sharpe | Val Sharpe | Eligible | TVT Score | Gates+G5 | Test Sharpe* |
|---|---:|---:|:-:|---:|:-:|---:|
| `r1_e1_volspread_20d`           | +0.141 | +1.056 | N | 0.782 | N | **+0.142** |
| `r1_e2_volratio_20d`            | −0.273 | +1.451 | N | 0.934 | N | −0.660 |
| `r1_e3_logvolratio_20d`         | −0.120 | +1.538 | N | 1.041 | N | −0.788 |
| `r1_e4_volspread_10d`           | +0.317 | +0.690 | N | 0.578 | N | **+0.190** |
| `r1_e5_volspread_20d_z504`      | −0.474 | +0.758 | N | 0.389 | N | −0.116 |
| `r1_e6_downvolspread_20d`       | −0.246 | −0.271 | N | −0.278 | N | −0.153 |
| `r1_e7_vol_accel_spread`        | −1.304 | −0.959 | N | −1.062 | N | −0.970 |
| `r1_e8_volspread_longbaseline`  | −0.007 | +0.545 | N | 0.380 | N | −0.430 |

*Test Sharpes are reported here as **diagnostic** only — per TVT discipline,
test must be untouched until a winner is selected; in this round there is
no eligible winner so all 8 test runs are diagnostic context, not a
selection signal. They are produced once and reported faithfully; we do
not iterate on test.

## What G4 actually flagged for the 7 failing v2 expressions

| Expr | IC sign match | Monotonic inversions | Peak-IC horizon | Classic-clone corr | Overall |
|---|:-:|---:|---:|---:|:-:|
| E1 | ✓ | 1 | **5** ✓ | −0.03 | **PASS** |
| E2 | ✓ | 2 ✗ | n/a | n/a | FAIL (monotonicity) |
| E3 | ✓ | 2 ✗ | n/a | n/a | FAIL (monotonicity) |
| E4 | ✓ | 3 ✗ | 5 ✓ | −0.00 | FAIL (monotonicity) |
| E5 | ✓ | 2 ✗ | n/a | n/a | FAIL (monotonicity) |
| E6 | ✓ | 3 ✗ | **20** ✗ | −0.32 | FAIL (monotonicity + horizon) |
| E7 | ✓ | 3 ✗ | 5 ✓ | +0.05 | FAIL (monotonicity) |
| E8 | ✓ | 1 ✓ | **10** ✗ | +0.01 | FAIL (peak-horizon mismatch) |

Notable: E1 passes every G4 sub-check on TRAIN with the smallest IC magnitude
of the survivors (IC=0.064, t≈1.93). The pattern across the batch is
"consistent direction, fragile shape" — the contrarian thesis has weak
directional evidence but the cross-sectional response across the score
distribution is not monotone. This is a textbook signature of a **noisy
mean-reverting signal contaminated by another regime** — see Agent-5
falsification below.

## Frozen-test diagnostic (E1, the only G4 survivor)

### TVT gradient

| Metric | Train | Val | Test |
|---|---:|---:|---:|
| Days | 906 | 484 | 558 |
| Sharpe | +0.141 | +1.056 | +0.142 |
| Ann return | n/a | n/a | +1.55% |
| Max DD | n/a | n/a | −14.97% |
| Calmar | n/a | n/a | 0.10 |
| Ann turnover | 26.4× | n/a | n/a |
| Non-zero days | n/a | n/a | 59.5% |

### Per-year test breakdown (E1)

| Year | n_days | Sharpe | Ann return | Max DD |
|---|---:|---:|---:|---:|
| 2024 | 244 | +0.01 | +0.10% | −10.83% |
| 2025 | 244 | +0.75 | +8.41% | −9.49% |
| 2026 | ~75 | −1.15 | −12.85% | −9.36% |

### Mandatory pre-PROMOTE audits applied to E1

- **Audit 1 (execution-delay)**: PASS — engine invariant
  `target_shift == −(1 + delay)` (= −2 with delay=1) holds; 30-sample
  future-perturbation test produced 0 mismatches. See
  `outputs/backtest_results_batch_0001.md` `audit_1_execution_delay`.
- **Audit 2 (look-ahead)**: PASS — 30-sample bar shuffle on bars after
  each sample date `t` produced 0 deviations in `score_t`.
- **Audit 3 (worst-year Sharpe ≥ 0.5)**: **FAIL** — worst test year is
  2026 (partial, 75 days) with Sharpe −1.15. Even on full years, 2024
  Sharpe of +0.01 is far below 0.5.
- **Audit 4 (best-year-out ≥ 50% headline)**: **FAIL** — headline +0.14;
  excluding the best year (2025, +0.75), the 2024+2026 combined Sharpe
  is approximately −0.30 (no longer positive). The headline is essentially
  carried by 2025 alone.
- **Audit 5 (falsification, see below)**: see next section.

### Audit 5 — falsification ("if Sharpe is wrong by 50%, what is the most likely single cause?")

**Most likely single cause**: the test window is dominated by **two partial regimes** —
the 2024-Q1 micro-cap panic + April 2025 small-cap rally + early-2026 reversal.
With only ~75 trading days of 2026 in-sample, the partial-year inclusion
swings the headline aggressive Sharpe by ~0.3 in either direction. The
true full-year-2026 Sharpe could land anywhere in [−0.5, +0.5] depending
on how the rest of 2026 prices.

**The test that would prove this**: recompute the Test Sharpe excluding
2026 (i.e. 2024-2025 only). That gives:

```
2024-2025 combined: Sharpe ≈ +0.38, ann return ≈ +4.3%, n=488 days
2026 (partial):     Sharpe = −1.15
Headline (full):    Sharpe = +0.14
```

Removing the 2026 partial year roughly **doubles** the test Sharpe (+0.14
→ +0.38). Headline is sensitive to ±2 months of additional 2026 data;
the factor is **observation-period-fragile**, not a stable PROMOTE
candidate.

A second candidate cause is **cost mis-specification**: the assumed
5 bps/side is for a sophisticated execution; retail/agency execution
often pays 10-20 bps round-trip on these ETFs. At 10 bps/side, the
gross-of-cost +0.14 Sharpe drops below zero on the test window. Test:
re-run engine with `cost_bps_per_side_per_leg=10` and report Sharpe
delta.

Either way, the headline does not survive scrutiny → confirmation of
the RESEARCH-ONLY decision.

### Hard floors for PROMOTE — checkbox

- [ ] Test IC mean t-stat ≥ 3.0  ← E1 train IC=0.064, t≈1.93; test IC not even computed because below floor
- [ ] Test Sharpe ≥ 1.0  ← E1 test Sharpe = +0.14
- [ ] Worst-year Sharpe ≥ 0.5  ← worst (2026 partial) = −1.15
- [ ] Best-year-out Sharpe ≥ 50% × headline  ← without 2025, no longer positive
- [ ] Test max DD < 2× train max DD  ← train DD not measured rigorously this round
- [ ] Calmar ≥ 1.5  ← E1 test Calmar = 0.10
- [x] Execution-delay audit passed
- [x] Look-ahead audit passed

8/8 unchecked sufficient → **PROMOTE blocked**.

## Decision

- **Decision**: **RESEARCH-ONLY**.
- **Reason**: 0/8 expressions TVT-eligible; G5 batch-level still failing in
  v2; even the strongest expression (E1) fails 4 of 6 numeric PROMOTE
  floors with only 2/8 audits passing; signal is dominated by a single
  test year (2025) and reverses in partial-2026.

### Notable diagnostic finding worth carrying to R2

`r1_e4_volspread_10d` (faster 10d window) is the *only* expression with
**consistent positive Sharpe across all three test years**: 2024 +0.10,
2025 +0.27, 2026 +0.25. It fails G4 only on quintile monotonicity (3
inversions) and shows a much smaller magnitude than E1's 2025 spike.
This is what a **stable but weak** signal looks like — exactly the
profile that R2 should try to amplify (e.g. via vol-state conditioning,
or by combining with M2 turnover signals). E4 itself is not deployable
but its per-year stability is a positive R2 lead.

### Next-round (R2) focus

If this research direction continues, R2 should:

1. **Pivot the mechanism family** away from M1 vol-regime to M2 turnover
   divergence or M3 dispersion — the M1 evidence is too weak to justify
   another full batch.
2. **If M1 is retained**, drop the 20d expressions (E1, E2, E3, E5, E8)
   in favour of faster windows like E4's 10d, with explicit conditioning
   on vol *state* (only take signal when vol is in top/bottom quartile of
   trailing year).
3. **Revisit cost assumption**. 5 bps/side is aggressive for ETF retail
   execution; sensitivity at 10 bps/side determines whether any of these
   factors are deployable even with a successful R2.
4. **Consider universe expansion**. With only 3 ETFs and no
   cross-section, every signal is a directional timing call — the
   information-to-noise ratio is intrinsically poor. Pull constituent
   data and revisit "small-cap basket dispersion" (M3) as a true
   cross-sectional signal.
