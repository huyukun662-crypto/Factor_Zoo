# Backtest Results — Batch 0001 (Round 1)

**Session:** `20260423_a_share_etf_reversal_v1`
**Agent:** 4 (Backtest Operator)
**Date:** 2026-04-23
**Sample:** 18 A-share ETFs, 2020-01-02 → 2026-04-22, 1,525 trading days
**Rebalance:** every 5 trading days, long top-4 / short bottom-4 by signal
**Cost baseline:** 5 bps / side

---

## 1. Headline: the batch inverts the thesis

All 8 expressions were built under the hypothesis **reversal / dip-buy works
at k=10 trading days on this universe**. The data rejects the hypothesis
at the batch level:

| | value |
|---|---:|
| IC signs matching thesis (positive) | **1 of 8** |
| Gross Sharpe > 0 at baseline | 3 of 8 |
| Net Sharpe > 0 at 5 bps | 3 of 8 (marginal: 0.10 max) |
| G3 pass (includes net_sharpe ≥ -0.5) | 3 of 8 |
| G4 pass (sign + monotonicity + corr) | **0 of 8** |
| G5 batch horizon consistency | **fail** (0 G4 survivors) |

## 2. IC table (primary horizon k=10)

| expression | IC_mean@k5 | IC_mean@k10 | IC_mean@k20 | IC_tstat@k10 |
|---|---:|---:|---:|---:|
| r1_dd20                 | -0.041 | **-0.049** | -0.054 | -5.12 |
| r1_rsi14                | -0.027 | -0.022 | -0.015 | -2.30 |
| r1_bb_pos               | -0.036 | -0.035 | -0.029 | -3.67 |
| r1_logbias_ma20         | -0.017 | -0.020 | -0.016 | -1.96 |
| r1_rev_5d               | -0.024 | -0.022 | -0.034 | -2.12 |
| r1_vol_scaled_rev5      | -0.036 | -0.028 | -0.032 | -2.96 |
| r1_vol_confirmed_rev    | **+0.018** | **+0.020** | +0.015 | **+2.58** |
| r1_kitchen_sink         | -0.033 | -0.032 | -0.031 | -3.22 |

The IC of `r1_dd20` growing in magnitude from k=5 (-0.041) to k=20 (-0.054)
is a textbook **momentum continuation** signature: past losers keep losing,
past winners keep winning, and the effect strengthens slightly with horizon.
This is the opposite of what the Round 1 thesis expected.

## 3. Quintile monotonicity at k=10 (inverted)

Quintiles on `r1_dd20` (high signal = deep dip):

| bin | signal interpretation | 10d fwd log-ret (excess) |
|---:|---|---:|
| Q1 | least dipped / near recent highs | +0.00442 |
| Q2 |   | +0.00303 |
| Q3 |   | +0.00170 |
| Q4 |   | +0.00084 |
| Q5 | deepest dip | +0.00033 |
| **Q5 − Q1** | | **−0.00408** |

Monotonically **decreasing** with dip depth. The 0.41% 10-day spread
(Q1 over Q5) annualized to weekly rebalance is ~10%/year in the wrong
direction — large.

7 of 8 expressions (all except `r1_vol_confirmed_rev`) show the same
inverted monotonicity pattern.

## 4. LS summary (weekly rebalance, top-4 / bottom-4, 5 bps/side)

| expression | gross Sharpe | net Sharpe@5bps | CAGR net | maxdd | annual TO% |
|---|---:|---:|---:|---:|---:|
| r1_dd20                 | -0.45 | -0.52 | -15.3% | -104% | 4247 |
| r1_rsi14                | +0.15 |  +0.10 |  +3.9% |  -85% | 4222 |
| r1_bb_pos               | -0.33 | -0.42 | -14.6% | -118% | 6312 |
| r1_logbias_ma20         | +0.14 |  +0.07 |  +2.4% |  -64% | 5321 |
| r1_rev_5d               | -0.72 | -0.87 | -24.5% | -173% | 9469 |
| r1_vol_scaled_rev5      | -0.19 | -0.34 | -10.5% | -106% | 9361 |
| r1_vol_confirmed_rev    | +0.33 | +0.16 |  +4.7% |  -52% | 9799 |
| r1_kitchen_sink         | -0.40 | -0.49 | -16.1% | -120% | 6098 |

Even the two "positive" signals (`r1_rsi14` +0.10, `r1_logbias_ma20` +0.07,
`r1_vol_confirmed_rev` +0.16 net Sharpe) are far below the 0.5 floor.

Turnover is 4,000-9,800% per year — weekly rebalance on a 20-ETF basket
with a threshold strategy is very high-churn (each rebalance flips ~50%
of the 4-4 book).

## 5. Per-year Sharpe breakdown (net@5bps)

The per-year table (`outputs/per_year_sharpe_batch_0001.csv`) shows
worst-year Sharpe ≤ -2.3 on 5 of 8 expressions — nowhere near the
`worst_year_sharpe ≥ 0` floor.

## 6. Validation gates summary

| gate | result | notes |
|---|:---:|---|
| G1 syntax | 8/8 pass | script imports and runs |
| G2 runs   | 8/8 pass | no exceptions |
| G3 non-degenerate | 3/8 pass | `r1_rsi14`, `r1_logbias_ma20`, `r1_vol_confirmed_rev` clear the net-Sharpe ≥ -0.5 floor; the other 5 fail |
| G4 fidelity | **0/8 pass** | all 8 fail one or more of: (a) IC sign ≠ thesis, (b) quintile monotonicity inverted, (c) corr vs universe EW |
| G5 batch horizon | **fail** | 0 G4 survivors — cannot evaluate peak-k distribution |

## 7. Falsification-first

> If my verdict ("reversal is not the mechanism here") is wrong by 50%,
> what is the most likely single cause?

- **Most likely**: the primary horizon k=10 is too short. Classical
  long-term reversal (De Bondt-Thaler) is 3-5 years; 10 trading days
  sits squarely inside the intermediate-momentum regime (Jegadeesh &
  Titman 1993: 3-12 month momentum). The IC's monotone growth in
  magnitude from k=5 to k=20 is consistent with this. Round 2 should
  test k ∈ {60, 120, 250}.
- **Second most likely**: weekly rebalance on 20 ETFs amplifies turnover
  cost (9,800%/yr on `r1_rev_5d`). If monthly rebalance reduces
  turnover to 2-3000%/yr, the cost drag shrinks ~5×, but the NEGATIVE
  IC cannot flip to positive via cost reduction alone.
- **Third**: the threshold strategy (top-4 / bottom-4) on |universe|=18
  is noisy — Q1 and Q5 are 4 names each. A rank-weighted portfolio
  would be smoother but wouldn't invert the IC sign.

None of these inverts the thesis. The Round 2 action is to test the
long-horizon reversal hypothesis (k ∈ {60, 120, 250}) AND keep one
"narrow-condition" reversal (1-day intraday, deep-dip only) as a
hedge against the first-order finding being window-specific.

## 8. Round 1 verdict

**RESEARCH-ONLY (do not promote any expression from this batch).**

**G5 interpretation**: this batch fails the "mechanism = reversal at k=10"
hypothesis at the batch level. Per `references/validation-gates.md`, G5
failure returns to Agent 2 for re-specification, not to Agent 3 for
expression repair.

**Return to Agent 2 diagnostic**: "Batch IC is uniformly negative at
k∈{5,10,20}, monotonically growing in |IC| with k. The mechanism at
this horizon is momentum continuation, not reversal. Re-specify:
either (a) flip to long-horizon reversal (k ∈ {60, 120, 250}) OR
(b) pivot to explicit momentum and close this session."

Choosing (a) — Round 2 tests long-horizon reversal + narrow-condition
reversal variants to preserve the reversal mandate before closing.

## 9. Files

- `outputs/ic_table_batch_0001.csv`
- `outputs/ls_summary_batch_0001.csv`
- `outputs/decile_summary_batch_0001.csv`
- `outputs/cost_sensitivity_batch_0001.csv`
- `outputs/per_year_sharpe_batch_0001.csv`
- `outputs/validation_gates_batch_0001.json`
