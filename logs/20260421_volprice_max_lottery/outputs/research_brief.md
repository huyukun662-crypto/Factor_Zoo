# Research Brief — Volume-Price Anomaly: Lottery Demand / MAX Effect

**Session:** `20260421_volprice_max_lottery`
**Agent:** 1 — Research Librarian
**Date:** 2026-04-21
**Market:** A-share (Shanghai + Shenzhen, ex-ST, ex-suspended)
**Data coverage available:** 2018-01-02 to 2025-04-18 daily; ~5,614 tickers

---

## 1. Candidate mechanisms considered

| Family | Key paper | A-share evidence | Fit with data (open/close/vol/amount only) |
|---|---|---|---|
| Short-term reversal | Jegadeesh 1990; Nagel 2012 | Strong (Cheung et al 2015) | Good (need only close) |
| Momentum | Jegadeesh & Titman 1993 | Weak / often reversed in A-share | Good |
| Idiosyncratic volatility (IVOL) | Ang, Hodrick, Xing, Zhang 2006 | Strong, robust (Han & Zhou 2013) | Good |
| **MAX effect / lottery demand** | **Bali, Cakici, Whitelaw 2011 (JFE)** | **Strong in A-share — Liu, Stambaugh, Yuan 2019 CH-3** | **Good — close returns only** |
| Turnover anomaly | Lee & Swaminathan 2000; Chen et al 2019 | Strong (retail-driven) | Good (vol + circ_mv) |
| Amihud illiquidity | Amihud 2002; Chen Chollete Ray 2019 | Weak as alpha (risk premium) | Good |
| Overnight-intraday decomposition | Berkman et al 2012; Lou Polk Skouras 2019 | Mixed A-share evidence | Partial (we have open, close) |
| MAX-adjusted reversal | Bali Engle Murray 2016 book | New, less-crowded | Good |

## 2. Mechanism selected: MAX Effect (Lottery Demand Anomaly)

**Hypothesis.** Stocks with extreme positive daily returns in the recent past (~1 month) attract
attention and lottery-seeking demand from retail investors, driving prices above fundamentals.
The mispricing corrects over the subsequent month, so high-MAX stocks **underperform** in
the next period. Direction: alpha = −MAX.

**Why this mechanism for this session:**

1. **A-share fit.** Retail participation rate in A-share exceeds 80% of turnover. Daily ±10%
   price limits make "hot stocks" (stocks that hit the limit up) highly visible and create
   a natural lottery-like payoff distribution. Liu, Stambaugh & Yuan (2019, JFE) include a
   turnover-based sentiment factor in the CH-3 model precisely because this retail attention
   channel is priced.
2. **Orthogonal to our deployed factor.** Factor_Zoo already has an accruals factor in
   `factors/fundamental/accruals_median_ttm_ind_neutral_v2`. MAX is a *behavioral / attention*
   signal and should be low-correlation with fundamental quality.
3. **Data match.** Only needs daily close returns and turnover — both are in our cache for
   2018-2025. No high/low needed (which we don't have).
4. **Multiple operationalizations.** MAX has natural variants (window, top-N averaging,
   vol-normalization, attention weighting) which map cleanly to the Rule-of-8.
5. **Published benchmarks.** Bali et al 2011 report Sharpe ~0.5 for long-short MAX in US;
   A-share replications report 0.7-1.1 depending on neutralization. Sets a realistic bar.

**Direction.** Short high-MAX → `alpha = -max_return_window`.

## 3. Key references (paper IDs, not URLs — follow standard citation)

- Bali, T.G., Cakici, N., Whitelaw, R.F. (2011). "Maxing out: Stocks as lotteries and the cross-
  section of expected returns." *Journal of Financial Economics*, 99(2), 427-446.
- Ang, A., Hodrick, R.J., Xing, Y., Zhang, X. (2006). "The cross-section of volatility and
  expected returns." *Journal of Finance*, 61(1), 259-299.
- Liu, J., Stambaugh, R.F., Yuan, Y. (2019). "Size and value in China." *Journal of Financial
  Economics*, 134(1), 48-69. [CH-3 factor model, includes turnover-sentiment factor]
- Han, Y., Zhou, G. (2013). "Trend factor: A new cross-sectional predictor of stock returns."
  Working Paper. [A-share IVOL and MAX evidence]
- Nagel, S. (2012). "Evaporating liquidity." *Review of Financial Studies*, 25(7), 2005-2039.
  [Short-term reversal, related to MAX via return extremes]
- Chen, K., Chollete, L., Ray, R. (2019). "Cross-sectional anomalies in China." *Pacific-Basin
  Finance Journal*, 57, 101185.
- Chui, A.C.W., Titman, S., Wei, K.C.J. (2010). "Individualism and momentum around the world."
  *Journal of Finance*, 65(1), 361-392. [Explains why A-share momentum is weak → reversal/MAX strong]

## 4. Known failure modes and pitfalls (from common-pitfalls.md + literature)

1. **Size confound.** MAX is mechanically correlated with small-cap; must either neutralize
   size or include as control. A-share small-cap bias is strong.
2. **Liquidity confound.** Illiquid stocks have larger discrete price moves → higher MAX
   by construction. Winsorization or turnover control is needed.
3. **Industry confound.** Tech and biotech have structurally higher MAX. **Industry
   neutralization is mandatory per CLAUDE.md for all volume-price factors.**
4. **Price-limit artifact.** A-share ±10% daily limit truncates the upper tail of the return
   distribution. Stocks at limit up for multiple days will have MAX=0.10 exactly, creating
   mass points. Winsorize at 99th percentile handles this.
5. **Short-sale constraint.** A-share short selling is costly and restricted. Report BOTH the
   LS (Q5−Q1) and Q1-long-only excess metrics; deployment is long-only.
6. **Reversal contamination.** MAX partially overlaps with short-term reversal. The LS Sharpe
   reported in literature (~0.7) is net of reversal neutralization. Audits must include
   residualization vs ret_5 / ret_20.

## 5. Data requirements (all already cached)

| Field | Source | Status |
|---|---|---|
| Adjusted close (for returns) | `daily` × `adj_factor` | Cached |
| Volume / amount | `daily` | Cached |
| Circulating market cap | `daily_basic.circ_mv` | Cached |
| Industry (CITIC level 1 proxy via `stock_basic.industry`) | `panel.parquet` (from accruals session) | Cached |
| Size bin | `panel.parquet` | Cached |
| Trading calendar | derivable from `daily.trade_date` | Cached |

No external fetch required.

## 6. Deliverable for Agent 2 (handoff)

- Mechanism: lottery demand / MAX effect
- Direction: short high-MAX; alpha sign = negative
- Neutralization stack (non-negotiable): industry (CITIC L1 proxy)
- Residualization stack to test in audits: ret_5, ret_20, log_mv, turnover_20, ivol_20
- 8 variants must share the mechanism (extreme recent returns) but differ in:
  window length, top-N averaging, vol-scaling, attention-weighting (turnover)
- TVT split: train 2018-2022, validate 2023, test 2024 + 2025-YTD
- Cost model: turnover-aware, 5 bps one-side (万5)
- Rebalance: monthly (20-trading-day) default, weekly variant for robustness
