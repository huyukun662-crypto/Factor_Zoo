# Expressions Batch 0001 — Accruals Earnings-Quality

**Session:** 20260420_fundamental_accruals_alpha
**Agent:** 3 Alpha Builder
**Batch:** 0001  (Rule of 8 — exactly 8 expressions, one mechanism)

**Sign convention:** all expressions are pre-flipped so that **higher value = higher expected forward return** (i.e. lower accruals / higher earnings quality).

**Common preprocessing (applied by the runtime, NOT repeated in every expression):**
- Universe filter: all-A ex-financials ex-ST, listed > 252 trading days.
- Quarterly → daily: forward-fill from `ann_date + 1` trading day; never `end_date`.
- Winsorize daily at [0.01, 0.99] cross-section.
- Missing data: require ≥3 of trailing 4 quarters; else drop the stock-day.

---

## Expression 1 — Sloan canonical CFS-method accruals (flipped)

```
acc_ttm    = ts_sum(n_income - n_cashflow_act, 4_quarters) / ts_mean(total_assets, 4_quarters)
alpha_01   = -rank(acc_ttm)
```

**Economic rationale:** Classical Sloan (1996). Short high-accruals (low quality, low persistence), long low-accruals. Baseline; any refinement must beat this.

**Expected turnover:** lower (quarterly refresh of numerator, monthly rebalance → ~8-12% monthly turnover).

**Fragility notes:**
- Biased toward low-growth / mature firms → need industry neutralization when comparing to baseline.
- Zero CFO quarters (newly listed) explode the ratio → keep the `≥3 of 4` quarters filter.

---

## Expression 2 — Balance-sheet-method working-capital accruals

```
delta_wc   = ts_delta(acct_rcv + inventories - acct_pay, 4_quarters)
dep_ttm    = ts_sum(depr_fa_coga_dpba, 4_quarters)
wca_ttm    = (delta_wc - dep_ttm) / ts_mean(total_assets, 4_quarters)
alpha_02   = -rank(wca_ttm)
```

**Economic rationale:** Alternative accruals definition isolating *working-capital* distortion rather than total NI-CFO gap. Should correlate 0.5-0.7 with alpha_01; divergence reveals cash-flow-statement adjustments.

**Expected turnover:** lower (same update cadence as #1).

**Fragility notes:**
- A-share BS-method is known to suffer from restatements (librarian caveat #2); expect slightly lower IC than #1.
- Mark as secondary; if #1 dominates, #2 is redundant.

---

## Expression 3 — Industry-neutral Sloan accruals

```
acc_ttm    = ts_sum(n_income - n_cashflow_act, 4_quarters) / ts_mean(total_assets, 4_quarters)
alpha_03   = -group_rank(acc_ttm, sw_l1_industry)
```

**Economic rationale:** Remove industry-level accrual norms (real-estate runs high accruals structurally; tech runs low). A-share lesson from SKILL.md: industry neutralization typically boosts test Sharpe 30-40%.

**Expected turnover:** lower.

**Fragility notes:**
- Degenerate if an industry has <5 names on a given date → fall back to unneutralized rank.
- SW L1 ~28 industries: sample per industry is thin for small sectors (defense, agri).

---

## Expression 4 — CFO / |NI| ratio (earnings "quality score")

```
cfo_ttm    = ts_sum(n_cashflow_act, 4_quarters)
ni_ttm     = ts_sum(n_income, 4_quarters)
quality    = cfo_ttm / (abs(ni_ttm) + 0.01 * ts_mean(total_assets, 4_quarters))
alpha_04   = rank(quality)          # already in "higher = better", no flip
```

**Economic rationale:** Direct "what fraction of reported earnings is cash?" framing. The denominator floor (1% of avg TA) prevents explosion when NI ≈ 0. A cleaner story to explain than raw accruals.

**Expected turnover:** lower.

**Fragility notes:**
- NI negative + CFO positive → ratio is negative but firm is *healthier* than the raw ratio suggests. The floor partially mitigates but not fully; check bottom decile manually in Stage 4.

---

## Expression 5 — Accruals change (Δaccruals yoy)

```
acc_this   = ts_sum(n_income - n_cashflow_act, 4_quarters) / ts_mean(total_assets, 4_quarters)
acc_prev   = lag(acc_this, 252_trading_days)    # ≈ 4 quarters ago
alpha_05   = -rank(acc_this - acc_prev)
```

**Economic rationale:** Quality is improving if accruals are *falling*. Captures the *change* in earnings quality rather than the level — complementary signal that may fire earlier than #1.

**Expected turnover:** neutral (change-signals rebalance slightly more).

**Fragility notes:**
- More noise than level; expect lower t-stat but lower correlation with #1, useful for ensemble in later rounds.
- IPO stocks lack t-1y baseline → drop if `lag` is NaN.

---

## Expression 6 — Accruals *scaled by earnings volatility* (stability-weighted)

```
acc_ttm    = ts_sum(n_income - n_cashflow_act, 4_quarters) / ts_mean(total_assets, 4_quarters)
ni_vol_8q  = ts_std(n_income / total_assets, 8_quarters)
alpha_06   = -rank(acc_ttm / (ni_vol_8q + 1e-4))
```

**Economic rationale:** Accruals signal is more trustworthy for firms with *stable* earnings streams. Dividing by earnings-vol downweights noisy firms where a single quarter dominates.

**Expected turnover:** neutral.

**Fragility notes:**
- Requires 8 quarters of history → drops young firms; universe shrinks.
- If ni_vol_8q is near zero (utilities), ratio explodes; check distribution and winsorize post-construction.

---

## Expression 7 — Persistence-weighted accruals (accruals × auto-correlation of CFO)

```
cfo_q      = n_cashflow_act / total_assets
cfo_persist = ts_corr(cfo_q, lag(cfo_q, 4_quarters), 12_quarters)   # persistence of cash earnings
acc_ttm    = ts_sum(n_income - n_cashflow_act, 4_quarters) / ts_mean(total_assets, 4_quarters)
alpha_07   = -rank(acc_ttm * cfo_persist)
```

**Economic rationale:** Accruals matter more when the *cash* component of earnings is itself persistent (so the extrapolation-mistake by the market is larger). For firms with lumpy cash flows, the accrual signal is noisier.

**Expected turnover:** neutral.

**Fragility notes:**
- Needs 12 quarters → further universe shrinkage; test on test window where 2012+ firms qualify.
- Non-linear interaction with level → harder to interpret; if it beats alpha_01 by <5%, prefer alpha_01 for interpretability.

---

## Expression 8 — Industry + size neutral Sloan accruals (double-neutralized flagship)

```
acc_ttm    = ts_sum(n_income - n_cashflow_act, 4_quarters) / ts_mean(total_assets, 4_quarters)
log_mv     = log(total_mv)
size_bin   = quantile_bin(log_mv within sw_l1_industry, 5)
alpha_08   = -group_rank(acc_ttm, sw_l1_industry x size_bin)
```

**Economic rationale:** A-share size effect is known to contaminate most cross-sectional fundamentals. Double-neutralizing against industry × size (5 bins) strips both effects, leaving the pure earnings-quality signal. SKILL.md lesson: industry-neutralization alone often cuts train-test gap by half.

**Expected turnover:** lower.

**Fragility notes:**
- 28 industries × 5 size bins = 140 buckets; some will have <3 names → fall back to industry-only rank.
- If `total_mv` falls back to `close*total_share` (free Tushare), point-in-time error is small but non-zero (daily share count changes at ex-div).

---

## Batch summary

| # | name | complexity | dominant ingredient | expected IC rank |
|---|------|------------|---------------------|------------------|
| 1 | sloan_cfs | low | NI - CFO level | baseline |
| 2 | bs_wca | low | ΔWC - Dep | below #1 (A-share) |
| 3 | sloan_ind_neutral | low | #1 + industry | above #1 |
| 4 | cfo_ni_ratio | low | CFO/\|NI\| | close to #1 |
| 5 | dacc_yoy | mid | Δaccruals | independent, lower t-stat |
| 6 | acc_vol_weighted | mid | acc / ni-vol | close to #1 |
| 7 | acc_persist_weighted | high | acc × cfo-persist | mid-pack |
| 8 | sloan_ind_size_double | low | #3 + size | **expected top** |

**Distinctness check:** #1, #2, #3, #4, #8 share the accruals *level* core but differ by (neutralization, definition, normalization). #5 uses *change*. #6 uses *stability scaling*. #7 uses *persistence interaction*. Expected pairwise correlation of alphas 0.4-0.8, which satisfies the "sufficiently distinct" rule without polluting the mechanism.

**Turnover direction commitment:** whole batch is **lower** turnover (fundamental data cadence; monthly rebalance).
