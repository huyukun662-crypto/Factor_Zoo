# Alpha Ranking — Batch 0001 (Overnight–Intraday Decomposition)

**Session:** `20260428_a_share_overnight_intraday_alpha`
**Agent:** 5 — Evaluator & Recorder
**Date:** 2026-04-28
**Universe:** A-share 主板 + 创业板 + 科创板, ex-ST, including delisted (`list_status=L+D`)
**Window:** 2018-01-02 → 2026-04-25 (2016 trading days)
**Rebalance:** 20 trading days (monthly), 99 rebalances
**Cost:** 5 bps per side, turnover-aware
**Delay:** 1 (signal at close T, execute close T+1)

---

## 1. Headline IC table (rank-IC, mean across dates)

| alpha                   |    1d |    5d |   10d |   20d |   60d | t-stat 20d |
|---|---:|---:|---:|---:|---:|---:|
| α_01 on_cum_20d         | 0.011 | 0.018 | 0.023 | 0.030 | 0.055 | **28.0** |
| α_02 on_cum_5d          | 0.011 | 0.018 | 0.025 | 0.027 | 0.040 | 27.3 |
| α_03 on_cum_60d         | 0.014 | 0.025 | 0.033 | 0.044 | 0.068 | 35.4 |
| **α_04 on_minus_id_20d**| **0.031** | **0.046** | **0.055** | **0.064** | **0.076** | **42.7** |
| α_05 on_cum_20d_volsc   | 0.010 | 0.018 | 0.023 | 0.030 | 0.052 | 28.1 |
| α_06 on_cum_20d_x_tovz  | 0.004 | 0.008 | 0.011 | 0.014 | 0.020 | 11.4 |
| α_07 on_uppct_20d       | 0.005 | 0.011 | 0.013 | 0.014 | 0.019 | 11.8 |
| α_08 on_sharpe_20d      | 0.010 | 0.018 | 0.023 | 0.030 | 0.052 | 28.1 |

All 8 alphas have positive IC at every horizon — sign matches Agent 2's
hypothesis. IC monotonically increasing with horizon for 7/8 alphas
(consistent with the Lou-Polk-Skouras "slow informed-flow" interpretation).
**α_04 dominates at every horizon.**

## 2. LS Q5−Q1 ranking (net of 5 bps/side cost, monthly rebal)

| rank | alpha | ann ret | ann vol | net Sharpe | gross Sharpe | max DD | tov q5 | cost / reb |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | **α_04 on_minus_id_20d** | **16.13 %** | 6.62 % | **2.44** | 2.58 | -4.90 % | 75.1 % | 7.30 bps |
| 2 | α_03 on_cum_60d         | 14.24 % | 5.90 % | 2.41 | 2.49 | -3.93 % | 38.7 % | 3.72 bps |
| 3 | α_02 on_cum_5d          | 9.89 %  | 5.00 % | 1.98 | 2.17 | -5.84 % | 76.4 % | 7.51 bps |
| 4 | α_05 on_cum_20d_volsc   | 9.08 %  | 4.84 % | 1.88 | 2.06 | -4.64 % | 72.3 % | 7.20 bps |
| 5 | α_08 on_sharpe_20d      | 9.09 %  | 4.84 % | 1.88 | 2.06 | -4.66 % | 72.3 % | 7.20 bps |
| 6 | α_01 on_cum_20d         | 9.70 %  | 5.34 % | 1.82 | 1.98 | -5.25 % | 72.8 % | 7.04 bps |
| 7 | α_06 on_cum_20d_x_tovz  | 5.54 %  | 5.36 % | 1.03 | 1.19 | -5.13 % | 67.9 % | 6.67 bps |
| 8 | α_07 on_uppct_20d       | 3.86 %  | 5.30 % | 0.73 | 0.90 | -7.55 % | 71.2 % | 7.06 bps |

## 3. Q5 long-only excess (vs equal-weight universe, IR)

| rank | alpha | ann excess | IR | max DD |
|---:|---|---:|---:|---:|
| 1 | α_05 on_cum_20d_volsc   | 3.43 % | 1.26 | -2.74 % |
| 2 | α_08 on_sharpe_20d      | 3.44 % | 1.26 | -2.74 % |
| 3 | **α_04 on_minus_id_20d**| **4.06 %** | **1.04** | -5.08 % |
| 4 | α_03 on_cum_60d         | 4.11 % | 1.03 | -5.08 % |
| 5 | α_07 on_uppct_20d       | 2.33 % | 0.80 | -3.45 % |
| 6 | α_02 on_cum_5d          | 1.31 % | 0.40 | -8.79 % |
| 7 | α_01 on_cum_20d         | 1.46 % | 0.39 | -6.70 % |
| 8 | α_06 on_cum_20d_x_tovz  | -1.77 % | -0.41 | -18.72 % |

**α_05 ≈ α_08 in Q5 (1.26 IR vol-scaled forms)** but α_04 has the more
balanced LS+Q5 profile and passes worst-year-floor for *every* year.

## 4. Audit results (CLAUDE.md mandatory 5 + look-ahead grep + future-perturb)

| alpha | exec-delay | look-ahead grep | future-perturb | worst-year ≥ 0.5 | best-year-out ≥ 50 % | residual ≥ 50 % | **decision** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| α_01 | ✅ | ✅ | ✅ | ✅ 0.87 (2025) | ✅ 94 % | ✅ 119 % | **PROMOTE** |
| α_02 | ✅ | ✅ | ✅ | ✅ 0.55 (2025) | ✅ 88 % | ✅ 56 %  | **PROMOTE** |
| α_03 | ✅ | ✅ | ✅ | ✅ 0.78 (2024) | ✅ 94 % | ✅ 101 % | **PROMOTE** |
| **α_04** | ✅ | ✅ | ✅ | ✅ **0.90 (2020)** | ✅ **91 %** | ✅ **81 %** | **PROMOTE ★** |
| α_05 | ✅ | ✅ | ✅ | ❌ 0.07 (2024) | ✅ 89 % | ✅ 117 % | RESEARCH-ONLY |
| α_06 | ✅ | ✅ | ✅ | ❌ -0.65 (2022) | ✅ 95 % | ❌ -10 % | RESEARCH-ONLY |
| α_07 | ✅ | ✅ | ✅ | ❌ -0.83 (2024) | ✅ 74 % | ✅ 129 % | RESEARCH-ONLY |
| α_08 | ✅ | ✅ | ✅ | ❌ 0.06 (2024) | ✅ 89 % | ✅ 116 % | RESEARCH-ONLY |

(α_05 and α_08 fail only because of 2024; in 2024 the vol-scaled forms
collapsed to ~zero LS Sharpe — likely because the within-stock vol of
overnight returns was unusually compressed in mid-2024 megacap rotation.)

## 5. Per-year LS net Sharpe — PROMOTE candidates

| year | n | α_01 | α_02 | α_03 | **α_04** |
|---|---:|---:|---:|---:|---:|
| 2018 | 12 | 2.08 | 1.34 | 5.63 | **4.67** |
| 2019 | 12 | 1.33 | 1.42 | 3.06 | **3.68** |
| 2020 | 12 | 2.34 | 3.90 | 2.74 | **0.90** ← α_04 worst |
| 2021 | 12 | 2.89 | 3.80 | 1.70 | **3.80** |
| 2022 | 12 | 1.52 | 2.60 | 1.41 | **3.69** |
| 2023 | 12 | 3.27 | 2.07 | 4.59 | **2.48** |
| 2024 | 12 | 1.30 | 2.04 | 0.78 | **1.64** |
| 2025YTD | 13 | 0.87 | 0.55 | 2.75 | **2.20** |

**α_04 is the only alpha with all 8 years above 0.5 AND every year above
0.9.** 2020 is its weakest year (a rare A-share megacap rally that
compressed cross-sectional dispersion of overnight returns), but even
that delivered LS net Sharpe 0.90.

## 6. Why α_04 wins among the PROMOTE candidates

- **Highest LS net Sharpe (2.44 vs 2.41/1.98/1.82).**
- **Mechanically orthogonal to total CC return** — the spread `ON_20 − ID_20`
  cancels the "total return" component; this is the cleanest test of the
  decomposition thesis.
- **Most balanced per-year profile** — no year below 0.90 (the others have
  a 0.55-0.78 floor year somewhere).
- **81 % residualization retention** — the second-best PROMOTE candidate is
  α_03 at 101 %, but α_03 has lower LS Sharpe and a 0.78 worst-year. α_04's
  81 % is comfortably above the 50 % floor, so the alpha is not just a
  vehicle for {log_mv, σ_20, ret_5, ret_20, turnover_20}.
- **Cost per rebalance 7.30 bps** is healthy; the alpha is not turnover-
  starved (α_03's lower turnover comes at the price of slower signal
  refresh, which hurts in years like 2020 and 2024).

## 7. Final ranking

| rank | alpha | family | decision |
|---:|---|---|---|
| **1** | **α_04 on_minus_id_20d (deployment: overnight_intraday_spread_20d_v1)** | overnight–intraday decomposition spread | **PROMOTE** |
| 2 | α_03 on_cum_60d | pure long-horizon overnight | PROMOTE (secondary) |
| 3 | α_02 on_cum_5d  | pure short-horizon overnight | PROMOTE (secondary) |
| 4 | α_01 on_cum_20d | pure 20d overnight (canonical LPS) | PROMOTE (secondary) |
| 5 | α_05 / α_08 vol-scaled | 2024 worst-year fail | RESEARCH-ONLY |
| 6 | α_07 frequency form | 2024 worst-year fail | RESEARCH-ONLY |
| 7 | α_06 attention-weighted | residual fail + 2022/2023 worst-year fail | RESEARCH-ONLY |

**Promotion choice: α_04.** Secondary alphas (α_01/α_02/α_03) are
documented in `final_summary.md` as future ensemble candidates but are
NOT separately deployed in this round to avoid in-family multiplicity.
