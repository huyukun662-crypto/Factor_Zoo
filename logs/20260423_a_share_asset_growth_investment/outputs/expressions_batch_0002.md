# Expressions Batch 0002 — Asset Growth Round 2 refinements

**Session**: 20260423_a_share_asset_growth_investment
**Round**: 2
**Agent**: 3 Alpha Builder
**Parent signal**: `f5_ag_2y_ind` (Round 1 winner: IC t-stat 17.08 at h=60, LS Sharpe 0.825)

## Round 1 failure diagnosis

The mechanism is **validated** (IC is real, 5 of 6 years positive) but the **packaging failed**:
- Monthly rebal (21d) mismatches IC peak horizon (60d)
- LS short leg destroyed in 2020 bull run (Pitfall 7) → worst year -1.24
- No regime awareness; fires when 6m market momentum is extremely positive

Round 2 keeps the same dominant mechanism (Asset Growth / investment anomaly) and explores **deployment packaging** along 4 dimensions.

## Refinement dimensions

1. **Horizon match**: quarterly rebal (63 trading days) instead of monthly (21)
2. **Short-leg removal**: long-only Q5 (or Q10) with equal/rank weighting
3. **Regime filter**: disable long position when CSI300 6m return > 20% (bull-market kill switch)
4. **Liquidity floor**: restrict universe to top 60% by circ_mv
5. **Size residualization**: OLS residualize factor vs log(total_mv) (proper, not median-demean)

## 8 expressions (Rule of 8)

All are built on the same underlying `ag_2y_ind` raw signal (2-year YoY total-asset growth, industry-demeaned, PIT-lagged).

| # | name | rebal | portfolio | filters | size treatment | note |
|---|------|-------|-----------|---------|----------------|------|
| 1 | `r2_q5_ew_q` | 63d | long-only Q5 equal-weight | — | none | Minimal refinement — only rebal freq changed; direct comparison to Round 1 |
| 2 | `r2_q5_rw_q` | 63d | long-only Q5 rank-weighted within Q5 | — | none | Higher conviction on top names |
| 3 | `r2_q5_ew_q_regime` | 63d | long-only Q5 equal-weight | CSI300 6m < 20% | none | Regime filter ON |
| 4 | `r2_q5_ew_q_liqfl` | 63d | long-only Q5 equal-weight | top 60% circ_mv | none | Liquidity floor |
| 5 | `r2_q5_ew_q_sresid` | 63d | long-only Q5 equal-weight | — | OLS residualize vs log(total_mv) | Replace Round 1's failed f3 double-demean |
| 6 | `r2_q10_ew_q` | 63d | long-only Q10 (top decile) equal-weight | — | none | Higher selectivity: top 10% only |
| 7 | `r2_q5_ew_q_combo` | 63d | long-only Q5 equal-weight of composite(0.6·f5 + 0.4·f2) | — | none | Blend 2y + 1y AG for slight diversification |
| 8 | `r2_q5_ew_q_all` | 63d | long-only Q5 equal-weight | regime + liqfl | OLS size-resid | All filters stacked (best-effort packaging) |

## Market-regime proxy (for #3 and #8)

```python
# Cross-sectional EW average of fwd_ret_1 reversed into market return (proxy for CSI300)
mkt_daily = panel.groupby("trade_date")["fwd_ret_1"].mean().shift(1)  # today's ret = yesterday's fwd_ret_1
mkt_126d_ret = (1 + mkt_daily).rolling(126).apply(np.prod) - 1      # 6-month rolling market return
regime_on = mkt_126d_ret <= 0.20                                     # filter OFF when mkt 6m > 20%
```

## Size residualization (for #5 and #8)

Per-date cross-sectional OLS:
```python
for date, g in panel.groupby("trade_date"):
    x = np.log(g["total_mv"].clip(lower=1))
    y = g["ag_2y_ind"]
    # residualize y = a + b*x + eps, keep eps
    mask = x.notna() & y.notna()
    if mask.sum() < 30: continue
    b, a = np.polyfit(x[mask], y[mask], 1)
    resid = y - (a + b*x)
    panel.loc[g.index, "ag_2y_ind_sresid"] = resid
```

## Hard-floor targets (from session_metadata.yml)

Round 2 is Q5 long-only excess (not LS), so the relevant floors are:
- **Headline Sharpe (Q5-excess after 5bps)** ≥ 0.8
- **Worst-year Sharpe** ≥ 0.0 (relaxed from 0.5 because long-only excess is fundamentally 1-sided)
- **Best-year-out Sharpe** ≥ 50% of headline
- **IC t-stat** ≥ 3 (easier than Round 1; already at 17)
- **Annual turnover** ≤ 200% (quarterly rebal should comfortably meet this)

## Handoff to Agent 4

- Same panel (no re-pull); reuse Round 1 PIT merge
- Save computed `ag_2y_ind` to `.cache/panel_ag_r2.parquet` for future rounds
- Report: per-variant Sharpe Q5-excess, worst year, best-year-out, IC t-stat, annualized turnover
