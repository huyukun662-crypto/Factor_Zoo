# Final Summary — A-Share ETF Reversal v2

**Session:** `20260424_a_share_etf_reversal_v2`
**Universe:** 34 A-share thematic ETFs, 2019-01-04 → 2026-04-22 (43,136 live rows)
**Verdict:** **RESEARCH-ONLY.** No factor promoted. Session closed after Round 1.

## One-paragraph summary

The WorldQuant 5-agent workflow was applied to the 34-ETF V7_gold universe
to extend prior session's 18-ETF reversal results. Mechanism reproduces and
sharpens: **IC t-stat is 3.02 at k=40, 2.43 at k=60, 2.29 at k=80** — the
40-to-80d horizon is the reversal zone on this universe (vs prior 18-ETF's
~60d point estimate). **Long-only top-3 monthly** is the dominant wrapper
(net Sharpe +0.774 at 5 bps for r1_rev_40d; LS adds a persistent ~0.8 Sharpe
drag on the short leg from momentum persistence in A-share thematics).
**All 4 pipeline audits pass** (execution-delay, look-ahead randomization,
best-year-out ratio, falsification probe). The one blocker is the
**worst-year Sharpe floor**: every candidate has 2023 (or 2022) sub-zero
(best: r1_rev_40d weekly at -0.028; most: monthly variants at -0.6 to -0.8).
Fusion with V7_gold does not help — every blend weight reduces the combined
Sharpe vs V7 alone. Net: **mechanism confirmed and cross-universe replicated,
but worst-year failure blocks PROMOTE**.

## Headline comparison — A-share ETF reversal sessions

| | v1 (2026-04-23, 18 ETFs) | **v2 (this session, 34 ETFs)** |
|---|---|---|
| Horizon map | k=10 → momentum; k=60 → reversal; k=120/250 → momentum | k=5 → neutral; k=20 → weak; **k=40 sweet**; k=60/80 → reversal; k ≥ 120 not tested |
| Best expression | r2_lt_rev_60d (LS top-4/bot-4 monthly) | **r1_rev_40d (long-only top-3 monthly)** |
| Best net Sh @5bps | +0.56 | **+0.774** |
| Best IC t | +2.35 | **+3.02** |
| Worst year (best cand.) | 2020 Sh = -0.68 | 2023 Sh = -0.585 |
| Wrapper learning | LS was the assumed container | **long-only dominates; short-leg ~0.8-1.0 Sh drag** |
| V7 fusion | (not tested) | tested: no value added at any weight |

## Key numbers — headline candidate `r1_rev_40d`, long-only top-3 monthly

| | value |
|---|---:|
| Expression | `-logret_40d`, universe-EW demeaned |
| Strategy  | top-3 long, 20-bar hold (monthly rebalance on rolling 4th Friday) |
| Cost baseline | 5 bps/side |
| IC @ k=40 | +0.0262 (t=+3.02, n_dates=1727) |
| ICIR annualized | ≈ +1.08 |
| Gross Sharpe | +0.81 |
| **Net Sharpe @5bps** | **+0.774** |
| Net Sharpe @15bps | +0.702 |
| Max drawdown | -42.4% |
| Annual turnover | ≈ 17% |
| **Worst year Sharpe** | **-0.585 (2023)** ❌ blocks PROMOTE |
| Years ≥ 0 | 6 of 8 (2022, 2023 negative) |
| 2019-2020 Sharpe | 2.61 / 2.06 |
| 2024-2026 YTD Sharpe | 1.07 / 0.99 / 0.65 |
| Best-year-out Sharpe | +0.563 (drop 2020), ratio 0.73 |
| Falsification probe IC @ k=60 | -0.003 (t=-0.32) |

## What worked

- **Long-only container** — single biggest lever. LS losses were structural
  (short leg sheds ~0.8-1.0 Sharpe) and removing the short side lifted
  headline Sharpe from near-zero into +0.77 territory.
- **Monthly rebalance** — lower turnover (17% annual) improves cost
  robustness and reduces whipsaw. But weekly rebalance has the best
  worst-year (2023 Sh -0.028 ≈ flat) — a tradeoff.
- **Horizon scan** — the k=20, 40, 60, 80 ladder converged to a clean
  IC-t plateau at 40-80d. Prior 18-ETF session's point estimate at k=60
  generalized into a wider 40-80d band on the larger cross-section.
- **Falsification probe** — `+logret_20d` at k=60 was forced into the
  batch and came out near zero (IC -0.003, t -0.32), confirming the
  pipeline is clean of momentum leakage.
- **G1 non-degeneracy gate** — caught no bug this time but pre-empted a
  false positive on `r1_dd60_recover` (nonzero fraction 0.43, still above
  the 0.01 floor).
- **Baseline re-reproduction** — V7's Sh on the common 349-week inner-joined
  slice was 3.73 (post-warmup), not the published full-sample 1.91. Fusion
  comparisons were run at the correct baseline to avoid inflation bias.

## What did not work

- **Drawdown-event signals** — `r1_dd60_raw` IC = -0.006 (t = -0.78 at k=60)
  and `r1_dd60_recover` IC = +0.013 (t = +1.63). Drawdown depth alone is
  not a reversal feature on this universe (past-winners kept winning,
  past-dippers kept falling at 60d horizon). The 5d-recovery confirmation
  gate added a small positive but not enough for G4.
- **LS wrapper** — every LS configuration had net Sh < 0 at 5 bps. The
  short leg is systematically poisonous on A-share thematic ETFs.
- **V7 fusion** — negative delta at all blend weights (10-50%). Reversal
  factor's residual-vs-V7 is not a productive addition to the V7 chassis
  on this window.
- **Worst-year floor (2023 specifically)** — no candidate clears the ≥ 0
  research floor, let alone the ≥ 0.5 promote floor. 2023 was a momentum
  regime year on A-share thematics.

## Cross-session finding: "bad-reversal-year" pattern

Two sessions, two different bad years:

| Session | Worst year | Dominant regime | Mechanism |
|---|---|---|---|
| v1 (18 ETFs) | 2020 | COVID momentum in 消费/医药 | past-winners kept winning → short leg hit |
| **v2 (34 ETFs)** | **2023** | TMT dispersion, AI/半导体 concentration | past-losers kept losing → long leg hit |

The bad year has **shifted from short-leg-pain (2020) to long-leg-pain (2023)** as the wrapper moved from LS to long-only. The underlying issue is that A-share thematic regimes produce ~1-in-4 years where reversal reverses sign, and the current 8-year sample has only 6 years ≥ 0. Regime detection (not factor improvement) is the next frontier.

## Round 2 suggestions (if user approves)

1. **Regime-conditional long-only** — gate the r1_rev_40d long-only top-3
   trade by a simple regime filter (universe breadth, dispersion z-score,
   or 200d momentum of the universe EW index). If the filter flips off
   during 2023-like regimes (concentrated trending markets), the worst
   year should lift toward zero.
2. **k=40 ensemble with k=80 for diversification** — same horizon band,
   different lookback. Low correlation between the two (both IC positive)
   might stabilize the year-over-year variance.
3. **Monthly long-only top-3 but with stop-loss rule** — if any held ETF
   breaks its 20d low, exit mid-cycle. Adds touch of ex-post discipline
   that may help 2022-2023 specifically.
4. **Long-only top-3 with industry dispersion filter** — only enter when
   the cross-section dispersion of 40d returns > 75th percentile (i.e.
   only trade when there's a clear loser cohort). Thin-trigger, high
   conviction.

None of these rescue the full-period promote-grade worst-year 0.5 floor
without regime-conditioning. The next session should start from the
regime-conditional angle (suggestion 1).

## Workflow / dogfood observations

- **Long-only vs LS divergence is not a rounding error.** Short-leg drag
  was ~0.8 Sharpe, dominating the LS headline. Recommend updating
  `references/common-pitfalls.md` with an explicit "test both LS and
  long-only top-N" directive for A-share ETF / concentrated-regime universes.
- **Within-date symbol-label permutation** is the correct randomization
  scheme for the look-ahead audit; within-symbol shuffle retains mean-return
  bias per symbol and can produce misleadingly non-zero IC on the shuffled
  target. Worth documenting in `references/execution-delay-audit.md`.
- **Common-window baseline re-reproduction** — V7 Sharpe changed from
  1.76 (prior session's 377w) to 3.73 (this session's 349w inner-join).
  Always compute the baseline on the exact alignment window used for
  fusion, or fusion deltas become uninterpretable.

## Research-log entry (for README)

```
session: 20260424_a_share_etf_reversal_v2
factor_family: trend_technical.medium_horizon_reversal_etf (k=40-80)
best_candidate: r1_rev_40d (long-only top-3, monthly rebal, universe-EW demean)
universe: 34 A-share thematic ETFs (same as V7_gold)
gross_sharpe: +0.81
net_sharpe_5bps: +0.774
net_sharpe_15bps: +0.702
ic_tstat_at_k40: +3.02
worst_year_sharpe: -0.585 (2023)
best_year_out_ratio: 0.73
status: RESEARCH_ONLY (fails worst-year floor; V7 fusion flat)
key_finding: "On 34-ETF extended universe, reversal sweet spot widens
              from 60d point to 40-80d band. k=40 is sharpest. Long-only
              top-3 dominates LS (short leg = persistent 0.8 Sh drag).
              2023 is this session's bad-reversal year (2020 was prior
              session's). Cross-session pattern: ~1-in-4 years flip sign.
              Regime-conditional gating is the natural next direction."
```

## Files

```
logs/20260424_a_share_etf_reversal_v2/
├── inputs/                  (objective.md)
├── scripts/
│   ├── 01_build_and_backtest.py
│   └── 02_audits_and_fusion.py
├── outputs/
│   ├── research_brief.md
│   ├── session_metadata.yml
│   ├── expressions_batch_0001.md
│   ├── ic_table_batch_0001.csv
│   ├── decile_summary_batch_0001.csv
│   ├── ls_summary_batch_0001.csv
│   ├── longonly_summary_batch_0001.csv
│   ├── per_year_sharpe_batch_0001.csv
│   ├── cost_sensitivity_batch_0001.csv
│   ├── validation_gates_batch_0001.json
│   ├── audit_report.json
│   ├── v7_fusion_results.csv
│   ├── v7_fusion_pnl_r1_rev_40d_monthly.csv
│   ├── signal_panel.parquet
│   ├── pnl_*_longonly_*.csv  (per-candidate pnl series)
│   ├── alpha_ranking.md
│   └── final_summary.md
├── working/                 (handoff_1_to_2.json, handoff_2_to_3.json)
├── round_0001.yml
└── run_state.json
```
