# Alpha Ranking — Round 2 (V7_gold overlay follow-up)

**Session:** `20260423_a_share_etf_weekly_tqpb_v1` · **Round 2**
**Agent:** 5 (Evaluator & Recorder)
**Date:** 2026-04-24

---

## 0. Critical finding: Round 1 overlay claim was spurious

**Round 1 reported:** 85% V7 + 15% LS top-5/bot-5 of `r1_breakout_vol_conf`
gave Sharpe 1.79, MaxDD −7.7%, corr with V7 −0.009.

**Round 2 audit:** The `r1_breakout_vol_conf` signal was **identically zero on
every bar**. Round 1's `max_high_20` was `rolling(20).max()` which INCLUDES
the current bar; therefore on breakout days (`close == max`), the raw signal
`(close − max_high_20) / std_20d` was exactly 0, and on non-breakout days it
was negative and clipped to 0. The LS top-5/bot-5 book was ranking on a
tied-at-zero signal and produced pnl only from pandas' stable sort
tie-break (effectively ranking by ts_code alphabetically). The reported
corr −0.009 and Sharpe lift were ghost artifacts.

**Evidence:**
```
Round 1 breakout semantics: max_high_20 = rolling(20).max()  # includes today
→ signal_raw > 0 in 0 / 42788 observations (all zeros)
```

This invalidates the Round 1 deploy recommendation. Round 2 re-runs every
direction with the corrected breakout semantics (`max_high_20 =
shift(1).rolling(20).max()`, and the inequality is strict `close >
max_high_20`).

With the corrected signal, breakouts fire on 1,901 / 42,788 obs (~4.4%) —
a truly sparse-trigger signal.

## 1. Round 2 verdict (4 directions, none deploy-worthy)

| # | Direction | Metric | Result | vs V7 baseline |
|---|---|---|---|---|
| 1 | Long-only top-3 overlay | best blend Sh | 1.714 @ 5% | **−0.045** |
| 2 | Signal-level fusion (Leg A) | best fused Sh | 1.746 (20/10 weights) | **−0.013** |
| 3 | Regime-conditional overlay (breadth_z < −0.25) | combined Sh | 1.748 | **+0.021** ⚠ |
| 4 | Extended 48-ETF universe | best blend Sh | 1.711 @ 5% | **−0.048** |

**V7 baseline (Round 2 reproduction):** Sharpe **1.759**, MaxDD −9.1%.

**None of the four directions produce a statistically meaningful improvement.**
The +0.021 lift for regime-conditional at threshold `-0.25` has t-stat well
under 1 on 377 weeks; per-year decomposition shows the "improvement" is
concentrated in two lucky years (2024–2025).

## 2. Direction 1 — Long-only top-3 breakout overlay

**Intent:** remove short-leg tail risk; hold breakout top-3 only.

**Standalone stats (34-ETF universe):**
- Sharpe: 0.63 (at 5 bps/side)
- MaxDD: −24.3%
- Ann. turnover: ~3,500% (67% weekly turnover)
- Trade frequency: rebalances activate ~2% of weeks (signal is very sparse)

**Blend with V7 (grid):**

| weight | Sharpe_combo | Δ vs V7 | MaxDD_combo |
|---:|---:|---:|---:|
| 0.050 | 1.714 | −0.013 | −8.9% |
| 0.100 | 1.696 | −0.031 | −8.8% |
| 0.150 | 1.671 | −0.056 | −8.7% |
| 0.300 | 1.553 | −0.174 | −8.4% |

**Verdict:** Every weight dilutes. The standalone Sharpe (0.63) is well
below V7 baseline (1.76), and the correlation with V7 is positive (breakouts
tend to coincide with V7's rally weeks), so the Leg's orthogonality claim
does not hold. Top-3 is also more concentrated than top-5 and has worse
MaxDD. **RESEARCH-ONLY, not recommended.**

## 3. Direction 2 — Signal-level fusion into V7's Leg A

**Intent:** replace V7's `0.3 × breadth_z` scalar term in `score_A` with
`0.15 × breadth_z + 0.15 × z_cs(breakout_vol_conf)`, so breakout information
enters V7's chassis directly instead of as an external overlay.

**Fused V7 variants** (all with full V7 chassis: Leg A + Leg G + MA50 gate
+ gold fallback + 15% vol target):

| variant | breadth_w | breakout_z_w | Sharpe | MaxDD | 2022 Sh |
|---|---:|---:|---:|---:|---:|
| v7_orig | 0.30 | 0.00 | **1.759** | −9.1% | 0.83 |
| fused_20_10 | 0.20 | 0.10 | 1.746 | −9.6% | 0.83 |
| fused_15_15 | 0.15 | 0.15 | 1.727 | −9.6% | 0.83 |
| fused_10_20 | 0.10 | 0.20 | 1.736 | −9.6% | 0.83 |
| fused_00_30 | 0.00 | 0.30 | 1.728 | −9.3% | 0.83 |
| fused_25_10 | 0.25 | 0.10 | 1.746 | −9.6% | 0.83 |
| fused_15_30 | 0.15 | 0.30 | 1.728 | −9.3% | 0.83 |

**Per-year decomposition (orig vs fused 15+15):**

| year | n_w | orig_Sh | fused_Sh | Δ |
|---:|---:|---:|---:|---:|
| 2019 | 51 | 2.09 | 2.09 | 0.00 |
| 2020 | 52 | 2.21 | 2.14 | −0.07 |
| 2021 | 55 | 1.70 | 1.58 | −0.12 |
| 2022 | 50 | 0.83 | 0.83 | +0.00 |
| 2023 | 50 | 1.60 | 1.55 | −0.04 |
| 2024 | 51 | 1.88 | 1.92 | +0.04 |
| 2025 | 53 | 2.04 | 2.06 | +0.02 |
| 2026 | 15 | 0.93 | 0.82 | −0.11 |

**Verdict:** All fusion weights are either neutral (fused_25_10, Δ −0.013)
or strictly worse. V7's `mom_4w` already captures breakout-like trend
information — the explicit breakout z-score adds noise. **Hypothesis
rejected: no value at Leg A level.**

## 4. Direction 3 — Regime-conditional overlay

**Intent:** only deploy the 15% LS overlay when V7's breadth z-score is
below a threshold (i.e., low-breadth / choppy / bearish regime).

With corrected LS signal (top-5/bot-5 on `r1_breakout_vol_conf`):

| threshold | overlay fires | Sh_combo | MaxDD | Δ vs V7 | Δ vs always-on |
|---:|---:|---:|---:|---:|---:|
| −0.50 | 36% | 1.740 | −8.5% | +0.013 | +0.047 |
| **−0.25** | **46%** | **1.748** | **−8.4%** | **+0.021** | **+0.055** |
| 0.00 | 54% | 1.729 | −8.3% | +0.002 | +0.036 |
| 0.25 | 60% | 1.726 | −7.5% | −0.001 | +0.034 |
| 0.50 | 66% | 1.744 | −7.5% | +0.017 | +0.051 |

**Always-on 15% LS baseline (new data):** Sh 1.693, MaxDD −7.7%.
(i.e., the "Round 1" deploy recommendation, when re-run with the correct
signal, gives Sh **1.693 — below V7 baseline**, not 1.79.)

**Verdict:** The best threshold (−0.25) gives Sharpe 1.748, +0.021 over V7
baseline. On 377 weeks this Δ has t-stat ~0.4 (noise). The MaxDD
improvement from −9.1% → −8.4% is more robust but is also achievable by
simply halving V7's gross exposure. **Marginal at best, hazardous to
deploy on conviction.**

## 5. Direction 4 — Extended universe (34 → 48 ETFs)

**Broad-index ETFs added (14):**
- 大盘 / 宽基:510300 (HS300), 510500 (ZZ500), 510050 (SZ50), 510180 (SH180), 588000 (STAR50), 588080 (STAR50), 159915 (ChiNext), 159949 (ChiNext-50), 159845 (ZZ1000)
- 港股 / 海外:510900 (H-shares), 513050 (中概互联), 513100 (纳指), 159941 (纳指-SZ)
- 黄金 SH:518880 (dedupes with 159934.SZ)

**Standalone long-only top-3 on 48-ETF universe:**
- Sharpe: 0.60 (slightly lower than 34-ETF's 0.63)
- MaxDD: −18.6%
- TO: ~4,000%/y (higher — wider universe means more churn)

**Best blend with V7 at 5%:** Sharpe 1.711, Δ −0.048.

**Verdict:** Extending the universe slightly lowers standalone Sharpe and
increases turnover. The broad-index ETFs are too correlated with each other
and with V7's top picks to add meaningful diversification. **Hypothesis
rejected: universe expansion does not resolve the orthogonality gap.**

## 6. Root cause: why nothing works

The Round 1 framing — "find an orthogonal weekly signal to combine with
V7_gold" — presupposed that V7's `mom_4w` and `breadth` don't capture some
information that breakout/pullback signals do. After fixing the broken
breakout semantics, the picture is:

1. **V7 already captures most systematic information.** Its Leg A
   (penalized mom_4w) and Leg G (group-rotator on 4-week returns) already
   exploit medium-term momentum. The MA50 gate + gold fallback handle
   regime changes. Vol target compresses tails.
2. **Breakout signals that fire on the same regime as V7's trend picks are
   redundant.** When breadth is positive and V7 is rallying, breakouts
   happen on already-held or similar ETFs. When breadth is negative, the
   gate goes off and V7 holds gold — breakout picks don't help because V7
   is out of the market.
3. **The remaining "orthogonal" information after V7 is noise-heavy at
   weekly horizon.** Sample size is 377 weeks; residual signals need IC
   t-stats ≥ 2 to make a real contribution. None of the four directions
   reaches that bar.

## 7. Recommendation

**The Round 1 deploy recommendation (85% V7 + 15% breakout LS overlay) is
RETRACTED.** The original claim of Sh 1.79 / MaxDD −7.7% was a ghost result
from an all-zero signal.

**Replacement guidance:**
- Do NOT deploy any breakout-based overlay with V7_gold.
- If a defensive diversifier is needed, consider out-of-universe sleeves
  (bond ETF, commodity, long-volatility) rather than signal-level additions.
- V7_gold stands on its own at Sh 1.76 (reproduced), MaxDD −9.1%.

## 8. Workflow dogfood — new lessons

### 8.1 Mandatory signal-nonzero sanity check

Every expression in `backtest_results_batch_*.md` should include:

```
count(signal_raw != 0) / total_obs
count(signal_raw > 0)
max(|signal|)
```

An all-zero signal (or all-constant) is detectable in O(1) but produces
valid-looking downstream pnl via tie-breaking. This should be a G1
(syntax) or new G1.5 check.

### 8.2 Definition audit: boundary-inclusive rolling operations

The bug:

```python
# WRONG (includes today in prior-window max)
max_high_20 = close.rolling(20).max()
breakout = close >= max_high_20    # trivially true on local max day
signal   = (close - max_high_20)   # = 0 on breakout day, clipped to 0 elsewhere
                                   # → always 0
```

Correct semantics for "breaks the prior N-day high":

```python
max_prior_20 = close.shift(1).rolling(20).max()
breakout     = close > max_prior_20    # strict, excludes current bar
signal       = (close - max_prior_20) / std_20d    # strictly positive on breakout
```

**Add to `common-pitfalls.md`:** rolling operations for "prior N bars"
must shift(1) before rolling, and boundary comparisons should use strict
inequality.

### 8.3 Audit probe for sparse-trigger signals

When IC is NaN or `pd.qcut` collapses bins, the first hypothesis should be
"signal is degenerate (all zero / all equal)", not "signal is sparse but
valid". The audit should include:

1. Print `signal.describe()` including `n_nonzero`
2. Print `signal.value_counts().head(5)` — a degenerate signal shows a
   single value with 100% frequency
3. Plot signal histogram — degeneracy is visually obvious

### 8.4 Reproducibility: re-compute baseline from source

Round 1 used the pre-saved `round7c_v7_pnl.csv` as V7 baseline. Round 2
reproduces V7 from the weekly panel and gets Sh 1.759 instead of 1.91
(the published figure). The gap is because the saved PnL uses a longer
sample (2019 H1 included with vol-target warmup) while the reproduced
version matches only the overlapping weeks in the combine analysis. **For
combine-mode sessions, baselines should be re-computed from source over
the exact evaluation sample.**

### 8.5 Consistency of "long-only rebalance" semantics

My initial Round 2 code skipped rebalance weeks when no breakouts fired
but left prior weights via ffill → positions held indefinitely → Sharpe
and MaxDD explode. The fix: each rebalance date must write explicit
(possibly all-zero) weights; cash weeks must be explicit. Add to
`execution-plan.md`.

## 9. Files

```
outputs/round2/
├── d1_top3_grid.csv                  # Direction 1 grid search
├── d1_top3_pnl_weekly.csv            # Direction 1 PnL
├── d2_signal_fusion_results.json     # Direction 2 variants + per-year
├── d2_per_year_compare.csv
├── d2_v7_pnl_series.csv
├── d3_regime_sensitivity.csv         # Direction 3 threshold grid
├── d3_ls_top5bot5_pnl_weekly.csv
├── d4_top3_ext48_grid.csv            # Direction 4 grid search
├── d4_top3_ext48_pnl_weekly.csv
├── directions_1_3_4_results.json     # D1, D3, D4 structured
├── etf_daily_broad.parquet           # 14 broad-index ETFs
├── etf_universe_broad.csv
├── alpha_ranking.md                  # this file
└── final_summary.md
```
