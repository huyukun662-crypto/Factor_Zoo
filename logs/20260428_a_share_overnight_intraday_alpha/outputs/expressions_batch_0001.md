# Expressions Batch 0001 — Overnight–Intraday Decomposition

**Session:** `20260428_a_share_overnight_intraday_alpha`
**Agent:** 3 — Alpha Builder
**Date:** 2026-04-28
**Mechanism (single, dominant):** Overnight return as informed-flow proxy
**Rule of 8 contract:** exactly 8 expressions, all sharing primitive `ret_overnight`,
differing along window length, normalization, attention weighting, and
frequency-vs-magnitude axes.

---

## Primitives (computed per (ts_code, trade_date) once)

```python
ret_overnight = (open_t * adj_factor_t) / (close_{t-1} * adj_factor_{t-1}) - 1
ret_intraday  = close_t / open_t - 1
ret_close     = (close_t * adj_factor_t) / (close_{t-1} * adj_factor_{t-1}) - 1   # full close-to-close
log_ON        = log1p(ret_overnight).clip(-0.105, 0.105)
log_ID        = log1p(ret_intraday).clip(-0.105, 0.105)
log_CC        = log1p(ret_close).clip(-0.105, 0.105)
turnover      = amount / (circ_mv * 10.0)                                         # decimal
```

All sums/means below are **rolling on past bars only**. Per-date pipeline (after
the rolling computation): winsorize 1%/99% → industry-demean (CITIC L1) →
cross-sectional zscore.

---

## Alpha 01 — `on_cum_20d`  (canonical Lou-Polk-Skouras)

```
α_01 = sum(log_ON over [t-19, t])
```

**Window:** 20 trading days (≈ 1 month).
**Direction:** sign +.
**Expected turnover:** medium (signal updates slowly because new ON returns
enter as 1/20 weight per day).
**Why:** Direct A-share replication of Lou-Polk-Skouras (2019). Uses *only* the
overnight component, removing intraday-noise contamination from the standard
1-month close-to-close momentum. Under T+1 + retail-dominated intraday, this
is the cleanest informed-flow signal we can build from `open` and `close` alone.

---

## Alpha 02 — `on_cum_5d`  (short-horizon variant)

```
α_02 = sum(log_ON over [t-4, t])
```

**Window:** 5 trading days (≈ 1 week).
**Direction:** sign +.
**Expected turnover:** high (refreshes ~20 % per day).
**Why:** Tests whether overnight informed-flow autocorrelation is concentrated
at short horizons (post-event drift) or persists over a month. If α_02 IC > α_01 IC,
the signal is a fast post-news drift; if α_01 > α_02, it is a slower-burning
preference channel. The contrast is itself informative for Agent 5.

---

## Alpha 03 — `on_cum_60d`  (long-horizon variant)

```
α_03 = sum(log_ON over [t-59, t])
```

**Window:** 60 trading days (≈ 3 months).
**Direction:** sign +.
**Expected turnover:** low.
**Why:** If overnight is a persistent firm-quality signal (Aboody et al 2018:
overnight returns reflect retail clientele sentiment that compounds over months),
α_03 should still earn positive IC. If the signal flips sign, the mechanism is
short-term information drift, not a chronic clientele effect — important
diagnostic.

---

## Alpha 04 — `on_minus_id_20d`  (decomposition spread)

```
α_04 = sum(log_ON over [t-19, t]) - sum(log_ID over [t-19, t])
```

**Window:** 20 trading days.
**Direction:** sign +.
**Expected turnover:** medium.
**Why:** This is the canonical **tug-of-war** signal of Lou-Polk-Skouras: long
the *overnight component minus the intraday component*. By construction it is
orthogonal to total close-to-close return at the cumulative level, so it carries
no momentum/reversal exposure mechanically. Strongest test that the alpha is
*decomposition*-driven, not trend-driven.

---

## Alpha 05 — `on_cum_20d_volscaled`  (vol normalization)

```
σ_ON_20 = std(log_ON over [t-19, t])
α_05    = sum(log_ON over [t-19, t]) / max(σ_ON_20, 1e-4)
```

**Window:** 20 trading days.
**Direction:** sign +.
**Expected turnover:** medium.
**Why:** Removes the mechanical correlation between cumulative magnitude and
realized vol. A stock with ten +0.5% overnight moves and a stock with one +5%
overnight move have the same cumulative ON but very different vol. The
vol-scaled form is the *information-ratio* of overnight returns and should be
more comparable across stocks. If α_05 IC > α_01 IC, the signal is about
*consistency* of overnight buying, not magnitude.

---

## Alpha 06 — `on_cum_20d_x_turnover`  (attention amplification)

```
turnover_20 = mean(turnover over [t-19, t])
turnover_z  = cross-section zscore of turnover_20 at date t
α_06        = sum(log_ON over [t-19, t]) * turnover_z
```

**Window:** 20 trading days.
**Direction:** sign +.
**Expected turnover:** medium-high (turnover rank shifts faster than the ON sum).
**Why:** Aboody et al (2018) argue overnight returns matter most when the stock
has investor attention (proxied by turnover). The product amplifies the signal
on attention-rich names and dampens it on neglected names. In A-share retail-
dominated markets, attention should *boost* the lottery side AND the
informed-flow side; net direction remains +.

---

## Alpha 07 — `on_uppct_20d`  (frequency, not magnitude)

```
α_07 = mean( 1[log_ON > 0] over [t-19, t] )
```

**Window:** 20 trading days.
**Direction:** sign +.
**Expected turnover:** low (the indicator-mean is smoother than cumulative log).
**Why:** Pure frequency form — fraction of days the overnight gap was up.
Robust to a single large overnight spike (which can dominate α_01) and tests
whether the signal is *consistency of positive overnight* rather than *size of
positive overnight*. The pure-fraction form mirrors the "frog-in-the-pan"
information-discreteness construct (Da-Gurun-Warachka 2014) but applied to
overnight only — a novel construct in A-share.

---

## Alpha 08 — `on_sharpe_20d`  (risk-adjusted overnight)

```
μ_ON_20 = mean(log_ON over [t-19, t])
σ_ON_20 = std (log_ON over [t-19, t])
α_08    = μ_ON_20 / max(σ_ON_20, 1e-4)
```

**Window:** 20 trading days.
**Direction:** sign +.
**Expected turnover:** medium.
**Why:** A within-stock Sharpe of overnight returns. Differs from α_05
in the centering: α_05 uses *cumulative* log return / std; α_08 uses *mean* log
return / std. They are linearly related by a factor of 20, but cross-sectional
percentile rank can differ if volatilities span very different scales. Included
as the "textbook" risk-adjusted form for falsification — if α_05 and α_08 give
materially different LS Sharpes, the difference is informative about how
the cross-section binds.

---

## Distinctness check

| pair | shared core | distinct axis | expected pairwise rank-corr |
|---|---|---|---|
| α_01 ↔ α_02 | cumulative ON | window 20 vs 5 | ~0.60 |
| α_01 ↔ α_03 | cumulative ON | window 20 vs 60 | ~0.50 |
| α_01 ↔ α_04 | both 20d | total vs decomposition spread | ~0.65 |
| α_01 ↔ α_05 | 20d ON sum | raw vs vol-scaled | ~0.80 |
| α_01 ↔ α_06 | 20d ON sum | raw vs attention-weighted | ~0.85 |
| α_01 ↔ α_07 | 20d ON | magnitude vs frequency | ~0.55 |
| α_01 ↔ α_08 | 20d ON | cumulative-IR vs mean-IR (≈ collinear) | ~0.95 ← intentionally close as falsification anchor |
| α_04 ↔ α_07 | 20d windows | spread vs frequency | ~0.30 (most distinct) |

α_08 is intentionally close to α_05 as a *falsification anchor* — if the two
diverge by > 0.2 Sharpe, there's an artifact.

## Expected turnover summary

| alpha | annualized turnover (rough prior) | direction |
|---|---:|---|
| α_01 | 80 % | + |
| α_02 | 220 % | + |
| α_03 | 30 % | + |
| α_04 | 90 % | + |
| α_05 | 80 % | + |
| α_06 | 110 % | + |
| α_07 | 40 % | + |
| α_08 | 80 % | + |

All 8 are within the G3 turnover band [10 %, 2000 %]; α_03 and α_07 are
deliberately on the low side as cost-tolerant fallbacks if α_01-α_02 face
cost-erosion in deployment.

## Out-of-scope

- **No volume-shock construction** — would dilute the single-mechanism rule.
- **No size-regime overlay** — that is `lottery_idio_max_q5_overlay_v1`'s
  innovation; not duplicated here. If the raw factor needs regime help we'll
  add it in Round 2 only after Round 1 numbers justify it.
- **No high/low-based features** — A-share `high`/`low` are observed at the
  noisy intraday extremes, which is exactly the leg this mechanism *isolates
  away from*.
