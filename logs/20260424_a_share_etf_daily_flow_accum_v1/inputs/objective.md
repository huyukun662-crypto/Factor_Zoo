# Objective — A-Share ETF Daily Flow-Accumulation Factor

## Session

`20260424_a_share_etf_daily_flow_accum_v1` — WorldQuant 5-agent workflow, 2026-04-24.

Branch: `claude/etf-daily-factors-X2LHk`.

## Task (original user instruction, Chinese)

> 用 worldquant workflow 挖一个 etf 日度因子

"Use the WorldQuant 5-agent workflow to mine a single A-share ETF daily factor."

## Scope

- Data frequency: daily close-bar data (OHLC + volume + amount), delay=1, MOC execution.
- Factor universe: 34 A-share on-shore ETFs (broad-index + thematic + commodity), dedup-merged from two prior sessions' universes.
- Window: 2019-01-02 → 2026-04-22 (~1,770 trading days / ~7 calendar years).
- Exactly 8 candidate expressions in one Rule-of-8 batch.
- Evaluation horizons: k ∈ {5, 10, 20} trading days, primary k = 10.
- Rebalance: weekly (5-day period) — trades off turnover cost vs. signal decay.

## Context (why this session, and why this mechanism)

Two prior ETF sessions ran on 20260423:

1. `logs/20260423_a_share_etf_reversal_v1` (daily, 20 ETFs, 2020-2026) — reversal study, closed `RESEARCH_ONLY`. Best expression `r2_lt_rev_60d`: IC t = +2.35, net Sharpe @5bps = +0.56, **blocked by worst-year 2020 Sharpe = -0.68**. The short leg shorted 消费/医药 winners that kept rallying.
2. `logs/20260423_a_share_etf_weekly_tqpb_v1` (weekly, 34 ETFs, 2019-2026) — weekly overlay study, also `RESEARCH_ONLY` but produced an orthogonal defensive overlay (`r1_breakout_vol_conf`) with corr -0.009 to V7_gold.

Neither session used **volume as a primary cross-sectional signal**. The reversal session used price history only; the weekly session used volume as a confirmation filter for breakouts. This session fills the gap — the primary mechanism is **amount-based stealth accumulation** (price-volume-orthogonal / PVO family).

### Economic thesis

Institutional accumulation into a thematic ETF leaves a *volume* footprint before it leaves a *price* footprint. When an ETF sustains abnormally high daily amount (CNY traded) relative to its own 60-day baseline while price impact stays small, the flow is one-sided, patient and well-executed — behavior consistent with building positions, not speculative chasing. Cross-sectionally, ETFs with persistent high-volume / low-impact days should outperform over ~5-20 day horizons as the accumulation resolves into quotes.

Literature anchors:
- Amihud, Y. (2002) ILLIQ — price-impact asymmetry
- Llorente, Michaely, Saar, Wang (2002) — volume-informed vs liquidity decomposition
- Kaniel, Saar, Titman (2008) — investor trading predicts returns
- Barardehi & Bernhardt (2018) — price-volume-orthogonal family

### Why amount-based (not volume-share-count)

ETF share count per unit NAV varies across symbols; CNY amount normalizes for AUM scale and is the economically meaningful flow quantity. All expressions use `amount` (close × volume) directly.

### Why this mechanism structurally avoids the 2020 reversal failure

The 60d-reversal blew up in 2020 because short-side exposure to 消费/医药 winners compounded as those names kept winning. A volume-based ranking doesn't systematically short winners — in 2020 it would have flagged 消费/医药 as *positive* (they were the volume destination). The failure mode is structurally absent.

## Success criteria

**PROMOTE** requires ALL of:
- Long-only IC t-stat at primary k ≥ 3.0
- Long-only top-N excess annualized Sharpe ≥ 1.0 (primary ETF metric; LS reported for sanity only)
- Worst-year Sharpe ≥ 0.5 (the floor that killed the reversal session)
- Best-year-out Sharpe ≥ 50% of headline
- Net Sharpe @ 5 bps/side > 0
- Annual turnover ≤ 600%
- All 5 mandatory audits pass (execution-delay, look-ahead, worst-year, best-year-out, falsification-first)

Otherwise **RESEARCH_ONLY** with an honest write-up.

## Deliverables

- Regardless of verdict: all session artifacts under this folder, committed + pushed to `claude/etf-daily-factors-X2LHk`, draft PR opened against `main`.
- If PROMOTE: additionally a new `factors/price_volume/etf_flow_accum_v1/` folder following the convention of `factors/price_volume/idio_12_3_momentum_disp_gated_v1/`.

## Constraints

- Single batch (Rule of 8). If all 8 expressions fail G4, session closes `RESEARCH_ONLY` — no second round on this session.
- No Tushare (free-tier does not cover the window cheaply). Yahoo Finance v8/chart endpoint is used — same as the reversal session, proven to work in this sandbox.
- Delay = 1 (MOC execution at t+1 after signal at close[t]). Invariant `target_shift == -(1+delay) = -2` must hold in the backtest code.
