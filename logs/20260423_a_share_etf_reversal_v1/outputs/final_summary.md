# Final Summary — A-Share ETF Dip-Buy / Reversal v1 (Rounds 1 + 2)

**Session:** `20260423_a_share_etf_reversal_v1`
**Data:** 18 A-share ETFs daily, 2020-01-02 → 2026-04-22, 27,017 bars
**Verdict:** **RESEARCH-ONLY.** No factor promoted. Session closed after Round 2.

## One-paragraph summary

Ran the WorldQuant 5-agent workflow on 18 high-liquidity A-share ETFs
(broad indices + industry + thematic + gold) at daily frequency. Round 1
(weekly rebalance, k=10) found reversal sign INVERTED — 7/8 signals had
negative IC, quintile monotonicity inverted (Q1 no-dip +0.44% vs Q5 deep-
dip +0.03% over 10 days). The new G5 gate caught this as a batch-level
thesis failure (hypothesis wrong, not code wrong) and routed the batch
back to Agent 2 for mechanism re-specification. Round 2 (monthly rebal,
k=60, long-term reversal + selective OS) found 2 of 8 pass G4: best is
`r2_lt_rev_60d` (60-day reversal) with net Sharpe @5bps = +0.56, Q5-Q1
monotonic, IC t-stat +2.35, diversified long/short legs across 15-17 of
18 ETFs. But 2020 calendar-year Sharpe = -0.68 fails the worst-year ≥ 0
hard floor (2020 was a momentum-dominated year where past winners kept
winning). 6 of 7 years are positive or flat; 2026 YTD Sharpe +1.54 on 71
days. **Reversal on A-share ETFs is a narrow ~60-day window; ≤20d is
momentum, ≈1y is also momentum.**

## Two-round summary

| | Round 1 | Round 2 |
|---|---|---|
| Primary horizon | 10 d (weekly) | **60 d (monthly)** |
| Mechanism scope | broad reversal | long-term + selective OS |
| Expressions | 8 | 8 |
| G1/G2 | 8/8 / 8/8 | 8/8 / 8/8 |
| G3 (includes net-Sharpe ≥ -0.5) | 3/8 | 0/8 (signal-warmup coverage) |
| **G4** | **0/8** | **2/8** |
| G5 batch horizon | **fail** | **pass** (1 of 2 survivors peak at k=60) |
| Best gross Sharpe | +0.33 | **+0.58** |
| Best net Sharpe @5bps | +0.16 | **+0.56** |
| Best IC t-stat | +2.58 (k=10) | **+7.75** (k=20, rsi_extreme_os) |
| Worst-year Sharpe of best | -1.05 | -0.68 (2020) |
| Verdict | thesis rejected, pivot | RESEARCH-ONLY |

## Key numbers (best candidate)

| | value |
|---|---:|
| Expression | `r2_lt_rev_60d` = -logret_60d, universe-EW demeaned |
| Strategy  | top-4 long / bottom-4 short, monthly rebalance |
| Cost baseline | 5 bps/side |
| IC@k60 | +0.0226 (t=+2.35) |
| ICIR annualized | +0.99 |
| Gross Sharpe | +0.58 |
| **Net Sharpe @5bps** | **+0.56** |
| CAGR net | +22.1% |
| Max drawdown | -47% |
| Annual turnover | 1363% |
| Worst year Sharpe | **-0.68 (2020)** ❌ blocks PROMOTE |
| Years positive or flat | 6 of 7 |
| 2026 YTD Sharpe (71 days) | +1.54 |
| Long-leg ETFs (top 3) | 512290生物医药 39%, 512690酒 35%, 512170医疗 34% |
| Short-leg ETFs (top 3) | 518880黄金 50%, 510880红利 37%, 159949创业板50 32% |

## What worked

- **G5 batch-level horizon gate** caught Round 1's mechanism inversion
  correctly and routed back to Agent 2 rather than wasting retries on
  individual expressions. Second successful dogfood after BTC session.
- **Audit probe** (`+logret_20d` at k=60 forward) gave clean pipeline
  sanity check: IC = -0.003, t = -0.34 near zero → no pipeline bug.
  Recommend making this a standard Agent 4 deliverable.
- **Data source substitution** (Yahoo Finance `v8/chart` with User-Agent)
  worked where Chinese-native endpoints (eastmoney, xueqiu, sina, 163)
  were all sandbox-blocked. Adjusted prices computed via `adjclose/close`
  ratio.
- **Research_brief pre-registered the universe-size-thinness concern**
  (|universe|=18, Q5=4). Round 2's threshold-top-4 spec honored it.

## What did not work

- Reversal at k=10 weekly rebalance on this universe does not work —
  data is momentum at that horizon. The Round 1 thesis was simply wrong.
- Long-term reversal at 6-month (k=120) and 1-year (k=250) is ALSO
  wrong-direction — those are momentum zones. Only ~2-3 months (k=60)
  is a reversal window.
- 2020 is a hard year for the reversal bet (short leg = past winners
  from COVID/消费/医药 rally = kept winning), and no year-by-year
  drawdown control can rescue it within our chosen strategy spec.
- Selective RSI oversold signal is strong (IC t=+7.75 at k=20) but
  top-4/bot-4 LS strategy is the wrong container — short leg is noise
  when 16/18 ETFs have zero signal.

## Round 3 suggestions (if user approves)

1. **Long-only top-3 variant of r2_lt_rev_60d** — likely dodges 2020's
   short-leg pain. If long-only-2020 Sharpe > 0, becomes PROMOTE candidate.
2. **Triggered long-only for r2_rsi_extreme_os** — long each ETF when
   its RSI(14) crosses < 30, hold until RSI crosses > 50, equal weight
   across active triggers.
3. **Extend universe to 40-50 ETFs** and rerun the horizon map. 18 is
   thin; more cross-section should sharpen the k=60 reversal and the
   k=250 momentum detection.
4. **Extend history back to 2015** to see whether 2020's bad year is a
   repeating 3-4 year pattern or a one-off.

## Research-log entry (for README)

```
session: 20260423_a_share_etf_reversal_v1
factor_family: trend_technical.long_term_reversal_etf
best_candidate: r2_lt_rev_60d (60-day cross-sectional reversal,
                monthly rebal, top-4 long / bot-4 short, univ-EW demean)
gross_sharpe: +0.58
net_sharpe_5bps: +0.56
ic_tstat_at_k60: +2.35
worst_year_sharpe: -0.68 (2020)
status: RESEARCH_ONLY (fails worst-year floor)
key_finding: "Reversal on A-share ETFs is a narrow ~60d window.
              ≤20d is momentum; ~1y is also momentum. Only the 2-3
              month zone carries reversal payoff. Short-leg damage
              concentrated in 2020 (COVID-era momentum regime)."
```

## Files

```
logs/20260423_a_share_etf_reversal_v1/
├── inputs/                 (objective.md, etf_daily.parquet, fetch.log)
├── scripts/                (01_fetch_etf_daily.py, 02_build_and_backtest.py, 03_round2_backtest.py)
├── outputs/                (2 × research/expressions/backtest MDs; ic/ls/decile/cost/per_year/validation CSVs+JSONs;
│                            momentum_probe_batch_0002.json; alpha_ranking.md; final_summary.md)
├── working/                (handoff_*.json)
├── round_0001.yml / round_0002.yml
└── run_state.json
```
