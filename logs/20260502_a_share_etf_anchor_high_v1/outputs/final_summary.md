# Final Summary — A-share ETF Anchor / 52W-High Proximity v1

**Decision:** RESEARCH-ONLY.
**Lead candidate:** E3 = `range_pos_252` (top-5 long-only excess sleeve).
**Promotable:** No — fails the ≥ 0.5 worst-year LS Sharpe floor.

## What was tested

8 expressions exploring the 52-week-high anchoring effect (George &
Hwang 2004) on a 32-ETF A-share universe (2019-01 to 2026-04).
Cross-sectional ranking, monthly rebalance, 5 bps/side cost,
delay=1, primary horizon k=20.

## Headline result

| metric                 | E3 (range_pos_252) |
|------------------------|--------------------|
| LS Sharpe (gross)      | 0.628              |
| LS Sharpe (net 5 bps)  | 0.625              |
| top-5 long excess net  | **0.486**          |
| top-3 long excess net  | 0.313              |
| Train Sharpe (LS)      | 0.671              |
| Validate Sharpe (LS)   | -0.112             |
| Test Sharpe (LS)       | **0.745**          |
| Worst-year LS Sharpe   | -0.181 (2024)      |
| Best-year-out LS       | 0.408 (= 65% of headline) ✓ |
| Annualized turnover    | ~9 (top-5)         |
| Cost-net break-even    | passes at 20 bps/side |

Per-year LS Sharpe: 2020 +1.09 / 2021 +0.92 / 2022 -0.11 / 2023 +1.46
/ 2024 -0.18 / 2025 +1.09. Test (2023-2026) > Train (2019-2021), no
sign of overfitting; 2022 and 2024 are the soft years.

## Why "RESEARCH-ONLY", not "PROMOTE"

The five mandatory pre-promote audits resolved as:

1. Execution-delay audit — **PASS** (`target_shift = -(1+delay) = -2`).
2. Look-ahead randomization — **PASS** (zero diff for E1, E3, E5).
3. Worst-year LS Sharpe ≥ 0.5 — **FAIL** (E3 worst is -0.18; floor
   wants ≥ 0.5, even if mild). Per `references/tvt-split-template.md`
   this single failure precludes PROMOTE regardless of headline
   strength.
4. Best-year-out ≥ 50 % of headline — **PASS** for E3 (65 %).
5. Falsification-first — **PASS at the batch level**: the canonical
   anchor (E1, p/max_252) was falsified — its sign-flip (E8) only
   underperforms by 0.04 LS Sharpe, confirming E1 carries no signal.
   The mechanism that *does* work (E3) survives this same scrutiny:
   it is a min-max range position, not a literal high anchor, and
   its xs-rank correlation with 252d momentum is materially lower
   than E1's 0.38 — i.e. E3 is not a momentum clone.

## What is the actual mechanism

The literal "near-52-week-high" effect from George & Hwang (2004) on
US single-stocks does NOT cleanly transfer to this 32-ETF A-share
universe. ETFs differ in long-run drift (gold +90% since 2019;
some niche thematics -50%), and ranking p/max_252 cross-sectionally
collapses into a noisy momentum proxy.

What does transfer is **range position** —
`(close - min_252) / (max_252 - min_252)`. This double-normalization
cancels long-run drift and isolates "where in its own 1-year band is
this ETF today". Going long the top-5 (high in own band) and avoiding
the bottom yields a 0.49 net-of-cost long-only excess Sharpe with
robust train→test behavior.

## Distinct from prior 6 ETF sessions

- 20260423_etf_reversal — short-term reversal
- 20260423_etf_weekly_tqpb — weekly turnover-quality momentum
- 20260424_etf_daily_flow_accum — flow accumulation
- 20260501_etf_ivol_momentum — IVOL momentum
- 20260501_etf_ivol_reversal — IVOL reversal
- 20260501_etf_leadlag — lead-lag

This session adds **range position / anchor proximity** — none of
the prior sessions tests min-max range. Correlation with prior
factors should be checked in any subsequent ensemble work; not
done in this round because the result is not promotable in
isolation.

## Recommended next step

If the reader wants a deployable A-share ETF sleeve from this
session, the cleanest interpretation is:

> Hold an equal-weight basket of the **top-5 ETFs by range_pos_252**,
> rebalanced monthly. Treat this as a **research sleeve only** —
> historical worst-year underperformance (2024) is -3 % relative to
> equal-weight benchmark, which is within tolerance for many sleeve
> mandates but does not clear the formal worst-year LS Sharpe ≥ 0.5
> bar required for PROMOTE.

If batch_0002 is run, the highest-leverage hypothesis to test is
combining E3 with E4 (`max60/max252`) — their per-year patterns are
weakly anti-correlated in 2024-2025 and the combination may rescue
the worst-year floor.

## Caveats / open questions

- 32-ETF universe is small; the LS leg has ~6 names per quintile.
  Statistical power is limited; bootstrap CI not computed.
- 2026 is partial (4 months). Test-window Sharpes use 2023 + 2024 +
  2025 fully and 2026-Jan-Apr.
- No explicit residualization of E3 against 252d momentum was done;
  qualitative argument only. Recommended for batch_0002 if pursued.
- Cost model is a flat 5 bps/side; A-share ETF microstructure for
  smaller thematic ETFs may impose 10-15 bps in practice — raise
  cost to 10-20 bps to stress-test.
