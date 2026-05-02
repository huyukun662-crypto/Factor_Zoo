# Objective — A-Share ETF Risk-Adjusted Momentum v1

## Session

`20260502_a_share_etf_riskadj_mom_v1` — WorldQuant 5-agent workflow,
2026-05-02. Branch: `claude/ashare-etf-factor-worldquant-dDDJ2`.

## Task (user instruction, Chinese)

> 用 worldquant workflow 挖一个 a 股 etf 因子

User asked to mine a fresh A-share ETF factor using the 5-agent
WorldQuant workflow. This session picks a mechanism orthogonal to the
existing logs (IVOL momentum/reversal, daily-flow, lead-lag,
weekly-TQPB, daily-flow-accum) and grounded in classic equity-factor
literature: **risk-adjusted momentum (Sharpe-style)**.

## Research question

**Does cross-sectional ranking of A-share ETFs by risk-adjusted
return (k-day total return divided by k-day realized volatility)
deliver a deployable monthly long-only top-N portfolio that beats
plain-momentum at A-share thematic-ETF level?**

The economic claim is straightforward: when returns are normalized by
volatility, ranking deflates the noise from short-term volatility
spikes (IPO/listing turbulence, single-day limits) and surfaces ETFs
with persistent risk-adjusted trends. Risk-adjusted momentum has been
documented in single-name equities (Asness 1994, AQR follow-ups), in
US sector-ETFs (Faber 2007 derivatives), and is widely used inside
multi-asset trend-following programs. To our knowledge it has not been
formally tested on a small A-share thematic-ETF universe.

## Scope

- **Universe**: 30-ETF A-share universe used in prior sessions
  (broad index 8 + thematic 21 + commodity 1).
- **Window**: 2019-01-02 → 2026-04-30 (~7 years).
- **Bar**: daily OHLCV from `_shared_cache/etf_daily.parquet`.
- **Beta benchmark**: 510300.SS (沪深300 ETF) — used for excess
  computation, not residualization (the factor is total-return
  momentum, not residual momentum).
- **Primary horizon**: k = 60 trading days (~3 months).
- **Rebalance**: monthly (~21 trading days, end-of-month signal).
- **Cost**: 5 bps / side (10 bps round-trip).

## Mechanism (one dominant)

For each ETF i and date t (signal date = end of calendar month):

1. `mom_k_t = close[t] / close[t-k] - 1`  (k = 60 default)
2. `vol_k_t = std(log_ret_i, past k bars) * sqrt(252)`
3. `signal_i_t = mom_k_t / max(vol_k_t, eps)`  (Sharpe-style)
4. Cross-section rank → long top-N (top-3 or top-5).
5. Hold for 21 trading days, then re-rank.

The 8 expressions vary `k`, `N`, regime gates, and risk-adjustment
flavor (vol vs. downside vol vs. unadjusted), all on the **same
mechanism**.

## Hypothesized 8 expressions (Rule of 8)

1. `m1_riskadj_mom_60_top5` — baseline: 60d return / 60d vol, monthly,
   top-5 long-only.
2. `m2_riskadj_mom_60_top3` — 60d/60d, monthly, top-3 (more concentrated).
3. `m3_riskadj_mom_120_top5` — 120d/120d (slower lookback) monthly top-5.
4. `m4_riskadj_mom_20_top5` — 20d/20d (faster lookback) monthly top-5.
5. `m5_riskadj_mom_60_top5_ma50_gate` — m1 plus MA50(510300) regime
   gate (cash when below MA50).
6. `m6_riskadj_mom_60_skip5_top5` — Jegadeesh-Titman skip: 60d return
   computed t-65→t-5 to suppress 1-week reversal contamination.
7. `m7_plain_mom_60_top5` — control: plain 60d return, no
   vol-deflation. If m1 ≈ m7, vol-deflation isn't doing real work.
8. `m8_sortino_mom_60_top5` — replace 60d vol with 60d *downside*
   vol (std of negative log-returns). Tests whether downside-only
   risk adjustment is the operative element.

## Success criteria (deployable, A-share-aware)

A-share deployment is **long-only enhancement, not LS** (per CLAUDE.md
A-share lessons). PROMOTE requires ALL of:

- Long-only Sharpe ≥ 1.0 (gross)
- Long-only Sharpe ≥ 0.7 (net @ 5 bps/side)
- Excess Sharpe vs EW universe ≥ 0.6
- Worst-year Sharpe ≥ 0.5
- Best-year-out Sharpe ≥ 50% headline
- Annual turnover ≤ 800% (monthly rebalance, top-N)
- All 5 mandatory audits pass (delay, look-ahead, worst-year,
  best-year-out, falsification-first)

RESEARCH-ONLY if Sharpe ≥ 0.5 and worst-year ≥ 0 but a single floor
fails.

STOP if no expression breaks 0.5 net Sharpe.

## Why this could work

- Risk-adjusted ranking is robust to the lottery-bid noise that
  bedevils raw-return momentum on A-share thematic ETFs.
- Monthly rebalance keeps turnover and cost realistic at A-share
  retail-broker fees.
- Downside-risk-adjustment (m8) and skip-most-recent (m6) are the
  two cleanest variants that decouple the Sharpe-style mechanism
  from confounds (downside-aversion vs. one-week reversal).
