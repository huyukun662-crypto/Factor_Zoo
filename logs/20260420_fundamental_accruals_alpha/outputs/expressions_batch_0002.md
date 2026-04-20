# Expressions Batch 0002 — Accruals Earnings-Quality (Round 2 variants)

**Session:** 20260420_fundamental_accruals_alpha
**Agent:** 3 Alpha Builder
**Batch:** 0002  (Round 2 — 8 refinement variants of alpha_03)

**Mechanism (unchanged):** earnings quality via accruals. All 8 variants short high-accruals / long low-accruals. Industry-neutrality is the common baseline; variants differ in winsorization, normalization style, TTM construction, ensemble weighting, and denominator choice.

**Sign convention:** all flipped so higher value = higher expected forward return.

---

| # | Variant | Construction (vs alpha_03 baseline) |
|---|---------|-------------------------------------|
| v1 | baseline | `-group_rank( acc_4q , industry )` — same as Round 1 alpha_03 |
| v2 | tighter winsorize | clip at [0.05, 0.95] instead of [0.01, 0.99] |
| v3 | industry z-score | `-group_zscore(acc_4q_wz, industry)` — preserves magnitude, not only rank |
| v4 | 8-quarter TTM | TTM over 8 quarters (smoother) instead of 4 |
| **v5** | **median TTM** | **median(NI - CFO) × 4 / avg_TA — robust to single-quarter restatements** |
| v6 | revenue-scaled | denominator = TTM revenue (not avg_TA); alt normalization |
| v7 | stability-weighted | `acc_4q / ni_vol_8q`, then industry-rank |
| v8 | ensemble | 0.5 × v1 + 0.5 × v7 |

**Rule of 8 passed; one-mechanism preserved.**
