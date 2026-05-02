# ashare_etf_lowbeta_bot15_ma200gate_v1

A-share ETF defensive overlay: long the bottom-15 ETFs by absolute beta to
HS300 (60-day window), monthly rebalance, with an MA200(510300) regime gate
that flattens the book to cash when the broad market is below MA200.

- **Session origin**: `logs/20260502_a_share_etf_riskadj_mom_v1`
- **Universe**: 71 A-share ETFs (Tushare passive/enhanced index, list_date ≤
  2020-06-30, ≥ 1500 bars, avg daily amount ≥ 50M CNY)
- **Window**: 2019-01-02 → 2026-04-30
- **Rebalance**: monthly, 1-day execution delay
- **Cost model**: 5 bps / side
- **Decision**: RESEARCH-ONLY (defensive overlay deployment)

## Headline metrics (net 5 bps/side)

| Metric | Winner | EW baseline |
|---|---|---|
| Annualised Sharpe (net) | **0.45** | 0.57 |
| Annual return | 5.0% | 6.4% |
| Annual volatility | 11.2% | 11.2% |
| Max drawdown | **-22%** | -33% |
| Worst-year Sharpe | **0.00** | -1.17 |
| BYO/headline ratio | 0.95 | 0.68 |
| Annual turnover | 202% | 19% |
| IC mean (21d) | +0.055 | n/a |

## Files

- `factor.md` — formal definition and economic story
- `code.py` — minimal reproducer (loads the Tushare cache, builds the
  factor and the daily PnL)
- `metrics.json` — machine-readable metrics
- `annual.csv` — per-year breakdown
- `rebalances.csv` — per-month-end weights
- `factor_signals.parquet` — daily long-form factor (date, symbol, beta,
  signal, in_top15, weight, regime_active)

## Trade-off vs EW

This factor is NOT an alpha source against the EW baseline — it sacrifices
~0.13 of headline Sharpe. Its deployment value is **drawdown control**: max
drawdown is reduced by 11 percentage points (-22% vs -33%), and there are
zero negative-Sharpe years over 8 calendar years vs EW's two (2022, 2023).

Suitable for capital that cannot tolerate full A-share market drawdowns.
For an absolute-Sharpe seeker, stay in EW or in a cap-weighted broad index.
