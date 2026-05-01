# Objective — A-Share ETF IVOL-Reversal v1

## Session

`20260501_a_share_etf_ivol_reversal_v1` — WorldQuant 5-agent workflow, 2026-05-01.
Branch: `claude/build-etf-factor-model-O6yXK`.

## Task (user instruction, Chinese)

> 启动 5-agent 挖一个 A 股 ETF 因子。

User selected mechanism #1: **idiosyncratic-volatility (IVOL) reversal** on a
universe of A-share ETFs.

## Research question

**Does cross-sectional rank of idiosyncratic volatility (residualized to the
broad-market beta) predict negative future excess returns at weekly /
monthly horizons across A-share thematic ETFs?**

The classic Ang–Hodrick–Xing–Zhang (2006, 2009) IVOL anomaly says high-IVOL
names underperform. Applying it to ETFs is novel because:

1. ETFs absorb idiosyncratic stock noise but retain *thematic* idiosyncratic
   risk (sector flows, narrative-driven turnover) that can be measured against
   a broad-market beta.
2. The factor is structurally different from the price-level reversal mechanism
   tested in `logs/20260423_a_share_etf_reversal_v1` — IVOL ranks by *vol*
   (squared residual), not by price drawdown. The 2020 short-side blowup that
   killed `r2_lt_rev_60d` does not apply mechanically: high-IVOL in 2020 was
   the small-cap basket, not 消费/医药 winners.
3. Thematic ETFs have stable broad-market betas (~0.6–1.4 vs 510300), so the
   residualization is well-conditioned.

## Scope

- **Universe**: 34 top-liquidity A-share ETFs (broad index 10 + thematic 23 +
  commodity 1), reusing the universe defined in
  `logs/20260424_a_share_etf_daily_flow_accum_v1`.
- **Window**: 2019-01-02 → 2026-04-30 (~7 calendar years, ~1,770 trading days).
- **Bar**: daily OHLCV (adjusted close) via Yahoo Finance v8 chart endpoint.
- **Beta benchmark**: 510300.SS (沪深300 ETF, the largest broad-market ETF).
- **Beta window**: 60-day rolling (~3 months).
- **IVOL window**: 20-day rolling realized residual std (one trading month).
- **Primary horizon**: k = 5 trading days (weekly).
- **Secondary horizons**: k ∈ {1, 10, 20} for fidelity / decay analysis.
- **Rebalance**: weekly (Monday close), 5 bps/side cost.

## Hypothesis (one dominant mechanism, Rule of 8 to follow)

`IVOL = std(residual_t over the past 20d)`, where residual is from a
60-day rolling univariate regression of the ETF's daily return on
510300's daily return. Sort ETFs cross-sectionally on IVOL each week.
**Long the bottom-quintile (low IVOL), short the top-quintile (high IVOL).**

Eight expressions vary the residualization choice (raw vol vs IVOL vs
residual-amplitude), the window (10/20/40d), the lag (t vs t-5), and a
volatility-of-volatility / vol-of-vol amplification.

## Success criteria

**PROMOTE** requires ALL of:
- Long-short IC t-stat at primary k ≥ 3.0 (one-sided, sign matches thesis)
- Long-short Sharpe ≥ 1.0 (gross), ≥ 0.7 (net @ 5 bps/side)
- Long-only top-N excess Sharpe ≥ 0.5 (the deployable A-share metric)
- Worst-year LS Sharpe ≥ 0.5 (the floor that killed reversal R1)
- Best-year-out LS Sharpe ≥ 50% of headline
- Annual turnover ≤ 600% (weekly rebalance with rank-based factor)
- All 5 mandatory audits pass (execution-delay, look-ahead, worst-year,
  best-year-out, falsification-first)

**RESEARCH-ONLY** if any single floor fails but IC t-stat ≥ 2.0 at primary k.
**STOP** if no expression has IC t-stat ≥ 2.0 at any horizon.

## Why structurally different from prior ETF sessions

| Prior session | Mechanism | Failure mode | Why IVOL is orthogonal |
|---|---|---|---|
| `etf_reversal_v1` | Price drawdown / RSI / Bollinger | Worst-year 2020 Sharpe -0.68 (short leg shorted 消费/医药 winners) | IVOL is volatility-rank, not price-level. 2020 winners had moderate IVOL, not extreme. |
| `etf_weekly_tqpb_v1` | Trend quality + selective dip-buy | Long-only @ V7_gold combine; orthogonal overlay only | Different signal — IVOL is risk-rank, not trend-rank. |
| `etf_daily_flow_accum_v1` | Amount-based stealth accumulation | Stage-3 abandoned (no backtest in outputs) | IVOL uses returns-only — no amount input. |

## Hard floors (Stage-2 will refine into session_metadata.yml)

| Metric | Threshold |
|---|---|
| Coverage / day | ≥ 25 ETFs (cross-section min) |
| Turnover / yr | ≤ 600% |
| Net Sharpe @ 5 bps | > 0 |
| Q5 size | ≥ 6 ETFs (top quintile of 34 ≈ 7) |
| Worst-year Sharpe | ≥ 0.5 |
| Best-year-out Sharpe | ≥ 50% headline |
