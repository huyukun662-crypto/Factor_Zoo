# Alpha Ranking — Round 0002 (M2 turnover divergence)

Session `20260425_a_share_style_timing_csi300_csi1000` · Mechanism family
M2_turnover_divergence (pivot from R1 M1) · TVT splits unchanged
(train [2018,2022) / val [2022,2024) / test [2024,now]) · 5 bps/side ·
delay = 1 · z-score deadband 0.5.

## Headline

> **Decision: RESEARCH-ONLY for R2.** Improvement over R1 (2/8 G4 pass
> vs 1/8) but no expression is TVT-eligible (train Sharpe floor 0.5
> not cleared). Even the strongest val candidates (E1/E8, val Sh +1.7)
> show **negative test Sharpe** (−0.35). The val-period strength was
> a regime artifact specific to 2022-2023, not a generalizable signal.
>
> **Notable secondary finding**: E3 (small-cap turnover acceleration) has
> IC = **−0.196 with t = −5.93** on TRAIN — strongly significant in the
> *anti-thesis* direction. Turnover acceleration on small-cap behaves as
> a **momentum signal** (small-cap continues outperforming), not the
> mean-reversion implied by M2's level thesis. This is the cleanest
> signal-with-economic-meaning surfaced in either round and is the
> recommended R3 lead.

## Eligibility table

| Expr | Train Sharpe | Val Sharpe | Eligible | TVT Score | Gates | Test Sharpe* |
|---|---:|---:|:-:|---:|:-:|---:|
| `r2_e1_log_amount_ratio_20d`     | +0.156 | +1.686 | N | 1.227 | **G1-G4 pass** | **−0.359** |
| `r2_e2_log_amount_ratio_5d`      | +0.303 | +0.396 | N | 0.368 | G3+G4 fail | −0.179 |
| `r2_e3_abnormal_amount_1000`     | −1.356 | −0.817 | N | −0.978 | G3+G4 fail | −1.343 |
| `r2_e4_abnormal_amount_spread`   | −0.243 | −0.603 | N | −0.711 | G3+G4 fail | −0.762 |
| `r2_e5_log_amount_ratio_z504`    | +0.313 | +0.924 | N | 0.741 | G4 fail | −0.657 |
| `r2_e6_amount_resid_vs_vol_spread` | −0.985 | +0.463 | N | 0.028 | G3+G4 fail | **+0.186** |
| `r2_e7_log_amount_accel_spread`  | −0.113 | −0.740 | N | −0.928 | G3+G4 fail | −1.187 |
| `r2_e8_amount_share_1000`        | +0.200 | +1.699 | N | 1.249 | **G1-G4 pass** | **−0.352** |

*Test Sharpes are diagnostic context (no eligible winner → no selected
candidate → all 8 frozen-test runs are reported as raw evidence, not
selection signals).

## What G4 actually flagged

| Expr | IC sign match | Monotonic inversions | Peak-IC horizon | Classic-clone corr | Overall |
|---|:-:|---:|---:|---:|:-:|
| E1 | ✓ | 1 | **5** ✓ | low | **PASS** |
| E2 | ✓ | 2 ✗ | n/a | n/a | FAIL (monotonicity) |
| E3 | ✗ (sign flipped, t=−5.93!) | n/a | n/a | n/a | FAIL (sign) |
| E4 | ✓ | n/a | n/a | n/a | FAIL (multiple) |
| E5 | ✓ | n/a | **20** ✗ | n/a | FAIL (peak horizon mismatch) |
| E6 | ✗ (sign flipped, t=−3.72) | n/a | n/a | n/a | FAIL (sign) |
| E7 | ✓ | 3 ✗ | n/a | n/a | FAIL (monotonicity) |
| E8 | ✓ | 1 | **5** ✓ | low | **PASS** |

## The acceleration sub-mechanism is anti-thesis (the R2 surprise)

E3 (`r2_e3_abnormal_amount_1000` = z(log MA5/MA60 of small-cap amount))
has TRAIN IC = **−0.196 with t = −5.93** vs forward 5d (idx300−idx1000)
return. That is materially significant in the OPPOSITE direction
predicted by M2's mean-reversion thesis. E6 (`r2_e6_amount_resid_vs_vol_spread`)
shows the same anti-thesis sign with IC = −0.123, t = −3.72.

Economic reading: when small-cap turnover **accelerates** (current
relative to its 60-day baseline), small-cap momentum **continues** for
~5 trading days — the opposite of the mean-reversion expected from a
"retail euphoria → exhaustion" narrative. This matches A-share
empirical practice that small-cap rallies are characterized by
sustained turnover acceleration (2024-Q4 micro-cap surge being the
most recent textbook case).

If E3 were negated at source (i.e. `score = +z(log MA5/MA60 of amount_1000)`
becomes `score = −z(...)`, with thesis_sign +1), it would have IC ≈ +0.196
on TRAIN. This would be the strongest single-expression signal observed
in either round of this session.

**Important TVT caveat**: re-running R2 with E3 negated would be a
mid-session sign-flip that this round would NOT report cleanly. Per
`validation-gates.md`, sign-flipping a sub-cluster is acceptable as an
Agent-2 hypothesis revision but should be done as a clean R3, not as
R2 v2. Treating it as an R3 hypothesis preserves the test window's
honesty.

## Frozen test diagnostic — the val-strong candidates fail to generalize

Per-year test Sharpe for the two G4-pass candidates:

| Year | E1 | E8 |
|---|---:|---:|
| 2024 | −0.38 | −0.36 |
| 2025 | −0.85 | −0.85 |
| 2026 (partial) | +4.34 | +4.34 |
| **Headline** | −0.36 | −0.35 |

E1 and E8 are construction-distinct (log ratio vs flow share) but
behave near-identically on test (their TRAIN correlation was 1.00
on the z-score response, see `expressions_batch_0002.md`).

The 2026-partial spike is from only ~75 trading days, dominated by 1-2
extreme spread moves. Full-year 2024 and 2025 are clearly negative.
The val-window strength (Sh +1.7) was driven by a 2022-2023 regime
where small-cap-amount-share was a leading indicator of style rotation
— that regime did not persist into test.

This is a clean **out-of-sample disconfirmation** of the M2-level
thesis. Honest reporting → RESEARCH-ONLY.

## Mandatory pre-PROMOTE audits

- **Audit 1 (execution-delay)**: PASS — engine invariant
  `target_shift = −(1+delay) = −2`, future-perturbation 0/30 mismatches
  on every R2 expression.
- **Audit 2 (look-ahead)**: PASS — bar-shuffle 0/30 deviations on
  every R2 expression (R2 expressions use only rolling/MA/log
  operators on past data).
- **Audit 3 (worst-year Sharpe ≥ 0.5)**: FAIL — E1 worst year is
  2025 with Sharpe −0.85.
- **Audit 4 (best-year-out ≥ 50% headline)**: FAIL — E1 headline is
  −0.36; without 2026 partial (best year, +4.34), Sharpe drops to
  approximately −0.62. Removing best year makes it worse, but the
  audit's intent (regime-concentration check) is clearly failed —
  the entire positive contribution comes from 75 days.
- **Audit 5 (falsification — see below)**.

### Audit 5 — falsification

**Most likely single cause** that R2's headline picture is wrong by 50%:
the val-window 2022-2023 contained two distinct phases — the late-2022
small-cap defensive rotation (favoured 300, M2-level was right) and
the 2023 small-cap recovery (favoured 1000, M2-level was wrong but in
roughly equal magnitude). The val Sharpe of +1.7 averaged out to be
*directionally favourable* to the level signal, but the underlying IC
is much weaker than the Sharpe suggests (val IC ≈ +0.005, t < 0.2).
Sharpe is being driven by a small number of large directional bets in
val, not by consistent edge.

**Test that would prove it**: compute val IC t-stat per quarter and
report the dispersion. If 4 of 8 val quarters have IC sign opposite
to thesis, the +1.7 val Sharpe is from a tiny number of correct
calls, not from a stable signal — making the test failure expected
rather than surprising.

A second candidate cause: **E1 ≈ E8 inflation**. The Rule-of-8
intent is 8 *distinct* probes; in this batch, E1 and E8 are
construction-distinct but response-identical (TRAIN corr 1.00 on
z-score). Effective batch size is 7 distinct signals, not 8. This
weakens batch-level conclusions but does not change the per-expression
G4 picture or the RESEARCH-ONLY decision.

## Hard floors for PROMOTE — checkbox

- [ ] Test IC mean t-stat ≥ 3.0  ← E1 train IC=0.006, t≈0.18; nowhere near
- [ ] Test Sharpe ≥ 1.0  ← E1 test Sharpe = −0.36
- [ ] Worst-year Sharpe ≥ 0.5  ← worst (2025) = −0.85
- [ ] Best-year-out Sharpe ≥ 50% × headline  ← removing best (2026 partial) makes it worse
- [ ] Test max DD < 2× train max DD  ← train DD reference not measured
- [ ] Calmar ≥ 1.5  ← E1 test Calmar negative
- [x] Execution-delay audit passed
- [x] Look-ahead audit passed

PROMOTE blocked.

## Decision

- **Decision**: **RESEARCH-ONLY**.
- **Reason**: 0/8 TVT-eligible (train floor not cleared); G5 batch
  fails (2 < 4 required); even the G4-passing candidates have negative
  test Sharpe; the val-strong picture does not survive frozen test.

### R3 leads (in order of strength)

1. **PIVOT**: small-cap turnover acceleration as **momentum** signal,
   not mean-reversion. Build R3 around `−1 × z(log MA5/MA60 of amount_1000)`
   and variants, with `thesis_sign = +1` (Agent-3 negates at source).
   IC of E3 on TRAIN was −0.196, t = −5.93 (anti-thesis); flipping
   gives IC +0.196 — substantially stronger than anything tested so
   far.
2. **COMBINE**: regime-conditional combination of M1 (vol) and M2
   (turnover). When |vol_spread| is large AND |turnover_spread| is
   large in the same direction, the signal may be more robust than
   either alone. Requires careful design to avoid in-sample optimization.
3. **DROP**: M2-level thesis (the E1/E8/E5 cluster). val-favorable, test-failed,
   no economic story for why 2022-2023 worked.
4. **EXPAND DATA**: pull constituent stocks for the three indices and
   build true cross-sectional turnover-divergence factors. With only
   3 ETFs and no cross-section, every M2 signal is a coarse
   directional bet.

The R3 #1 lead (acceleration-as-momentum) is the highest-value
followup of the entire session — the IC of −0.196 with t ≈ −6 is
the most statistically meaningful single number we have produced.
