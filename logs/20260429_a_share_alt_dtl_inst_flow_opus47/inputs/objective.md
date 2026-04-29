# Session objective

**Goal:** Mine an A-share *alternative-data* alpha factor using the
worldquant-5-agent-workflow skill.

**Scope choice:** Dragon-Tiger List (龙虎榜) institutional-seat informed-flow.

**Why "alternative":**
- It is not OHLCV/volume — it is event-triggered disclosure (only stocks
  hitting CSRC/exchange disclosure rules appear).
- The *signal carrier* is the seat type (机构专用 vs. 营业部) and net-buy
  direction, which is a behavioral/textual disclosure tag, not a price.
- The mechanism is informed-trading microstructure, not factor-style
  risk-premium.

**Constraints (inherited from CLAUDE.md A-share lessons):**
- Industry-neutralize all volume-price-adjacent components.
- Report BOTH long-short AND long-only Q5 excess metrics.
- Default execution delay = 1 day (DTL is published t+0 ~17:00, so `delay=1`
  means we trade at t+1 close; `delay=0` would be look-ahead).
- Monthly rebalance considered as fallback if daily turnover blows up cost.

**Universe:** CSI All-Share, drop ST and IPO < 250 trading days.
**Sample window (planned):** 2018-01-01 → 2025-12-31 (8y).
**Train / Validate / Test:** 2018–2019 / 2020 / 2021–2025 (per
`references/tvt-split-template.md`).

**Out-of-scope this session:** northbound-flow (`hk_hold`, paid tier),
satellite, news-sentiment NLP.
