# Objective — A-Share ETF Weekly Trend-Quality + Pullback-Buy (combine with V7_gold)

## Session

`20260423_a_share_etf_weekly_tqpb_v1` — WorldQuant 5-agent workflow, 2026-04-23.

## Task

> 找周频因子,因为我希望和 A 股 ETF rotation 2.0 (V7_gold) 结合。

## Combination target (V7_gold) — what it already does

V7_gold (`logs/20260422_industry_rotation_cn/outputs/v7_gold_description.md`):

- Universe: 34 A-share thematic ETFs, 9 super-industries
- Weekly rebalance (Fri close, T+1 Monday execute)
- Leg A (penalized momentum): `z(mom_4w) − 1.5·z(turn_4w) + 0.3·breadth` → top-4 equal weight
- Leg G (group rotator): 9 groups, top-3 groups, 1 leader each → 3 names
- Ensemble 50/50 → 7-name book
- MA50 market gate + gold (159934.SZ) fallback
- 15% vol target
- Sharpe 1.91, MaxDD −8.9%, AnnRet 28.6% on 2019-2026 (377 weeks)

Already captured: 4w momentum magnitude, crowding penalty, market breadth,
group-level rotation, regime gate, anti-cyclic hedge, vol target.

**Dimensions NOT captured (combine opportunities):**

1. **Trend quality / consistency** (not magnitude): a 4-week signal with
   mom=+10% can have very different forward behavior if that +10% was
   grindy-up (low daily vol) vs one-big-day (high daily vol). V7 uses
   magnitude only.
2. **Pullback-buy within uptrend**: V7 picks top momentum. It does NOT
   refine entry timing within those picks. The 20260423 ETF reversal
   session (R2) found RSI<30 selective oversold has IC t=+7.75 at k=20
   — potentially a strong entry-timing overlay when conditioned on
   positive medium-term momentum.
3. **Relative strength vs benchmark / cross-section**: V7 uses absolute
   4w return. A z-score relative-strength variant might be more stable
   across low-dispersion regimes.
4. **Drawdown quality**: shallow-drawdown ETFs (vs deep-drawdown) may
   be better trend candidates in V7's universe.

## Hypotheses (Rule of 8, all weekly, long-only top-5 spec)

1. **r1_trend_sharpe_20d**: `mean(daily_ret_20d) / std(daily_ret_20d) × √252`.
   Trend-quality axis orthogonal to mom_4w magnitude.
2. **r1_trend_sharpe_60d**: same, 60-day window. Longer horizon trend quality.
3. **r1_pullback_in_uptrend**: `(40 − RSI14) × I[RSI14 < 40] × I[mom_4w > 0]`.
   Selective dip-buy ONLY inside uptrend. Builds on R2's RSI finding.
4. **r1_vol_adj_mom_4w**: `mom_4w / std_20d`. Orthogonal to raw mom_4w.
5. **r1_rel_strength_zscore**: `(mom_4w − mom_4w_universe_mean) / cross_std`.
   Z-score relative strength.
6. **r1_low_drawdown_20d**: `−max_drawdown_20d` (shallow DD = strong trend).
7. **r1_breakout_vol_conf**: `(close − max_high_20) / std_20 × I[breakout × vol_ratio > 1.2]`.
   Volume-confirmed 20d breakout.
8. **r1_kitchen_sink**: mean rank of 1-7.

## Data contract

- Use existing panel: `/home/user/Factor_Zoo/logs/20260422_industry_rotation_cn/outputs/etf_daily.parquet`
  (48,600 rows, 34 ETFs, 2015-01-05 → 2026-04-22) — already computed by V7_gold session
- Window: 2019-01-01 → 2026-04-22 (matches V7_gold IS/OOS reporting)
- Rebalance frequency: weekly, Friday close → execute Monday (delay = 1 bar)
- Horizon: k = 5 trading days (1 week forward)

## Combination analysis

For each expression (and especially the best-IC candidate):

- Correlation of signal's weekly LS PnL with V7_gold weekly PnL (from
  `round7c_v7_pnl.csv`) — we want LOW correlation for additive alpha
- **ENSEMBLE 50/50 backtest** for the top candidate:
  `new_pnl_weekly = 0.5 × v7_pnl + 0.5 × new_signal_pnl`
- Report: Sharpe / MaxDD of combined vs standalone, whether combine
  improves the worst-year Sharpe (2020 COVID or 2022 bear)

## Hard floors

| Metric | Threshold |
|---|---|
| Rank IC mean at k=5 | ≥ 0.02 (weekly is noisier than monthly) |
| ICIR | ≥ 0.3 |
| Standalone LS gross Sharpe | ≥ 0.8 |
| Standalone LS net Sharpe @5bps | ≥ 0.4 |
| |corr| with V7_gold weekly PnL | ≤ 0.70 (otherwise adds nothing) |
| Combined 50/50 Sharpe | > max(V7_gold, standalone) |
| Worst year Sharpe (combined) | ≥ V7_gold worst year (−0.13 → 0) |

## Decision rules

- **PROMOTE as combine candidate**: best signal clears IC/Sharpe floors AND
  |corr with V7| ≤ 0.70 AND 50/50 combined Sharpe > V7_gold
- **RESEARCH-ONLY**: signal has mechanism but is too correlated OR does not
  improve combined
- **FAIL**: no signal clears IC/Sharpe floors

## Non-goals

- Not rebuilding V7_gold (already done, not changing its design)
- Not testing monthly frequency (R2 of reversal session covered that)
- Not using fundamental data (ETF-level fundamentals are noisy)
