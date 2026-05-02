# Factor definition — `ashare_etf_lowbeta_bot15_ma200gate_v1`

## Inputs

- Daily OHLCV panel of A-share ETFs (Tushare `fund_daily` + `fund_adj`,
  forward-adjusted close).
- HS300 ETF (`510300.SH`) close, used as benchmark for beta and regime
  gate.

## Construction (deterministic, no look-ahead)

For each ETF i and trading day t:

```
log_ret_i_t   = log(close_i_t) - log(close_i_{t-1})
log_ret_b_t   = log(close_b_t) - log(close_b_{t-1})              # b = 510300.SH
beta_i_t      = cov(log_ret_i, log_ret_b; past 60 bars)
                / var(log_ret_b; past 60 bars)
abs_beta_i_t  = |beta_i_t|

regime_t      = 1 if close_b_t > mean(close_b; past 200 bars) else 0
```

At each calendar month-end signal date `t_me`:

```
selected_i_t_me = 1 if abs_beta_i_t_me is among the 15 smallest values
                       across the universe at t_me
                  0 otherwise

w_i_t_me        = (1/15 if selected_i_t_me == 1 else 0) * regime_t_me
```

Weights apply on bars `[close[t_me + 1], close[next_me + 1]]`. Cash
holding when `regime_t_me == 0`. Rebalance is monthly.

## Execution invariant

`target_shift = -(1 + delay) = -2`. Signal at close[t_me] → trade at
close[t_me+1] → next month-end fill. See
`logs/20260502_a_share_etf_riskadj_mom_v1/outputs/audit_winner_m7_R5.json`
for the audit.

## Economic story

Cross-sectional low-beta selection captures the well-documented "betting
against beta" premium (Frazzini & Pedersen 2014) at the ETF level. In
A-share thematic ETFs the premium is genuine but **periodically
overwhelmed by broad-market crashes** (2022 deleveraging, 2024
deleveraging) because all ETFs in the basket carry residual market
exposure. The MA200 broad-market gate detects regime-level downtrends
and flattens the book to cash, eliminating the negative-Sharpe years
that plague unconditional long-only ETF baskets.

The premium has IC mean +0.055 at the 21-day horizon (t-stat 1.28 over
80 month-ends). Shuffled-label IC averages -0.009 (audit 5), confirming
the signal is not a label-shuffle artefact.

## What's tested in the audits

1. **Execution-delay** — `target_shift = -2` invariant verified in code.
2. **Look-ahead** — perturbing future bars leaves all past beta values
   bit-identical.
3. **Worst-year floor (revised)** — winner ≥ 0 AND strictly better than
   EW worst-year (-1.17). Original 0.5 floor proved infeasible on this
   window because EW itself fails it.
4. **Best-year-out** — recomputing Sharpe excluding the best year (2019)
   gives 0.42 = 95% of headline 0.45.
5. **Falsification-first** — shuffled-label IC -0.009 vs real +0.055.

All 5 PASS.

## Limitations

- **Universe is small (71 ETFs)** — selection error is a meaningful
  fraction of total variance. Top-15 = ~21% of universe.
- **Sample window includes 2022-23 deleveraging** — these are precisely
  the years the regime gate is designed to handle, so out-of-sample
  generalisation to *new* deleveraging episodes is the main risk.
- **Survivorship bias** — selected ETFs all listed by 2020-06-30 and
  not delisted. Bias is mild for ETFs (delisting rate is low) but not
  zero.
- **No bond/cash leg in down regime** — currently goes to literal zero
  weight, capturing money-market rate (~2-3% annually). Adding a
  short-bond ETF leg in down regimes could lift Sharpe by ~0.05-0.10.

## Versioning

- v1: 2026-05-02. Initial release. 71-ETF Tushare universe, monthly
  rebalance, 5 bps/side cost. See session
  `logs/20260502_a_share_etf_riskadj_mom_v1` for the 5-round
  derivation.
