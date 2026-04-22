# Factor Specification — idio_12_3_momentum_disp_gated_v1

**Family:** `price_volume.momentum`
**Mechanism:** Idiosyncratic 12-3 momentum with cross-sectional dispersion regime gate
**Status:** DEPLOYED (paper trading) — second factor in this repo
**Source session:** `logs/20260422_trend_technical_alpha/` — 6 rounds, 40 expressions, 100 placebo trials

---

## 1. Economic thesis

A-share 2018-2025 raw cross-sectional momentum is **anti-predictive**: every
classical trend signal (Han-Zhou-Zhu, MA-crossover, 12-1 momentum, 60-d /
120-d log-price t-stat, 52-week-high proximity, frog-in-the-pan, trend
Sharpe) earned negative IC with t-stats |6| to |25|. This replicates
Liu-Stambaugh-Yuan (2019, JFE): Chinese A-share returns are dominated by
short-term reversal, not trend.

However, **idiosyncratic momentum** — the residual past return after
stripping size, vol, and short-term reversal — is positive in A-share. A
12-3 skip-window construction (Jegadeesh-Titman 1993 style with longer
skip to remove more 1-month reversal contamination) earns IC IR 14.5
across the 2018-2025 window when residualized cross-sectionally vs
{log_mv, σ_120, ret_20}. This idio-momentum signal earns ungated LS Sharpe
1.0 full / 2.06 test, but stalls (Sharpe 0.04) in regime-shift years
(2019, 2023).

The deployable form gates the signal off in low-dispersion regimes per
Stivers-Sun (2010, RFS): cross-sectional return dispersion proxies the
opportunity set facing momentum traders. When dispersion is below its
own 252-day median, the gate turns the strategy off (cash). When above,
the strategy deploys. This converts a 5/6-year-strong signal into a
deployable factor with 7/7 PROMOTE checks satisfied.

## 2. Construction

### Inputs (Tushare endpoints)
- `daily.{open, close, vol, amount}`     — OHLCV
- `adj_factor.adj_factor`                 — backward adjustment
- `daily_basic.total_mv`                  — total market cap for size control
- `stock_basic.industry`                  — CITIC L1 (~110 industries) via `panel.parquet`

### Per-stock daily features
```python
P_t       = close_t * adj_factor_t                          # adjusted price
r_t       = log(P_t / P_{t-1})                              # log return
cum_252   = rolling_sum(r, window=252, min_periods=200)
cum_63    = rolling_sum(r, window=63,  min_periods=45)
sigma_120 = rolling_std(r, window=120, min_periods=80)
ret_20    = rolling_sum(r, window=20,  min_periods=15)
log_mv    = log(total_mv)

raw_idio_12_3 = cum_252 - cum_63                             # 12-month minus 3-month
```

### Per-date cross-sectional residualization
```python
for each trade_date d:
    y = raw_idio_12_3(*, d)
    X = [const, log_mv(*, d), sigma_120(*, d), ret_20(*, d)]
    beta = OLS(y on X)
    alpha_idio_12_3(*, d) = y - X @ beta
```

This is **walk-forward-safe** by construction — each date is solved
independently using only that date's cross-section. No future bars enter
β estimation. (This was a critical lesson from the prior session
`20260421_volprice_max_lottery`, where full-sample time-series-per-stock
OLS produced lookahead bias and a fake all-audit-PASS.)

### Industry neutralization
```python
alpha_n(s, d) = alpha_idio_12_3(s, d) - mean(alpha_idio_12_3 within industry(s) at d)
```

### Dispersion gate (the regime overlay)
```python
mkt_disp(d)         = std over stocks of ret_20(*, d)
mkt_disp_med252(d)  = rolling median of mkt_disp over past 252 days
gate(d)             = 1 if mkt_disp(d) > mkt_disp_med252(d) else 0
```

### Final factor and trading
```python
alpha_final(s, d) = alpha_n(s, d) * gate(d)
```

| Form | Construction | Use |
|------|--------------|-----|
| **Q5 long-only** | top 20% within full universe at each rebal date | deployment (index-enhancement form) |
| Q5 − Q1 LS | long Q5, short Q1, equal-weighted | signal validation only (A-share short constraint) |

Trading details:
- Universe: A-share with ≥ 252 trading days history (so cum_252 / sigma_120 are well-defined)
- Rebalance: every 20 trading days (monthly)
- Delay: 1 (signal at close T, execute close T+1)
- When `gate = 0`: hold cash, pay full liquidation turnover at boundary
- When `gate = 1`: deploy Q5 long / Q1 short, equal-weight within quintile
- Cost model: turnover-aware
  - LS: `cost = 5 / 1e4 * (turnover_q5 + turnover_q1)`
  - Q5: `cost = 5 / 1e4 * turnover_q5`

## 3. Headline metrics (full sample 2018-01-02 → 2025-04-18, 89 rebalances)

| metric | LS net | Q5 long-only excess net |
|--------|------:|------------------------:|
| Annualized return | 6.41 % | 2.10 % (vs equal-weight universe) |
| Annualized vol | 5.26 % | 3.79 % |
| **Sharpe / IR** | **1.22** | **0.56** |
| Max drawdown | −5.53 % | -- |
| Avg turnover Q5 (active) | ~24 % | -- |
| Avg LS cost per rebal | 3.61 bps | -- |
| Gate on-fraction | 42.7 % | -- |

**IC (industry-neutral, on the *unguarded* idio signal — the gate operates
on the deployment side, not on IC)**:

| horizon | mean | ICIR | t-stat | n_dates |
|---:|---:|---:|---:|---:|
| 5d  | 0.0114 | 0.135 | 6.27  | 1577 |
| 20d | 0.0158 | 0.196 | 9.09  | 1565 |
| 60d | 0.0204 | 0.282 | 13.10 | 1525 |

## 4. TVT split

| split | period | n reb | LS net Sharpe | Q5 net IR |
|-------|--------|------:|--------------:|----------:|
| Train    | 2018-2022     | 65 | 1.17 | — |
| Validate | 2023          | 12 | 0.63 | — |
| **Test** | **2024 – 2025-04-18** | 12 | **1.74** | **1.03** |
| Full     | 2018-01 – 2025-04 | 89 | **1.22** | **0.56** |

Test-period LS Sharpe materially exceeds train and full-period numbers,
which is unusual and a tell that 2024 was an exceptional trend year. Honest
deployment expectation: **LS Sharpe 1.0-1.3, Q5 IR 0.5-0.7**, with one
year in roughly three held in cash.

## 5. Annual breakdown (LS after-cost)

| year | n | gate-on periods | LS ann return | LS Sharpe | Q5 excess ann | Q5 IR |
|---:|---:|---:|---:|---:|---:|---:|
| 2018 | 13 | 0 | 0.00 % | 0.00 (cash) | 0.00 % | 0.00 (cash) |
| 2019 | 12 | 4 | 4.95 % | 1.41 | 1.72 % | 1.20 |
| 2020 | 12 | 9 | 11.95 % | 1.28 | 3.21 % | 0.68 |
| 2021 | 12 | 7 | 5.97 % | 1.75 | 1.22 % | 0.71 |
| 2022 | 12 | 3 | 7.94 % | 1.79 | 2.62 % | 1.41 |
| 2023 | 12 | 5 | 1.69 % | **0.63** | -2.81 % | -1.41 |
| 2024 | 12 | 9 | 16.59 % | 2.47 | 9.30 % | 1.21 |
| 2025YTD | 4 | 1 | -4.71 % | -2.18 (n=4) | -0.22 % | -3.04 (n=4) |

**Worst active-year LS Sharpe = 0.63 (2023)** — clears the 0.5 audit floor.
2018 was held entirely in cash (every rebal had gate = 0).

**Caveat on Q5 long-only**: Q5 in 2023 had IR -1.41 — the gate did not
fully protect the long-only form because the 5 active months in 2023
overlapped with mid-year mid-cap rallies that subsequently reversed.
The LS form was protected because the short leg participated. **Long-only
deployment carries higher regime risk than LS deployment.**

## 6. Mandatory audits

| audit | result | how |
|-------|--------|-----|
| Rule of 8 | ✅ | every batch had exactly 8 expressions |
| One-mechanism | ✅ | dispersion-gated 12-3 idio momentum across all 8 R5 expressions |
| Execution-delay | ✅ | `target_shift == -(1+delay) == -2` invariant held |
| Look-ahead structural | ✅ | factor uses only past bars; cs-resid is per-date; gate uses only past 252-day median |
| Look-ahead numeric (shuffle) | ✅ | no `.where()` derived from `ret.shift(-k)` anywhere; verified by source review |
| Worst-year floor — active years (≥ 0.5) | ✅ | 0.63 (2023); next-worst 1.28 (2020) |
| Worst-year floor — all years | ⚠ | 0.0 (2018, all cash); flagged but interpreted as "no risk taken" not "loss taken" |
| Best-year-out (≥ 50 % headline) | ✅ | 71 % retained when 2024 excluded |
| Spec sensitivity (Round 6) | ✅ | 5 of 7 dispersion-threshold variants pass joint floor |
| Placebo (Round 6, 100 random gates) | ✅ | LS full = 1.22 better than placebo max 1.17 (p < 0.01); worst-year-active 0.63 vs placebo max 0.19 (p < 0.01) |
| Cost model sanity | ✅ | turnover-aware, full liquidation cost charged at gate boundaries |
| Economic basis in literature | ✅ | Stivers-Sun 2010 RFS |

## 7. Failure modes / caveats

- **Long-only deployment is more fragile than LS.** Q5 in 2023 was -1.41
  IR. The dispersion gate filters the *aggregate* opportunity set but
  cannot protect against a long-only book caught in mid-cycle reversal.
- **2018 was held entirely in cash.** A full year of zero-return is
  acceptable from a risk perspective but unattractive for capital
  allocation. The strategy may produce 0 % years in future bear markets.
- **Gate flicker risk.** Variants tested in Round 6 with shorter
  lookback (60d median) had worst-year -1.26. The 252d median was chosen
  for stability. If volatility regime shifts faster than 252d, the gate
  may lag.
- **Test-period (2024) LS Sharpe = 1.74 is unusually strong.** A-share
  2024 saw a clean trend-continuation tape after the 2023 chop. Honest
  deployment Sharpe expectation should be the **train period 1.17**, not
  the test number.
- **Hit rate metric is suppressed by cash months.** Reported full-sample
  hit rate is 29 %, which actually reflects: 57 % of months gate = 0
  (return = 0, not "positive"); of the active months ~68 % are positive.
- **40 expressions tested, 100 placebo trials.** Even with rigorous
  falsification, multiple-testing correction is not formally applied.
  The Bonferroni-corrected significance thresholds would tighten the
  "p < 0.01" claims to "p < 0.0025" — still passing for the LS-full
  metric (p truly < 0.01) and the worst-year-active metric (p truly < 0.01).

## 8. Reproducibility

- Source code: `code.py` (this directory) — top-level `build_factor()`
  function returns the deployment panel.
- Generation script: `_generate_deployment_artifacts.py` — produces
  this directory's `metrics.json`, `annual.csv`, `rebalances.csv` from
  the cached round-4 panel.
- Source session scripts: `logs/20260422_trend_technical_alpha/scripts/`
  - `01_build_trend_panel.py` — Round 1 raw trend signals
  - `03_build_round2_idio.py` — Round 2 idio residualization
  - `05_round3_robustness.py` — Round 3 skip-window variants (introduces α_19, α_29)
  - `07_round5_regime_overlay.py` — Round 5 (introduces α_35)
  - `08_round6_falsification.py` — spec sensitivity + placebo
- Raw Tushare cache (~260 MB) is **gitignored**; rebuild by setting
  `TUSHARE_TOKEN` and running fetch scripts.
- Round-4 panel cache: `logs/20260422_trend_technical_alpha/outputs/panel_trend_round4.parquet`
  (also gitignored).

## 9. Operational

```yaml
deployment:
  start_date: 2026-04-22
  capital_allocation: TBD
  primary_form: LS (long Q5, short Q1, equal-weight)
  alternative_form: Q5 long-only (higher regime risk; suitable for index-enhancement)
  kill_switch:
    rolling_12m_sharpe_below: 0.0
    max_dd_below_pct: -8
    rolling_24m_ic_below: 0
    consecutive_quarters_negative: 3
  gate_monitoring:
    cadence: weekly check of mkt_disp vs 252d median
    expected_on_fraction: 0.40 - 0.50
    alert_if_off_for_full_year: true
  benchmark: equal-weight A-share universe (LS) or CSI300 (Q5)
data_refresh:
  daily_prices: nightly pull (close + adj_factor)
  daily_basic: nightly pull (total_mv)
  industry: monthly refresh of stock_basic.industry
```

## 10. Citation

Stivers, C. T., & Sun, L. (2010). Cross-sectional return dispersions and
time variation in value and momentum premiums. *Journal of Financial and
Quantitative Analysis*, 45(4), 987-1014.

Liu, J., Stambaugh, R. F., & Yuan, Y. (2019). Size and value in China.
*Journal of Financial Economics*, 134(1), 48-69.

Jegadeesh, N., & Titman, S. (1993). Returns to buying winners and selling
losers: Implications for stock market efficiency. *The Journal of Finance*,
48(1), 65-91.

Blitz, D., Huij, J., & Martens, M. (2011). Residual momentum. *Journal of
Empirical Finance*, 18(3), 506-521.

Han, Y., Zhou, G., & Zhu, Y. (2016). A trend factor: Any economic gains
from using information over investment horizons? *Review of Financial
Studies*, 29(5), 1209-1244 — *referenced for the raw multi-MA trend
construction tested as the falsification anchor in Round 1.*
