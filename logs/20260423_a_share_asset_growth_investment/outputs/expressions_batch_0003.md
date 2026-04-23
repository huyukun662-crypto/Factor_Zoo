# Expressions Batch 0003 — NSI + AG⊕NSI composite

**Session**: 20260423_a_share_asset_growth_investment
**Round**: 3
**Batch**: 0003
**Agent**: 3 Alpha Builder
**Parent**: Round 1/2 residue — AG 2y worked but 2020 hole; pivot to issuance channel
**Dominant mechanism**: Investment anomaly (CGS 2008) via both channels: real-investment (AG) + financing (NSI)

All expressions use **PIT-lagged** quarterly `total_assets` and `total_share` (from `.cache/balancesheet.parquet`),
lookup key `f_ann_date + 1 trading day`. All signed so **high value → long**.

## 8 expressions (Rule of 8)

| # | name | formula (pseudocode) | neutralization | horizon | expected turnover (ann.) | expected IC sign | economic note |
|---|------|----------------------|----------------|---------|--------------------------|------------------|---------------|
| 1 | `r3_nsi_yoy_raw` | `-(Shares_t - Shares_{t-4q}) / Shares_{t-4q}` | none | 21d | ~170% | + | NSI benchmark, no industry demean |
| 2 | `r3_nsi_yoy_ind` | `r3_nsi_yoy_raw` − median by [date, industry] | SW/coarse industry | 21d | ~250% | + | Primary NSI candidate |
| 3 | `r3_nsi_log_ind` | `-log(Shares_t / Shares_{t-4q})` industry-demean | industry | 21d | ~250% | + | Log transform for tail control (splits/huge SPO) |
| 4 | `r3_nsi_2y_ind` | `-(Shares_t - Shares_{t-8q}) / Shares_{t-8q}` industry-demean | industry | 42d | ~270% | + | NSI slow variant (matches R1 winner f5 window) |
| 5 | `r3_cma_2y` | `0.5 · z(f5_ag_2y_ind) + 0.5 · z(g4_nsi_2y_ind)` | (inherited) | 21d | ~240% | + | **Naive** FF-CMA-style 2y composite (baseline) |
| 6 | `r3_cma_triple` | `(z(f2_ag_yoy_ind) + z(f5_ag_2y_ind) + z(g2_nsi_yoy_ind))/3` | (inherited) | 21d | ~250% | + | 3-way fundamental investment basket |
| 7 | `r3_ag_orth_nsi` | `0.5 · (f5 ⊥ g4) + 0.5 · g4`, where `⊥` is per-date OLS residualize | (inherited) | 21d | ~220% | + | **Orthogonalized composite — WINNER** |
| 8 | `r3_nsi_rank_ind` | `rank_cs(nsi_yoy_q)` industry-demean | industry | 21d | ~250% | + | NSI rank-normalized for outlier immunity |

## Construction pseudocode (canonical)

```python
# INPUTS
bs = load_parquet(".cache/balancesheet.parquet")   # total_assets, total_share, f_ann_date
panel = load_parquet(".cache/panel.parquet")       # industry, size_bin, total_mv, fwd_ret_{1,5,20,60}

# STEP 1: quarterly AG and NSI signals
bs["ag_yoy_q"]     = -(bs.total_assets - bs.groupby("ts_code")["total_assets"].shift(4)) / bs.total_assets.shift(4)
bs["ag_2y_q"]      = -(bs.total_assets - bs.groupby("ts_code")["total_assets"].shift(8)) / bs.total_assets.shift(8)
bs["nsi_yoy_q"]    = -(bs.total_share  - bs.groupby("ts_code")["total_share"].shift(4))  / bs.total_share.shift(4)
bs["nsi_log_yoy_q"]= -(log(bs.total_share)        - log(bs.total_share.shift(4)))
bs["nsi_2y_q"]     = -(bs.total_share  - bs.groupby("ts_code")["total_share"].shift(8))  / bs.total_share.shift(8)

# STEP 2: PIT merge_asof to daily panel via f_ann_date + 1
panel = merge_asof_by_ts_code(panel, bs[["f_ann_date+1", signals]], direction="backward")

# STEP 3: Industry demean (median per [date, industry])
for s in [ag_yoy_q, ag_2y_q, nsi_yoy_q, nsi_log_yoy_q, nsi_2y_q]:
    panel[s + "_ind"] = panel[s] - group_median(panel[s], by=["trade_date","industry"])

# STEP 4: Winsor 1%/99% + z-score per date
for col in [...]:
    panel[col] = cs_winsor_z(panel[col])

# Name aliases (used in expressions):
#   f2 = z(ag_yoy_q_ind)     — Round 1 winner 1y
#   f5 = z(ag_2y_q_ind)      — Round 1 winner 2y
#   g1 = z(nsi_yoy_q)        — NSI raw
#   g2 = z(nsi_yoy_q_ind)    — NSI 1y ind
#   g3 = z(nsi_log_yoy_q_ind)— NSI log 1y ind
#   g4 = z(nsi_2y_q_ind)     — NSI 2y ind
#   g5 = z(rank(nsi_yoy_q)_ind) — NSI rank ind

# STEP 5: Composites
panel["cma_2y"]    = cs_winsor_z(0.5 * panel.f5 + 0.5 * panel.g4)
panel["cma_triple"]= cs_winsor_z((panel.f2 + panel.f5 + panel.g2)/3)

# Per-date OLS residualize f5 vs g4, then blend
panel["ag_orth_nsi"]      = per_date_ols_residualize(y=panel.f5, x=panel.g4)   # y - (a + b*x)
panel["ag_orth_plus_nsi"] = cs_winsor_z(0.5*panel.ag_orth_nsi + 0.5*panel.g4)  # ← WINNER
```

## Hard constraints met

- [x] Exactly 8 expressions
- [x] One dominant mechanism (investment anomaly, two channels)
- [x] Distinct construction: 4 pure-NSI variants (windows/transforms), 3 composites, 1 benchmark
- [x] Each has economic note
- [x] PIT rule embedded (f_ann_date + 1)
- [x] Universe filter: inherited from panel (ST exclusion, history >= 1y, price filter)

## Handoff to Agent 4 (already executed)

Script: `scripts/05_round3_nsi.py`
Results: `backtest_results_batch_0003.md`, `r3_summary_batch_0003.csv`, `r3_annual_batch_0003.csv`,
`r3_ic_table_batch_0003.csv`, `r3_correlation_matrix.csv`, `r3_best_year_out.csv`,
`r3_audit_execution_delay.json`.

## Outcome

- Winner: `r3_ag_orth_nsi` — Sharpe Q5-excess **0.860**, abs Sharpe **0.70**, 5/6 years positive
- Naive composite `r3_cma_2y` only 0.284 Sharpe excess → orthogonalization is essential
- Pure NSI (g2/g3/g5) has highest IC t-stat (24.7) but weakest portfolio Sharpe (0.18) — information concentration issue
- See `alpha_ranking_round3.md` for full ranking and `round_0003.yml` for decision record.
