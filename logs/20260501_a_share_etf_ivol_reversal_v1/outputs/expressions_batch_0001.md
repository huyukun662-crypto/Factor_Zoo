# Expressions Batch 0001 — IVOL-Reversal v1

Owner: Agent 3 (Alpha Builder).
Generated: 2026-05-01.
Mechanism: idiosyncratic-volatility cross-sectional rank reversal,
residualized to 510300.

## Convention

All expressions are written so that **higher signal value → long
position**. The directional convention is enforced inside each formula
(typically via a leading minus sign on IVOL).

`r_i_t` = log return of follower ETF i on date t.
`r_M_t` = log return of 510300 on date t.
`β_iL_t = cov(r_i, r_M; window) / var(r_M; window)` evaluated at t (uses
data ≤ t).
`ε_i_t = r_i_t - β_iL_t × r_M_t` (residual return).
All windows are *backward-looking* and end at t (or t-lag).

Cross-section ranking is `groupby(date).rank(pct=True)`.

---

## E1 — `f1_ivol_resid_20d`  (headline)

```
beta = roll_cov(r_i, r_M, 60) / roll_var(r_M, 60)
eps  = r_i - beta * r_M
ivol = roll_std(eps, 20) * sqrt(252)
signal = -ivol
```

- Headline expression of the batch. 60d-rolling β, 20d-rolling residual std.
- Expected sign: long-bottom-IVOL (low std), short-top-IVOL (high std).
- Expected turnover: moderate; IVOL is reasonably persistent week-on-week
  so weekly rebalance turnover ~150-250%.

## E2 — `f2_total_vol_20d`  (no residualization control)

```
signal = -roll_std(r_i, 20) * sqrt(252)
```

- Same target as E1, but with raw daily-return std instead of residual std.
- Diagnostic: if E2 ≈ E1 in IC and Sharpe, the residualization to 510300
  isn't doing much (which would mean the cross-section's beta dispersion
  is too narrow to matter).
- Expected sign: positive long-short, but typically weaker than IVOL
  (Liu-Shu-Wei 2017 result on A-share single names).

## E3 — `f3_ivol_resid_10d`  (short window)

```
beta = roll_cov(r_i, r_M, 60) / roll_var(r_M, 60)
eps  = r_i - beta * r_M
signal = -roll_std(eps, 10) * sqrt(252)
```

- Half the window of E1. Faster reaction, more noise.
- Expected: higher turnover (~300-450%), possibly higher IC at k=1
  (matches the shorter-horizon noise), comparable IC at k=5.

## E4 — `f4_ivol_resid_40d`  (long window)

```
beta = roll_cov(r_i, r_M, 60) / roll_var(r_M, 60)
eps  = r_i - beta * r_M
signal = -roll_std(eps, 40) * sqrt(252)
```

- Two months of residual std. Smoother, lower turnover (~80-150%).
- Expected: comparable IC at k=5, slightly higher IC at k=20.

## E5 — `f5_ivol_resid_amplitude_20d`  (mean-abs instead of std)

```
beta = roll_cov(r_i, r_M, 60) / roll_var(r_M, 60)
eps  = r_i - beta * r_M
amp  = roll_mean(|eps|, 20) * sqrt(252)
signal = -amp
```

- Robust to single-day outliers (e.g., 2020-02-03 black-swan).
- Expected: slightly weaker than E1 in steady regimes, slightly more
  stable across crises.

## E6 — `f6_ivol_lagged_5d`  (decay test)

```
beta = roll_cov(r_i, r_M, 60) / roll_var(r_M, 60)
eps  = r_i - beta * r_M
ivol_lag = shift(roll_std(eps, 20) * sqrt(252), 5)
signal = -ivol_lag
```

- Same IVOL as E1, but observed 5 trading days ago.
- Diagnostic: if E6 ≈ E1, the signal is slow-decaying and weekly
  rebalance is fine. If E6 << E1, the signal decays inside the
  rebalance window and we should consider higher frequency.

## E7 — `f7_vol_of_vol_20_40`  (acceleration variant)

```
beta = roll_cov(r_i, r_M, 60) / roll_var(r_M, 60)
eps  = r_i - beta * r_M
ivol_short = roll_std(eps, 20) * sqrt(252)
ivol_long  = roll_std(eps, 40) * sqrt(252)
signal = -(ivol_short - ivol_long)   # negative when vol is accelerating up
```

- Captures vol *acceleration*: ETFs whose IVOL is rising fast (short >
  long) get penalized harder than ETFs at high but stable IVOL.
- Hypothesis: the lottery-preference / arb-limit story is stronger when
  IVOL is increasing, not just high.

## E8 — `f8_kitchen_sink_rank`  (composite)

```
signal = mean_rank([
    rank(-ivol_20d_resid),     # E1 component
    rank(-vol_20d_total),      # E2 component
    rank(-amp_20d_resid),      # E5 component
    rank(-(ivol_short - ivol_long))   # E7 component
])
```

- Mean of cross-sectional percentile ranks of the four core variants.
- Acts as the variance-reduction ensemble of the dominant mechanism.
- Expected: slightly lower IC than the best single variant but better
  worst-year robustness.

---

## Pre-flight check (before handing to Agent 4)

| Check | Status |
|---|---|
| Exactly 8 expressions | ✅ E1-E8 |
| All share dominant mechanism (IVOL family) | ✅ all rooted in residual std / total std |
| Sign convention "high signal = long" | ✅ negation applied at source |
| No look-ahead in formulas | ✅ all rolling windows are backward |
| All inputs in shared cache | ✅ r_i, r_M from etf_daily.parquet |
| Expected turnover bands stated | ✅ per-expression |
| No expression is identical to another | ✅ varies on window, residualization, lag, transform |
