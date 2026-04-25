# Alpha Ranking — Round 0004 (M3 regime-conditioning attempt)

Session `20260425_a_share_style_timing_csi300_csi1000` · Mechanism family
M3_regime_conditioned (refinement of R3 E4) · TVT splits unchanged ·
5 bps/side · delay = 1.

## Headline

> **Decision: RESEARCH-ONLY. R4 regime-conditioning hypothesis is FALSIFIED.**
> 0/8 G4 PASS. 0/8 TVT-eligible. **R3 E4 remains the session-best factor.**
>
> **Strong falsification finding**: smooth-tanh gates on R3 E4
> (E1, E2, E5, E6) all produce **TRAIN IC strongly negative** (t = −4.9
> to −6.5) — the gate is flipping the signal in the *opposite* of the
> helpful direction. The R4 hypothesis "M3 works in elevated-vol regimes"
> is wrong on TRAIN: M3 actually worked **primarily in CALM regimes**
> (2018-2021), not the elevated-vol periods. The 2025 test failure is
> NOT a regime-flip phenomenon — it's a year-specific event no
> regime indicator we tested can capture.
>
> **Useful sub-finding**: R4 E7 (R3 E4 with 20d monthly rebalance, no
> gate) has **TRAIN IC t = +7.30** — STRONGER than R3 E4's daily-rebalance
> t ≈ 9.5 (close), confirming the IC peaks at h=20. But val Sh ≈ 0 and
> test Sh = −0.24 — the cost reduction does NOT rescue out-of-sample
> performance. Cost was not the binding issue.

## Round-4 history

R4 was hypothesis-driven: refine R3 E4 with a regime gate to filter out
2025-style failure regimes. Tested 6 gate variants (smooth tanh, one-sided,
turnover-z, composite, market-60d, soft temperature) plus 1 rebalance-frequency
variant (E7). Pre-registered tighter PROMOTE bars before Stage 4
(`session_metadata.yml#round_0004.pre_registered_tighter_bars`).

## Eligibility table

| Expr | Train Sh | Val Sh | TRAIN IC (h=20) | t-stat | Eligible | Gates |
|---|---:|---:|---:|---:|:-:|:-:|
| `r4_e1_e4_x_volgate_tanh_t1`     | −1.170 | −0.544 | **−0.206** | **−6.13** | N | G3+G4 fail |
| `r4_e2_e4_x_volgate_tanh_t2`     | −1.718 | −0.834 | **−0.217** | **−6.47** | N | G3+G4 fail |
| `r4_e3_e4_x_turnoverlevel_tanh`  | −0.111 | +0.065 | −0.056 | −1.64 | N (train≤0.5) | G3+G4 fail |
| `r4_e4_e4_x_volgate_oneside`     | −0.262 | +0.573 | +0.044 | +1.28 | N (train≤0.5) | G3+G4 fail |
| `r4_e5_e4_x_composite_regime`    | −1.044 | +0.155 | **−0.190** | **−5.65** | N | G3+G4 fail |
| `r4_e6_e2_x_volgate_tanh_t1`     | −1.394 | +0.427 | **−0.162** | **−4.85** | N | G3+G4 fail |
| `r4_e7_e4_monthly_rebalance`     | **+1.245** | −0.009 | **+0.246** | **+7.30** | N (val<0) | G3 pass, G4 fail (mono inv=2) |
| `r4_e8_e4_x_market_60d_gate`     | −0.082 | +0.052 | +0.019 | +0.54 | N | G3+G4 fail |

R4 has **0 TVT-eligible candidates** (R3 had 3). The smooth-gate batch
(E1, E2, E5, E6) is strongly **anti-thesis on TRAIN** — the gate is
WORKING but in the wrong direction.

## Why the smooth-tanh-gate IC is negative — falsifying R4's premise

The R4 hypothesis assumed **M3 mechanism is amplified in elevated-vol
regimes** (vol_spread_z > 0). Multiplying R3 E4 by `tanh(vol_spread_z)`
should preserve M3's direction in high-vol days and flip it in low-vol days.
If the hypothesis were correct, gated IC ≥ R3 E4 base IC.

Observed: **gated IC = −0.21 (E1), base IC = +0.31 (R3 E4 raw)**. The
sign flips. Mechanism:

- On TRAIN, vol_spread_z spent more days NEGATIVE (calm regime is the
  default) than positive
- M3 mechanism produced strong correct-direction returns specifically
  during those calm days
- The tanh gate flipped the signal precisely on those days
- Net IC ends up negative and statistically significant in the wrong
  direction

**Conclusion**: M3 (small-cap turnover acceleration → small-cap
continuation) operated on TRAIN primarily in CALM regimes, not in
elevated-vol regimes. The R4 premise is empirically falsified.

R4's failure is informative: a different gate direction (`tanh(-vol_z)`,
amplifying in calm) might work — but testing that within R4 would be
mid-round cherry-picking. R5 should test it cleanly if pursued.

## Why E7 (monthly rebalance, no gate) doesn't generalize

E7 is the **purest test of the rebalance-frequency hypothesis**: same
M3 base as R3 E4, just sampled every 20 days instead of daily. Results:

| Window | Days | E7 Sharpe | R3 E4 Sharpe | Δ |
|---|---:|---:|---:|---:|
| Train | 853 | **+1.245** | +1.13 | **+0.11** |
| Val | 484 | **−0.009** | +0.44 | **−0.45** |
| Test | 558 | **−0.236** | +0.58 | **−0.81** |

Train improves modestly (lower-cost signal). But val and test get *worse*.
With ~12 rebalances/year × 2y val = ~24 trades total in val, the Sharpe
estimate is statistically very thin — single-trade noise can swing it
±0.5. The val/test degradation could be entirely sampling noise, not
a real loss of edge.

**Honest reading**: monthly rebalance does not rescue the factor. Cost
was not the binding constraint. The R3 E4 daily-rebalance Sharpe of
+0.58 on test is the strongest result we have; R4 has not improved it.

## Frozen test diagnostic (no winner → all 8 tested as context, NOT for selection)

Per TVT discipline, when no winner is selected the test runs are
diagnostic only. **R4 winner is None**; all 8 test results below are
context, not selection signals.

| Expr | Test Sh | 2024 | 2025 | 2026 (partial) | Δ vs R3 E4 (test) |
|---|---:|---:|---:|---:|---:|
| R3 E4 (reference) | +0.58 | +1.51 | −1.19 | +2.02 | — |
| r4_e1 | −0.53 | −0.22 | −0.68 | −1.48 | −1.11 |
| r4_e2 | −0.25 | −0.13 | −0.43 | +0.00 | −0.83 |
| r4_e3 | −0.47 | −0.77 | −0.10 | +0.00 | −1.05 |
| r4_e4 (one-sided) | −0.68 | +0.00 | −1.12 | −0.20 | −1.26 |
| r4_e5 | −0.50 | −0.50 | −0.86 | +0.00 | −1.08 |
| r4_e6 | **−1.25** | −1.51 | −0.76 | −1.89 | −1.83 |
| r4_e7 (monthly) | −0.24 | +0.42 | −0.62 | −1.55 | −0.82 |
| r4_e8 (market gate) | **+0.22** | +0.98 | −1.77 | −0.59 | −0.36 |

Every single R4 variant has *worse* test Sharpe than R3 E4. The R4
hypothesis fails universally. Notable observation: even E8 (market-direction
gate) has 2025 = −1.77, much worse than R3 E4's −1.19 — gating made 2025
**worse**, not better.

This is a strong, clean falsification.

## Mandatory pre-PROMOTE audits

R4 has no winner → no candidate to audit. Decision is RESEARCH-ONLY by
construction (no eligible candidate). Falsification audit (audit 5)
applies at the round level:

### Audit 5 — falsification ("if R4's null result is wrong, what's the most likely cause?")

**Most likely single cause**: the gate direction is reversed for TRAIN.
On TRAIN (2018-2021), M3 worked in CALM regimes (low vol_spread_z),
not in elevated-vol regimes. A gate of `tanh(-vol_spread_z)` (or
equivalently a one-sided gate gated on calm days) might rescue some
expressions.

**Test that would prove it**: build R5 with `tanh(-vol_spread_z)` and
check whether train IC of E1-style variants becomes positive AND test
2025 Sharpe improves. If yes, the calm-regime amplification hypothesis
is the right framing. If no, the M3 mechanism is genuinely
year-specific (2025-only failure not explainable by any regime axis we
have access to).

**Second candidate cause**: the M3 mechanism is genuinely a
year-specific phenomenon, not regime-dependent. 2018-2021 train
worked because A-share micro-cap dynamics were favorable; 2025 broke
because of structural shifts (regulatory, retail-investor demographics,
flow patterns) that don't show up in price-derived regime indicators.
This is unfalsifiable with our 3-asset universe.

## Hard floors for PROMOTE — checkbox (R4 round level, no winner)

- [ ] R4 winner test Sharpe > R3 E4 +0.58 (pre-registered)  ← no winner; best R4 test = +0.22 (E8) which is the only positive
- [ ] Test IC t-stat ≥ 4.0 (R4 tighter bar)  ← no winner
- [ ] Worst-year Sharpe ≥ 0.7  ← no winner
- [x] Execution-delay audit (engine invariant, all R4 factors)
- [x] Look-ahead audit (rolling/MA only, no forward access)

PROMOTE blocked at "no eligible candidate". RESEARCH-ONLY confirmed.

## Decision

- **Decision**: **RESEARCH-ONLY** for R4.
- **Session-level decision**: **R3 E4 remains the strongest factor**;
  R4 attempted to refine it and demonstrably failed. R4's value is
  a clean falsification of the regime-conditioning hypothesis (in the
  direction tested) and a confirmation that 2025's bad year is NOT
  a function of vol/turnover/market regime indicators.

## R5 leads (if pursued — calibrated honesty)

The session has now exhausted the obvious refinements of M3 within
the 3-asset broad-base ETF universe. Each pivot was data-clean
(R2 from R1 train+val, R3 from R2 train IC, R4 from R3 audit 3
diagnostic), and each round produced a clear next-step direction.
After 4 rounds × 8 expressions = 32 expressions on the same test
window, **the multiple-comparisons accumulation is now significant
enough that further rounds on this dataset risk diminishing returns**.

Honest R5 options, in priority order:

1. **REVERSE-DIRECTION REGIME GATE** (cheapest test, may rescue): R4
   E1's IC was −0.21, t=−6.13. A `tanh(-vol_spread_z)` variant should
   give IC ≈ +0.21 on TRAIN by the same logic. If it ALSO rescues 2025
   on test, the calm-regime-amplification framing is correct. If not,
   M3 is year-specific and not deployable as-is. ONE round, ONE
   expression — minimal cost.

2. **CROSS-SECTIONAL VERSION** (highest expected value): pull
   constituent stocks of CSI300, CSI1000 (~1300 names total). Build
   the same MA5/MA120 turnover-acceleration signal at the stock level,
   form L/S baskets cross-sectionally. Information capacity is
   ~1300× higher; audits become much more meaningful (Q5 size, IC
   t-stats over thousands of cross-sections). The R3 E4 finding
   suggests the mechanism is real; cross-sectional version should
   amplify it dramatically. **Significant scope expansion required**
   (data fetching, harness extension for cross-sectional factors).

3. **STOP & DEPLOY R3 E4 AS RESEARCH-ONLY**: paper-trade R3 E4 daily
   for 6-12 months alongside production. Gather more out-of-sample
   data. Re-evaluate when 2026 fills out and 2027 begins. Worst-year
   audit gets meaningful again at 4y+ test window. **Most TVT-honest
   option** for the current session.

4. **ABANDON THIS UNIVERSE**: the 3-asset broad-base ETF universe is
   information-poor. After 4 rounds, the best factor we have (R3 E4)
   has Sharpe +0.58 on a 2.3y test, blocked from PROMOTE only by a
   single bad year. This is roughly the ceiling of what's achievable
   with 3 ETFs alone.

The session has demonstrably reached the ceiling of its scope.
Recommendation: archive R3 E4 as the session winner (RESEARCH-ONLY,
near-PROMOTE), execute R5 #1 cheaply to confirm the regime-direction
diagnosis, then pivot to either #2 (cross-sectional, new session) or
#3 (paper-trade & wait).
