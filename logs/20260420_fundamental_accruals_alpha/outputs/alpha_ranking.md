# Alpha Ranking — Session Leader Board (after Round 4)

**Session:** 20260420_fundamental_accruals_alpha
**Agent:** 5 Evaluator & Recorder
**Flagship:** `alpha_med_ind` (a.k.a. `accruals_median_ttm_ind_neutral_v2`)
**Round 4 outcome:** **no new winner**; cost model corrected; flagship kept; session closed.

---

## 1. Cross-round final table (all LS-net on corrected turnover-aware cost model, full 2018-2025)

| rank | alpha | round | Ann ret | Ann vol | **Sharpe net** | Max DD | Q5 IR | turnover |
|-----:|-------|------:|--------:|--------:|---------------:|-------:|------:|---------:|
| **1** | **v1_baseline = alpha_med_ind** | 1-4 | 10.2 % | 7.4 % | **1.32** | **−1.8 %** | 1.11 | 9.7 % |
| 2 | v6 sticky 10 % (of baseline) | 4 | 9.8 % | 7.4 % | 1.28 | −1.9 % | **1.11** | **7.3 %** |
| 3 | v2 ema20 | 4 | 10.0 % | 7.4 % | 1.29 | −2.9 % | 1.09 | 9.2 % |
| 4 | v5 consensus ind+indxsize | 4 | 10.0 % | 7.5 % | 1.28 | −2.7 % | 1.10 | 12.9 % |
| 5 | v3 ema60 | 4 | 9.8 % | 7.4 % | 1.27 | −2.9 % | 1.04 | 8.7 % |
| 6 | alpha_sum_ind (= Round 1 alpha_03) | 1,3 | — | — | ~1.29 | −2.6 % | 1.13 | ~9.6 % |
| — | v7 bi-monthly | 4 | — | — | *not comparable (annualization)* |
| — | v8 horizon blend | 4 | — | — | *rejected (vol artifact)* |

## 2. Cost-model correction

**The most important Round 4 deliverable is retroactive.** Rounds 1-3 applied a flat **20 bps per rebalance** (implicitly assuming 100 % turnover). The actual Q5-plus-Q1 turnover is only ~19 % combined, so the true per-rebalance LS cost is **~1.9 bps, not 20 bps**. Rounds 1-3 were **over-penalizing by a factor of ~10**.

**Revised honest flagship expectations:**

| metric | Round 3 over-penalized | Round 4 corrected |
|--------|-----------------------:|------------------:|
| Full LS net Sharpe | 1.03 | **1.32** |
| Full LS net ann return | 7.9 % | **10.2 %** |
| Full Q5 IR (net) | 1.15 | **1.11** |
| Full Max DD | −1.8 % | −1.8 % |

Q5 excess barely moves because Q5 is one-sided; LS moves materially.

## 3. Why no new winner

Baseline `alpha_med_ind` is already a low-turnover factor (~10 % per rebalance). Smoothing / sticky-band variants only cut turnover by 10-25 % and preserve Sharpe, but don't *improve* it. The cleanest diagnostic is:

- **Full-window Sharpe ordering:** v1 ≥ v2 ≥ v5 ≥ v6 ≥ v3 ≥ v4. Baseline is #1.
- **Test-period Sharpe ordering:** v3 > v2 > v6 > v1 > v4 > v5. EMA-60 takes the crown on Test (1.20 vs baseline 0.95), but the 15-rebalance Test sample is too small to declare statistical significance.
- **Turnover ordering:** v6 < v4 < v3 < v2 < v1 < v5 < v7. Sticky-band cuts turnover most with negligible performance cost.

**Decision principle:** no robust strict-dominance → keep the simplest (baseline). Optional `sticky 10 %` overlay if turnover minimization matters (paper-trading pilot could use it to lower tracking error from rebalance timing).

## 4. What we now know about the factor (4-round cumulative)

1. **Mechanism:** earnings quality via trailing-4-quarter **median** of (NI − CFO) / avg TA. Median beats sum because it absorbs restatement noise.
2. **Neutralization:** **industry-only** is the decisive lever (+0.30 Sharpe vs no-neut). Size alone does nothing. Double (industry × size) destroys more signal than it saves risk on 2018-2025 but may help on shorter post-2022 windows.
3. **Cadence:** monthly rebalance is correct (signal updates quarterly, 20-day horizon IC stable). Bi-monthly has comparable raw numbers but the hold-period change complicates comparison.
4. **Turnover:** ~10 % per month, ~1.9 bps total cost. Factor is cheap to trade; smoothing buys little.
5. **Orthogonality:** 96 % of Sharpe survives residualization against {size, mom, rev, turnover, vol}. Not a classic-factor vehicle.
6. **Robustness:** worst-year Sharpe 1.33 (2022), max DD −1.8 %, 7 years including 2018 deleveraging. Passes all audits.
7. **Deployable form:** Q5 long-only within industry, CSI300 benchmark. IR ~1.1 full-sample, ~0.9 on honest Test period (dragged by 3-point 2025 sample).

## 5. Final deployment spec

```yaml
name:           accruals_median_ttm_ind_neutral_v2
mechanism:      Earnings quality via accruals (Sloan 1996, CFS-method, median-TTM)
universe:       A-share ex-financials ex-ST, listed > 252 trading days
frequency:      monthly rebalance (every 20 trading days)
delay:          1
deployment:
  primary:      Q5 (top quintile within industry) long-only, equal-weighted; CSI300 benchmark
  validation:   LS (Q5 - Q1) for signal integrity; not deployed
  cost_model:   ~2 bps per rebalance (turnover-aware)
expected:
  ls_net_sharpe: 1.32 (full 2018-2025); 0.95 (Test 2024-2025YTD honest); 1.20 with ema60 overlay
  q5_net_ir:     1.11 (full); 0.87 (Test); 1.16 with ema60 overlay
  max_dd:        -1.8 % (seen); -5 % kill-switch
monitoring:
  rolling_12m_ic_below_0:  alert
  rolling_12m_sharpe_below_0.3: investigate
  max_dd_worse_than_-5pct: pause
next_session:
  - SUE/PEAD (Bernard-Thomas 1989) — independent mechanism
  - Gross Profitability (Novy-Marx 2013) — value/quality cross
  - 2-3 factor ensemble after 3 months of paper-trading evidence
```

## 6. Continue / refine / stop

**Decision:** **stop accruals-family work.** Four rounds, 32 expressions, one clear flagship, all audits pass, cost model corrected. Further accruals tuning is curve-fitting. Open new sessions for independent mechanisms.
