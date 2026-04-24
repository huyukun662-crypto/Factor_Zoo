# Alpha Ranking — Weekly TQPB for V7_gold combine

**Session:** `20260423_a_share_etf_weekly_tqpb_v1`
**Agent:** 5 (Evaluator & Recorder)
**Date:** 2026-04-23

---

## 1. Single-round verdict

| | |
|---|---|
| **Best combine candidate** | `r1_breakout_vol_conf` LS top-5/bot-5 |
| **Combine spec** | `V7_gold_pnl × 0.85 + new_LS_pnl × 0.15` |
| **Combined Sharpe** | **+1.79** (vs V7 baseline 1.73, Δ +0.06) |
| **Combined MaxDD** | **−7.7%** (vs V7 −9.1%) |
| **Correlation with V7** | **−0.009** (truly orthogonal) |
| **Verdict** | **RESEARCH-ONLY**, deploy as 15% overlay at your own risk |

## 2. Why standalone signals can't beat V7_gold

V7_gold is Sharpe 1.73 on the sample. Our 8 weekly signals have standalone
LS Sharpes 0.04 to 0.51. None reaches the 0.5 floor cleanly (`r1_pullback_in_uptrend`
LS +0.51 is the only one). **A 50/50 blend dilutes V7 every time.** The
right combine spec is an OVERLAY at ~15% vol contribution, not an equal-
weight ensemble.

## 3. Ranked by "V7_gold combine value"

| rank | expression | combine corr | LS Sh | optimal w_V7 | **combo Sharpe** | MaxDD | note |
|---:|---|---:|---:|---:|---:|---:|---|
| 1 | **r1_breakout_vol_conf** | **−0.009** | +0.45 | 0.85 | **+1.79** | **−7.7%** | orthogonal alpha, defensive |
| 2 | r1_pullback_in_uptrend | +0.10 | +0.43 | 0.925 | +1.75 | −8.4% | sparse, low-TO, small lift |
| 3 | r1_trend_sharpe_60d    | +0.17 | +0.29 | 0.95 | +1.71 | −8.6% | redundant with V7 mom |
| 4 | r1_low_drawdown_20d    | +0.32 | +0.36 | 0.95 | +1.70 | −8.6% | too correlated with V7 |
| 5 | r1_kitchen_sink        | +0.30 | +0.22 | 0.95 | +1.68 | −8.6% | ensemble underperforms best single |
| 6 | r1_rel_strength_zscore | +0.23 | +0.10 | 0.95 | +1.68 | −8.6% | weak standalone |
| 7 | r1_vol_adj_mom_4w      | +0.27 | +0.20 | 0.95 | +1.68 | −8.6% | essentially the same as V7 mom_4w |
| 8 | r1_trend_sharpe_20d    | +0.28 | +0.20 | 0.95 | +1.68 | −8.6% | weakest of the batch |

## 4. Why `r1_breakout_vol_conf` is the interesting one

**Formula** (before demean):
```
(close − max_high_20d) / std_20d   × I[close ≥ max_high_20d AND vol_5d/vol_20d > 1.2]
```

In plain terms: **how far above the 20-day high the close is, normalized
by 20-day vol, and only if confirmed by >20% volume surge**.

Why it's orthogonal to V7_gold:
- V7 uses `mom_4w` (magnitude over a 20-day window): captures AVERAGE trend.
- This signal captures **BREAKOUT events** — rare, sharp, volume-confirmed
  upward moves. It fires on only ~2% of ETF-weeks.
- V7 has no volume component in Leg A (penalty on turnover, not volume
  surge); Leg G is group-level momentum.
- Correlation −0.009 is not accidental; the two capture genuinely
  different regimes.

Why it helps specifically in V7's weak years:
- In momentum-coherent rallies (2020, 2021), breakout confirmations are
  frequent and V7 catches them via mom_4w → overlay is redundant.
- In choppy / regime-transition years (2022, 2023), V7's mom_4w pivots
  and loses. Breakout signal is sparser but when it fires, it's on the
  real leaders (volume confirms). That's when the overlay adds lift.

## 5. Recommended deployment spec

```python
# Pseudo-code
weekly_pnl_combined[t] = 0.85 * v7_gold_pnl[t] + 0.15 * breakout_ls_pnl[t]

# Where breakout_ls_pnl is from:
signal[i,t] = max(0, (close[i,t] - max_high_20[i,t]) / std_20d[i,t])
            * I[close[i,t] >= max_high_20[i,t] AND vol_5d[i,t] / vol_20d[i,t] > 1.2]
signal[i,t] = xs_demean(signal[i,t])

# Weekly rebalance (Fri close, T+1 Mon execute)
# Long top-5, short bottom-5, equal-weight each leg
# Cost: 5 bps/side (matches V7)
# Annual turnover: ~94% (very cost-efficient due to sparse trigger)
```

Expected metrics (based on 2019-2026 backtest):
- Sharpe: 1.79 (vs V7 baseline 1.73)
- Annual return: ~27% (vs V7 ~30%)
- MaxDD: −7.7% (vs V7 −9.1%)
- Biggest help: V7's weakest years (+0.23 Sharpe in 2022)

## 6. Limitations / risks

1. **Sharpe lift is within noise.** ΔSharpe 0.06 on 377 weeks is not
   statistically significant (t-stat ≈ 0.5). We recommend deployment
   because of DEFENSIVE characteristics (MaxDD reduction, 2022 rescue),
   not headline Sharpe.
2. **NaN IC.** Standard IC-based quality checks don't work on sparse-
   trigger signals. The signal passed validation via LS PnL metrics
   only, which is a weaker form of confidence.
3. **2025 slight loss** (−0.21 Sharpe). In strong-momentum years, the
   overlay's breakout signal overlaps with V7's trend picks, and the
   15% allocation to a lower-Sharpe sub-book creates a small drag.
4. **Short-leg risk.** The LS version carries market-neutral exposure;
   if the short-leg book concentrates in a laggard sector that rallies
   unexpectedly (e.g., gold ETF in a risk-off spike), the overlay can
   contribute a −5% weekly loss.
5. **Universe overlap with V7.** This overlay uses V7's exact 34-ETF
   universe, so it's not adding new asset-level diversification — it's
   adding signal-level diversification. If the universe is constrained,
   combining with an out-of-universe asset (HK ETF, gold, bonds) would
   likely add more defensive benefit.

## 7. Round 2 suggestions

1. **Long-only top-3 variant of breakout_vol_conf**. Eliminates the
   short-leg tail risk. Might clock similar defensive benefit at lower
   vol.
2. **Signal-level fusion into V7**: replace V7's `0.3 × breadth` term
   with `0.15 × breadth + 0.15 × z(breakout_vol_conf)`. Backtest the
   modified V7 directly; if the Sharpe lift is similar (+0.06), we've
   pulled the alpha into V7's chassis and removed the overlay complexity.
2. **Regime-conditional overlay**: activate the 15% breakout overlay
   ONLY when V7's breadth z-score < 0 or market vol > 20%. Expected to
   preserve the 2022 lift while avoiding the 2025 drag.
4. **Extend universe**: add 10-15 broad-index ETFs (510300, 510500,
   510050, 510180, 588000, 588080, ...). Cross-section of 44-49 should
   sharpen both IC and portfolio construction.

## 8. Workflow dogfood

### What worked

- **LS-mode combine analysis** (§4.1): long-only combine told us the
  wrong story (all correlated, all dilutive); LS-mode revealed the real
  orthogonality signature. Lesson: **always compute combine correlation
  in market-neutral mode, even if the target strategy is long-only**.
- **Per-year decomposition of combine Sharpe**: the 2022 +0.23 lift was
  invisible at the headline level but became the main story once per-
  year was added. Should be a default Agent 4 deliverable for any
  combine-mode session.
- **Grid search over blend weight**: 50/50 was the wrong benchmark; the
  optimal (85/15 or 92.5/7.5) reveals the true value of the signal.
  Consider making this a standard deliverable in session_metadata when
  a `combine_target` is specified.

### What did not work

- **G4 corr_vs_uew gate** is the wrong invariant for long-only weekly
  factors on an ETF basket (it fails 8/8 by construction). Suggest
  adding a `strategy_spec` field to G4 thresholds in
  `references/validation-gates.md` — LS spec uses the current 0.85
  floor, long-only spec uses a higher floor (0.97) or skips this check.
- **IC-based ranking** broke for `r1_breakout_vol_conf` (NaN IC from
  sparse trigger). Sparse-trigger signals need a different evaluation
  protocol (LS PnL on triggered subset, bootstrap-adjusted Sharpe).
- **50/50 ensemble as default combine spec** was misleading. A
  high-Sharpe strategy combined 50/50 with a low-Sharpe strategy always
  dilutes — regardless of correlation. Recommend documenting in
  `references/` that combine mode should default to vol-matched or
  grid-optimal weighting.

## 9. Files

See `outputs/backtest_results_batch_0001.md` for full file index.
