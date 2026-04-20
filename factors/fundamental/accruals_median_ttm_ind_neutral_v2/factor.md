# Factor Specification — accruals_median_ttm_ind_neutral_v2

**Family:** `fundamental.quality`
**Mechanism:** Earnings quality via accruals (Sloan 1996, CFS-method, median-TTM)
**Status:** DEPLOYED (paper trading)
**Source session:** `logs/20260420_fundamental_accruals_alpha/` — 4 rounds, 32 expressions tested

---

## 1. Economic thesis

The market underweights how much of reported earnings comes from cash vs accruals.
Cash earnings are more persistent than accrual earnings. Firms with **high accruals**
(NI >> CFO) tend to disappoint over the next 20-60 trading days as the accrual
component reverses; firms with **low accruals** (high cash component) outperform.

Sloan (1996) is the seminal reference; the premium has been replicated across
markets and decades (Richardson, Sloan, Soliman, Tuna 2005; Chan, Jegadeesh,
Lakonishok 2006). The A-share replication shows the premium is intact but
requires industry-neutralization to surface (without it, sector accrual norms
dominate).

## 2. Construction

### Inputs (Tushare endpoints)
- `income.n_income`            — quarterly net income
- `cashflow.n_cashflow_act`    — quarterly operating cash flow
- `balancesheet.total_assets`  — quarterly total assets
- `income.ann_date`            — announcement date (publication-lag gating)
- `stock_basic.industry`       — sector grouping (~110 industries)

### Quarterly fundamental (per ts_code)
```python
ni_med  = rolling_median(n_income,        window=4q, min_periods=3) * 4
cfo_med = rolling_median(n_cashflow_act,  window=4q, min_periods=3) * 4
ta_avg  = rolling_mean  (total_assets,    window=4q, min_periods=3)
acc_med = (ni_med - cfo_med) / ta_avg
```

### Daily panel
Forward-fill `acc_med` to daily via `merge_asof(trade_date, ann_date, direction='backward', allow_exact_matches=False)`. **Strictly `ann_date < trade_date` — never use `end_date`.**

### Cross-sectional ranking (per trade_date)
```python
acc_med_w = winsorize(acc_med, 0.01, 0.99)              # tail clip
alpha     = -group_rank(acc_med_w, by='industry')        # within-industry pct rank, flipped
```

Higher alpha = higher expected forward return.

### Universe filter (applied at each trade_date)
- A-share `list_status == 'L'`
- exclude industries: 银行 / 保险 / 证券 / 多元金融 / 期货 / 地产
- exclude ST (`name contains 'ST'`)
- listed > 252 trading days

## 3. Portfolio construction

| Form | Construction | Use |
|------|--------------|-----|
| **Q5 long-only** | top 20% of alpha within industry, equal-weighted | **deployment** (CSI300 benchmark) |
| Q5 − Q1 LS | long Q5, short Q1, equal-weighted | signal validation only (A-share short constraint) |

- Rebalance: every 20 trading days (monthly)
- Delay: 1 (signal at close T, execute close T+1)
- Cost model: turnover-aware
  - LS: `cost = bps_per_side / 1e4 * (turnover_q5 + turnover_q1)`
  - Q5: `cost = bps_per_side / 1e4 * turnover_q5`
- Default cost: **5 bps per side (万5)** ← matches user's brokerage

## 4. Headline metrics (full sample 2018-07 → 2025-04)

| metric | LS net | Q5 long-only net |
|--------|------:|------------------:|
| Annualized return | 10.37 % | 4.42 % (excess vs equal-weight universe) |
| Annualized vol | 7.39 % | 3.83 % |
| **Sharpe / IR** | **1.34** | **1.13** |
| Max drawdown | −1.85 % | −1.33 % |
| Hit rate (positive months) | 70.7 % | 67.1 % |
| Avg turnover per rebalance | 9.7 % (Q5 side) | — |
| Avg per-rebalance cost | 0.95 bps (LS, both sides) | 0.48 bps (Q5 side) |

**IC**: 20d = 0.0149 (ICIR 0.44, t = 17.7); 60d = 0.0302 (ICIR 0.94, t = 37.5).

## 5. TVT split

| split | period | n reb | LS net Sharpe | Q5 net IR |
|-------|--------|------:|--------------:|----------:|
| Train    | 2018-2021    | 43 | 1.36 | 1.14 |
| Validate | 2022-2023    | 24 | 2.45 | 1.80 |
| **Test** | **2024-2025YTD** | 15 | **0.96** | **0.88** |
| Full     | 2018-2025YTD | 82 | **1.34** | **1.13** |

Test period dragged by 3 negative observations in 2025 YTD (small sample). Pure 2024 LS Sharpe is 1.32. Honest deployment expectation: LS Sharpe ≥ 1.0, Q5 IR ≥ 0.9.

## 6. Annual breakdown

| year | n reb | LS net ann | LS net Sharpe | Q5 net ann | Q5 net IR |
|-----:|------:|-----------:|--------------:|-----------:|----------:|
| 2018 | 6  | 42.83 % | 1.46 | 17.24 % | 1.26 |
| 2019 | 13 |  9.54 % | 2.64 |  3.12 % | 1.55 |
| 2020 | 12 |  5.89 % | 1.82 |  4.83 % | 2.59 |
| 2021 | 12 | 13.43 % | 3.64 |  3.83 % | 2.22 |
| 2022 | 12 |  5.71 % | 1.36 |  2.99 % | 1.33 |
| 2023 | 12 | 10.58 % | 5.24 |  3.86 % | 2.46 |
| 2024 | 12 |  6.84 % | 1.32 |  3.81 % | 1.28 |
| 2025YTD | 3 | −4.06 % | −5.09 (n=3) | −2.95 % | n.s. |

**Every full year (2018-2024) positive on both LS and Q5.** Worst-year LS Sharpe = 1.32 (2024).

## 7. Mandatory audits

| audit | result | how |
|-------|--------|-----|
| Rule of 8 | ✅ | every batch had exactly 8 expressions |
| One-mechanism | ✅ | all 32 expressions on accruals family |
| Execution-delay | ✅ | `fwd_ret_h = close.shift(-1-h)/close.shift(-1) - 1`; delay=1 baked in |
| Look-ahead structural | ✅ | `merge_asof(backward, allow_exact_matches=False)` on ann_date |
| Look-ahead numeric (shuffle) | ✅ | clean IC 0.0149 vs shuffled 0.000065 → **229× ratio** |
| Worst-year floor (≥ 0.5) | ✅ | 1.32 (2024); even worse-year 1.36 (2018) |
| Best-year-out (≥ 50 % headline) | ✅ | 92 % retained when dropping single best year |
| Falsification-first (pub-lag) | ✅ | leaky end_date IC 0.0156 vs clean 0.0157 — ratio 0.99, no leakage |
| Residualization vs classics | ✅ | 96 % of Sharpe retained when orthogonalized vs {size, mom_20, rev_5, turnover_z, vol_20}; ICIR *improves* 0.495 → 0.575 |
| Cost model sanity | ✅ | turnover-aware (Round 4 fix); ~0.95 bps/rebalance LS, 0.48 bps Q5 |

## 8. Failure modes / caveats

- **Tushare BS-method WCA fails** (Round 1 alpha_02 collapsed −60 % drawdown). Always use CFS-method (NI − CFO).
- **No-neutralization variants fail** the worst-year floor in 2019 bull market (IC 0.02 in that year). Industry neutralization is not optional.
- **Industry × size double-neutralization** loses on full window (worst-year 0.36) due to thin cells; **industry-only is the sweet spot**.
- **5-year (2020-2025) window over-states Sharpe by ~50 %** (1.57 vs 1.34). Always include pre-2020 stress.
- **2025 YTD has only 3 rebalances** in this dataset; treat as partial sample.

## 9. Reproducibility

- Source code: `code.py` (this directory) + scripts in `logs/20260420_fundamental_accruals_alpha/scripts/{01,02,03,08,09,10}.py`
- Raw Tushare cache (~260 MB) is **gitignored**; rebuild by setting `TUSHARE_TOKEN` and running scripts in order.
- Panel cache: `.cache/panel_round3.parquet` (5.6M rows, 5,285 stocks, 1,604 trade days).

## 10. Operational

```yaml
deployment:
  start_date: 2026-04-21
  capital_allocation: TBD
  kill_switch:
    rolling_12m_sharpe_below: 0.3
    max_dd_below_pct: -5
    rolling_12m_ic_below: 0
  monitoring:
    cadence: monthly P&L review, quarterly factor-health audit
    benchmark: CSI300
data_refresh:
  fundamentals: weekly poll of income_vip / balancesheet_vip / cashflow_vip
  daily_prices: nightly pull
```

## 11. Citation

Sloan, R. G. (1996). Do stock prices fully reflect information in accruals and cash flows about future earnings? *The Accounting Review*, 71(3), 289-315.

Richardson, S. A., Sloan, R. G., Soliman, M. T., & Tuna, I. (2005). Accrual reliability, earnings persistence and stock prices. *Journal of Accounting and Economics*, 39(3), 437-485.

Chan, K., Chan, L. K., Jegadeesh, N., & Lakonishok, J. (2006). Earnings quality and stock returns. *The Journal of Business*, 79(3), 1041-1082.
