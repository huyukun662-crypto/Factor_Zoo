# Expressions Batch 0003 — Accruals Attribution Decomposition (Round 3)

**Session:** 20260420_fundamental_accruals_alpha
**Agent:** 3 Alpha Builder
**Batch:** 0003  (Round 3 — 2 × 4 factorial attribution)
**Window:** **2018-07 → 2025-04** (extended from Round 2's 2020-2025 to include the 2018 deleveraging stress and the 2019 bull)

**Purpose:** cleanly decompose the alpha_v5 result along two axes
- *TTM rollup style:* {sum_4q, median_4q}
- *Neutralization:* {none, size-only, industry-only, industry × size}

This gives **8 expressions in 2 × 4 factorial**, one dominant mechanism (accruals), satisfying the Rule of 8 and one-mechanism constraints.

All 8 are constructed as:
```
acc_ttm = aggregate(NI_ttm - CFO_ttm, 4q) / ts_mean(total_assets, 4q)
alpha   = -rank(acc_ttm_winsorized,  [optional grouping cols])
```
Sign flipped so higher alpha = higher expected forward return.

| # | Variant | TTM | Neutralization |
|---|---------|-----|----------------|
| 1 | `alpha_sum_none`      | sum    | none (global rank) |
| 2 | `alpha_sum_size`      | sum    | size quintile only |
| 3 | `alpha_sum_ind`       | sum    | industry only  (= Round 1 alpha_03) |
| 4 | `alpha_sum_indxsize`  | sum    | industry × size |
| 5 | `alpha_med_none`      | median | none |
| 6 | `alpha_med_size`      | median | size quintile only |
| 7 | `alpha_med_ind`       | median | industry only  (= Round 2 alpha_v5) |
| 8 | `alpha_med_indxsize`  | median | industry × size |
