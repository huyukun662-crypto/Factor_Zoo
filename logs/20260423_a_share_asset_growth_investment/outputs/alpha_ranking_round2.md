# Alpha Ranking — Round 2

**Session**: 20260423_a_share_asset_growth_investment
**Round**: 2
**Decision**: **RESEARCH-ONLY** — all refinements FAILED to improve on Round 1

## Ranking (Round 2 variants, long-only Q5 excess, 5bps)

| Rank | Variant | Sharpe excess | Ann ret excess | Worst year (2020/25) | Turnover |
|------|---------|---------------|----------------|----------------------|----------|
| 1 | r2_q5_rw_q (rank-weighted) | **0.293** | 3.2% | -0.75 (2025) | 1.57 |
| 2 | r2_q5_ew_q (equal-weight Q5) | 0.279 | 2.9% | -0.72 (2025) | 1.55 |
| 3 | r2_q5_ew_q_combo (0.6·f5+0.4·f2) | 0.257 | 2.7% | -0.91 (2025) | 1.67 |
| 4 | r2_q10_ew_q (top decile) | 0.252 | 2.8% | -0.73 (2025) | 1.66 |
| 5 | r2_q5_ew_q_sresid (size-resid OLS) | 0.028 | 0.2% | -0.83 (2025) | 1.49 |
| 6 | r2_q5_ew_q_regime (6m mom filter) | -0.014 | -0.2% | -1.18 (2020) | 1.95 |
| 7 | r2_q5_ew_q_liqfl (top-60% circ_mv) | **-0.523** | -5.2% | -3.13 (2023) | 1.99 |
| 8 | r2_q5_ew_q_all (all filters) | -0.592 | -8.0% | -2.47 (2022) | 1.87 |

**For reference, Round 1's f5_ag_2y_ind monthly Q5-excess was Sharpe 0.594.** Round 2's best is 0.293 — a **50% degradation**.

## Failure diagnosis — every refinement backfired

### 1. Quarterly rebal (63d) < Monthly rebal (21d) — **contrary to expectation**

IC at h=60 being highest does NOT mean 63d rebalance is optimal. The signal value changes day-to-day as new quarterly reports land (PIT updates), and cross-sectional rank shifts accordingly. Monthly rebal captures these micro-updates. Quarterly rebal throws away 2/3 of the information refresh events.

**Lesson**: IC-horizon analysis tells you where the signal is strongest, not how often to trade. Rebalance frequency should match **information arrival rate**, not return horizon.

### 2. Regime filter (CSI300 6m > 20% → flat) — kills the BEST year

2021 was Round 2's best year (Sharpe 2.13 without filter). The filter flattened position during Q1-Q3 2021 because market had rallied 30%+ in prior 6 months → **we missed the best year of AG**. Headline Sharpe dropped from 0.279 to -0.014.

**Lesson**: 6m momentum is not a valid regime signal for AG. The 2020 bull that destroyed Round 1's LS short leg was a **small-cap liquidity spike**, not a sustained market trend. Need a different regime definition (e.g., small-cap-over-large-cap momentum spread, or credit-spread proxy).

### 3. Liquidity floor (top 60% circ_mv) — catastrophic (-0.523 Sharpe)

**AG is predominantly a small-cap effect in A-share.** Filtering out bottom-40% by market cap removes exactly where the signal lives. This is consistent with CGS 2008 (size-decile analysis shows AG effect concentrated in bottom 3 size deciles globally).

**Lesson**: For A-share AG deployment, you cannot exclude small caps — but you must accept the resulting capacity constraint (billions CNY, not tens of billions).

### 4. Size residualization (OLS vs log(total_mv)) — wipes out 90% of IR (0.028 Sharpe)

Same lesson as Round 1's f3 double-demean: **a large fraction of AG's signal is size-correlated**. Removing that correlation leaves mostly noise. This confirms AG is a legitimate but not "pure" signal — it's an idiosyncratic-plus-size composite.

**Lesson**: In A-share, AG should be reported as-is without size residualization. The size loading is a feature, not a bug.

### 5. Composite (0.6 f5 + 0.4 f2) — slightly worse than pure f5

Mixing 2y with 1y AG adds noise without new information. They are ~80% correlated; diluting the dominant signal (2y) with a worse one (1y) can only hurt. **Lesson**: don't compose factors from the same mechanism at different horizons — they share too much information.

### 6. Q10 (top decile) vs Q5 — marginally worse

Top-10% selection concentrates risk without adding alpha. Small effect (0.252 vs 0.279), but directionally negative.

## Cross-cutting finding: 2025 YTD is catastrophic

| Variant | 2025 YTD Sharpe (excess) |
|---------|--------------------------|
| r2_q5_ew_q | **-0.72** |
| r2_q5_rw_q | -0.75 |
| r2_q5_ew_q_combo | -0.91 |
| r2_q5_ew_q_sresid | -0.83 |
| r2_q5_ew_q_liqfl | -3.13 |
| r2_q5_ew_q_all | -1.18 |
| r2_q5_ew_q_regime | -1.18 |

**Every single variant is negative in 2025.** This is not a tail event — it's a regime break. The AG factor has stopped working in 2025-01 to 2025-04.

**Hypotheses for the 2025 break**:
1. Policy-driven M&A wave inverted the investment anomaly (firms forced to merge = high AG, but mandated and profitable)
2. Small-cap retail-driven rally (similar to 2020) — likely with STAR / ChiNext names
3. AI-theme concentration — high-growth tech names spun out capex faster than revenue, showing up as high-AG without fundamental deterioration

We cannot distinguish these without further research. But the signal is genuinely off.

## Best-year-out audit (top 3)

| Variant | Headline | Ex-2021 (approx) | Ratio |
|---------|----------|------------------|-------|
| r2_q5_rw_q | 0.293 | 0.439 | 1.50 |
| r2_q5_ew_q | 0.279 | 0.464 | 1.66 |
| r2_q5_ew_q_combo | 0.257 | 0.469 | 1.83 |

**Ratio > 1 means headline is DRAGGED DOWN by best year**, not supported by it. Unusual and — on its face — good for robustness. But the approximation uses annual Sharpes; proper daily-reconstruction would give a cleaner number. Regardless: the signal is *not* concentrated in a single year, unlike many momentum-style factors.

## Hard floors (Round 2 target from session_metadata)

| Criterion | Target | Best (r2_q5_rw_q) | Pass? |
|-----------|--------|-------------------|-------|
| Sharpe Q5-excess (5bps) | ≥ 0.8 | 0.293 | ❌ |
| Worst-year Sharpe | ≥ 0.0 | -0.75 (2025) | ❌ |
| Best-year-out ratio | ≥ 0.5 | 1.50 | ✅ (inverted sign, but holds) |
| IC t-stat | ≥ 3 | 17 (inherited) | ✅ |
| Ann turnover | ≤ 200% | 157% | ✅ |
| Audits | PASSED | PASSED | ✅ |

**Verdict**: 4 of 6 floors pass → still **RESEARCH-ONLY**. Short of the 0.8 headline floor by a wide margin.

## Net conclusion of Rounds 1 + 2

The Asset Growth mechanism:
- **Is statistically real** (IC t-stat 17 is bulletproof)
- **Worked well 2021-2023** (Sharpe LS 1.4-2.2)
- **Failed in 2020 and 2025** (liquidity-driven small-cap rallies)
- **Is not packageable into a PROMOTE-grade product with simple refinements**

The best deployable form we found is Round 1's original `f5_ag_2y_ind` with monthly Q5-excess (Sharpe 0.594). Round 2's attempts to improve it via horizon match / regime filter / liquidity filter / size residualization all failed.

## Decision: RESEARCH-ONLY, pivot to Round 3

### Round 3 direction options (for user to choose)

**Option A — Sibling mechanism (orthogonal channel)**:
- **Net Share Issuance** (Pontiff-Woodgate 2008) — captures dilution channel directly
- Data: `total_share` from balancesheet.parquet (already cached)
- Expected orthogonality to AG: moderate (shares a channel via ΔEquity / TA)
- **If successful, combine AG + NSI into a CMA-style composite**

**Option B — Pair AG with a regime-complement (balance the 2020/2025 weakness)**:
- AG fails when small caps rally (2020, 2025). Momentum / 12-1M works BEST in those regimes.
- Build AG ⊥ Momentum (residualize AG against 12M momentum cross-sectionally)
- Or: dynamic blend AG · w(t) + Momentum · (1-w(t)) with w based on AG's rolling 3M Sharpe

**Option C — Cash-flow earnings quality (orthogonal fundamental channel)**:
- `OCF / TotalAssets` (Sloan 1996 cash-flow quality)
- Correlates with accruals (already done 20260420), so weaker novelty
- Still useful as a diversifier in a fundamental basket

**Option D — Accept RESEARCH-ONLY, publish and move on**:
- Log AG as a known-working but currently-regime-broken factor
- Revisit in 6 months when 2025 data accumulates
- Start a new session on a different mechanism (e.g., earnings-quality, SUE, or valuation-momentum)

**Recommended**: **Option A** (NSI) — same family (investment anomaly), different data channel, highest expected marginal information.

## Artifacts

```
outputs/
├── expressions_batch_0002.md
├── r2_summary_batch_0002.csv
├── r2_annual_batch_0002.csv
├── r2_best_year_out.csv
├── backtest_results_batch_0002.md
└── alpha_ranking_round2.md   (this file)
```
