# Research Brief — Fundamental Factor Mining

**Session:** 20260420_fundamental_accruals_alpha
**Agent:** 1 Research Librarian

## 1. Literature evidence pack

### Primary mechanism candidates

| # | Mechanism | Core thesis | Seminal reference |
|---|-----------|-------------|-------------------|
| A | **Accruals anomaly** (*selected focus*) | Firms with high accruals (earnings >> cash flow) earn lower future returns because accruals are less persistent than cash earnings and proxy for low-quality / managed earnings. | Sloan (1996) *AR*; Richardson, Sloan, Soliman, Tuna (2005) *JAE* |
| B | Post-Earnings-Announcement Drift (SUE) | Positive earnings surprises are underreacted to for 20-60 trading days. | Ball & Brown (1968); Bernard & Thomas (1989) |
| C | Profitability (Gross Profitability) | High gross profit / assets predicts higher returns; not captured by book/market. | Novy-Marx (2013) *JFE* |
| D | Piotroski F-Score | 9-binary financial-strength composite distinguishes winners from losers within value stocks. | Piotroski (2000) *JAR* |
| E | Investment / Asset Growth | Firms aggressively growing assets underperform; low-investment firms outperform. | Cooper, Gulen & Schill (2008) *JF*; Fama & French (2015) |

### Why select **(A) Accruals** for Round 1

- **Single dominant mechanism** — satisfies "one mechanism per batch" rule.
- **Data accessible on Tushare** — needs only `income`, `balancesheet`, `cashflow`, `fina_indicator`; these fields are available historically, unlike `daily_basic`.
- **Well-documented A-share evidence** — Chan, Jegadeesh & Lakonishok (2006) show accruals predict returns in most international markets; Ke, Liu, and Xu (2010) and GF Securities (2019 研报) document a ~3-4% annualized long-short premium in A-shares, stronger after 2010 post-IPO reform.
- **Short-side is shortable proxy** — use Q5 long-only Top-quintile (excess vs CSI300) as deployable decision metric; LS used only for signal validation (per A-share adaptation lesson in SKILL.md).
- **Orthogonal to price-volume book** — low expected correlation with momentum / reversal / turnover factors; qualifies as "new information" for factor library.

## 2. Dataset recommendation

| Required field | Tushare source | Freq | Note |
|----------------|----------------|------|------|
| Net income (NI) | `income.n_income` | Q | TTM rollup required |
| CFO (operating cash flow) | `cashflow.n_cashflow_act` | Q | TTM rollup |
| Total assets (avg) | `balancesheet.total_assets` | Q | Avg(t, t-1) |
| Current assets, current liab, cash, ST debt | `balancesheet.*` | Q | For Working-Capital Accruals decomposition |
| Depreciation | `cashflow.depr_fa_coga_dpba` | Q | For the Sloan-style WCA - Dep |
| Industry (SW L1 proxy) | `stock_basic.industry` | Static | Free tier, ~110 groups |
| Total market cap | `daily_basic.total_mv` | D | For size neutralization; falls back to `close * total_share` if `daily_basic` unavailable |
| Close price | `daily.close` | D | Returns |
| Trading status | `daily.vol`, `suspend_d` | D | Liquidity filter |

**Caching plan:** snapshot quarterly statements into `data/fundamentals/{period}.parquet`; daily panel into `data/daily/{year}.parquet`. Full 1500-stock × 12-year panel ≈ 20 min fetch, <3 s load.

## 3. Operator toolbox (WorldQuant-style)

- `ts_rank(x, N)` — time-series rank (stability)
- `rank(x)` — cross-sectional rank
- `ts_sum(x, N)`, `ts_mean(x, N)` — TTM aggregation
- `ts_delta(x, N)` — change detection
- `group_neutralize(x, industry)` — industry demean/rank
- `group_rank(x, industry)` — within-industry rank
- `winsorize(x, 0.01)` — tail clipping
- `zscore(x)` — normalization
- `quarterly_to_daily(x, period_col)` — forward-fill quarterly to daily at `ann_date + delay`
  **CRITICAL:** publication lag must use `ann_date` (announcement date), NOT `end_date` (report period). Using `end_date` would leak 30-90 days of look-ahead.

## 4. Caveats / risks (Librarian's concern list)

1. **Announcement-date leakage** — A-share annual reports published up to 4 months after period-end. Any factor using `end_date` without `ann_date` lag will look great in backtest and fail live.
2. **Accruals definition sensitivity** — Balance-sheet-method (ΔWC) vs cash-flow-statement-method (NI − CFO) differ materially in A-share due to restatements. Prefer CFS-method (more robust to restatement).
3. **Financials + Real-estate tail** — Banks and insurers have non-meaningful working capital; either drop (SW L1 == 银行/非银金融) or industry-neutralize.
4. **2015 bubble / 2018 unwind** — Accruals long-short suffered in 2015 Q2 (everything went up, quality underperformed); test must survive this year at the worst-year floor.
5. **Post-2019 SOE reform and STAR-board listings** — Small-cap / newly-listed skew; use universe filter `listed > 252 days` and `total_mv > median(day)`.
6. **High-to-low seasonality** — Annual report (April) delivers a fresher signal than Q1/Q2; expect IC spike around May and Sep.
7. **Earnings-management reversal** — Accruals is a slow-decay signal; IC decay test at {1, 5, 20, 60} days expected to *improve* with horizon, arguing for monthly rebalance.

## 5. Recommended focus for Stage 2

**Primary mechanism (go):** *Earnings quality proxied by accruals; short high-accruals, long low-accruals.*

**Core economic narrative to encode:** High cash-earnings component of NI is more persistent; the market underweights this persistence at fundamental-data release times, so a portfolio long low-accruals / short high-accruals captures the reversal of the mispricing over 20-60 trading days.

**Expected properties to verify in Stage 4:**
- Rank IC mean (20d): 0.02 – 0.05
- Rank ICIR (annualized): 0.4 – 0.8
- LS Sharpe (gross): 0.8 – 1.3
- Q5 long-only excess vs CSI300: 3 – 6 % annualized
- Monthly turnover ≤ 25 % (quarterly fundamentals update + monthly rebalance)

**Red flags that would trigger refine/stop:**
- Rank IC t-stat < 2 on full sample → weak mechanism, stop.
- IC decays to zero by day 20 → re-time horizon or kill.
- Worst-year Sharpe < 0 → RESEARCH-ONLY regardless of headline.
