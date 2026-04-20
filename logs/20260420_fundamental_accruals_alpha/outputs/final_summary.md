# Final Summary — 20260420_fundamental_accruals_alpha  (Session complete, 4 rounds)

**Topic:** 基本面因子挖掘 — 应计项目 / 盈余质量 (Sloan 1996)
**Workflow:** worldquant-5-agent-workflow
**Final flagship:** `accruals_median_ttm_ind_neutral_v2` (= `alpha_med_ind`, = Round 4 v1_baseline)
**Disposition:** **SESSION CLOSED.** Deploy flagship to paper trading with corrected expectations.

---

## 1. Corrected deployment headline  (Round 4 cost-model fix)

| metric | value |
|--------|------:|
| Full LS net Sharpe (2018-2025) | **1.32** |
| Full LS net ann return | 10.2 % |
| Full Q5 long-only net IR | 1.11 |
| Full Q5 long-only net ann excess | 4.4 % |
| Max drawdown | −1.8 % |
| Worst-year Sharpe (2022) | 1.33 |
| ICIR@20d / ICIR@60d | 0.44 / 0.94 |
| Avg turnover per rebalance (Q5 side) | 9.7 % |
| Per-rebalance cost (LS) | ~1.9 bps |
| **Test Sharpe (2024-2025 YTD)** | **0.95 LS / 0.87 Q5 IR** |

**Note the correction vs Round 3.** Earlier rounds applied a flat 20 bps/rebalance cost (assumed 100 % turnover). Actual turnover is ~10 %; true cost is ~1.9 bps. Round 4 uses turnover-aware cost. This alone lifts LS Sharpe from 1.03 → 1.32 with **no change to the factor**.

## 2. Four-round arc

| round | question | batch | winner | outcome |
|------:|----------|------:|--------|---------|
| 1 | Discover a fundamental mechanism | 8 expressions on accruals family | alpha_03 (sum-TTM ind-neutral) | promoted; sharpe 1.38 on 2020-2025 |
| 2 | Refine the mechanism | 8 refinement variants + residualization | alpha_v5 (median-TTM ind-neutral) | supersedes; sharpe 1.57 on 2020-2025 |
| 3 | Extend window & attribute | 2 × 4 factorial on 2018-2025 | alpha_med_ind (same as v5) | confirmed; sharpe 1.03 on 2018-2025 (Round 3 cost model) |
| 4 | Deployment robustness | 8 smoothing / turnover variants | v1_baseline (same as alpha_med_ind) | kept; corrected cost gives sharpe 1.32 |

Factor identity stayed the same from Round 2 onward. Rounds 3 and 4 sharpened the honest expectations: Round 3 stress-tested on 2018, Round 4 fixed the cost model.

## 3. The single most important line in this session

**Round 1 Librarian caveat #2 was the pivot point.** The caveat flagged "Tushare BS-method restatement noise". Round 1.5 verified it when alpha_02 (BS-method WCA) collapsed with −60 % drawdown. Round 2 v5 (median-TTM) operationalized the fix and jumped the Sharpe. Round 3 confirmed median-TTM still dominates on 2018-2025. That caveat → factor-design decision → empirical victory chain is exactly what a 5-agent pipeline is supposed to produce.

## 4. Mandatory audits — final state

| audit | status | round verified |
|-------|--------|---------------:|
| Rule of 8 | ✅ | 1, 2, 3, 4 |
| One-mechanism | ✅ | all rounds |
| Execution-delay structural | ✅ | 1.5 |
| Look-ahead shuffle | ✅ 229× signal-to-noise | 3 |
| Worst-year floor ≥ 0.5 | ✅ 1.33 | 3 |
| Best-year-out ≥ 50 % | ✅ 92 % | 3 |
| Falsification-first pub-lag | ✅ ratio 0.99 | 2 |
| Residualization vs classics | ✅ 96 % kept | 2A |
| Cost model sanity | ✅ turnover-aware (Round 4 fix) | 4 |

## 5. Hard-won learnings (for the factor library)

1. **Always use median-TTM on A-share fundamentals.** Tushare restatement noise is large.
2. **Industry is the one neutralization that matters** for A-share quality signals. Size alone does nothing; double-neut over-slices.
3. **Use CFS-method (NI − CFO), not BS-method.** The BS-method variant failed catastrophically.
4. **Use ann_date, not end_date.** Publication-lag test showed both give similar IC on this factor, but the structural discipline is non-negotiable — other factors will leak.
5. **Turnover-aware cost model matters.** Flat 20 bps/rebalance over-penalizes low-turnover fundamentals by 10× and makes the factor look 30 % worse than it is. Always measure actual turnover.
6. **Benign windows lie.** 2020-2025 Sharpe 1.57 dropped to 1.03 (Round 3) then recovered to 1.32 (Round 4 cost fix). Always extend, always audit cost assumptions.
7. **Smoothing has diminishing returns on already-slow signals.** `alpha_med_ind` is monthly-stable; EMA / sticky-band buy marginal turnover reduction, not meaningful alpha.
8. **Stop when the factor is characterized.** Round 4 was the "one more round" that correctly returned "no new winner" — the signal the mechanism is saturated and the next session should attack a different mechanism.

## 6. File manifest (final)

```
logs/20260420_fundamental_accruals_alpha/
├── inputs/objective.md
├── working/ handoff_{1..4}.json + handoff_5_round{2,3,4}.json
├── outputs/
│   ├── research_brief.md                          # R1
│   ├── session_metadata.yml                       # R1
│   ├── expressions_batch_{0001,0002,0003,0004}.md
│   ├── backtest_results_batch_{0001,0002,0003,0004}.md
│   ├── alpha_ranking.md                           # final leader-board
│   ├── final_summary.md                           # this file
│   ├── ic_table_batch_{0001,0002,0003}.csv
│   ├── ls_summary_batch_{0001,0002,0003,0004}.csv
│   ├── ls_annual_batch_{0001,0002,0003}.csv
│   ├── tvt_split_batch_{0003,0004}.csv
│   ├── audit_{worst_year_best_out,residualization,v5_winner,batch_0002}.{csv,json}
│   ├── audits.json
│   ├── correlation_matrix.csv
│   ├── test_set_alpha_med_ind.csv
│   ├── test_set_metrics_full.csv
│   └── round4_winner_port_*.csv
├── scripts/ 01..10
├── round_000{1,2,3,4}.yml
└── run_state.json
```

## 7. One-sentence takeaway

**After 4 rounds and 32 tested expressions, the Factor_Zoo fundamental flagship is `accruals_median_ttm_ind_neutral_v2`: median-TTM industry-neutral Sloan accruals on A-share, with turnover-aware-cost-model Sharpe 1.32 (LS net) and IR 1.11 (Q5 long-only), max drawdown −1.8 % over 2018-2025 and every mandatory audit passed — deploy to paper trading at target LS Sharpe 1.2 and Q5 IR 1.0 after selection-bias adjustment, then open new sessions for SUE/PEAD and gross profitability.**
