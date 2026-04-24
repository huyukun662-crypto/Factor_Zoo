# Objective — A-Share ETF Dip-Buy / Reversal v1

## Session

`20260423_a_share_etf_reversal_v1` — produced by the WorldQuant 5-agent
workflow on 2026-04-23.

## Research question

**Does a daily-bar dip / reversal signal on a universe of top-liquidity
A-share ETFs produce a deployable long-only or long-short factor at
monthly / weekly rebalance after 5 bps/side cost?**

## Scope

- **Universe**: 20 top-liquidity A-share ETFs
  - Broad index (10): 510300 沪深300, 510500 中证500, 510050 上证50,
    159915 创业板, 510180 上证180, 159949 创业板50, 588000 科创50,
    588080 科创板100, 512100 中证1000, 510880 红利 ETF
  - Industry / thematic (9): 512880 证券, 512660 军工, 512170 医疗,
    512760 芯片, 515030 新能源车, 512290 生物医药, 515050 5G,
    512690 酒, 512980 传媒
  - Commodity (1): 518880 黄金 ETF
- **Window**: 2020-01-01 → 2026-04-22 (~6 calendar years, ~1,540 trading days)
- **Bar**: daily OHLCV (adjusted close) via Yahoo Finance `.SS/.SZ`
- **Primary horizon**: k = 10 trading days (2 weeks)
- **Rebalance candidates**: weekly (Wed) and monthly (month-end); start weekly

## Why dip / reversal on ETFs

ETFs absorb idiosyncratic stock noise; what remains is the index-level
mean-reversion component. Prior literature (De Bondt–Thaler 1985,
Jegadeesh 1990 weekly reversal, Nagel 2012 liquidity-provision) argues
reversal is strongest where idiosyncratic noise is heaviest — industry
and thematic ETFs are between single stocks and broad indices, so they
should retain some idiosyncratic reversal while being cleaner to
instrument than the underlying baskets. Spot-ETF fees are lower than
single-stock fees (no stamp duty), so the cost floor is friendlier to
short-horizon signals than single-stock A-share factors were in the
Accruals / Asset Growth sessions.

## Hypothesized mechanisms (Rule of 8)

1. **Rolling drawdown**: `(close - max_high_20d) / max_high_20d` — deeper
   drawdown → long signal
2. **RSI oversold**: Wilder RSI(14), mapped so low RSI = long
3. **Bollinger position**: `(close - MA20) / (2 × std20)` — low position
   = long
4. **Log-bias MA20**: `-(log close - log MA20)` — negative bias (below
   MA) = long
5. **5-day cumulative return reversal**: `-ret_5d`
6. **Vol-scaled short reversal**: `-ret_5d / std_20d`
7. **Volume-confirmed reversal**: `-ret_5d × z(log_volume_ratio)` where
   `log_volume_ratio = log(vol_5d / vol_20d)` — down days on volume
   should rebound harder
8. **Kitchen-sink rank combo**: mean of ranks of signals 1-6

## Hard floors (from session_metadata_round1.yml)

| Metric | Threshold |
|---|---|
| Rank IC mean at k=10 | ≥ 0.03 |
| ICIR at k=10 | ≥ 0.3 |
| Decile-spread gross Sharpe | ≥ 1.0 |
| Net Sharpe at 5 bps/side | ≥ 0.5 |
| Worst calendar-year Sharpe | ≥ 0 |
| Best-year-out Sharpe | ≥ 50% of headline |
| G5 horizon consistency | ≥ 50% of G4 survivors peak at k=10 |

Any failure → decision is RESEARCH-ONLY, never PROMOTE.

## Cost model

- Baseline: 5 bps per side (covers commission + impact; ETF no stamp duty)
- Sensitivity: {2, 5, 8} bps/side curve at Round 1, expand if needed

## Non-goals

- Intraday / minute-level signals (see BTC 1m session for why fees
  dominate minute-level signals on spot venues)
- Multi-asset cross-market reversal (US ETF or HK ETF overlay left for
  a later session)
- Deployment infrastructure (order book, routing, slippage modelling)

## Data contract

`inputs/etf_daily.parquet` columns:

| column | type | note |
|---|---|---|
| date | datetime | trading date (Asia/Shanghai close) |
| symbol | str | Yahoo ticker, e.g. `510300.SS` |
| open, high, low, close | float | adjusted |
| volume | int | shares |
| amount | float | close × volume proxy (Yahoo doesn't expose VWAP) |

## Success / abort criteria

- **PROMOTE**: at least one expression clears all hard floors at k=10 with
  weekly or monthly rebalance, at 5 bps/side.
- **RESEARCH-ONLY**: mechanism confirmed (G5 passes, Q5 monotone) but
  costs wipe net Sharpe, OR one bad year drags worst-year Sharpe below 0.
- **FAIL**: no expression clears G1–G4 in two rounds; mechanism is wrong.
