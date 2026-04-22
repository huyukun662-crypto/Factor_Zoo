# Alpha Expressions — Batch 0001 — MAX Effect / Lottery Demand

**Session:** `20260421_volprice_max_lottery`
**Mechanism:** Extreme recent returns proxy retail lottery attention → short high-MAX.
**Direction:** alpha sign = negative (all 8).
**Target:** `fwd_ret_20` (monthly), delay=1 → `target_shift = -2` applied by builder.
**Neutralization:** industry (CITIC L1) — demean within industry per trade_date, then cross-sectional z-score.

Notation:
- `r_t` = daily log return = `ln(close_adj_t / close_adj_{t-1})` (close-to-close).
- `w(n)` = rolling window of n trading days ending at t (exclusive of t+1).
- `topk(x, k)` = mean of top-k values of series x.
- `ind_rank(x)` = cross-sectional rank within industry per trade_date, divided by group size.
- `cs_z(x)` = cross-sectional z-score per trade_date.

## α_01 — max_1_20 (single-max, Bali simplest)
```
raw = -max(r_t over w(20))
α_01 = cs_z( ind_demean( winsorize(raw, 1%, 99%) ) )
```

## α_02 — max_avg5_20 (Bali-Cakici-Whitelaw exact form)
```
raw = -mean( top5(r_t over w(20)) )
α_02 = cs_z( ind_demean( winsorize(raw, 1%, 99%) ) )
```

## α_03 — max_avg10_60 (longer horizon)
```
raw = -mean( top10(r_t over w(60)) )
α_03 = cs_z( ind_demean( winsorize(raw, 1%, 99%) ) )
```

## α_04 — max_vol_scaled_5_20 (Sharpe-like extreme)
```
m = mean(top5(r_t over w(20)))
s = std(r_t over w(20))
raw = -(m / s)                    # dimensionless extremity
α_04 = cs_z( ind_demean( winsorize(raw, 1%, 99%) ) )
```

## α_05 — max_turnover_weighted (attention amplifier)
```
m = mean(top5(r_t over w(20)))
turn = mean(amount / circ_mv over w(20))     # turnover rate
raw = -m * cs_z(turn)
α_05 = cs_z( ind_demean( winsorize(raw, 1%, 99%) ) )
```

## α_06 — max_minus_min_20 (two-sided extremity / range)
```
m_pos = mean(top5(r_t over w(20)))
m_neg = mean(bot5(r_t over w(20)))
raw = -(m_pos - m_neg)                        # spread of extremes
α_06 = cs_z( ind_demean( winsorize(raw, 1%, 99%) ) )
```

## α_07 — max_zscore_20 (standardized extreme)
```
m = max(r_t over w(20))
mu = mean(r_t over w(20))
s  = std(r_t over w(20))
raw = -(m - mu) / s
α_07 = cs_z( ind_demean( winsorize(raw, 1%, 99%) ) )
```

## α_08 — max_abnormal_20 (residualized MAX vs market)
```
# Market return same day = equal-weight mean of r_t across universe on day t
ab_r_t = r_t - market_r_t
raw = -mean(top5(ab_r_t over w(20)))
α_08 = cs_z( ind_demean( winsorize(raw, 1%, 99%) ) )
```

## Builder-side pre-submission checks (performed before handoff to Agent 4)

For each alpha on validate window (2023):
1. **Coverage:** ≥ 70% non-null per trade_date after all filters
2. **Cross-sectional dispersion:** std > 0.001 (not a constant column)
3. **IC sign:** Spearman IC(α, fwd_ret_20) on validate period should be POSITIVE (because α
   is constructed with negative sign already — higher α means lower lottery demand → higher future return).
4. **No infs / NaN explosions:** divide-by-zero handled by `std > eps`, default to 0 on degenerate groups.
5. **Industry-neutrality check:** mean(α | industry, date) ≈ 0 ± 1e-9.

If any check fails → builder must fix the expression, not retry blindly.

## Ready for handoff to Agent 4

After pre-submission checks pass, Agent 4 receives:
- `panel_volprice.parquet` with columns: `ts_code`, `trade_date`, `industry`, `alpha_01..alpha_08`, `fwd_ret_1`, `fwd_ret_5`, `fwd_ret_20`, `fwd_ret_60`, `total_mv`, `circ_mv`, `turnover_20`, `sigma_20`, `ret_5`, `ret_20` (controls for audits).
