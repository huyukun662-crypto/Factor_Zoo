# Expressions Batch 0001 — Trend Strength (Multi-Horizon)

**Session:** `20260422_trend_technical_alpha`
**Author:** Agent 3 — Alpha Builder
**Mechanism:** trend strength via multi-horizon agreement of price-vs-MA
**Falsification anchor:** α_08 = classic 12-1 momentum (expected ≤ 0 in A-share)

All factors use **adjusted close** `P_t = close_t × adj_factor_t`, log-returns
`r_t = log(P_t / P_{t-1})`. All windows reference past data only.

---

## α_01 — Han-Zhou-Zhu trend signal (multi-MA z-score)

```
MA_k(t) = mean(P_{t-k+1..t})  for k in K = {3, 5, 10, 20, 50, 100, 200}
ratio_k(t) = P_t / MA_k(t)  - 1
trend_raw(t) = mean over k in K of ratio_k(t)
alpha_01(t) = cross-section z-score of trend_raw(t) on each trade_date
```

**Economic story:** Han-Zhou-Zhu (2016 RFS) show that aggregating
`P/MA_k` across multiple horizons produces a trend factor that beats classic
JT-momentum out of sample. We use 7 horizons spanning weekly to yearly. The
mean of (P/MA-1) is positive when price is above its own MA across most
horizons — a coherent up-trend signal.

**Expected turnover:** low. Multi-MA averages are slow-moving.

---

## α_02 — 60-day log-price trend t-stat

```
For each (ts_code, trade_date):
  y = log(P_{t-59..t})   length = 60
  x = [0,1,...,59]
  beta, beta_se = OLS(y on x)
  alpha_02(t) = beta / beta_se
```

**Economic story:** A high t-stat means the price is rising in a *statistically
consistent* fashion, not just by chance. The slope alone (without SE) is just
60-d return; dividing by SE penalizes noisy paths. This is "trend with
significance".

**Expected turnover:** medium. New bars shift both slope and SE.

---

## α_03 — 120-day log-price trend t-stat

```
Same as α_02 with window = 120.
```

**Economic story:** Longer window emphasizes medium-term trend, less sensitive
to short-term noise. Tests whether trend persistence at quarterly horizon
predicts forward returns.

**Expected turnover:** low.

---

## α_04 — MA-crossover stack

```
alpha_04(t) = sign(MA_20(t) - MA_60(t))
            + sign(MA_60(t) - MA_120(t))
            + sign(MA_120(t) - MA_252(t))
```

**Economic story:** Classic technical-analysis "golden cross" / "death cross"
reading, formalized as integer signal in [-3, +3]. +3 = aggressively bullish
across all horizons, -3 = aggressively bearish. Coarse signal but very robust
to outliers and limit days.

**Expected turnover:** low-medium. Sign-function changes are sticky.

---

## α_05 — 252-day rolling close-max proximity (52-week-high proxy)

```
max_252(t) = max(P_{t-251..t})
alpha_05(t) = P_t / max_252(t)   in (0, 1]
```

**Economic story:** George-Hwang (2004) document that stocks near their
52-week high earn higher subsequent returns; the 52-week high acts as a
psychological anchor that biases traders to under-react to good news. We
proxy with rolling close-max because we don't have intraday `high` in the
cache.

**Expected turnover:** low. Proximity to running max is sticky.

---

## α_06 — Frog-in-the-pan (60-d positive-day fraction × sign of cum-return)

```
ret_t = log(P_t / P_{t-1})
pos_frac_60(t) = mean(ret_{t-59..t} > 0)
sign_60(t) = sign(sum(ret_{t-59..t}))
alpha_06(t) = pos_frac_60(t) × sign_60(t)
```

**Economic story:** Da-Gurun-Warachka (2014 RFS) — information that arrives
gradually (high % positive days for an up-trend) is under-reacted to;
information that arrives in jumps (low % positive days, but big moves) is
over-reacted to. So gradual up-trends predict positive forward returns; jumpy
up-trends predict reversal. Multiplying by sign of cum-return gives a
directional signal.

**Expected turnover:** medium.

---

## α_07 — 120-day trend Sharpe

```
mean_120(t) = mean(ret_{t-119..t})
std_120(t)  = std(ret_{t-119..t})
alpha_07(t) = mean_120(t) / std_120(t)
```

**Economic story:** The information-ratio of a stock's own past return.
Rewards stocks that have had a positive drift with low daily noise — i.e.,
clean trends, not lottery-like volatile gainers. By construction this signal
prefers low-σ winners over high-σ winners, which is helpful in A-share where
the latter group is heavily contaminated by lottery demand.

**Expected turnover:** medium.

---

## α_08 — Classic 12-1 momentum [FALSIFICATION ANCHOR]

```
alpha_08(t) = sum(ret_{t-251..t-21})   (skip the most recent 21 days = ~1 month)
```

**Economic story:** Jegadeesh-Titman (1993) cross-sectional momentum, with
the standard 1-month skip to avoid the short-term reversal effect. **This is
included as a control, not a candidate.** We expect α_08 to be weak or
negative in A-share. If α_01-07 outperform α_08 substantially, that confirms
the trend-shape mechanism is doing real work beyond raw past-return loading.
If α_01-07 are highly correlated with α_08, the falsification has fired.

**Expected turnover:** low.

---

## Build / pipeline notes for Agent 4

1. Build adjusted close once: `P = close × adj_factor` per `(ts_code, trade_date)`.
2. Compute all 8 alphas in vectorized form (no `rolling.apply` with Python lambdas — use `sliding_window_view` or pandas built-ins).
3. Compute targets: `fwd_ret_{1,5,20,60}` with `delay = 1`, formula
   `fwd_ret_K = sum(r_{t+1+delay : t+K+delay})`.
4. **Validate**: for each alpha, check no NaN below 252 days of history, and
   check that future bars do not affect current alpha values (shuffle test).
5. Industry-neutralize alpha at evaluation time, not at construction time.
6. Save panel to `outputs/panel_trend.parquet` with columns
   `[ts_code, trade_date, industry, total_mv, alpha_01..alpha_08, fwd_ret_1, fwd_ret_5, fwd_ret_20, fwd_ret_60]`.

## Construction-time hygiene

- All windows are **trailing** (use closed bars, no peeking).
- Alpha at trade_date `t` uses bars up to and including `t`. Trading happens at `t+1` open or close depending on convention; with `delay=1`, the target is forward returns from `t+2` to `t+1+K`.
- For α_02, α_03 (regression t-stat): require ≥ window/2 non-NaN observations in the window; otherwise NaN.
- For α_05 (max_252): require ≥ 200 non-NaN observations in the trailing year; otherwise NaN.
