# Alpha Ranking — Batch 0001

**Session**: 20260423_a_share_asset_growth_investment
**Agent**: 5 Evaluator & Recorder
**Decision**: **RESEARCH-ONLY** — hard floors not met

## Ranking

| Rank | Factor | IC t-stat (h=60) | Sharpe LS (full) | Sharpe Q5-excess | Worst Year LS | Worst Year Q5-excess |
|------|--------|------------------|------------------|------------------|---------------|----------------------|
| 1 | **f5_ag_2y_ind** | **17.08** | **0.825** | **0.594** | -1.24 | -0.64 |
| 2 | f2_ag_yoy_ind | 12.70 | 0.637 | 0.299 | -1.71 | -1.54 |
| 3 | f8_ag_composite | 12.70 | 0.651 | 0.311 | -1.67 | -1.54 |
| 4 | f4_ag_log_yoy_ind | 12.70 | 0.655 | 0.319 | -1.69 | -1.58 |
| 5 | f1_ag_yoy_raw | 12.86 | 0.619 | 0.395 | -1.59 | -1.41 |
| 6 | f7_ag_rank_ind | 11.65 | 0.524 | 0.286 | -1.91 | -1.76 |
| 7 | f3_ag_yoy_ind_size | 10.30 | 0.241 | -0.471 | -2.44 | -2.14 |
| 8 | f6_ag_qoq_ind | 1.96 | -0.032 | -0.247 | -2.45 | -2.26 |

## Hard-floor check (from session_metadata.yml)

| Criterion | Target | Best candidate (f5) | Pass? |
|-----------|--------|---------------------|-------|
| Test-window Sharpe (5bps) | ≥ 1.0 | 0.825 (full sample) | ❌ |
| Worst-year LS Sharpe | ≥ 0.5 | -1.24 | ❌ |
| Best-year-out Sharpe | ≥ 50% headline | n/a (already failed above) | ❌ |
| IC t-stat (Test) | ≥ 2.5 | 17.08 (h=60) | ✅ |
| Execution-delay audit | PASSED | PASSED | ✅ |
| Look-ahead audit (future-perturbation) | PASSED | PASSED | ✅ |

**Verdict**: 2 of 5 hard floors pass → **RESEARCH-ONLY**.

## What the data actually says

1. **IC is unambiguously real**: f5_ag_2y_ind shows IC t-stat = 17.08 at h=60, IC mean = 4.38% — Spearman-rank-IC this clean over 5.3 years is not noise.

2. **The signal is slow**: IC increases monotonically with horizon for every non-broken variant. This is textbook fundamental-factor behavior — monthly rebal at 21d is **too fast**; the signal's natural horizon is 60-120 days.

3. **The catastrophic worst year is 2020, not a tail event**: all 8 factors are negative in 2020 (Sharpe -0.6 to -2.5). This is the **bull-market short-leg destruction pattern** (Pitfall 7 from `common-pitfalls.md`) — small-cap high-growth names went parabolic on liquidity, and AG's short leg was precisely these names.

4. **2021-2023 is very strong**: 1.0-2.3 Sharpe LS across all surviving factors. The mechanism works in normal/bear regimes.

5. **2024-2025 weakness**: partially confirmed the research brief's 2024 policy-M&A concern. 2025 YTD is particularly weak — flag for round 2.

6. **Double-demean (f3) destroys signal**: subtracting size-quintile median on top of industry wipes out ~60% of IR. The AG signal is **partially a size proxy** — but that's a feature of the anomaly (CGS 2008 show small-firm effect is the primary channel), not a bug.

7. **QoQ (f6) is noise**: quarterly seasonality dominates. Avoid single-quarter differencing for AG.

## Economic interpretation

The findings replicate the classic CGS 2008 pattern but reveal A-share's regime dependence: **investment anomaly is a bear-market factor**. The deployable form is NOT dollar-neutral LS (the short leg is unhireable in A-share and gets destroyed in bull years), but a **long-only low-AG tilt**. Even then, the headline numbers are modest.

## Decision: RESEARCH-ONLY, with refinement plan

### Why not PROMOTE
- Full-sample headline Sharpe 0.825 is below the 1.0 hard floor.
- Worst-year LS Sharpe -1.24 is catastrophically below the 0.5 floor.
- Adversarial question "if Sharpe is wrong by 50%, what's the cause?" — answer: the 2021-2023 window dominates, best-year-out would likely destroy the number. Didn't compute because the worst-year floor already fails.

### What to try in Round 2 (refinement, not pivot)
1. **Quarterly rebalance** (63 trading days) instead of monthly. IC is strongest at h=60, so reb freq should match horizon.
2. **Long-only Q5 of f5_ag_2y_ind with rank-based weighting, not quintile**. Avoid short leg entirely.
3. **Regime filter**: add on-off switch based on 6-month CSI300 return (off when market is bull); accept fewer trades for higher per-trade quality.
4. **Liquidity floor**: restrict to top 60% by circ_mv (cap-weighted AG deployment reduces tiny-cap noise that drives 2020 short-leg destruction).
5. **Residualize against size**: even though f3's double-demean hurt, a proper regression residualization (not median-demean) on log(total_mv) might preserve more signal.

### What to try in Round 3 (pivot to sibling mechanism)
- **Net Share Issuance** (NSI) — `-Δ(total_share) / total_share`. More directly captures the "dilution" channel of CGS 2008, and the data is cached.
- **Combine** winner of NSI with winner of AG into a composite investment factor. Historically (Fama-French CMA) the composite Sharpe is 50-80% higher than either leg.

## Orthogonality to prior sessions

- vs `20260420_fundamental_accruals_alpha`: mechanism is **investment**, theirs was **earnings quality / accruals**. Signals correlate weakly (both are balance-sheet-ratio anomalies) but channels are distinct. Should combine in a later session.
- vs `20260421_volprice_max_lottery`, `20260422_trend_technical_alpha`, etc.: fundamental vs price-based — orthogonal by construction.

## Artifacts produced

```
outputs/
├── research_brief.md            (Agent 1)
├── session_metadata.yml         (Agent 2)
├── expressions_batch_0001.md    (Agent 3)
├── ic_table_batch_0001.csv
├── ls_summary_batch_0001.csv
├── ls_annual_batch_0001.csv
├── audit_execution_delay.json
├── backtest_results_batch_0001.md
├── alpha_ranking.md             (this file)
├── round_0001.yml
└── final_summary.md
working/
├── handoff_1_to_2.json
├── handoff_2_to_3.json
├── handoff_3_to_4.json
└── handoff_4_to_5.json
```
