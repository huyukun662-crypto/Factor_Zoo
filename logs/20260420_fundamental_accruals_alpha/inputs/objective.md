# Session Objective

**Date:** 2026-04-20
**Session id:** 20260420_fundamental_accruals_alpha

## User request

挖掘一个**基本面因子**,使用仓库中的 worldquant-5-agent-workflow 流水线。

## Technical translation

- **Family:** fundamental (财务报表类),not price-volume.
- **Universe:** A-share all-market, exclude ST / 上市 < 252d / 停牌 > 20d in window.
- **Frequency:** monthly rebalance (fundamentals update quarterly; daily rebalance wastes turnover).
- **Horizon:** 20-day forward return as primary; additionally check 60-day for robustness.
- **Region/Delay:** CHN, delay=1 (execute at T+1 close relative to signal formation at T).
- **Deliverable:** one batch of 8 expressions centered on a single dominant economic mechanism, with handoffs, pre-submission audit, and an evaluation plan.

## Non-goals for this session

- No multi-mechanism blending in one batch (violates Rule of 8 economic discipline).
- No PROMOTE decision without the five mandatory pre-PROMOTE audits passing on real data.
- No live-trading recommendation; outcome is either RESEARCH-ONLY or ready-for-next-round.
