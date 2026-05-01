# Alpha Ranking — IVOL-Reversal v1, Batch 0001

Owner: Agent 5 (Evaluator & Recorder).
Generated: 2026-05-01.

## Summary verdict

**STOP — original hypothesis falsified. RESEARCH-ONLY for the inverted variant.**

The classical Ang-Hodrick-Xing-Zhang IVOL anomaly **does not hold** on
A-share thematic ETFs in 2019-2026. The cross-sectional sign is the
opposite of the equity-stock literature: high-IVOL ETFs OUTperform
low-IVOL ETFs across all tested horizons.

## What the data showed

### G5 batch-level horizon consistency — FAIL

Round-1 declared primary horizon was k=5 (weekly). All 8 expressions
peaked at k=1 instead. Per workflow rules this is an Agent-2 horizon
mis-specification (not an Agent-3 retry). A round-2 metadata revision
moved primary k to 1.

### Round 2 (k=1, daily rebalance, 5 bps/side cost)

| expr | LS gross | LS net@5bps | longonly | excess | turnover% | wy_pass |
|---|---:|---:|---:|---:|---:|---|
| f1_ivol_resid_20d   | -0.61 | -0.73 | +0.47 | -0.69 | 1074 | False |
| f2_total_vol_20d    | -0.67 | -0.82 | +0.68 | -0.61 | 1622 | False |
| f3_ivol_resid_10d   | -0.59 | -0.80 | +0.44 | -0.53 | 2102 | False |
| f4_ivol_resid_40d   | -0.66 | -0.72 | +0.56 | -0.55 |  555 | False |
| f5_ivol_resid_amp_20d | -0.67 | -0.79 | +0.44 | -0.72 | 1147 | False |
| f6_ivol_lag5_20d    | -0.67 | -0.79 | +0.43 | -0.72 | 1066 | False |
| f7_vol_of_vol_20m40 | -0.29 | -0.61 | +0.61 | -0.06 | 3810 | False |
| f8_kitchen_sink     | -0.65 | -0.86 | +0.41 | -0.78 | 2254 | False |

Every long-short Sharpe is **negative**. Long-only sharpe is positive
because the universe trends up, but the long-only excess vs the EW
universe is also **negative** — Q5 (low-IVOL) underperforms the average
ETF.

### Why IC t-stat at k=1 was misleading

IC t-stat at k=1 was +3.0 to +3.4 (Round 1, several expressions). That
positive IC reflects a slight cross-sectional rank correlation across
ALL ranks. The decile table (k=5) shows the truth:

| quintile | f1_ivol_20d ann_ret | f5_ivol_amp ann_ret |
|---:|---:|---:|
| 1 (high-IVOL, the SHORT leg) | **+24.6%** | **+25.6%** |
| 2 |  +9.8% |  +9.0% |
| 3 | +14.0% | +14.7% |
| 4 | +15.8% | +15.2% |
| 5 (low-IVOL, the LONG leg) |  +6.7% |  +6.5% |

The relationship is non-monotonic (Q1 highest, Q2 lowest, then
recovery). LS = Q5 - Q1 = -18% annualized, the wrong direction.

This is the **`common-pitfalls.md` Pitfall 11 / IC-vs-LS dispersion
trap**: a small positive Spearman IC can coexist with a wrong-signed
LS when the cross-section is non-monotonic.

### Inverted-sign sensitivity (long high-IVOL, short low-IVOL)

If we flip the directional convention — long Q5 = high-IVOL, short
Q1 = low-IVOL — the picture changes. Tested on f1_ivol_resid_20d
(headline expression, sign flipped):

| Horizon | Rebalance | LS gross | LS net@5bps | turnover% | worst-year |
|---:|---:|---:|---:|---:|---:|
| k=1  | daily   | +0.57 | +0.45 | 1740 | -0.37 |
| k=5  | weekly  | +0.67 | +0.66 |  857 | -0.03 |
| k=20 | monthly | +0.66 | +0.66 |  436 | +0.04 |

Per-year LS at k=20 monthly:

| 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---:|---:|---:|---:|---:|---:|---:|
| 1.83 | 0.93 | 0.76 | 0.18 | 0.19 | 0.04 | 1.56 |

All years positive but 2022/2023/2024 below the 0.5 floor.

| Floor | Required | Inverted f1 (k=20 monthly) | Pass |
|---|---:|---:|---|
| LS Sharpe gross | ≥ 1.0 | +0.66 | ❌ |
| LS Sharpe net @5bps | ≥ 0.7 | +0.66 | ≈ borderline |
| Worst-year Sharpe | ≥ 0.5 | +0.04 (2024) | ❌ |
| Best-year-out Sharpe | ≥ 50% × 0.66 = 0.33 | 0.61 | ✅ |
| Annual turnover | ≤ 600% | 436% | ✅ |

The inverted variant is **RESEARCH-ONLY**: real signal exists but the
worst-year floor blocks PROMOTE.

## Ranking (round 2, original-sign convention)

All 8 expressions are tied for last — none has positive LS Sharpe, none
passes any floor. Reporting them in IC t-stat order at k=1:

1. f6_ivol_lag5_20d        — IC t=+3.36 @ k=1, LS=-0.67, longonly_excess=-0.72
2. f1_ivol_resid_20d       — IC t=+3.19 @ k=1, LS=-0.61, longonly_excess=-0.69
3. f5_ivol_resid_amp_20d   — IC t=+3.00 @ k=1, LS=-0.67, longonly_excess=-0.72
4. f3_ivol_resid_10d       — IC t=+3.01 @ k=1, LS=-0.59, longonly_excess=-0.53
5. f4_ivol_resid_40d       — IC t=+2.91 @ k=1, LS=-0.66, longonly_excess=-0.55
6. f8_kitchen_sink_rank    — IC t=+2.38 @ k=1, LS=-0.65, longonly_excess=-0.78
7. f2_total_vol_20d        — IC t=+1.57 @ k=1, LS=-0.67, longonly_excess=-0.61
8. f7_vol_of_vol_20m40     — IC t=-0.18 @ k=1, LS=-0.29, longonly_excess=-0.06

## Mandatory audits

| Audit | Result |
|---|---|
| Execution-delay (target_shift == -(1+delay), delay=1) | PASS |
| Look-ahead (perturb last-30d bench, check past unchanged, max diff < 1e-12) | PASS |
| Worst-year floor (≥ 0.5) | FAIL (all expressions, all signs) |
| Best-year-out (≥ 50% headline) | N/A (headline negative for original sign) |
| Falsification-first | "If LS is wrong by 50%, what's the most likely cause?" Answer pre-run: bull-market short-leg destruction. Test ran: high-IVOL Q1 returns +24.6% — exact match to the falsification hypothesis. The mechanism is not just regime-fragile, it's directionally wrong in A-share ETFs. |

## Decision

**STOP** the IVOL-reversal hypothesis as originally framed. The IVOL
anomaly is inverted in A-share ETFs.

Open research thread for **IVOL-momentum** (the inverted-sign variant)
in a future session. The factor has consistent positive years and
clean cost structure at monthly rebalance, but worst-year < 0.5 keeps
it RESEARCH-ONLY. A future session should:

1. Combine inverted IVOL with a regime gate (e.g., MA50 broad-market
   filter) — 2024 was the bad year and was a deleveraging regime;
   gating away from down-trend regimes may rescue the worst-year.
2. Test long-only top-3 instead of LS — long-only ann ret was +0.70-0.75
   Sharpe and the EW universe is the deployable benchmark in A-share.
3. Cross-check vs the V7_gold weekly factor in `logs/20260422_industry_rotation_cn`
   — if inverted IVOL is highly correlated with V7's already-deployed
   momentum signal, it adds nothing.

## Lessons for the next round

1. **Always inspect deciles before declaring an LS sign.** A positive
   Spearman IC is consistent with a non-monotonic decile pattern.
2. **A-share ETFs invert several equity-stock anomalies** because the
   universe IS the narrative buckets retail bids up. Test sign in both
   directions before committing.
3. **G5 saved one round.** Without horizon-consistency, we would have
   reported a -0.61 weekly Sharpe and called it "the IVOL anomaly
   doesn't work" — missing that the strongest signal IS at k=1, just
   in the wrong direction.
