# Final Summary — A-Share ETF Weekly TQPB v1 (combine with V7_gold)

**Session:** `20260423_a_share_etf_weekly_tqpb_v1`
**Universe:** 34 A-share thematic ETFs (V7_gold universe, 12w stagger)
**Sample:** 2019-01 → 2026-04, 377 weeks
**Verdict:** **RESEARCH-ONLY with deployment recommendation for 15% overlay**

## One-paragraph summary

Ran the WorldQuant 5-agent workflow on V7_gold's own 34-ETF universe to
find a weekly factor that ensembles well with V7_gold (the user's
"A-share ETF rotation 2.0"). Built 8 orthogonal-by-design signals across
trend-quality (Moskowitz-Ooi-Pedersen 2012 path-Sharpe), pullback-buy
within uptrend (R2 RSI<30 with trend filter), vol-adjusted momentum,
relative strength, drawdown quality, and volume-confirmed breakout axes.
All 8 standalone long-only Sharpes (0.25-0.32) and all LS Sharpes
(0.04-0.51) are well below V7_gold's 1.73, so naive 50/50 ensembles
always dilute the combined book. The correct combine framing — LS mode
+ grid-optimal blend weight — reveals that **`r1_breakout_vol_conf`
(volume-confirmed 20-day high breakout) has correlation −0.009 with V7
and residual Sharpe +0.44 orthogonal to V7**. Deployed as a 15%-weight
overlay on V7_gold's 85%, the combined book earns Sharpe 1.79 (vs V7
baseline 1.73) with MaxDD reduced from −9.1% to −7.7%. The Sharpe lift
is within sampling noise (ΔSharpe 0.06 on 377 weeks, t~0.5), but the
per-year decomposition shows the overlay **specifically helps V7 in its
weakest years** (2022 +0.23, 2023 +0.25, 2024 +0.23 Sharpe), which is
textbook defensive-diversifier behavior. Recommendation: RESEARCH-ONLY
deployment of the 15% overlay; track live; consider signal-level fusion
into V7's chassis as Round 2.

## Key numbers (winner: r1_breakout_vol_conf LS top-5/bot-5)

| | V7_gold baseline | 85% V7 + 15% LS overlay |
|---|---:|---:|
| Sharpe (weekly, ann. √52) | 1.73 | **1.79** |
| Annual return | +30.1% | +27.0% (slightly lower) |
| Max drawdown | −9.1% | **−7.7%** |
| 2022 Sharpe (V7's weakest year) | +0.95 | **+1.18** (+0.23) |
| 2023 Sharpe | +1.87 | **+2.12** (+0.25) |
| 2024 Sharpe | +1.57 | **+1.80** (+0.23) |
| 2025 Sharpe | +2.04 | +1.83 (−0.21) |
| Overlay TO/yr | — | ~94% (very low-cost) |

## Two key signals of interest

### 1. `r1_breakout_vol_conf` — RECOMMENDED combine candidate

- **Formula**: `(close − max_high_20d)/std_20d × I[breakout ∧ vol_5d/vol_20d > 1.2]`, demeaned
- **Standalone LS Sharpe**: +0.45 (at 5 bps/side)
- **Correlation with V7_gold**: **−0.009 (truly orthogonal)**
- **Residual Sharpe** (after removing V7 beta): +0.44
- **When to deploy**: always on (as defensive diversifier); Round-2
  conditional version would activate only in low-breadth regimes

### 2. `r1_pullback_in_uptrend` — secondary candidate (low-TO, small lift)

- **Formula**: `(40 − RSI14) × I[RSI14 < 40] × I[mom_20d > 0]`, demeaned
- **Standalone LS Sharpe**: +0.43 (5 bps/side), TO only 174%/y
- **Correlation with V7**: +0.10
- **Optimal overlay**: 7.5%, gives combined Sharpe 1.75 (+0.02 over V7)
- **Mechanism**: extends the R2 session's RSI finding (IC t=+7.75 at
  k=20) with a trend filter, so only pullback-buys happen inside
  uptrends. IC flips sign at k=20 (+0.010 → −0.031), confirming this
  is a pure 1-week signal.

## Mechanism topology (synthesis with sibling sessions)

| horizon | mechanism direction on A-share ETFs | source |
|---:|---|---|
| 1 week (k=5) | weak momentum + RSI-triggered pullback reversal | this session |
| 2-3 weeks (k=10-15) | weak momentum | this + reversal R1 |
| 4 weeks (k=20) | momentum reversal zone | reversal R2 |
| 60 days (k=60) | long-term reversal | reversal R2 |
| 120 days+ | momentum returns | reversal R2 |

V7_gold sits in the 4-week momentum magnitude sweet spot. A weekly
overlay with either (a) pullback-in-trend or (b) breakout-volume axes
captures orthogonal information without conflicting with V7's core.

## What worked (dogfood)

- **LS-mode combine correlation** was decisive. Long-only correlations
  were all +0.44, suggesting nothing was orthogonal. LS-mode revealed
  the real story (corr −0.009 for breakout).
- **Grid-optimal blend weight** is the right benchmark, not 50/50. For
  V7 (Sh 1.73) + noise_at_0.5_Sh, 50/50 is strictly dilutive.
- **Per-year Sharpe decomposition of combined PnL** surfaced the
  defensive pattern that was invisible at headline level.
- **R2 RSI finding reused**: this session's `r1_pullback_in_uptrend`
  is a direct extension of the sibling session's IC t=+7.75 finding,
  with a trend filter to fix the spec-mismatch issue.

## What did not work

- **G4 corr_vs_uew gate** fails 8/8 long-only because long-only
  trend-following is market-correlated by construction. Gate is the
  wrong invariant here. Suggest documenting in `references/validation-gates.md`
  that G4's corr check needs spec-dependent thresholds (LS vs long-only).
- **IC-based floors** are brittle for sparse-trigger signals
  (`r1_breakout_vol_conf` IC is NaN due to `pd.qcut` bin collapse).
  Sparse signals need bootstrap-adjusted Sharpe or triggered-IC
  (IC on triggered subset only).
- **Ensemble (r1_kitchen_sink)** underperforms the best single
  candidate. Ensembling 8 weakly-correlated signals with average
  quality does not beat the best single one here. Ranked 5th.

## Round 2 directions

If the user wants to push further:

1. **Long-only top-3 version of breakout_vol_conf** — remove short-leg
   tail risk while keeping the defensive benefit.
2. **Signal-level fusion into V7's Leg A** — replace V7's `0.3×breadth`
   with `0.15×breadth + 0.15×z(breakout)`, backtest V7 directly.
3. **Regime-conditional overlay** — activate the 15% only when V7's
   breadth z < 0 (choppy / bearish regime), preserving 2022-style lift
   and avoiding the 2025 small drag.
4. **Extend universe to 44-49 ETFs** — add broad-index ETFs to sharpen
   cross-section and resolve the G4 corr-vs-uew artifact.

## Research-log entry (for README)

```
session: 20260423_a_share_etf_weekly_tqpb_v1
factor_family: trend_technical.breakout_volume_confirmed_weekly_etf
best_candidate: r1_breakout_vol_conf (LS top-5/bot-5, weekly, 94% TO/y)
combine_target: V7_gold (logs/20260422_industry_rotation_cn)
combine_spec: 85% V7 + 15% r1_breakout_vol_conf LS
combined_sharpe: 1.79 (V7 baseline 1.73; ΔSharpe +0.06 within noise)
combined_maxdd: -7.7% (V7 baseline -9.1%; real defensive benefit)
biggest_contribution: 2022 +0.23 Sharpe lift in V7's weakest year
corr_with_v7: -0.009 (orthogonal)
residual_sharpe: +0.44 (independent alpha to V7)
status: RESEARCH_ONLY
key_finding: "Volume-confirmed 20d high breakout is orthogonal to V7_gold's
              mom_4w ensemble. 15% overlay adds defensive alpha mainly in
              V7's choppy/weak years (2022-2024). Shallow Sharpe lift (0.06)
              but meaningful MaxDD reduction (9.1% -> 7.7%)."
```

## Files

```
logs/20260423_a_share_etf_weekly_tqpb_v1/
├── inputs/
│   └── objective.md
├── scripts/
│   └── 02_build_and_backtest.py   (Agents 3+4 combined)
├── outputs/
│   ├── research_brief.md                      (Agent 1)
│   ├── session_metadata.yml                   (Agent 2)
│   ├── expressions_batch_0001.md              (Agent 3)
│   ├── backtest_results_batch_0001.md         (Agent 4)
│   ├── ic_table_batch_0001.csv
│   ├── longonly_summary_batch_0001.csv
│   ├── ls_summary_batch_0001.csv
│   ├── decile_summary_batch_0001.csv
│   ├── cost_sensitivity_batch_0001.csv
│   ├── per_year_sharpe_batch_0001.csv
│   ├── validation_gates_batch_0001.json
│   ├── combine_analysis_v7_gold.json
│   ├── combined_optimal_r1_breakout_vol_conf.csv  (deploy spec PnL)
│   ├── combined_optimal_r1_pullback_in_uptrend.csv
│   ├── alpha_ranking.md                       (Agent 5)
│   └── final_summary.md                       (this file)
├── working/
│   └── handoff_1_to_2.json
├── round_0001.yml
└── run_state.json
```
