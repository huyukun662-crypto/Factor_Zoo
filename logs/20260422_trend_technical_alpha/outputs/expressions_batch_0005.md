# Expressions Batch 0005 — α_29 + Market Regime Overlays

**Session:** `20260422_trend_technical_alpha`
**Author:** Agent 3 — Alpha Builder
**Mechanism:** trend signal **gated** by market-regime indicator. Hold cash
when regime is "off"; deploy α_29 when regime is "on".

Motivation: α_29 (12-3 idio momentum) earns IC IR 14.5 in 5 of 6 years but
stalls in regime-shift years (2019, 2023). A regime overlay that turns the
signal off during such years could lift worst-year above the 0.5 floor.

## Regime indicators (computed per trade_date, on past data only)

- `ew_ret(t)` — cross-sectional mean of stock log-returns at t
  (equal-weight market proxy).
- `ew_cum(t) = cumsum(ew_ret)` — equal-weight market log price.
- `ew_MA200(t)` — 200-day rolling mean of `ew_cum`.
- `ew_slope_21(t) = ew_MA200(t) − ew_MA200(t−21)` — slope of 200-d MA.
- `breadth(t)` — fraction of stocks with `P(t) > MA_200_stock(t)`.
- `mkt_TS_mom(t) = sum(ew_ret over t−251..t−21)` — market 12-1 momentum.
- `mkt_disp(t)` — cross-sectional std of `ret_20` across stocks at t.
- `mkt_vol_60(t)` — 60-day rolling std of `ew_ret`.

All gates are computed at end-of-day t and applied to next-month positions
(consistent with delay=1 execution).

## α_33 — uptrend gate
`α_33(s, t) = α_29(s, t) × 1{ew_slope_21(t) > 0}`. Trade only when the
equal-weight market 200d MA is sloping up.

## α_34 — breadth gate
`α_34(s, t) = α_29(s, t) × 1{breadth(t) > 0.5}`. Trade only when more than
half of stocks are above their own 200d MA.

## α_35 — dispersion gate
`α_35(s, t) = α_29(s, t) × 1{mkt_disp(t) > median_252(mkt_disp)}`. Momentum
needs cross-sectional dispersion to work — gate on relative dispersion.

## α_36 — market TS-momentum gate
`α_36(s, t) = α_29(s, t) × 1{mkt_TS_mom(t) > 0}`. Only deploy when market
itself shows 12-1 momentum.

## α_37 — calm-market gate
`α_37(s, t) = α_29(s, t) × 1{mkt_vol_60(t) < median_252(mkt_vol_60)}`. Only
deploy in below-median market vol regimes.

## α_38 — continuous gate (softmax overlay)
`weight(t) = sigmoid(z_score_252(regime_score))` where
`regime_score = ew_slope_21 + breadth − 0.5 + sign(mkt_TS_mom)`. Scaled
between 0 and 1, smooth instead of binary.

## α_39 — combined hard gate
`α_39 = α_29 × 1{ew_slope_21 > 0 AND breadth > 0.4}`. Both market trend up
and breadth healthy.

## α_40 — adaptive gate (whichever single gate had best worst-year)
Materialized as `α_29 × 1{best gate from α_33..α_37 trial}`. Selected after
running α_33..α_37 on training period; for honesty we report it as
*ex-post-best* and treat with appropriate suspicion.

## Gating mechanics

When gate(t) = 0:
- LS portfolio holds 0% (cash).
- Q5 long-only excess vs equal-weight returns 0.
- **Turnover at boundary**: liquidate (tov = 1) when transitioning on→off,
  enter (tov = 1) when transitioning off→on. Cost charged accordingly.
- Within-off regime, position is flat, cost = 0.
- Within-on regime, normal monthly turnover applies.

This is the proper way to charge cost for a binary gate. Avoids the
"free regime gate" artifact.

## Decision logic

If any α_33..α_40 achieves:
- worst-year LS Sharpe ≥ 0.5 AND
- test LS Sharpe ≥ 1.0 AND
- test Q5 excess IR ≥ 0.5

then the trend family has a deployable candidate (the gated version of
α_29). Otherwise RESEARCH-ONLY stands.
