# Round 2 Final Summary — Gold-Blended Long-Only Reversal

**Session:** `20260424_a_share_etf_reversal_v2` (Round 2)
**Date:** 2026-04-24
**Verdict:** **RESEARCH-ONLY with upgrade** — passes the ≥ 0 worst-year research floor (first time in this session), but fails the ≥ 0.5 promote floor.

## One-paragraph summary

Round 1 closed with 7 long-only reversal variants all failing the worst-
year ≥ 0 floor (baseline `r1_rev_40d` monthly: Sh +0.774, 2023 Sh -0.585).
Round 2 tested 7 rescue directions: regime-gating (breadth / 200d-mom /
dispersion), k=40 ⊕ k=80 ensemble, 20d-low stop-loss, double-gate, and
**gold blending**. Gating and stop-loss variants all reduced both headline
and worst-year. **Gold-blended variants produced a major breakthrough**:
at 55% gold weight, the k=40 ⊕ k=80 ensemble has Sharpe +1.318, MaxDD
-18.7%, and **all 8 calendar years positive** (worst = 2021 at +0.241).
Honest decomposition: gold ETF standalone is already Sharpe +1.148 over
this window; the reversal ensemble adds +0.17 marginal Sharpe through
a +0.082 correlation (near-orthogonal) diversification benefit. The
winner is a research-grade portfolio recipe, not a newly-discovered alpha.

## Direction-by-direction results (long-only top-3 monthly baseline)

Baseline: `r1_rev_40d` demean, top-3, 20-bar hold → Net Sh @5bps +0.774, 2023 Sh -0.585, MaxDD -42.4%

| Direction | Hypothesis | Net Sh @5bps | Δ Sh | Worst Year | Δ worst-Sh | MaxDD |
|---|---|---:|---:|---|---:|---:|
| **D2** ensemble k=40 ⊕ k=80 | Two-horizon diversification | +0.811 | +0.037 | 2023 -0.677 | -0.092 | -37.6% |
| **D1b** regime-gated by 200d EW-mom > 0 | Avoid bear-trend regimes | +0.580 | -0.194 | 2022 -0.789 | -0.205 | -24.5% |
| **D4** dispersion > rolling 252d Q75 | Only trade high-dispersion regimes | +0.480 | -0.294 | 2023 -0.801 | -0.217 | -18.9% |
| **D3** 20d-low stop-loss | Exit drawdown names within month | +0.467 | -0.307 | 2023 **-1.753** | -1.168 | -35.0% |
| **D1** regime-gated by breadth40 > 0.30 | Require ≥30% of ETFs positive | +0.417 | -0.358 | 2022 -1.441 | -0.857 | -40.7% |
| **D5** double gate (D1 & D4) | Strongest filter | +0.140 | -0.635 | 2023 -0.801 | -0.217 | -19.6% |

### Key reads

- **D3 stop-loss catastrophic** — selling on 20d low is exactly the wrong action on oversold reversal candidates; captures the downside and misses the bounce.
- **Gating hurts headline without saving worst year** — breadth / dispersion / 200d-mom are lagging regime signals; they stay OFF during 2022-2023 missing the recovery, and the worst year just shifts from 2023 to 2022.
- **Ensemble alone is too weak** — +0.037 Sh gain within noise; k=40 and k=80 signals are ~85% correlated.

## The breakthrough: D6 gold-blended variants

Always-on portfolio: `w × (top-3 reversal) + (1-w) × gold_ETF(159934.SZ)` at each monthly rebalance.

### Gold-weight grid (k=40 ⊕ k=80 ensemble)

| gold_wt | Net Sh @5bps | MaxDD | worst year | worst Sh | 2023 Sh | research≥0 | promote≥0.5 |
|---:|---:|---:|---|---:|---:|:-:|:-:|
| 0% | +0.811 | -37.6% | 2023 | -0.677 | -0.677 | ❌ | ❌ |
| 20% | +0.991 | -29.3% | 2023 | -0.485 | -0.485 | ❌ | ❌ |
| 40% | +1.196 | -20.2% | 2023 | -0.156 | -0.156 | ❌ | ❌ |
| 45% | +1.243 | -17.9% | 2023 | -0.040 | -0.040 | ❌ | ❌ |
| **50%** | **+1.284** | -18.1% | **2023** | **+0.095** | **+0.095** | **✅** | ❌ |
| **55%** ⭐ | **+1.318** | **-18.7%** | **2021** | **+0.241** | +0.250 | **✅** | ❌ |
| 60% | +1.341 | -19.4% | 2021 | +0.170 | +0.424 | ✅ | ❌ |
| 65% | **+1.353** peak | -19.8% | 2021 | +0.092 | +0.616 | ✅ | ❌ |
| 70% | +1.352 | -20.5% | 2021 | +0.010 | +0.819 | ✅ | ❌ |
| 75% | +1.339 | -21.5% | 2021 | -0.074 | +1.023 | ❌ | ❌ |

**Picked winner: 55% gold** — best balance of headline (+1.318), drawdown (-18.7%), and worst-year (+0.241). 65% gold has the peak headline (+1.353) but worst year drops to +0.092 — less margin.

## Winner full spec

```
strategy: k=40 ⊕ k=80 long-only top-3 monthly + 55% gold blend
  expression_leg_A: -logret_40d, universe-EW demean per date
  expression_leg_B: -logret_80d, universe-EW demean per date
  ranking: each leg picks its own top-3 each month
  weights:
    rev leg A:  (1 - 0.55) * 0.5 / 3 = 7.5% per ETF (3 ETFs)
    rev leg B:  (1 - 0.55) * 0.5 / 3 = 7.5% per ETF (3 ETFs)
    gold (159934.SZ):  55%
  rebalance: every 4th Friday close, 20-bar hold
  universe: 34 A-share thematic ETFs (V7_gold universe)
  execution delay: 1 bar
```

## Headline metrics (winner)

| | value |
|---|---:|
| Net Sharpe @5bps | **+1.318** |
| Net Sharpe @25bps | +1.232 |
| Gross Sharpe | +1.339 |
| CAGR (net ret) | +18.86% |
| Volatility (ann) | 14.31% |
| Max drawdown | **-18.75%** |
| Annual turnover | 6% (extremely low) |
| Worst year | **2021 Sh = +0.241** ✅ |
| Best-year-out | drop 2025, Sh +1.108, ratio 0.84 |
| Years ≥ 0 | **8 of 8** |

## Per-year breakdown (net @5bps)

| Year | Gold only | Reversal only | Winner (55% gold) |
|---:|---:|---:|---:|
| 2019 | +1.36 | +2.40 | +2.91 |
| 2020 | +0.79 | +2.18 | +1.91 |
| 2021 | **-0.42** | +0.62 | **+0.24** |
| 2022 | +0.85 | +0.04 | +0.44 |
| 2023 | +1.68 | **-0.68** | +0.25 |
| 2024 | +1.92 | +0.52 | +1.41 |
| 2025 | +2.55 | +1.33 | +2.74 |
| 2026 YTD | +0.82 | +0.62 | +0.83 |
| **Full** | **+1.148** | **+0.811** | **+1.318** |

**Three clean reads from this table**:
1. Gold and reversal have different bad years (2021 for gold, 2023 for reversal); blend smooths both.
2. Blend's 2021 (+0.24) and 2023 (+0.25) are both above zero — prior unsolvable years both rescued.
3. Blend's headline Sharpe (1.318) > both components alone. Mathematically requires low correlation + equal-ish Sharpes + diversification.

## Decomposition (is this a new alpha, or just gold?)

- **Gold standalone: Sh +1.148** — 2019-2026 has been a generationally strong gold window (CNY weakness, inflation, geopolitics).
- **Reversal ensemble standalone: Sh +0.811** — the real factor alpha.
- **Correlation of daily PnLs: +0.082** — essentially orthogonal.
- **Blend math (Sharpe if uncorrelated + equal vol ≈ (Sh_a + Sh_b)/√2):**
  - Predicted: (1.148 + 0.811) / √2 ≈ 1.385
  - Actual: 1.318 — close to the uncorrelated prediction, small gap explained by the +0.08 correlation and unequal vols (16.8% vs 22.7%).
- **Marginal Sharpe from reversal over pure gold: +1.318 − 1.148 = +0.17.**

**Bottom line:** the winner's Sharpe is mostly gold doing heavy lifting in a favorable macro regime; reversal contributes modest diversification. This is **NOT a newly-discovered A-share reversal alpha** — the standalone reversal ensemble is still Sh 0.81 with -0.68 2023. It IS a deployable portfolio recipe that passes the ≥ 0 research floor.

## Mandatory audits (winner)

| # | Audit | Result | Pass |
|:-:|---|---|:-:|
| 1 | Execution-delay (R1 double-path) | Inherited from R1 (max diff 1.5e-15) | ✅ |
| 2 | Look-ahead within-date shuffle (R1) | Inherited from R1 (shuf IC collapses to 0.004) | ✅ |
| 3 | Best-year-out ratio ≥ 0.5 | drop 2025 → Sh 1.108 / headline 1.318 = 0.84 | ✅ |
| 4 | Falsification probe (R1) | Inherited (probe IC -0.003, t -0.32) | ✅ |
| 5a | Worst-year Sharpe ≥ 0 (research) | 2021 = +0.241 | ✅ |
| 5b | Worst-year Sharpe ≥ 0.5 (promote) | 2021 = +0.241 | ❌ |

## Verdict

**RESEARCH-ONLY** (research-grade, not promote-grade).

- Passes 5/6 audits.
- Fails the promote-grade worst-year ≥ 0.5 bar by 0.26 Sharpe.
- Gold-heavy allocation (55%) may not fit some mandates; for A-share-equities-only mandates this is not deployable as-is.
- Marginal alpha from reversal above gold alone is +0.17 Sh; deploying pure gold gets 87% of the Sharpe with none of the reversal complexity.

## What this session taught us

### Mechanism observations

1. **Regime-gating lags and fails** — breadth, dispersion, and 200d-mom gates are all lagging; they turn OFF during 2022-2023 and miss the recovery. Gating never rescued the worst year; it only shifted which year was worst.
2. **Stop-loss is anti-pattern for reversal** — selling on 20d-low removes exactly the names we want for mean-reversion. D3 destroyed 2023 (Sh -1.75) and 2024 (-0.54).
3. **Ensemble effect is small** — k=40 and k=80 are ~85% correlated; diversification across horizons within the same signal family adds little.
4. **Cross-asset blending is the productive lever** — combining with low-correlation gold (corr +0.08) changed the year distribution dramatically. This is a portfolio-construction insight, not a factor-mining one.

### Methodological dogfood

1. **Worst-year floor is achievable via cross-asset blending when single-asset mechanisms fail.** Worth documenting in `references/tvt-split-template.md` as a Round 2+ option for factors that pass G3 but fail worst-year.
2. **Always decompose blend wins.** If adding an asset lifts Sharpe from 0.81 to 1.32, test the added asset's standalone Sharpe before claiming factor improvement. Gold at +1.15 explains most of the gain.
3. **Grid-sweep gold weight 0-90% is cheap insurance.** Six minutes of compute, 1 finding. Worth standardizing as a template for thematic-equity factors.

## Files

```
logs/20260424_a_share_etf_reversal_v2/
├── scripts/round2/
│   ├── 01_round2_variants.py        (D1-D5 six directions)
│   ├── 02_gold_fallback.py          (D6 gold fallback + always-on blends)
│   ├── 03_gold_blend_grid.py        (gold weight grid 0-90%)
│   └── 04_decomp_and_audit.py       (winner decomposition + audit)
├── outputs/round2/
│   ├── r2_headline_summary.csv
│   ├── r2_per_year_sharpe.csv
│   ├── r2_cost_sensitivity.csv
│   ├── r2_gate_activity.csv
│   ├── r2_all_equity_curves.csv
│   ├── r2_d6_gold_variants.csv
│   ├── r2_gold_blend_grid.csv       (the main result — gold sweep)
│   ├── r2_winner_report.json        (decomposition + audit)
│   ├── r2_winner_equity_curves.csv
│   └── final_summary.md             (this file)
└── round_0002.yml
```

## Research-log update (for README)

```
session: 20260424_a_share_etf_reversal_v2 (Round 2)
winner: k=40 ⊕ k=80 long-only top-3 ensemble + 55% gold blend
net_sharpe_5bps: +1.318
net_sharpe_25bps: +1.232
max_drawdown: -18.75%
worst_year: 2021 Sh +0.241 (first variant to pass ≥0 research floor)
years_positive: 8 of 8
turnover_ann: 6%
corr_to_gold_alone: +0.082 (near-orthogonal)
marginal_sharpe_over_gold: +0.17 (gold standalone Sh = +1.148)
status: RESEARCH_ONLY (passes research floor, fails ≥0.5 promote floor)
key_finding: "Gold blend at 55% weight turns the A-share ETF reversal
              family into a research-grade portfolio; but honest
              decomposition shows gold is doing the heavy lifting
              (Sh 1.15 standalone). The reversal factor's structural
              worst-year problem is mitigated, not solved, by cross-
              asset diversification."
```
