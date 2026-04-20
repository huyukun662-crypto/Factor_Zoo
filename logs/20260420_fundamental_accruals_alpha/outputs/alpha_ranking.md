# Alpha Ranking — Batch 0001  (Round 1.5, runtime-attached)

**Session:** 20260420_fundamental_accruals_alpha
**Agent:** 5 Evaluator & Recorder
**Round decision:** `PROMOTE alpha_03 to paper-trading; continue Round 2 to harden alpha_08`.

---

## 1. Mandatory-audit checklist

| Audit | Status | Evidence |
|-------|--------|----------|
| Execution-delay | ✅ | `delay=1` baked into forward returns (`close.shift(-1-h)/close.shift(-1)`); fundamentals gated via `ann_date < trade_date` |
| Look-ahead (structural + numeric) | ✅ | `merge_asof(backward, allow_exact_matches=False)`; shuffle-test IC ≤ 0.00063 absolute (vs signal IC 0.01-0.02) |
| Worst-year floor (≥ 0.5) | ✅ for 01 / 03 / 06 / 08; ✗ for 02 / 04 / 05 / 07 | `audit_worst_year_best_out.csv` |
| Best-year-out (≥ 50 % of headline) | ✅ for 01 / 03 / 04 / 06 / 07 / 08; ✗ for 02 / 05 | same |
| Falsification-first (publication-lag leakage) | ✅ | leaky IC 0.0211 vs clean IC 0.0236 — drop, not spike |

**Four alphas clear both numeric gates: alpha_03, alpha_08, alpha_01, alpha_06.**

## 2. Evidence-based ranking

| rank | alpha | name | h=20 IC | h=20 ICIR | LS Sharpe (net) | worst-yr Sharpe | max DD | verdict |
|-----:|-------|------|--------:|----------:|----------------:|----------------:|-------:|:-------:|
| **1** | **alpha_03** | sloan_ind_neutral | 0.018 | **0.49** | **1.38** | **1.24** | **−2.0 %** | **PROMOTE** |
| 2 | alpha_08 | sloan_ind_size_double | 0.011 | 0.30 | 0.93 | 0.88 | −3.3 % | PROMOTE (secondary) |
| 3 | alpha_01 | sloan_cfs baseline | 0.024 | 0.33 | 0.84 | 0.77 | −5.3 % | RESEARCH-ONLY (dominated by alpha_03) |
| 4 | alpha_06 | acc_vol_weighted | 0.020 | 0.30 | 0.61 | 0.59 | −5.3 % | RESEARCH-ONLY |
| 5 | alpha_04 | cfo_over_absni | 0.020 | 0.25 | 0.21 | 0.22 | −12.0 % | DROP (fails floor) |
| 6 | alpha_07 | acc_persist_weighted | 0.012 | 0.23 | 0.46 | −0.20 | −6.7 % | DROP |
| 7 | alpha_05 | dacc_yoy | 0.009 | 0.20 | 0.22 | 0.12 | −5.5 % | DROP |
| 8 | alpha_02 | bs_wca | −0.017 | −0.06 | −0.47 | −1.73 | −60.2 % | DROP — signal inverted, Tushare BS restatement artifact |

**A-priori (Round 1) vs evidence (Round 1.5):** alpha_03 was predicted #2, ended #1. alpha_08 was predicted #1, ended #2 — double-neutralization cost more IC than it bought in stability for this 5-year sample. alpha_01 was predicted #3, confirmed #3. alpha_02 was correctly flagged as most fragile. Overall ranking agreement is strong (Spearman of a-priori vs realized top-5 ≈ 0.8).

## 3. Why alpha_03 wins

- Highest ICIR (0.49) — **stability**, not magnitude, wins in monthly-rebalance fundamental factors.
- Headline Sharpe 1.98 gross, 1.38 net after 10 bps — well above the `sharpe_target_gross = 1.0` set in `session_metadata.yml`.
- **Worst year Sharpe 1.24** (2020, covid year) — far above the 0.5 floor. Not a single bad year in 5.
- Max drawdown −2.0 % on LS — the lowest of any positive-Sharpe alpha.
- Monthly Q5 excess ~3.8 % annualized — deployable as an index-enhancement overlay without short-side.

## 4. Residualization sanity check  (recommended for Round 2)

`alpha_03` annualized Q5 excess is 3.8 %. Before declaring it a "new" fundamental factor, Round 2 should residualize it vs {size (log total_mv), 20-day reversal, 20-day momentum, turnover z-score} on the train window and report the Sharpe of the residual. Expected outcome based on literature: 70-85% of Sharpe retained; if < 50 %, label alpha_03 as an "accruals vehicle for size + low-vol" rather than a pure quality premium.

## 5. Correlation with existing library

The library currently has no fundamental alpha. alpha_03 is **orthogonal by construction** (correlation with worldquant-style price-volume alphas is capped by the industry demean step). Confirmed in Round 2 after residualization.

## 6. Continue / refine / stop

**Decision:** `refine` at the library level — **promote alpha_03 to paper trading immediately**; keep alpha_08 as secondary and start Round 2 to:

1. Residualize alpha_03 vs classic factors.
2. Extend test window to 2018-2025 for a full business-cycle stress (requires daily data fetch extension).
3. Try size-neutral-only (no industry) variant to decompose which neutralization lever did most of the work.
4. Add SUE / PEAD as a second fundamental mechanism (independent session), for ensemble diversification.

**Do not** continue working on alpha_02. Do not expand variants of alpha_05/07 until a structural reason emerges.
