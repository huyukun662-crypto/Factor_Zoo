# Expressions — Batch 0001 (Round 1)

**Session:** `20260423_a_share_etf_reversal_v1`
**Agent:** 3 (Alpha Builder)
**Horizon:** k = 10 trading days (weekly rebalance on Wed)
**Universe:** 18 A-share ETFs (see session_metadata.yml)
**Execution delay:** 1 bar; target = `log(close[t+1+k]) - log(close[t+1])`
**Neutralization:** universe-EW cross-sectional demean per date (zero-sum)

All expressions follow the convention **high signal = long** (dip = positive signal).

| id | rationale | formula (before demean) |
|---|---|---|
| r1_dd20 | 20d drawdown; deeper dip → long | `-(close - max(high,20)) / max(high,20)` |
| r1_rsi14 | Wilder RSI oversold | `50 - RSI14` |
| r1_bb_pos | Bollinger position | `-(close - MA20) / (2 * std20)` |
| r1_logbias_ma20 | log distance vs MA20 | `-(log(close) - log(MA20))` |
| r1_rev_5d | 5d return reversal | `-logret_5d` |
| r1_vol_scaled_rev5 | vol-scaled 5d reversal (Nagel 2012) | `-logret_5d / std_20d` |
| r1_vol_confirmed_rev | volume-confirmed reversal | `-logret_5d * ts_z(log(vol_5d/vol_20d))` |
| r1_kitchen_sink | rank ensemble of 6 above | `mean(rank(r1_dd20), ..., rank(r1_vol_scaled_rev5))` |

Rule of 8 ✓. Each signal is then universe-EW demeaned per date before ranking.
