# Expressions — Batch 0002 (Round 2)

**Session:** `20260423_a_share_etf_reversal_v1`
**Agent:** 3 (Alpha Builder)
**Horizon:** k = 60 trading days (monthly rebalance, 20 trading days)
**Universe:** 18 A-share ETFs
**Execution delay:** 1 bar; target = `log(close[t+1+k]) - log(close[t+1])`
**Neutralization:** universe-EW cross-sectional demean per date

## Round 2 hypothesis

After Round 1's batch-level G5 failure, Agent 2 re-specified the
mechanism to **long-term reversal + selective oversold**. Round 2
expressions target k ∈ {20, 60, 120} to cover the DeBondt-Thaler
long-horizon range and narrow-condition variants (extreme drawdown
only, RSI<30 only, residual reversal after momentum control).

| id | rationale | formula (before demean) |
|---|---|---|
| r2_lt_rev_60d          | 60-day long-term reversal | `-logret_60d` |
| r2_lt_rev_120d         | 120-day (6-month) reversal | `-logret_120d` |
| r2_lt_rev_250d         | 250-day (1-year) reversal | `-logret_250d` |
| r2_vol_scaled_lt_120   | vol-scaled 120d reversal | `-logret_120d / std_60` |
| r2_deep_dip_rev        | selective 5d reversal; active only if dd20 < -5% | `-logret_5d * I[dd20 < -5%]` |
| r2_rsi_extreme_os      | RSI14 < 30 selective oversold | `(30 - RSI14) * I[RSI14 < 30]` |
| r2_vol_confirmed_lt60  | volume-confirmed 60d reversal | `-logret_60d * ts_z(log(vol20/vol60))` |
| r2_residual_rev        | 5d reversal residualized on 60d trend | `resid(-logret_5d, logret_60d)` |

Rule of 8 ✓. Universe-EW demean applied per date.

## Audit probe (outside Rule of 8)

`probe_momentum_20d` = `+logret_20d` — pipeline sanity check. If this
has IC ≫ 0 at k=60, momentum dominates and Round 2's reversal thesis
is wrong-horizon. If IC ≈ 0, then k=60 is in the transition zone
between short-horizon momentum and long-horizon reversal, which is what
Agent 2 expects.
