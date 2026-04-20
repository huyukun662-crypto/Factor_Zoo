# Alpha Ranking — Session Leader Board (after Round 2)

**Session:** 20260420_fundamental_accruals_alpha
**Agent:** 5 Evaluator & Recorder
**Current flagship:** `alpha_v5` — median-TTM industry-neutral Sloan CFS accruals

---

## 1. Leader board (across Round 1 + Round 2, ranked by net Sharpe)

| rank | alpha | batch | IC@20 | ICIR@20 | **Sharpe net** | worst yr | max DD | verdict |
|-----:|-------|------:|------:|--------:|---------------:|---------:|-------:|:-------:|
| **1** | **alpha_v5** median-TTM ind-neut | 0002 | 0.016 | **0.505** | **1.57** | **1.55** | **−1.6 %** | **FLAGSHIP → paper trading** |
| 2 | alpha_v2 tight-winsorize | 0002 | 0.018 | 0.492 | 1.40 | 1.19 | −2.0 % | retained; near-clone of v1 |
| 3 | alpha_03 / alpha_v1 baseline | 0001+0002 | 0.018 | 0.493 | 1.38 | 1.24 | −2.0 % | prior flagship; superseded by v5 |
| 4 | alpha_v4 8q-TTM | 0002 | 0.014 | 0.425 | 1.37 | 1.61 | −2.5 % | interesting worst-year; low ICIR |
| 5 | alpha_v8 ensemble | 0002 | 0.016 | 0.471 | 1.33 | 0.92 | −2.5 % | no ensemble benefit |
| 6 | alpha_v6 revenue-scaled | 0002 | 0.017 | 0.498 | 1.33 | 1.12 | −3.5 % | higher DD |
| 7 | alpha_v3 z-score | 0002 | 0.018 | 0.481 | 1.30 | 1.18 | −2.4 % | rank wins over z-score |
| 8 | alpha_v7 stability-weighted | 0002 | 0.013 | 0.437 | 1.10 | 1.08 | −2.1 % | normalization costs IC |
| 9 | alpha_08 ind × size double | 0001 | 0.011 | 0.300 | 0.93 | 0.88 | −3.3 % | over-neutralized |
| 10 | alpha_06 acc/ni-vol | 0001 | 0.020 | 0.300 | 0.61 | 0.59 | −5.3 % | — |
| 11 | alpha_01 raw Sloan | 0001 | 0.024 | 0.333 | 0.84 | 0.77 | −5.3 % | no neutralization |
| 12 | alpha_07 acc × persistence | 0001 | 0.012 | 0.228 | 0.46 | −0.20 | −6.7 % | dropped |
| 13 | alpha_05 Δacc yoy | 0001 | 0.009 | 0.205 | 0.22 | 0.12 | −5.5 % | dropped |
| 14 | alpha_04 CFO/\|NI\| | 0001 | 0.020 | 0.248 | 0.21 | 0.22 | −12.0 % | dropped |
| 15 | alpha_02 BS-method WCA | 0001 | −0.017 | −0.058 | **−0.47** | −1.73 | **−60.2 %** | dropped (signal inverted) |

## 2. Why v5 is the new flagship

The one change from baseline alpha_03: replace trailing-4-quarter **sum** of NI/CFO with trailing-4-quarter **median × 4**. That single substitution:

- Raises net Sharpe by 14 % (1.38 → 1.57).
- Raises worst-year floor by 25 % (1.24 → 1.55).
- Cuts max drawdown by 20 % (−2.0 % → −1.6 %).
- Raises ICIR from 0.495 → 0.505 at 20d, from 0.852 → 0.909 at 60d.

Mechanism: A-share financials carry restatement noise and occasional one-off items that distort a single quarter. The 4-quarter sum carries this noise forward; the median suppresses it without losing signal. This is exactly the Tushare-restatement fragility the Round 1 research brief flagged as caveat #2.

## 3. Round 2A residualization verdict (for alpha_03)

Residualizing alpha_03 cross-sectionally against {log_mv, mom_20, rev_5, turnover_z, vol_20} retains **96 %** of the net Sharpe and **improves** ICIR (0.495 → 0.575 at 20d). The accruals premium is a genuinely independent signal — not a repackaged size / momentum / reversal / liquidity / low-vol factor. By implication the same holds for v5 (which is the same mechanism with a more robust TTM).

## 4. Deployment spec for `alpha_v5`

```yaml
name:          accruals_median_ttm_ind_neutral_v2
mechanism:     earnings quality (Sloan 1996) via median-TTM accruals
universe:      A-share ex-financials ex-ST, listed > 252 trading days
frequency:     monthly rebalance (every 20 trading days)
delay:         1 (signal at close T, execute close T+1)
deployment:
  primary:     Q5 (top-quintile) long-only, equal-weighted within industry; benchmark = CSI300
  validation:  LS (Q5-Q1) for signal integrity monitoring; not deployed
data_refresh:
  quarterly_statements: tushare income_vip + balancesheet_vip + cashflow_vip, weekly poll
  daily_prices: tushare daily + adj_factor + daily_basic, nightly pull
kill_switch:
  rolling_12m_ic_below_0:  alert
  max_drawdown_below_-8%:  pause
  turnover_monthly_above_35%: investigate (shouldn't move much with fundamentals)
```

## 5. Continue / refine / stop

**Decision:** `continue` — promote v5 to paper trading; start Round 3 on a pre-2020 stress window.

- Round 3 should fetch 2018-01 → 2019-12 daily data to cover the 2018 deleveraging stress and full 2019 bull; re-run alpha_v5 over 2018-2025.
- Open a second session for SUE / PEAD (independent mechanism) to prepare factor ensemble.
- Do NOT further vary accruals normalization; the signal is well-characterized now.
