# Alpha Ranking — Round 0005 (M3 calm-regime amplified, mirror of R4)

Session `20260425_a_share_style_timing_csi300_csi1000` ·
Mechanism family M3_calm_regime_amplified · TVT splits unchanged ·
5 bps/side · delay = 1.

## Headline

> **Decision: RESEARCH-ONLY. R5 mirror gates DIRECTIONALLY confirmed
> (IC signs flipped to thesis-aligned exactly as R4 falsification
> predicted), but every R5 expression fails G3 — gate compression ×
> deadband leaves too few non-zero position days. 0/8 TVT-eligible
> AND all-gates-pass.**
>
> **Strongest sub-finding (diagnostic only)**: R5 E6
> (R3 E2 base × tanh(−vol_z)) has **test Sharpe +0.78 with all 3 test
> years positive** (2024 +1.05 / 2025 +0.30 / 2026 +1.27) — the
> calm-regime-amplification hypothesis IS rescuing 2025 in test. But
> E6 has **val Sh −1.13** (VAL 2022-2023 is an opposite regime for
> this gate) → not TVT-eligible. **There is no single regime gate
> that helps both VAL and TEST**, which is the deepest finding of
> the session: VAL 2022-2023 and TEST 2024-2026 are *structurally
> different regimes* under the M3 mechanism.

## Mirror-gate construction confirmed

R5 was designed as the literal sign-flip of R4 (negate the regime
indicator inside tanh). Mathematical prediction: R5 train IC ≈ −R4
train IC. Observed:

| R4 expr | R4 train IC | R5 expr | R5 train IC | Match? |
|---|---:|---|---:|:-:|
| R4 E1 | −0.206 | R5 E1 | **+0.206** | ✓ exact |
| R4 E2 | −0.217 | R5 E2 | **+0.217** | ✓ exact |
| R4 E3 | −0.056 | R5 E3 | +0.056 | ✓ exact |
| R4 E5 | −0.190 | R5 E5 | +0.190 | ✓ exact |
| R4 E6 | −0.162 | R5 E6 | +0.162 | ✓ exact |

Deviations on E4 (one-sided), E7 (market gate), E8 (combo with
discretization) are expected because the mathematical mirror is not
clean for those constructions. The R4 falsification is now confirmed:
R4's gate direction was wrong; R5's reverse-gate direction produces
the predicted positive IC.

## Eligibility table

| Expr | Train Sh | Val Sh | Eligible | TVT Score | Gates | Test Sh* | Per-year (2024/2025/2026) |
|---|---:|---:|:-:|---:|:-:|---:|:---|
| `r5_e1` | +0.561 | −0.268 | N (val<0) | — | G3 fail (turn 24.9), G4 pass | +0.09 | −0.21 / +0.35 / +0.48 |
| `r5_e2` | +1.239 | +0.102 | Y | −0.24 | G3+G4 fail | −0.07 | −0.25 / +0.12 / 0.00 |
| `r5_e3` | −0.239 | −0.664 | N | — | G3+G4 fail | +0.21 | +0.55 / −0.30 / 0.00 |
| `r5_e4` | +0.876 | +0.348 | Y | +0.19 | G3 fail (non-zero 0.18 < 0.30), G4 pass | −0.09 | −0.21 / −0.27 / +1.24 |
| `r5_e5` | +0.555 | −0.819 | N | — | G3+G4 fail | +0.24 | +0.20 / +0.52 / 0.00 |
| **`r5_e6`** | +0.849 | **−1.133** | **N (val<0)** | — | G3 fail (turn 24.4), G4 pass | **+0.78** | **+1.05 / +0.30 / +1.27** |
| `r5_e7` | −0.239 | −0.743 | N | — | G3 pass, G4 fail (sign) | −0.54 | −1.22 / +1.21 / −0.10 |
| `r5_e8` | +0.946 | **+1.584** | **Y** | **+1.39** | G3 fail (non-zero 0.27), G4 pass | +0.15 | +0.68 / −0.52 / +0.85 |

*Test Sharpes are diagnostic only — no winner selected (no expression
clears all gates), so no frozen-test reportable for selection.

## What G3 actually flagged

The 4 expressions that PASS G4 (E1, E4, E6, E8) all FAIL G3. Three patterns:

1. **Turnover ceiling (E1, E6)**: ann turnover 24.4-24.9 > 20.0 ceiling.
   Two-sided tanh gate doesn't smooth turnover enough; positions flip
   too frequently as gate crosses zero.
2. **Non-zero fraction floor (E4, E8)**: 18-27% non-zero days < 30% floor.
   Gate compression × deadband 0.5 means |gated_score|>0.5 is rare; signal
   spends 70-80% of days at zero position.
3. E2, E5: both turnover and non-zero issues simultaneously.

The G3 "non-zero ≥ 30%" threshold was an adaptation for the 3-asset
universe (proxy for the original "Q5 size ≥ 30 stocks"). The threshold
0.30 is heuristic; relaxing it to 0.20 would let E4/E8 pass. **Not
relaxing per `validation-gates.md` retry rule** ("Do not lower the gate
thresholds in validation-gates.md to make a failing expression pass").

## The deepest finding: VAL and TEST are opposite regimes for M3

R5 E6 is the most informative diagnostic of the session:

| Window | Sharpe | Per-year |
|---|---:|---|
| Train [2018,2022) | +0.85 | 4y favorable to calm-regime gate |
| **Val [2022,2024)** | **−1.13** | calm-regime gate FAILS in 2022-2023 |
| **Test [2024,2026]** | **+0.78** | calm-regime gate WORKS in 2024-2026 (all years +) |

R3 E4 (no gate) had: train +1.13, val +0.44, test +0.58 (2025 = −1.19).
R5 E6 (E2 base + calm gate) has: train +0.85, val **−1.13**, test +0.78.

The calm-regime gate **rescues 2025** (the R3 E4 audit-3 failure year)
but **destroys val 2022-2023**. There is **no single regime gate** that
helps TEST without breaking VAL — VAL 2022-2023 favors the opposite
gate direction (which is what R4's vol-amplifying gate did, and that
in turn breaks TEST).

This is a structural result. **A 4y/2y/2.3y TVT split on this universe
contains regime shifts within each window that no static regime gate
can navigate**. The mechanism is real (R3 E4 + R5 E6 both show real
TRAIN IC ≈ +0.27, t > 8) but the regime structure is too unstable for
an unconditional gate-based approach.

## Mandatory pre-PROMOTE audits

R5 has no winner → no candidate to audit. Round-level falsification
(audit 5) below.

### Audit 5 — falsification

**Most likely single cause** that R5's null result is missing an
opportunity: the val-vs-test regime opposition is a **2-regime**
structure, while we're testing a **1-regime gate**. R6 would need a
**dynamic regime classifier** that learns from train data which regime
is currently active and switches between forward and reverse gates.
This is a substantially more complex hypothesis (requires regime
identification, which itself can over-fit) and exceeds the scope of
"a single mechanical gate".

**The test that would prove it**: build a regime classifier on TRAIN
data using e.g. K-means on (vol_z, turnover_z) → 2 clusters. For each
TRAIN day, identify which cluster it belongs to. Compute M3 IC within
each cluster. If clusters give clearly opposite IC signs, the
2-regime structure is real and a switching strategy could work in
principle. But this introduces 2-3 new degrees of freedom (cluster
boundaries, regime transitions) on top of an already 5-round-tested
test window — multiple comparisons would be off the chart.

## Hard floors for PROMOTE — checkbox (round level, no winner)

- [ ] Test IC t-stat ≥ 4.5 (R5 tighter bar) — no winner to evaluate
- [ ] R5 winner test Sharpe ≥ +0.78 (pre-registered) — no eligible winner; best diagnostic test E6 is +0.78 but fails val/G3
- [ ] Worst-year Sharpe ≥ 0.7 — no winner; best diagnostic worst-year E6 = +0.30
- [x] Execution-delay audit (engine invariant)
- [x] Look-ahead audit

PROMOTE blocked at "no eligible candidate". RESEARCH-ONLY.

## Decision

- **Decision**: **RESEARCH-ONLY** for R5. Session winner unchanged: **R3 E4**.
- **Reason**: 0/8 TVT-eligible AND all-gates-pass. R5 directionally
  confirms R4's falsification but the same gate direction that helps
  test breaks val.
- **Session-level recommendation**: **STOP this session.** R5 is the
  fifth round on the same test window, and the val/test regime
  opposition is structural — further regime-conditioning work cannot
  beat a 2-regime classifier, which would itself overfit on this small
  test window. The session has reached its information-theoretic
  ceiling for the 3-ETF universe.

## R6+ leads (strongly de-prioritized)

After **5 rounds × 8 = 40 expressions on the same test window**, all
plausible single-gate refinements have been tested. R5 confirmed that
the val/test regimes are structurally opposite — **no future single-gate
factor will resolve this** without introducing dynamic regime
classification (which is itself a substantial overfitting risk on this
short test window).

If continuing within this universe is required:

1. **WAIT**: extend test window to 3+ years. Once 2026 fills out and
   2027 begins, the val/test regime opposition will be diluted by more
   data. Re-run R3 E4 with the same TVT split shifted forward; if test
   stays positive on 4-5 years and audit-3 worst year improves, a
   PROMOTE conclusion may become possible. **No coding required;
   just patience.**

2. **EXPAND DATA (new session)**: pull constituent stocks for cross-sectional
   M3 alpha. The 3-asset universe limits information capacity to
   ~+0.6 Sharpe ceiling; cross-sectional (~1300 stocks) should
   amplify by 1-2 orders of magnitude. **This is a new session,
   not a continuation of this one** — different universe, different
   audits (Q5 size, IC t-stats over thousands of cross-sections),
   different cost model.

3. **DEPLOY R3 E4 AS RESEARCH-ONLY PAPER-TRADE**: the strongest
   factor of the session is `r3_e4_amt_accel_5_120_neg`. Test Sharpe
   +0.58, calmar +0.50, near-PROMOTE blocked only by 2025. Paper-trade
   alongside production for 6-12 months; collect OOS data; re-evaluate
   when sample is sufficient.

**Strong recommendation: option 1 (wait) or option 3 (paper-trade as-is).
Option 2 is high-value but deserves a fresh session, not another round
on this dataset.**
