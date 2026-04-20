# Final Summary — 20260420_fundamental_accruals_alpha  (Round 1.5)

**Topic:** 基本面因子挖掘 — 应计项目 / 盈余质量 (Sloan 1996)
**Workflow:** worldquant-5-agent-workflow  (Research → Hypothesis → Builder → Backtest → Evaluator)
**Disposition:** **PROMOTE `alpha_03` (industry-neutral Sloan CFS) to paper trading. Continue Round 2.**

---

## 1. TL;DR

Ran the 5-agent workflow on A-share 2020-2025 (5,285 stocks, 64 monthly rebalances, delay=1, 10 bps cost). Of 8 accruals-family expressions, **alpha_03 (industry-neutral Sloan) clears every one of the five mandatory pre-PROMOTE audits**:

| metric | value | target |
|--------|------:|-------:|
| Rank IC (20d) | 0.018 | > 0.02 (close) |
| **ICIR (20d)** | **0.49** | **> 0.40** ✓ |
| LS Sharpe gross | 1.98 | — |
| **LS Sharpe net (10 bps)** | **1.38** | **> 1.00** ✓ |
| **Worst-year Sharpe** | **1.24** (2020) | **≥ 0.50** ✓ |
| Best-year-out kept | 85 % | ≥ 50 % ✓ |
| Max drawdown (LS) | −2.0 % | — |
| Q5 excess annualized | 3.8 % | ≥ 4 % (close) |

alpha_08 (industry × size double-neutral) is the secondary winner (Sharpe net 0.93, worst year 0.88). alpha_02 (BS-method WCA) is rejected — signal inverted due to Tushare restatement noise, validating the librarian's a-priori caveat.

---

## 2. What each Stage produced

| Agent | Output | Key result |
|-------|--------|------------|
| 1 Research Librarian | `outputs/research_brief.md` | Selected accruals over 4 alternatives; enumerated 7 A-share caveats (including ann_date leakage and BS-method fragility that both later played out in the evidence). |
| 2 Hypothesis Architect | `outputs/session_metadata.yml` | Locked targets (ICIR > 0.4, Sharpe > 1.0, worst-year ≥ 0.5); TVT windows; non-negotiable look-ahead contract. |
| 3 Alpha Builder | `outputs/expressions_batch_0001.md` | 8 expressions on one mechanism, spanning level / change / neutralization / normalization dimensions. |
| 4 Backtest Operator | `outputs/backtest_results_batch_0001.md` | Runtime-attached execution on 5.6 M stock-days; IC / LS / Q5 / annual tables; 5 numeric audits. |
| 5 Evaluator & Recorder | `outputs/alpha_ranking.md` + `round_0001.yml` | Evidence-based ranking; alpha_03 PROMOTE, alpha_08 PROMOTE-secondary, alpha_02/04/05/07 DROP. |

---

## 3. Audit outcomes

| audit | outcome |
|-------|---------|
| Execution-delay (physical timeline, invariant, target-mask) | **PASS** — `delay=1` encoded in `close.shift(-1-h)/close.shift(-1)`; fundamentals gated by `ann_date < trade_date` via `merge_asof(backward, allow_exact_matches=False)`. |
| Look-ahead (numeric) | **PASS** — shuffle-forward-returns test drops IC from 0.01-0.02 to ≤ 0.00063 for all 8 alphas. |
| Worst-year floor (≥ 0.5) | **PASS** for alpha_01 (0.77), alpha_03 (1.24), alpha_06 (0.59), alpha_08 (0.88); FAIL for 02 / 04 / 05 / 07. |
| Best-year-out (≥ 50 % of headline) | **PASS** for 01 / 03 / 04 / 06 / 07 / 08; FAIL for 02 / 05. |
| Falsification-first (publication-lag leakage) | **PASS** — leaky end_date-gated IC is 0.0211, lower than clean 0.0236; no leak detected. |

---

## 4. Key learnings

1. **A-priori top pick alpha_08 came 2nd; alpha_03 won.** Double-neutralization (industry × size) cost more IC than the additional stability bought in this 5-year window. For shorter samples the simpler single-axis neutralization dominates. Expected to flip if window extends to 2018-2025 (covering 2018 deleveraging stress).
2. **BS-method accruals are unusable on Tushare.** alpha_02 had the predicted negative sign and a worst-year Sharpe of −1.73. The restatement noise the librarian flagged turned out to be the decisive failure mode. Do not waste further cycles on BS-method without a proper point-in-time data vendor.
3. **Slow-decay signal confirmed.** IC at 1/5/20/60 days: 0.006 → 0.012 → 0.024 → 0.045. Monthly rebalance is the right cadence; daily would throw away 80 % of the information. This matches the A-share adaptation lesson in SKILL.md.
4. **Falsification-first was decisive.** The leaky-vs-clean comparison returns a *lower* leaky IC, not a higher one — refuting the most-likely-single-cause-of-being-wrong hypothesis from Stage 4. This is the exact "adversarial attack" SKILL.md asks for, and the mechanism passes.

---

## 5. Round 2 plan

1. **Residualize alpha_03** on train window vs {log total_mv, mom_20, rev_5, turnover_z}. Report residual Sharpe; target ≥ 50 % of headline to rule out classic-factor vehicle exposure.
2. **Extend window backward to 2018** (covers 2018 deleveraging stress); re-run the whole pipeline and verify alpha_03 worst-year floor still holds.
3. **Attribution decomposition:** run size-neutral-only variant (no industry) and industry-only (current alpha_03) and size×industry (alpha_08). Publish which axis buys what.
4. **Deploy alpha_03 Q5 long-only overlay** in paper trading (CSI300 benchmark); track monthly excess for out-of-sample evidence accumulation.
5. **Open a fresh session for SUE / PEAD** — independent fundamental mechanism; ensemble with alpha_03 once both are paper-traded.

---

## 6. File manifest

```
logs/20260420_fundamental_accruals_alpha/
├── inputs/objective.md
├── working/
│   ├── handoff_1_to_2.json  ...  handoff_4_to_5.json
├── outputs/
│   ├── research_brief.md
│   ├── session_metadata.yml
│   ├── expressions_batch_0001.md
│   ├── backtest_results_batch_0001.md  ← Round 1.5 (real numbers)
│   ├── alpha_ranking.md                ← Round 1.5
│   ├── final_summary.md                ← this file
│   ├── ic_table_batch_0001.csv
│   ├── ls_summary_batch_0001.csv
│   ├── ls_annual_batch_0001.csv
│   ├── audit_worst_year_best_out.csv
│   ├── correlation_matrix.csv
│   └── audits.json
├── scripts/
│   ├── 01_fetch_fundamentals.py
│   ├── 02_fetch_daily.py
│   ├── 03_build_alphas.py
│   └── 04_evaluate.py
├── round_0001.yml
└── run_state.json
```

Raw Tushare caches (fundamentals, daily panel, panel.parquet) live in `.cache/` and are **not tracked by git** (size + third-party data ToS). Anyone with the same Tushare token can rebuild them by running scripts 01 → 02 → 03 → 04.

---

## 7. One-sentence takeaway

**Industry-neutral Sloan CFS accruals (`alpha_03`) is promoted to the Factor_Zoo paper-trading queue: ICIR 0.49, net-of-cost Sharpe 1.38, worst-year Sharpe 1.24, max drawdown −2 % on A-share 2020-2025 — all five mandatory audits pass.**
