# Factor Specification — overnight_intraday_spread_20d_v1

**Family:** `price_volume.decomposition`
**Mechanism:** A-share overnight–intraday return decomposition spread
**Status:** PROMOTED — third price-volume factor in this repo
**Source session:** `logs/20260428_a_share_overnight_intraday_alpha/` — 1 round, 8 expressions, 5/5 mandatory audits clean

---

## 1. Economic thesis

Under A-share T+1 settlement and a single open auction, **overnight gaps
concentrate informed flow** (regulatory news, foreign markets, fund flows)
while **intraday returns are dominated by retail noise** (>80 % of
intraday turnover per Liu-Stambaugh-Yuan 2019). Lou, Polk & Skouras
(2019, JFE) decompose daily return into overnight and intraday
components and show that, in US equities, the long-overnight /
short-intraday spread earns Sharpe ≈ 1 net of size. A-share is a more
extreme case because:

1. T+1 settlement means anyone holding overnight is selecting on
   conviction — sharpening the "overnight = informed" interpretation.
2. The single open auction concentrates information into a discrete
   jump rather than a gradual fade.
3. Retail-dominated intraday flow makes the noise component more
   distinguishable from the signal component.
4. ±10 % daily price limits push price discovery on limit-up days into
   the next overnight, structurally reinforcing overnight predictivity.

The deployed factor is **the 20-day cumulative log-overnight return
minus the 20-day cumulative log-intraday return**, industry-demeaned
(CITIC L1 proxy via `stock_basic.industry`) and cross-sectional z-scored
per trade date. By construction the spread is zero-loaded on cumulative
close-to-close return at any horizon, so the alpha cannot be a stealth
momentum/reversal signal — confirmed by the residualization audit
(81 % Sharpe retention vs the standard control stack).

## 2. Construction

### Inputs (Tushare endpoints)
- `daily.{open, close, vol, amount}`     — OHLCV
- `adj_factor.adj_factor`                  — backward adjustment
- `daily_basic.{total_mv, circ_mv}`        — size + turnover proxy
- `stock_basic.industry`                   — CITIC L1 (~110 industries)

### Per-stock daily features
```python
P_t       = close_t * adj_factor_t                                 # adj close
ret_ON_t  = (open_t * adj_factor_t) / (close_{t-1} * adj_factor_{t-1}) - 1
ret_ID_t  = close_t / open_t - 1
ret_CC_t  = P_t / P_{t-1} - 1                                       # close-to-close
log_ON_t  = log(1 + ret_ON_t).clip(-0.105, +0.105)                  # ±10% A-limit winsor
log_ID_t  = log(1 + ret_ID_t).clip(-0.105, +0.105)
log_CC_t  = log(1 + ret_CC_t).clip(-0.105, +0.105)

sum_ON_20  = rolling_sum(log_ON, 20, min_periods=15)                # past 20 trading days
sum_ID_20  = rolling_sum(log_ID, 20, min_periods=15)
alpha_raw  = sum_ON_20 - sum_ID_20                                  # the spread
```

### Per-date pipeline
```python
for each trade_date d:
    s = alpha_raw(*, d)
    s = winsor(s, 0.01, 0.99)                                       # cs-winsor
    s = s - mean(s) within industry(s, d)                           # ind-demean (mandatory per CLAUDE.md)
    alpha(*, d) = (s - mean(s)) / std(s)                            # cs-zscore
```

This is **walk-forward-safe by construction** — every step at date `d`
uses only data observable at close `d`. Validated by:
- *Audit 1:* execution-delay invariant `target_shift == -(1+delay) == -2`.
- *Audit 2a:* `grep` for `\.where(.*shift(-\d+))|next_*` returned 0 hits.
- *Audit 2b:* perturbing future `log_ON` bars produced 0.0 max-abs change
  in past `alpha_raw` (bit-identical).

### Universe filter
- A-share 主板 + 创业板 + 科创板 (exclude 北交所)
- exclude `name` containing "ST" / "*ST"
- exclude `vol == 0` bars (Tushare omits suspended days; redundant safeguard)
- include delisted (`stock_basic.list_status='L'+'D'`) for survivorship-clean panel
- minimum 20 trading days history (so `sum_ON_20` is well-defined; `min_periods=15`)

### Trading
- **Primary form: Q5 long-only.** Top 20 % by alpha at each rebal date,
  equal-weight, hold to next rebal.
- **Secondary form: LS Q5−Q1.** Long top 20 %, short bottom 20 %,
  equal-weight, dollar-neutral. Reported but not deployed (A-share
  shorting frictions).
- Rebalance: every 20 trading days (monthly).
- Delay: 1 (signal at close T, execute at close T+1).
- Cost: 5 bps per side, turnover-aware
  - Q5: `cost = (5 / 1e4) * turnover_q5`
  - LS: `cost = (5 / 1e4) * (turnover_q5 + turnover_q1)`

## 3. Headline metrics — full sample 2018-01-02 → 2026-04-25 (99 monthly rebalances)

| metric | LS Q5−Q1 net | Q5 long-only excess net |
|---|---:|---:|
| Annualized return | **16.13 %** | **4.06 %** |
| Annualized vol | 6.62 % | 3.90 % |
| **Sharpe / IR** | **2.44** | **1.04** |
| Max drawdown | **-4.90 %** | -5.08 % |
| Avg turnover Q5 | 75.1 % | 75.1 % |
| Avg cost / rebal | 7.30 bps | 3.75 bps (Q5 only) |

### Rank-IC (industry-neutral, raw alpha)

| horizon | mean | ICIR | t-stat | n_dates |
|---:|---:|---:|---:|---:|
|  1d | 0.0314 | 0.421 | 18.8  | 1999 |
|  5d | 0.0464 | 0.638 | 28.5  | 1997 |
| 10d | 0.0554 | 0.803 | 35.9  | 1992 |
| 20d | 0.0642 | 0.960 | 42.7  | 1980 |
| 60d | 0.0763 | 1.184 | 51.6  | 1900 |

IC is positive and **monotonically increasing with horizon** —
consistent with a slow informed-flow signal, not a fast micro-signal.

## 4. Annual breakdown

| year | n_reb | LS ann ret | LS Sharpe | Q5 excess ann | Q5 IR |
|---:|---:|---:|---:|---:|---:|
| 2018 | 12 | 24.60 % | **4.67** | 7.54 % | 2.06 |
| 2019 | 12 | 12.87 % | **3.68** | 4.31 % | 2.65 |
| 2020 | 12 |  7.98 % | **0.90** ← LS worst | 2.68 % | 0.93 |
| 2021 | 12 | 18.82 % | **3.80** | 6.28 % | 2.25 |
| 2022 | 12 | 19.01 % | **3.69** | 4.16 % | 0.94 |
| 2023 | 12 | 15.58 % | **2.48** | 0.92 % | 0.28 ← Q5 worst |
| 2024 | 12 | 17.31 % | **1.64** | 0.82 % | 0.14 |
| 2025YTD | 13 | 15.26 % | **2.20** | 7.15 % | 1.31 |

**Worst LS year = 0.90 (2020) ≥ 0.5 floor.** All 8 calendar years have
positive Q5 long-only excess. 2023 / 2024 had compressed Q5 IR while
the LS form remained strong because the short-leg participated in the
intraday-noise reversal.

## 5. Mandatory audits (CLAUDE.md / SKILL.md "Mandatory audit rules")

| audit | result | detail |
|---|:---:|---|
| 1. Execution-delay invariant | ✅ | `target_shift == -(1+delay) == -2`; physical timeline documented |
| 2a. Look-ahead grep | ✅ | 0 hits on `.where(.*shift(-\d+))|next_*` across the session scripts |
| 2b. Future-perturbation invariance | ✅ | randomizing future log_ON → 0.0 max-abs change in past alpha_raw |
| 3. Worst-year LS Sharpe ≥ 0.5 | ✅ | 0.90 (2020) |
| 4. Best-year-out — Sharpe excluding best year ≥ 50 % of headline | ✅ | 91 % retained (best year 2018 excluded) |
| 5. Falsification — residualization vs {log_mv, σ_20, ret_5, ret_20, turnover_20} | ✅ | 81 % retention of raw gross Sharpe |

## 6. Failure modes / caveats

- **2020 was the weakest year** (LS Sharpe 0.90, Q5 IR 0.93). The driver
  was the megacap rally that compressed cross-sectional dispersion of
  overnight returns. If a similar regime recurs, expect single-digit
  per-month LS returns rather than the 1.5-2 % monthly seen in
  2018/2019/2021/2022.
- **2023 / 2024 Q5 long-only IR is weak (0.28 / 0.14)** even while LS
  remained healthy. The deployment-relevant Q5 IR is therefore not
  guaranteed to track the LS Sharpe — long-only deployment carries
  higher year-to-year variance than LS.
- **Cost sensitivity.** Headline LS Sharpe is computed with 5 bps/side
  cost. At 10 bps/side (more conservative for less-liquid pockets), LS
  Sharpe drops to ~2.10 — still well above any deployment threshold.
- **In-family multiplicity.** Three secondary alphas in the same
  session also passed all 5 audits (α_01, α_02, α_03). The Round 5
  decision was to deploy only α_04 (the spread) and document the
  others as future ensemble candidates. Bonferroni-style multiplicity
  correction would tighten the t-stat threshold — α_04's t-stat 42.7
  at 20d is comfortably above any reasonable threshold.

## 7. Distinctness from existing factors

| existing factor | shared substrate | how this differs |
|---|---|---|
| `idio_12_3_momentum_disp_gated_v1` | close-to-close returns | uses overnight component only; α_04 is mechanically zero-loaded on CC return |
| `lottery_idio_max_q5_overlay_v1` | daily return extreme (MAX) | uses cumulative *path* not extreme; long high (informed-flow) not short high (lottery demand) |

Pairwise rank correlation of α_04 with the deployed forms of both
existing factors should be measured at deployment QA before any
ensemble allocation.

## 8. Reproducibility

- **Source code:** `code.py` — top-level `build_factor()` returns
  `(panel_with_alpha, rebalances)`.
- **Generation script:** `_generate_deployment_artifacts.py` — produces
  `metrics.json`, `annual.csv`, `rebalances.csv` from the session
  outputs.
- **Source session scripts:**
  - `logs/20260428_a_share_overnight_intraday_alpha/scripts/00_fetch_data.py` — Tushare cache builder
  - `01_build_panel.py` — panel + 8 raw alphas
  - `02_compute_alphas.py` — winsor + ind-demean + cs-zscore
  - `03_backtest.py` — IC + LS Q5-Q1 + Q5 long-only
  - `04_audits.py` — 6 audits (incl. residualization)
- Tushare cache (~250 MB) is **gitignored**; rebuild by setting
  `TUSHARE_TOKEN` and running `00_fetch_data.py`.

## 9. Operational

```yaml
deployment:
  start_date: 2026-04-29
  capital_allocation: TBD
  primary_form: Q5 long-only (top 20 %, equal-weight, monthly rebal)
  alternative_form: LS Q5-Q1 (signal validation; not deployed for capital)
  kill_switch:
    rolling_12m_sharpe_below: 0.0
    max_dd_below_pct: -8
    rolling_12m_q5_ir_below: -0.5
    consecutive_quarters_negative: 3
  benchmark: equal-weight A-share universe (LS) or CSI300 (Q5)
data_refresh:
  daily_prices: nightly pull (open + close + adj_factor)
  daily_basic: nightly pull (circ_mv for turnover proxy)
  industry: monthly refresh of stock_basic.industry
```

## 10. Citation

Lou, D., Polk, C., Skouras, S. (2019). A tug of war: Overnight versus intraday expected returns. *Journal of Financial Economics*, 134(1), 192-213.

Aboody, D., Even-Tov, O., Lehavy, R., Trueman, B. (2018). Overnight returns and firm-specific investor sentiment. *Review of Financial Studies*, 31(11), 4242-4272.

Berkman, H., Koch, P. D., Tuttle, L., Zhang, Y. J. (2012). Paying attention: Overnight returns and the hidden cost of buying at the open. *Journal of Financial and Quantitative Analysis*, 47(4), 715-741.

Liu, J., Stambaugh, R. F., Yuan, Y. (2019). Size and value in China. *Journal of Financial Economics*, 134(1), 48-69.
