# Research Brief — A-Share ETF Weekly TQPB v1

**Agent 1: Research Librarian**
**Session:** `20260423_a_share_etf_weekly_tqpb_v1`
**Date:** 2026-04-23

## 1. Thesis in one paragraph

V7_gold (A-share ETF rotation 2.0) captures the "what" of momentum — 4-week
magnitude with crowding penalty — but not the "how" (trend quality /
consistency / pullback-entry). Literature on tsmom (Moskowitz-Ooi-Pedersen
2012) and "trend consistency" (Ooi 2014) shows that two positions with the
same 4w return but different daily-return paths have materially different
forward Sharpe; high-consistency trends persist, low-consistency trends
mean-revert. Separately, the 20260423 ETF reversal session Round 2 found
that RSI(14) < 30 selective oversold has IC t-stat +7.75 at k=20 forward —
the strongest single-horizon IC in our entire factor zoo to date — but
was spec-mismatched when forced into a symmetric LS portfolio. This
session proposes a weekly factor that combines these two insights into
a trend-quality + pullback-buy overlay designed to ensemble with V7_gold
on the same 34-ETF universe.

## 2. Literature grounding

### Trend quality / consistency

- **Moskowitz, Ooi, Pedersen (2012)** "Time series momentum" — tsmom
  works cross-asset; Sharpe-style signals (mean/vol of recent returns)
  are more robust than raw returns.
- **Grinblatt, Moskowitz (2004)** — monthly momentum with tax/price-
  anchoring effects; "consistency of past returns" matters.
- **Ooi (2014)** "How trends come to life" — trend CONSISTENCY (fraction
  of up-days, Sharpe of path) has independent predictive power beyond
  raw momentum.

### Pullback-buy within uptrend

- **Pullback-in-trend** classical playbook: buy oversold RSI only if
  longer-horizon moving-average or slope is positive. Reduces regime-
  break losses.
- **20260423_a_share_etf_reversal_v1 R2** (sibling session): `r2_rsi_extreme_os`
  IC t-stat +7.75 at k=20 forward, Q5-Q1 spread over 60d = +13.5%.
  Triggered long-only spec would capture.
- **Han, Zhang, Zhang (2013)** — profitability of trend-following with
  reversal overlays on China stocks; dual signal outperforms either
  alone.

### Combination / ensemble

- **Ilmanen (2011)** "Expected Returns" — two uncorrelated 0.7-Sharpe
  signals with 50/50 weight produce ~1.0 Sharpe combined.
- **Asness, Frazzini, Pedersen (2013)** "Quality minus junk" —
  quality-enhanced momentum improves Sharpe and reduces drawdown.
  The "quality" dimension here maps to trend-consistency.

## 3. Why this might work on A-share ETFs

1. **V7_gold leaves trend-consistency on the table.** mom_4w doesn't
   distinguish "grindy up" from "one-big-day up". Trend_Sharpe_20d
   captures exactly that.
2. **Pullback-in-trend is a known overlay winner.** The 20260423 session
   confirmed RSI<30 is a live signal on this universe. What was missing
   was the trend filter — without it the signal catches "dead cat
   bounces" (not trending at all).
3. **V7_gold's 2022 weakness (+7.8%)** was due to momentum mis-timing
   in an oscillating bear market. Pullback-in-trend should time entries
   better in choppy environments where mom_4w pivots frequently.
4. **The 34-ETF universe has strong sector dispersion** which amplifies
   relative-strength-style signals.

## 4. Why this might NOT work

1. **|corr with V7_gold| may be too high.** If the new signal is really
   just "momentum with different packaging", ensembling won't help.
   Pre-registered floor: |corr| ≤ 0.70.
2. **RSI<30 triggers rarely on ETFs.** On 34 ETFs, only 1-3 will be in
   RSI<30 in any given week. The short leg is essentially noise.
   Mitigation: long-only top-5 spec, not symmetric LS.
3. **Weekly data is noisier than monthly.** The R2 finding was at k=20
   (monthly); k=5 (weekly) will have smaller |IC|. Cost drag matters.
4. **Survivorship & staggered-listing bias.** Some ETFs in the universe
   launched 2021+; their inclusion in earlier years depends on
   staggered-join logic. V7_gold's 12-week-staleness rule applies.

## 5. Handoff to Agent 2 — parameter choices

- Primary horizon: k=5 trading days (1 week forward)
- Horizon grid: {5, 10, 20} (weekly / 2-week / monthly robustness)
- Rebalance: weekly (Friday close, T+1 execute)
- Strategy spec: **long-only top-5**, equal weight. Matches V7_gold's
  7-name concentration. Also compute LS top-5 / bot-5 as secondary.
- Cost: 5 bps/side (V7_gold's baseline)
- Combination test: 50/50 ensemble with V7_gold weekly PnL
- Hard floors: IC ≥ 0.02, standalone net Sharpe ≥ 0.4, combined Sharpe
  > max(V7_gold=1.91, standalone), |corr with V7| ≤ 0.70

## 6. References consulted (external)

- Moskowitz, Ooi, Pedersen (2012) JFE vol 104, 228-250
- Grinblatt, Moskowitz (2004) JFE vol 71, 541-579
- Ooi (2014) AQR working paper
- Han, Zhang, Zhang (2013) "Profitability of trend-following with
  reversal overlays on China", J. Econ. & Finance
- Ilmanen (2011) Expected Returns (Wiley), chs. 10-12
- Asness, Frazzini, Pedersen (2013) "Quality minus junk" AQR

## 7. Handoff

See `working/handoff_1_to_2.json`.
