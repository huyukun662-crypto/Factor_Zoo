# Expressions — Batch 0001 (Weekly TQPB for V7_gold combine)

**Session:** `20260423_a_share_etf_weekly_tqpb_v1`
**Agent:** 3 (Alpha Builder)
**Primary horizon:** k = 5 trading days (1 week forward)
**Horizon grid:** {5, 10, 20}
**Rebalance:** weekly (Fri close, T+1 execute Monday) — same as V7_gold
**Universe:** 34 A-share thematic ETFs (V7_gold universe, staggered 12w)
**Execution delay:** 1 bar; target = `log(close[t+1+k]) - log(close[t+1])`
**Neutralization:** universe-EW cross-sectional demean per date

| id | axis | rationale | formula (before demean) |
|---|---|---|---|
| r1_trend_sharpe_20d    | trend quality | Moskowitz-Ooi-Pedersen 2012: path Sharpe, not magnitude | `mean(ret_d[-20..0]) / std(ret_d[-20..0]) * √252` |
| r1_trend_sharpe_60d    | trend quality long | longer horizon trend Sharpe | `mean(ret_d[-60..0]) / std(ret_d[-60..0]) * √252` |
| r1_pullback_in_uptrend | pullback overlay | R2 RSI finding + trend filter | `(40-RSI14) * I[RSI14<40] * I[mom_20d>0]` |
| r1_vol_adj_mom_4w      | vol-adj momentum | orthogonalize V7's mom_4w by vol | `mom_20d / std_20d` |
| r1_rel_strength_zscore | rel strength | cross-sectional z-score of mom_20d | `xs_zscore(mom_20d)` |
| r1_low_drawdown_20d    | drawdown quality | AQR QMJ-style quality: shallow DD = strong trend | `(close - max_close_20d) / max_close_20d` (≤ 0) |
| r1_breakout_vol_conf   | breakout | volume-confirmed 20d high breakout | `clip((close-max_high_20)/std_20d, ≥0) * I[close≥max_high_20 ∧ vol5/vol20>1.2]` |
| r1_kitchen_sink        | ensemble | robust rank combo of 1-7 | `mean(rank(e_i))` |

Rule of 8 ✓. Universe-EW demean per date.
