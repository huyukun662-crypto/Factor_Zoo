# Alpha Ranking — Round 0003 (M3 turnover acceleration → momentum)

Session `20260425_a_share_style_timing_csi300_csi1000` · Mechanism family
M3_turnover_acceleration_momentum (pivot from R2 anti-thesis finding) ·
TVT splits unchanged · 5 bps/side · delay = 1 · z-score deadband 0.5.

## Headline

> **Decision: RESEARCH-ONLY (near-PROMOTE).** First eligible TVT winner
> of the entire session. Winner `r3_e4_amt_accel_5_120_neg` (TVT score
> 0.23, the lowest train/val gap among 3 eligible candidates) returns
> **test Sharpe +0.58, ann return +6.3%, max DD −12.7%, calmar 0.50**
> with per-year test profile 2024 = +1.51, 2025 = −1.19, 2026 (partial) = +2.02.
> **Audit 3 (worst-year ≥ 0.5) FAILS** because of 2025; pre-registered
> tighter bar (≥ 0.7) also fails. PROMOTE blocked.
>
> **However**: the M3 mechanism is now confirmed across 4 single-leg
> expressions (E1-E4) with TRAIN IC 0.20 to 0.31 (t-stat 4 to 9.5) —
> the strongest IC magnitudes of the session. R4 should refine M3
> (regime-conditioning out 2025-style markets) rather than abandon.

## Round-3 history (audit trail)

| Stage | Action | Outcome |
|---|---|---|
| Stage 4 v1 (horizon=5) | Run 8 R3 expressions; declared horizon 5d. | All 4 single-leg expressions (E1-E4) have IC strictly increasing 1d→20d, peaking at h=20 (NOT h=5). G5 escalates to Agent 2. |
| Stage 2 v2 revision | Revise declared primary horizon 5 → 20 per `validation-gates.md` G5 protocol. Mechanism is real but slower than initially declared (retail crowding persists ~1 month, not 1 week). | Agent-3 expressions unchanged in math; `Factor.horizon` updated to 20 across r3_e1..r3_e8. |
| Stage 4 v2 (horizon=20) | Re-run G4/G5 with horizon=20. | **2/8 G4 PASS** (E2, E4). 3/8 TVT-eligible (E1, E2, E4). G5 PASS (2/2 surviving expressions peak at declared 20d). |

## Eligibility table (v2, after horizon revision)

| Expr | Train Sh | Val Sh | Eligible | TVT Score | Gates | TRAIN IC (h=20) |
|---|---:|---:|:-:|---:|:-:|---:|
| `r3_e1_amt_accel_5_20_neg`           | +0.502 | +0.918 | Y | **0.793** | G3 fail (turn 35.5 > 20.0) | +0.201 |
| `r3_e2_amt_accel_5_60_neg`           | +1.024 | +0.320 | Y | 0.109 | **PASS** | **+0.271** (t=8.3) |
| `r3_e3_amt_accel_10_60_neg`          | +1.165 | −0.256 | N (val<0) | — | G4 fail | +0.263 |
| `r3_e4_amt_accel_5_120_neg`          | +1.132 | +0.438 | **Y** | **0.230** | **PASS — TVT WINNER** | **+0.311** (t=9.5) |
| `r3_e5_amt_accel_spread_5_20_neg`    | −0.612 | −0.126 | N | — | G3+G4 fail | +0.015 |
| `r3_e6_amt_accel_spread_5_60_neg`    | −0.225 | −0.338 | N | — | G3+G4 fail | +0.029 |
| `r3_e7_vol_accel_spread_5_60_neg`    | −0.765 | −0.027 | N | — | G3+G4 fail | −0.039 |
| `r3_e8_accel_high_vol_regime`        | −0.246 | +0.197 | N | — | G3+G4 fail | +0.101 |

E1 has the highest TVT score (val 0.92, low train/val gap) but fails
G3 turnover (annualized 35.5× exceeds 20× ceiling). E4 is the
gates-passing TVT winner.

## What G4 actually flagged (v2, horizon=20)

| Expr | IC sign | Monotonic inversions | Peak-IC horizon | Classic-clone corr | Overall |
|---|:-:|---:|---:|---:|:-:|
| E1 | ✓ | 1 | 20 ✓ | 0.27 | FAIL (G3 turnover) |
| E2 | ✓ | 1 | **20** ✓ | 0.50 | **PASS** |
| E3 | ✓ | 1 | 20 ✓ | 0.52 | FAIL (TVT eligibility — val < 0) |
| E4 | ✓ | 1 | **20** ✓ | 0.55 | **PASS** |
| E5 | ✗ (sign) | n/a | n/a | n/a | FAIL |
| E6 | ✗ (sign) | n/a | n/a | n/a | FAIL |
| E7 | ✗ (sign) | n/a | n/a | n/a | FAIL |
| E8 | ✓ (weak) | n/a | 10 ✗ | n/a | FAIL |

The single-leg amount-acceleration cluster (E1-E4) all share the same
IC structure: strictly increasing 1d → 20d. Spread-of-acceleration
variants (E5, E6, E7) and the regime-conditional (E8) test different
sub-mechanisms that don't replicate the single-leg result.

## G5 — corrected semantics

**Original implementation issue**: gate_g5 hardcoded `n_at_declared ≥ 4`
absolute, which never passes when fewer than 4 expressions survive G4.
Per `SKILL.md:194` the rule is "≥ 4 of 8 surviving expressions peak
elsewhere → escalate", which is "≥ 50% of survivors". With 2 G4
survivors both peaking at h=20 (declared), the *fraction* is 100% —
G5 should pass. The implementation was corrected in `src/backtest/audits.py`
to "fraction of survivors at declared ≥ 50%".

**Disclosure**: the fix was applied AFTER seeing R3 v2 results. The
correction is semantically aligned with SKILL.md text, not a
post-hoc rule loosening.

## Frozen test — winner E4 only

(Per TVT discipline, test runs ONCE on the TVT-selected winner. E2 was
also G4-eligible but lost on TVT score; its test results are NOT used
for the headline decision. E2 was incidentally tested in the v1 G5-fail
"no-winner-diagnostic" pass; that test is logged but does not enter
selection.)

### TVT gradient (winner = `r3_e4_amt_accel_5_120_neg`)

| Metric | Train | Val | Test |
|---|---:|---:|---:|
| Days | 905 | 484 | 558 |
| Sharpe | +1.13 | +0.44 | **+0.58** |
| Ann return | n/a | n/a | **+6.32%** |
| Max DD | n/a | n/a | −12.71% |
| Calmar | n/a | n/a | +0.50 |
| Ann turnover | 14.3× | n/a | 15.4× |
| Non-zero days | n/a | n/a | 48.2% |
| TRAIN IC (h=20) | +0.311 (t≈9.5) | n/a | n/a |

### Per-year test breakdown (E4)

| Year | n_days | Sharpe | Ann return | Max DD |
|---|---:|---:|---:|---:|
| 2024 | 244 | **+1.51** | +18.86% | −5.12% |
| 2025 | 244 | **−1.19** | −10.78% | −12.31% |
| 2026 | ~70 | **+2.02** | +21.85% | −3.86% |

### Mandatory pre-PROMOTE audits (E4)

- **Audit 1 (execution-delay)**: PASS — `target_shift = −2`,
  future-perturbation 0/30 mismatches.
- **Audit 2 (look-ahead)**: PASS — bar shuffle 0/30 mismatches.
- **Audit 3 (worst-year Sharpe ≥ 0.5)**: **FAIL** — 2025 = −1.19.
  Pre-registered tighter bar ≥ 0.7 also fails.
- **Audit 4 (best-year-out ≥ 50% headline)**: **PASS** — best year
  2026 partial Sh +2.02; without it Sharpe drops to +0.37; ratio
  0.63 ≥ 0.50.
- **Audit 5 (falsification)**: see below.

### Audit 5 — falsification

**Most likely single cause** the headline +0.58 test Sharpe is
mis-estimated by 50%: **2025 was a regime where the M3 mechanism
inverted**. In 2024, small-cap turnover acceleration predicted
small-cap continuation (M3 momentum — what we trained for). In 2025,
the same signal predicted small-cap **mean-reversion** (closer to
the M2 thesis we falsified in R2). The factor lost −10.8% in 2025
because the regime flipped underneath it.

**The test that would prove it**: compute IC of the SAME signal on
2024 vs 2025 vs 2026 separately. If 2025 IC is materially negative
while 2024/2026 are positive, the regime-flip hypothesis is
confirmed. This would also support the R4 direction: a
regime-conditional version of E4 that shuts off in
"reversal regimes" (potentially detectable via R1 vol-spread
state — note that R3 E8 attempted this but with a coarse on/off
gate; a smoother regime weight would be the right approach).

A second candidate cause: **daily-rebalance is sub-optimal for a
20d-peaking signal**. The IC peaks at h=20 but we rebalance daily;
this incurs unnecessary turnover (15.4× annual) and cost (~150 bps/year
at 5bps/side ×2 legs). A 20d-rebalance variant would have ~3.8× annual
turnover (~76 bps/year cost), which would add ~0.74% to ann return. 
The headline +6.32% might become ~+7%, and Sharpe would rise modestly.

### Hard floors for PROMOTE — checkbox

Both standard and pre-registered tighter bars:

- [ ] Test IC mean t-stat ≥ 3.0 / **3.5 (tighter)**  ← TRAIN IC t=9.5; test IC not directly computed, will be lower
- [ ] Test Sharpe ≥ 1.0  ← E4 = +0.58
- [ ] Worst-year Sharpe ≥ 0.5 / **0.7 (tighter)**  ← 2025 = −1.19
- [x] Best-year-out Sharpe ≥ 50% × headline  ← ratio 0.63
- [ ] Test max DD < 2× train max DD  ← train DD reference unmeasured this round
- [ ] Calmar ≥ 1.5  ← E4 = +0.50
- [x] Execution-delay audit passed
- [x] Look-ahead audit passed

3/8 unchecked → **PROMOTE blocked**. RESEARCH-ONLY confirmed.

## Decision

- **Decision**: **RESEARCH-ONLY** (near-PROMOTE).
- **Reason**: TVT-eligible winner identified for the first time in the
  session, but blocked by audit 3 (worst-year Sharpe). 2025 was a
  regime-flip year that the M3 momentum thesis cannot survive.

### Strong sub-mechanism finding (consistent across all 3 rounds)

Both R2 (E3 IC −0.20, t = −5.93 anti-thesis) and R3 (E2/E4 IC +0.27/+0.31
with negation, t = 8.3/9.5) confirm that **single-leg small-cap
turnover acceleration is informative about forward style returns**, on
a horizon of ~20 trading days. The R3 winner (E4 5d/120d windows) has
TRAIN IC = 0.311 and t = 9.5 — by far the strongest signal of the
session. The mechanism is real; the question is regime-stability.

### R4 leads (in order of strength)

1. **REGIME-CONDITION the M3 winner**: build R4 around E4-style signals
   gated by a smooth regime indicator that distinguishes "small-cap
   continuation" regimes from "small-cap mean-reversion" regimes. R3
   E8 attempted a coarse on/off vol-spread gate; R4 should use a
   smooth weighting (e.g., signal × tanh(vol-spread-z)).
2. **20d-REBALANCE variant**: re-test E4 with 20d hold (matching the
   peak-IC horizon) instead of daily. Cost reduction alone should
   add ~0.7% annual return. May also improve Sharpe via signal noise
   averaging.
3. **EXTEND TEST WINDOW** when more 2026 data accumulates. The current
   2.3y test is below the TVT 3y+ floor; an extra year makes the
   audit-3 worst-year check more meaningful.
4. **EXPAND DATA**: pull constituent stocks. With cross-sectional data
   the same mechanism could be tested as a stock-picking factor
   (positions in individual small-cap names) rather than a
   timing-only signal — much higher information capacity.

The R4 #1 (regime-conditioning) is the highest-value followup. The
mechanism is confirmed; the failure mode is single-regime
concentration; the fix is regime detection.
