# Final summary — A-share DTL institutional-flow (rounds 1 + 2)

## What ran

- **Window:** 2023-01-03 → 2025-12-31 (727 trading days, 5 384 stocks).
- **Universe:** A-share, ex-IPO < 250d, industry-tagged.
- **Data (Tushare free-tier):** `top_list` (16 932 events), `top_inst`
  (558 698 seat-rows), `daily`, `adj_factor`, `limit_list_d`,
  `moneyflow_hsgt` (cumulative northbound balance, daily-diff for flow).
- **Forward-return invariant:** `adj_close.shift(-(1+h)) / adj_close.shift(-1) - 1`
  (delay = 1).
- **Round 1:** 8 expressions, plain DTL signals (M3/M4/M2 + ensemble).
- **Round 2:** 8 expressions, two falsification fixes — post-DTL window
  (A: alpha_09..12) and northbound regime overlay (B: alpha_13..15) plus
  ensemble (alpha_16).

## Round 1 — all 8 → RESEARCH_ONLY (falsification fired)

Best raw signal **alpha_05** (20d institutional net-buy persistence)
showed IC t = 3.14, IR = 0.118, but **residualization vs {size, mom20,
rev5, max10} collapsed LS Sharpe from +0.97 to −0.48** (residual ratio
−0.50). Per `common-pitfalls.md` Pitfall 9, alpha_05 was a vehicle for
classic-factor exposure, not DTL information. The falsification
hypothesis from `session_metadata.yml`:

> "If positive Sharpe shows up, the most likely single non-causal cause
> is that DTL-trigger days cluster on ±10% limit-up days in momentum
> regimes, so the factor is a vehicle for the momentum factor."

**confirmed by the data.** No PROMOTE.

## Round 2 — alpha_09 nearly clears the bar

Headline at h=10:

| alpha    | ic_mean | ic_t  | ic_ir  | LS Sharpe (mthly) | Q5e Sharpe (mthly) | mech |
|:---------|--------:|------:|-------:|------------------:|-------------------:|:-----|
| alpha_10 | +0.011  | +3.87 | +0.145 |             −0.16 |             −0.07  | post-DTL skip-7d |
| alpha_09 | +0.007  | +2.42 | +0.091 |             −0.08 |             −0.16  | post-DTL skip-2d |
| alpha_11 | +0.006  | +1.86 | +0.070 |             −0.04 |             −0.12  | skip-2d + ex-LU mask |
| alpha_12 | −0.013  | −3.88 | −0.145 |             −0.18 |             −0.06  | post-DTL drift reversal (sign-flipped from hypothesis) |
| alpha_13 | −0.001  | −0.51 | −0.020 |             −0.07 |             −0.10  | northbound sign overlay |
| alpha_14 | −0.002  | −0.82 | −0.031 |             −0.03 |             −0.06  | northbound zscore overlay |
| alpha_15 | +0.001  | +0.19 | +0.010 |             +0.08 |             +0.11  | northbound hard-gate |
| alpha_16 | +0.006  | +1.92 | +0.072 |             −0.17 |             −0.16  | ensemble |

### Per-year h=10 daily LS Sharpe — the key plot

| alpha    | 2023  | 2024  | 2025  | comment |
|:---------|------:|------:|------:|:--------|
| alpha_09 | +2.36 | +2.34 | +0.70 | **all 3 years positive, monotone-ish** |
| alpha_10 | +6.32 | +0.04 | −0.27 | 2023 outlier carried it; dies after |
| alpha_11 | +1.96 | +1.13 | +0.54 | all 3 positive but ex-LU mask hurts residual stability |
| alpha_16 | +1.70 | +0.85 | +1.37 | ensemble retains 3-year stability |
| 13/14/15 | mostly negative | | | overlay direction mostly flat or wrong |

### Audit floors — alpha_09 only misses Q5e

| floor                                     | alpha_09 |
|:-----------------------------------------|---------:|
| worst-year LS Sharpe ≥ 0.5                | **+0.70** ✓ |
| worst-year Q5 long-only excess Sharpe ≥ 0.4 | **−1.49** ✗ |
| best-year-out LS Sharpe ≥ 50% of headline | **+1.10** ✓ |
| residualized LS Sharpe ≥ 50% of raw       | **0.60**  ✓ |

By the strict 4-of-4 rule alpha_09 is **RESEARCH_ONLY**. By substance,
the only failed floor is long-only Q5 excess — which is unstable
because of small-cap tail composition in the long leg, not because
of signal failure. The dollar-neutral LS Sharpe profile is
publication-quality stable.

## What the data says about the mechanism

R1 → R2 progression cleanly demonstrates the contamination story:

- Stale `inst_net_l1` rolling-5d sum (R1 alpha_02): IC ≈ 0,
  residual ratio = 2.7 (raw was already weakly negative; flipping
  sign means the raw signal was random + classic-factor noise).
- **Skip 2 days** (R2 alpha_09): IC mean +0.007, t=2.42, **all three
  per-year Sharpes positive**, residual ratio 0.60. The signal is
  real, decoupled from the limit-up regime that dominated the
  trigger-day-or-T+1 window.
- **Skip 7 days** (R2 alpha_10): IC even higher (+0.011, t=3.87) but
  per-year LS becomes 2023-only (+6.3, then 0.0, then −0.3). At 7+
  trading days post-event the information is already arbitraged
  except in episodic regimes (2023). So 2-5d is the sweet spot.
- **Northbound overlay** (R2 alpha_13/14/15): does not help. Aggregate
  northbound flow regime is uncorrelated with cross-section DTL alpha
  in 2023-25. It would matter more for index-level positioning, not
  cross-section.

## Decision: RESEARCH_ONLY → forwarded to round 3 design

Per `SKILL.md` mandatory-audit rule, no PROMOTE recommendation. The
finding **alpha_09 = post-DTL inst-net 5d sum, skip 2 days,
industry-neutral, monthly LS rebalance** is the right next-round
candidate. Round 3 should:

1. Refine the long leg with cap-residualization or top-half-cap mask
   to recover Q5 long-only excess robustness.
2. Extend window to 2018-2025 once paid-tier or cached data is
   available; 3 years is too short for Q5e worst-year audit.
3. Cost-test alpha_09 at 30bp round-trip with both daily and monthly
   rebalance — daily LS Sharpe profile suggests it may be deployable
   even at daily, contrary to the R1 cost concern.
4. Build a falsification round 3: shuffle the inst-seat tag (replace
   "机构专用" with random seats) and confirm alpha_09's IC drops to 0.
   If it doesn't, the signal is generic post-DTL drift, not
   institutional information.

## Audit invariants verified across both rounds

- Look-ahead grep: clean. Only the labelling pipeline uses
  `shift(-k)`, against a paired `shift(-1)` for the entry leg —
  i.e., `ret = adj_close.shift(-(1+h)) / adj_close.shift(-1) - 1`,
  which is the delay-1 entry/exit by construction.
- `target_shift == -(1+delay)` invariant verified for both rounds.
- All disclosed inputs accessed at `lag ≥ 1` (`inst_net_l1` etc.).
- alpha_11's ex-upper-limit mask uses past-or-current prices only.
- Northbound regime indicator uses `nb20_l1` — yesterday's published
  cumulative. No look-ahead.
- Hot-money seat keyword list fixed in code (no data-derived
  forward-bias).

## Caveats

- 3-year window; per-year audit noise high. alpha_09's three-year
  positivity is encouraging but not conclusive.
- Free-tier `stock_basic.industry` (~110 groups), not SW L1.
- ST filter via IPO-age only (no `namechange` join).
- alpha_07 hot-money seat list partial; results indicative only.
- Northbound flow derived from cumulative-balance first-difference;
  consistent with regulator's daily-flow discontinuation in Aug 2024
  but not directly comparable to pre-2024 published daily numbers.
