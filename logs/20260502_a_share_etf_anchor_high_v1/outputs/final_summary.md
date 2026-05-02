# Final Summary — A-share ETF Anchor / 52W-High Proximity v1 (post-R2)

**Decision:** RESEARCH-ONLY (confirmed and tightened in Round 2).
**Honest lead candidate:** F4 = multi-window range-position rank,
top-5 long-only excess (single-phase Sharpe 0.65 — pending
phase-rotation re-test).
**Promotable:** No — fails worst-year LS Sharpe ≥ 0.5 floor under
*any* phase, fails phase-rotation robustness floor on the original
R1 lead.

## Two-round arc

### Round 1 (initial 8 expressions)
- Falsified the literal G&H 52w-high proximity (E1 LS ≈ 0; E8 sign
  flip only 0.04 worse).
- Identified E3 = `range_pos_252` = `(p-min_252)/(max_252-min_252)`
  as the working factor with single-phase LS Sharpe 0.628 net.
- Worst-year LS -0.18 failed the 0.5 floor → RESEARCH-ONLY.

### Round 2 (8 E3-centric variants + phase-rotation audit)
- **Critical finding**: the R1 number 0.628 is the single-best
  phase out of 21 possible rebalance offsets. Phase-averaged LS
  Sharpe collapses to **0.239 ± 0.245** (top-5 long-only excess
  to 0.12).
- F2 (window=120) and F3 (window=60) gave higher single-phase LS
  Sharpe (0.41) but with even worse worst-year (-1.57, -0.68).
- F4 (multi-window rank average) gave the cleanest top-5 long-only
  number at 0.65 net but is also single-phase.
- F6 (MA200 risk-on gate) materially improved worst-year (-0.19)
  but its test-window Sharpe is -0.08 → rejected.
- F7 (residualization vs 252d momentum) retains 48% of F1's signal
  → factor is half momentum-clone, half genuine range-position
  effect.

## Honest E3 numbers (phase-averaged across 21 offsets)

| metric                           | value         |
|----------------------------------|---------------|
| LS Sharpe (gross, phase-avg)     | 0.239         |
| LS Sharpe std across phases      | 0.245         |
| LS Sharpe min phase / max phase  | -0.23 / 0.64  |
| top-5 long-only excess (phase-avg)| 0.121        |
| top-5 phase min / max            | -0.37 / 0.60  |
| Median worst-year LS across phases| -0.84        |
| Best phase-averaged year (LS)    | 2023 (+1.34)  |
| Worst phase-averaged year (LS)   | 2022 (-0.62)  |
| Best phase-averaged year (top-5) | 2023 (+1.34)  |
| Worst phase-averaged year (top-5)| 2022 (-0.63)  |

## Five mandatory audits — final disposition

| audit                              | R1     | R2 (after phase rotation) |
|------------------------------------|--------|---------------------------|
| Execution-delay                    | PASS   | PASS                      |
| Look-ahead randomization           | PASS   | PASS                      |
| Worst-year LS Sharpe ≥ 0.5         | FAIL   | FAIL (worse: median -0.84)|
| Best-year-out ≥ 50 % of headline   | PASS   | PASS only on phase-0      |
| Falsification-first (E1 vs E8)     | PASS   | PASS                      |
| **Phase-rotation robustness (new)**| —      | FAIL                      |

## Why phase rotation matters

In a daily-data world, a strategy with `rebal=21` has 21 possible
starting offsets. Live deployment can pick exactly one (or rotate
across all 21 with 1/21 capital each, "phase averaging"). The
single-phase Sharpe is a sample of size 1 from a distribution
whose realized std is 0.25 — a 95 % CI on the single-phase
estimator is roughly ±0.5 Sharpe units, larger than the headline
itself. Picking phase 0 because it is "the natural starting
offset" introduces selection bias relative to an investor who
deploys at an arbitrary calendar moment.

This pitfall is **not currently in
`worldquant-5-agent-workflow/references/common-pitfalls.md`**.
Recommend appending it as a new pitfall in any future iteration of
the skill package.

## What is genuine here

1. The cross-sectional range-position effect is positive on
   average — 16 of 21 phases produce LS Sharpe > 0.
2. The mechanism is half momentum (residualization shows 48 %
   retention) and half something else, plausibly the anchoring
   component this study set out to test, but with weaker effect
   size than G&H reported on US single-stocks.
3. F4 (multi-window long-only top-5) compresses phase noise
   in the long leg and is the most defensible R3 candidate.
4. 2023 was the dominant tailwind year (LS +1.34 even after phase
   averaging); 2022 was the floor (-0.62).

## What is NOT supported by the data

- A "0.63 LS Sharpe" headline for E3, full stop. That number is
  conditioned on phase-0 rebalancing and should not be reported
  without the phase-rotation distribution alongside.
- The R1 alpha_ranking.md's "0.49 net top-5 long-only excess
  Sharpe" claim — phase-averaged is 0.12.

## Recommended sleeve disposition

> Reject E3 phase-0 as a standalone sleeve.
> If the reader still wants exposure: hold the **phase-averaged
> top-5 long-only basket** with 1/21 capital deployed every
> trading day (1-month rolling holding, full universe coverage).
> Expected long-only excess return ~0.12 Sharpe; expected
> annualized turnover ~9; expected worst-year drawdown -3 %.
> Treat as a **research sleeve at single-digit % capital max**.

## R3 backlog (not run in this session)

1. Phase-rotation re-test of F4 multi-window top-5.
2. F4 + F6 combined (multi-window + risk-on gate) — F6 was the
   only variant with a meaningful worst-year improvement.
3. Lengthen the universe to include Hong Kong-listed China ETFs
   for cross-validation.
4. Bootstrap confidence intervals on the phase-averaged Sharpe to
   distinguish 0.12 ± noise from 0.12 ± 0.04.
5. Add phase-rotation as a **G6 validation gate** in the skill
   package and a Pitfall #13 in `common-pitfalls.md`.
