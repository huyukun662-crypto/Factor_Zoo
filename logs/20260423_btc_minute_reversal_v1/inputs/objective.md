# Objective — BTC 1-minute factor mining

Run the WorldQuant 5-agent workflow on BTC-USD 1-minute bars.

## Scope
- Asset: BTC-USD (spot, Coinbase Exchange as data source)
- Frequency: 1-minute OHLCV
- Sample window: ~60 days ending 2026-04-21 (~86k bars)
- Target: forward log return at horizons {1, 5, 15, 60} minutes
- Data limitation: only OHLCV is available (no order book, no trade tape)

## Single-asset adaptation

This is a time-series problem (one asset, one long sample), not a
cross-sectional problem. Adapt the workflow:

- Replace Q5 / Q1 selection with signal-decile time-series buckets
  (`qcut(signal, 10)` over the full sample, then evaluate the top and
  bottom buckets' forward returns)
- Replace cross-sectional IC with time-series Pearson(signal_t, fwd_ret_t+k)
- Replace portfolio turnover with trade frequency (position changes per
  hour / day)
- Replace "industry neutralization" with "intraday seasonality demean"
  (remove hour-of-day effect)

## Hard floors for PROMOTE

- IC at primary horizon: t-stat >= 4 (easier than A-share because
  minute-sample is ~86k vs A-share 1280 days)
- Decile D10-D1 Sharpe >= 1.0 in-sample (gross)
- Worst-week Sharpe >= -1.0 (minute-level can be noisy per week)
- After-cost Sharpe > 0 at 5 bps per side taker fee
  (Coinbase spot: ~10 bps default, but we'll use 5 bps as reasonable
  Kraken/OKX taker level)
- Trade frequency < 10 position changes per hour (else costs dominate)

## Non-goals (explicit)

- Not testing perpetuals / funding rate factors (requires separate data)
- Not testing order book imbalance (requires L2 snapshots)
- Not trading real capital; this is research.
