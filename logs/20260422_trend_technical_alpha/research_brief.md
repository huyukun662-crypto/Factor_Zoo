# Research Brief — A-share Trend / Technical Factors

**Session:** `20260422_trend_technical_alpha`
**Author:** Agent 1 — Research Librarian
**Date:** 2026-04-22
**Family:** 趋势-技术 (trend / technical)
**Cost model:** turnover-aware, 5 bps per side (万5)

---

## 1. Why this family, why now

Prior 4 sessions on this repo established:

- **Accruals (基本面)** — deployed (`alpha_01_accruals_median_ttm_ind_neutral_v2`, LS 1.42, Q5 IR 0.92).
- **Lottery demand / MAX (量价)** — RESEARCH-ONLY after 6 rounds, 28 alphas. Structural finding: in A-share 2018-2025, lottery signals exhibit an intrinsic tradeoff between residual IC ≥30 % and worst-year Sharpe ≥0.5.
- **Earnings-related fundamentals (PEAD, gross profitability)** — queued, not yet executed.

Trend / technical is the third of four factor families in `README.md` and the remaining un-mined liquid family. The user explicitly asks for an A-share trend factor.

The honest prior, before any backtesting, is *unfavorable*:

- Liu-Stambaugh-Yuan (2019, JFE) document that **A-share equity returns are dominated by short-term reversal**, not momentum.
- Standard 12-1 cross-sectional momentum (Jegadeesh-Titman 1993) has been **negative** on Chinese A-share for most of the post-2015 sample.
- However, *several* trend-family signals do work in A-share:
  - 52-week-high proximity (George-Hwang 2004) — robust in many emerging markets.
  - Multi-MA trend aggregation (Han-Zhou-Zhu 2016 RFS, "A trend factor") — beats classic momentum out-of-sample.
  - Idiosyncratic momentum (Blitz-Huij-Martens 2011) — residual-momentum after factor exposures, immune to the reversal that destroys raw momentum.
  - Time-series momentum (Moskowitz-Ooi-Pedersen 2012) — distinct from cross-sectional.

So: **don't bet on raw 12-1 cross-sectional momentum.** Bet on derivatives that residualize the reversal noise out — trend strength, MA aggregation, idiosyncratic momentum.

## 2. Academic landscape (focused subset)

| # | Paper | Mechanism | A-share evidence |
|---|---|---|---|
| 1 | Jegadeesh & Titman 1993 | 12-1 cross-sectional momentum | ✗ Negative in A-share (Liu-Stambaugh-Yuan 2019) |
| 2 | George & Hwang 2004 RFS | 52-week-high proximity | ✓ Documented positive (Birru 2015 reconciles with momentum) |
| 3 | Moskowitz-Ooi-Pedersen 2012 JFE | Time-series momentum (sign of own past return) | Mixed in A-share |
| 4 | Han-Zhou-Zhu 2016 RFS | Trend factor — convex combination of `P/MA_k` for k∈{3,5,10,20,50,100,200,400,600,800,1000} | ✓ Out-of-sample beats momentum, works in many markets |
| 5 | Blitz-Huij-Martens 2011 JEF | Idiosyncratic momentum — residualize past return after FF3, then sort | ✓ Robust across markets including emerging |
| 6 | Da-Gurun-Warachka 2014 RFS | Frog-in-the-pan / information discreteness — gradual info > discrete jumps | ✓ Documented in A-share |
| 7 | Han-Yang-Zhou 2013 JFQA | MA crossover with TS-MOM | Mixed |
| 8 | Asness-Moskowitz-Pedersen 2013 JF | Value & momentum everywhere | A-share stands out as *anti*-momentum |

## 3. Data we actually have (constraint analysis)

From `.cache/`:

- `daily.parquet` — 7.88 M rows, 5 614 stocks, **2018-01-02 → 2025-04-18**, columns `[ts_code, trade_date, open, close, vol, amount]`.
- `adj_factor.parquet` — 8.13 M rows, daily backward-adjustment factor.
- `daily_basic.parquet` — 7.81 M rows, `total_mv, circ_mv`.
- `panel.parquet` — has `industry` column (CITIC L1 mapped from Tushare `stock_basic`).

**Constraint:** no `high` / `low` columns. This kills strict 52-week-*high* (which needs intraday high). We use `rolling(252).max(close_adj)` as a proxy. Acceptable because daily close on a real high day is typically within ~0.5 % of intraday high in A-share (limit-up notwithstanding).

**Constraint:** no `daily_basic` history before 2018 — already start at 2018-01-02, so 7.3 years usable. Train 2018-22 / Validate 2023 / Test 2024-25YTD as before.

## 4. Candidate mechanisms (ranked by my prior)

1. **Trend strength via multi-horizon agreement** (Han-Zhou-Zhu lite) — **prior favorite**. Aggregates `P/MA_k` across 6-7 horizons; the trend signal is the consistency, not the magnitude.
2. **Idiosyncratic momentum** — residualize 252-d return after industry + size + value-proxy, then rank. Killing the reversal-dominated raw component is the key.
3. **Trend regression t-stat** — slope-t of log-price on time (60-d, 120-d windows). High t = persistent up-trend. Low t (incl. negative) = persistent down-trend.
4. **52-week-high proximity proxy** — `close / rolling_max(close, 252)`. Stocks near their 1-year high have run-room.
5. **MA crossover stack** — `sign(MA_20 - MA_60) + sign(MA_60 - MA_120) + sign(MA_120 - MA_252)`, integer-valued ∈ [-3,+3].
6. **Trend Sharpe** — `cum_return / std_of_daily_returns` over 60-120 d.
7. **Frog-in-the-pan** — `sign(R_T) × (% positive days)` over 252 d. Continuous information arrivals get under-reacted to; jumps over-reacted.
8. **Classic 12-1 momentum** — keep as a baseline / falsification anchor.

## 5. Operator / construction notes

- All price levels MUST be **adjusted close** (`close × adj_factor`). Raw close has dividends and splits.
- Returns: `r_t = log(close_adj_t / close_adj_{t-1})`.
- Forward return targets: `fwd_ret_K = sum(r_{t+1+delay : t+1+delay+K})` with `delay=1` (T+1 execution). Already validated invariant `target_shift = -(1+delay) = -2` for delay=1.
- Industry neutralization: per `trade_date`, demean alpha within each `industry` (CITIC L1, ~110 groups available from `panel.parquet`).
- Size neutralization: optional second step, demean within `size_bin` (already in panel).

## 6. Risks & caveats specific to trend in A-share

1. **Reversal dominance.** Any signal that loads on raw 12-1 return will be hurt. Need to either residualize reversal out (1-month return) or use trend-shape signals that are not just "past return".
2. **Limit-up days.** A-share has ±10 % daily limit (±20 % for ChiNext post-2020). A stock locked at limit-up shows zero further return that day; the "trend" is partly mechanical.
3. **2024 micro-cap rally.** Late-2023 / Jan-2024 saw a violent reversal where small-caps fell 30 %+ in 3 weeks then bounced. Any trend signal long the 2023 winners got destroyed Jan-Feb 2024. Worst-year audit will hammer on this.
4. **Industry rotation.** A-share style rotation between cyclicals, growth, defensives is fast (3-6 months). Trend signals that rebalance monthly may catch the rotation but get whipsawed.
5. **Turnover cost.** Trend signals are slowly varying — turnover is naturally low. Monthly rebalance × low turnover means cost should be manageable. Expect after-cost LS Sharpe degradation < 30 %.
6. **Lookahead in residualization.** If we residualize for "idio momentum" with full-sample OLS per stock, we *will* get a fake high Sharpe (this was the α_26 lesson from session 20260421). Use cross-section-per-date residualization, not time-series-per-stock.

## 7. Proposed batch-1 mechanism (single dominant)

**Trend strength via multi-horizon price-level signals.**

All 8 expressions cluster on the question: *is the price persistently above its own moving averages, across multiple horizons?* This is the Han-Zhou-Zhu mechanism, plus close-derivative variants. We deliberately put classic 12-1 momentum in slot 8 as the falsification anchor — if 12-1 is significantly negative in our sample, that confirms the reversal-dominance prior and validates that the other 7 trend-shape signals are not just "raw momentum re-skinned".

## 8. Handoff to Agent 2

- Pick `trend_strength_multi_horizon` as the dominant mechanism for batch 1.
- Train / Validate / Test split: 2018-2022 / 2023 / 2024-2025-04-18.
- Universe: all stocks in `.cache/daily.parquet` filtered to ≥ 250 trading days of history at signal date (so MA_252 is well defined).
- Industry neutralization: mandatory.
- Size neutralization: as a second batch lever, not in batch 1.
- Forward return horizons to evaluate: 5d, 20d, 60d.
- Rebalance: monthly (every 20 trading days).
- Cost: 5 bps per side, turnover-aware: `cost = (tov_q5 + tov_q1) × 5e-4`.

## 9. References (file-local citations)

- `references/common-pitfalls.md` — pitfalls 1 (look-ahead masks), 7 (bull-market short-leg destruction), 8 (industry noise eating signal), 10 (daily turnover cost trap).
- `references/execution-delay-audit.md` — `target_shift = -(1+delay)` invariant.
- `references/tvt-split-template.md` — TVT methodology and PROMOTE thresholds.
- Prior session `logs/20260421_volprice_max_lottery/final_summary.md` — section "Lessons" applies almost verbatim.
- `CLAUDE.md` — A-share adaptation block and load-bearing audit rules.
