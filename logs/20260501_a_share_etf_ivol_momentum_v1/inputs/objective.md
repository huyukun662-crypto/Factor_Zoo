# Objective — A-Share ETF Inverted-IVOL Momentum v1

## Session

`20260501_a_share_etf_ivol_momentum_v1` — WorldQuant 5-agent workflow,
2026-05-01. Continuation of the open thread from
`logs/20260501_a_share_etf_ivol_reversal_v1`.
Branch: `claude/build-etf-factor-model-O6yXK`.

## Task (user instruction, Chinese)

> sessionA 继续研究 sessionB 先 research only.

User asked to continue the IVOL session research. The prior session
(reversal v1) found the AHXZ IVOL anomaly is **inverted** in A-share
ETFs: long high-IVOL / short low-IVOL gives +0.66 LS Sharpe at monthly
rebalance, but worst-year (2024) = +0.04 misses the 0.5 floor.

This session pursues the three open-thread questions:

1. **Regime gate** — does an MA50 broad-market filter rescue 2024?
2. **Long-only top-N** — does long-only top-3/top-5 (the deployable
   A-share metric per CLAUDE.md) beat the LS variant?
3. **V7_gold orthogonality** — is inverted-IVOL incremental to the
   already-deployed V7_gold momentum factor in
   `logs/20260422_industry_rotation_cn`?

## Research question (revised)

**Is inverted IVOL — long high-IVOL A-share thematic ETFs at monthly
rebalance, conditioned on a broad-market trend gate — a deployable
factor that adds incremental Sharpe to V7_gold?**

## Scope

- **Universe**: same 30-ETF A-share universe used in the parent
  session (broad index 8 + thematic 21 + commodity 1).
- **Window**: 2019-01-02 → 2026-04-30 (~7 years).
- **Bar**: daily OHLCV from the shared cache.
- **Beta benchmark**: 510300.SS (沪深300 ETF).
- **Beta window**: 60 trading days.
- **IVOL window**: 20 trading days (monthly).
- **Primary horizon**: k = 20 trading days (monthly — best from prior
  sensitivity).
- **Rebalance**: monthly (~21 trading days).
- **Cost**: 5 bps / side.
- **Regime gate**: MA50 of 510300 close. When 510300 close > MA50,
  signal active; otherwise hold cash (long-only) or zero positions
  (LS).

## Mechanism

For each follower ETF i and date t:
1. `β_i_t = cov(r_i, r_510300; 60d) / var(r_510300; 60d)`
2. `ε_i_t = r_i_t − β_i_t × r_510300_t` (residual return)
3. `IVOL_i_t = std(ε_i over past 20d) × sqrt(252)` (annualized)
4. `signal = +IVOL` (the *inverted* convention: high IVOL → long)
5. Cross-section ranking. Long top-N (top-3 or top-5).

## Hypothesized 8 expressions (Rule of 8)

1. `m1_ivol_mom_LS_no_gate` — baseline: long Q5 (top-20%) high-IVOL,
   short Q1 (bottom-20%) low-IVOL, no regime gate. Reproduces prior
   +0.66 result and serves as the no-gate control.
2. `m2_ivol_mom_top3_no_gate` — long-only top-3 high-IVOL, no gate.
3. `m3_ivol_mom_LS_ma50_gate` — same as m1 but flat when 510300 < MA50.
4. `m4_ivol_mom_top3_ma50_gate` — long-only top-3 with MA50 gate.
5. `m5_ivol_mom_top5_ma50_gate` — long-only top-5 with MA50 gate.
6. `m6_ivol_mom_top5_ma200_gate` — slower regime gate (MA200 instead of MA50).
7. `m7_ivol_mom_top5_ma50_lag5` — m5 with IVOL signal lagged 5 days
   (slow-decay sensitivity).
8. `m8_total_vol_mom_top5_ma50` — use TOTAL vol instead of residual
   IVOL (no beta residualization). Sanity: if m8 ≈ m5, the
   residualization isn't critical.

## Success criteria (deployable)

A-share deployment is **long-only enhancement, not LS** (per CLAUDE.md
A-share lessons). PROMOTE requires ALL of:

- Long-only Sharpe ≥ 1.0 OR excess (vs EW universe) Sharpe ≥ 0.6
- Worst-year Sharpe ≥ 0.5 (the floor that killed reversal R1 and
  inverted-IVOL R1)
- Best-year-out Sharpe ≥ 50% headline
- Annual turnover ≤ 600% (monthly rebalance with quintile turnover
  typical 200-400%)
- Net Sharpe @ 5 bps > 0
- All 5 mandatory audits pass
- |corr| with V7_gold weekly returns ≤ 0.5 (orthogonality requirement
  for incremental deployment)

RESEARCH-ONLY if any single floor fails but Sharpe ≥ 0.5 and worst-year
≥ 0 (no negative years).

STOP if regime gate doesn't rescue 2024 worst-year.

## Why this could work where R1 didn't

- **2024 was a deleveraging regime** — broad-market downtrend with
  thematic narrative collapse. The MA50 gate flatten exposure during
  drawdowns and should rescue the worst year.
- **Top-3 concentration** matches the way thematic ETF momentum
  actually deploys — V7_gold uses top-3 within groups for the same
  reason.
- **Long-only beats LS in A-share** — short-side has structural
  costs (limited shorting, lottery-bid sticky on the high-vol leg).
  The deployable metric is long-only top-N excess to the EW universe.

## Hard floors

| Metric | Threshold |
|---|---|
| Long-only Sharpe (gross) | ≥ 1.0 |
| Long-only Sharpe (net @ 5bps) | ≥ 0.7 |
| Excess Sharpe vs EW universe | ≥ 0.6 |
| Worst-year Sharpe | ≥ 0.5 |
| Best-year-out / headline | ≥ 0.5 |
| Annual turnover | ≤ 600% |
| Q5/top-N min size on 95% of days | ≥ 3 (long-only top-3) or ≥ 5 (top-5) |
| |corr| vs V7_gold weekly | ≤ 0.5 |
