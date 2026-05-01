# Objective — A-Share ETF Broad-Market Lead-Lag Spillover v1

## Session

`20260501_a_share_etf_leadlag_v1` — WorldQuant 5-agent workflow, 2026-05-01.
Branch: `claude/build-etf-factor-model-O6yXK`.

## Task (user instruction, Chinese)

> 启动 5-agent 挖一个 A 股 ETF 因子。

User selected mechanism #2: **broad-market lead-lag spillover** — the
broad-index ETFs (沪深300 / 中证500 / 中证1000) lead, and thematic ETFs
lag asymmetrically. Cross-section trades on past broad-ETF returns
projected onto each thematic ETF's exposure.

## Research question

**Do lagged broad-ETF returns, projected onto each thematic ETF's
broad-beta vector, produce a positive cross-sectional return predictor at
1-3 day horizons after stripping the contemporaneous market move?**

Lo–MacKinlay (1990) and Hou (2007) document slow information diffusion
where small / less-liquid names lag large ones. In A-share, broad-index
ETFs are the most liquid instruments and information leaders — thematic
ETFs (especially smaller AUM thematic plays like 半导体 / 创新药 /
游戏) are well-known to **react to broad-market moves with a 1-2 day
lag** because thematic flows follow risk-on / risk-off shifts.

## Scope

- **Universe**: same 34 ETFs (broad index 10 + thematic 23 + commodity 1).
- **Leaders (broad set)**: 510300 (沪深300), 510500 (中证500),
  512100 (中证1000) — 3 broad benchmarks spanning the size spectrum.
- **Followers**: the remaining 31 ETFs (or all 34, with self-projection
  zeroed out).
- **Window**: 2019-01-02 → 2026-04-30 (~7 years).
- **Bar**: daily OHLCV (adjusted close) via Yahoo Finance v8 chart endpoint.
- **Beta window**: 60-day rolling (~3 months) for projecting follower onto
  each leader.
- **Primary horizon**: k = 1 trading day (next-day reaction).
- **Secondary horizons**: k ∈ {2, 3, 5} for diffusion-decay analysis.
- **Rebalance**: daily (close-to-close), 5 bps/side cost.

## Hypothesis (one dominant mechanism, Rule of 8 to follow)

For each follower ETF i and leader L:
```
beta_iL_t = cov(r_i, r_L; 60d) / var(r_L; 60d)
spillover_signal_iL_t = beta_iL_t × r_L_t          # most recent leader move
```

Aggregate over 3 leaders (sum / max-beta-weighted / equal-weighted).
Cross-sectionally rank each day, **long top quintile** (highest predicted
follower-up move), **short bottom quintile**.

Eight expressions vary:
- which leaders are used (single vs multi-leader)
- the leader-lag (t-1 only vs cumulative {t-1, t-2})
- whether to subtract own contemporaneous return (orthogonalization)
- a vol-scaled variant
- a residual-spillover variant (project on residual leader move, not raw)

## Success criteria

**PROMOTE** requires ALL of:
- Long-short IC t-stat at primary k=1 ≥ 3.0 (one-sided, positive)
- Long-short Sharpe ≥ 1.0 (gross), ≥ 0.5 (net @ 5 bps/side)
- Long-only top-N excess Sharpe ≥ 0.5 (deployable A-share metric)
- Worst-year LS Sharpe ≥ 0.5
- Best-year-out LS Sharpe ≥ 50% of headline
- Annual turnover ≤ 1500% (daily-rebalance ceiling — lead-lag is a
  short-horizon signal so cost is the binding constraint)
- All 5 mandatory audits pass

**Cost is the dominant risk** for daily-rebalance signals. The G3 net
Sharpe @ 5 bps gate is the decisive filter.

## Why structurally different from prior ETF sessions

| Prior session | Mechanism | Why lead-lag is orthogonal |
|---|---|---|
| `etf_reversal_v1` | Own-history reversal | Lead-lag uses broad-ETF returns as the input, not own price history |
| `etf_weekly_tqpb_v1` | Own-trend quality / RSI | Different input domain entirely |
| `etf_daily_flow_accum_v1` | Own-amount accumulation | Different input domain |
| `etf_ivol_reversal_v1` (sibling, 20260501) | Own residual vol | Lead-lag uses leader returns; IVOL uses follower residuals |

Lead-lag is the only mechanism in the ETF Factor Zoo so far that uses
**cross-asset return** as the primary input.

## Hard floors

| Metric | Threshold |
|---|---|
| Coverage / day | ≥ 25 followers |
| Turnover / yr | ≤ 1500% (daily rebalance) |
| Net Sharpe @ 5 bps | > 0.3 (binding) |
| Q5 size | ≥ 6 ETFs |
| Worst-year Sharpe | ≥ 0.5 |
| Best-year-out Sharpe | ≥ 50% headline |
