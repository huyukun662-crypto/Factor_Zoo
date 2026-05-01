# Backtest Results — Inverted IVOL Momentum, Batch 0001

Window: 2019-01-02 → 2026-04-30 | Universe: 30 ETFs | Bench: 510300.SS | Primary k: 20 | Rebalance: 21d | Cost: 5.0 bps/side

## Summary

| expr | type | gate | gross | net@5bps | excess vs EW | turnover% | s_train | s_val | s_test |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| m1_ivol_LS_no_gate | LS | none | 0.66 | 0.63 | n/a | 431 | 1.02 | 0.18 | 0.48 |
| m3_ivol_LS_ma50_gate | LS | ma50 | 0.44 | 0.41 | n/a | 431 | 0.58 | 0.96 | 0.26 |
| m2_ivol_top3_no_gate | topN | none | 0.58 | 0.56 | 0.13 | 558 | 0.79 | -0.17 | 0.60 |
| m4_ivol_top3_ma50_gate | topN | ma50 | 0.44 | 0.43 | -0.25 | 558 | 0.43 | 0.95 | 0.40 |
| m5_ivol_top5_ma50_gate | topN | ma50 | 0.51 | 0.49 | -0.27 | 464 | 0.53 | 0.88 | 0.44 |
| m6_ivol_top5_ma200_gate | topN | ma200 | 0.83 | 0.82 | 0.10 | 464 | 1.14 | nan | 0.69 |
| m7_ivol_top5_ma50_lag5 | topN | ma50 | 0.49 | 0.48 | -0.30 | 464 | 0.58 | 0.80 | 0.38 |
| m8_total_vol_top5_ma50 | topN | ma50 | 0.19 | 0.18 | -0.53 | 537 | 0.11 | 0.66 | 0.22 |

## Per-year Sharpe

| expr                    |   2019 |   2020 |   2021 |   2022 |   2023 |   2024 |   2025 |   2026 |
|:------------------------|-------:|-------:|-------:|-------:|-------:|-------:|-------:|-------:|
| m1_ivol_LS_no_gate      |   1.83 |   0.93 |   0.76 |   0.18 |   0.19 |   0.04 |   1.56 |   0.71 |
| m2_ivol_top3_no_gate    |   2.71 |   1.42 |  -0.8  |  -0.17 |   0.02 |   0.28 |   1.89 |   0.94 |
| m3_ivol_LS_ma50_gate    |   1.47 |   0.79 |  -0.24 |   0.96 |   0.24 |  -0.34 |   1.02 |  -0.15 |
| m4_ivol_top3_ma50_gate  |   1.39 |   1.16 |  -1.21 |   0.95 |   0.41 |  -0.33 |   1.26 |  -1.19 |
| m5_ivol_top5_ma50_gate  |   1.3  |   1.25 |  -0.8  |   0.88 |   0.11 |  -0.17 |   1.38 |  -1.2  |
| m6_ivol_top5_ma200_gate |   1.77 |   1.17 |   0.97 | nan    |   0.34 |  -0.55 |   1.98 |   0.75 |
| m7_ivol_top5_ma50_lag5  |   1.28 |   1.26 |  -0.71 |   0.8  |  -0.06 |  -0.21 |   1.24 |  -0.55 |
| m8_total_vol_top5_ma50  |  -0.11 |   0.97 |  -0.99 |   0.66 |  -0.06 |  -0.4  |   1.46 |  -2.08 |

## Floors

| expr | wy_sharpe | wy_pass | byo_avg | byo_pass |
|---|---:|---|---:|---|
| m1_ivol_LS_no_gate | 0.04 | False | 0.62 | True |
| m3_ivol_LS_ma50_gate | -0.34 | False | 0.33 | True |
| m2_ivol_top3_no_gate | -0.80 | False | 0.51 | True |
| m4_ivol_top3_ma50_gate | -1.21 | False | 0.15 | False |
| m5_ivol_top5_ma50_gate | -1.20 | False | 0.19 | False |
| m6_ivol_top5_ma200_gate | -0.55 | False | 0.74 | True |
| m7_ivol_top5_ma50_lag5 | -0.71 | False | 0.25 | True |
| m8_total_vol_top5_ma50 | -2.08 | False | -0.29 | False |

## V7_gold orthogonality (weekly)

| expr | corr_v7_gold | n_weeks | |corr| ≤ 0.5 |
|---|---:|---:|---|
| m1_ivol_LS_no_gate | 0.053 | 339 | True |
| m3_ivol_LS_ma50_gate | 0.068 | 339 | True |
| m2_ivol_top3_no_gate | 0.071 | 339 | True |
| m4_ivol_top3_ma50_gate | 0.098 | 339 | True |
| m5_ivol_top5_ma50_gate | 0.091 | 339 | True |
| m6_ivol_top5_ma200_gate | 0.068 | 339 | True |
| m7_ivol_top5_ma50_lag5 | 0.088 | 339 | True |
| m8_total_vol_top5_ma50 | 0.101 | 339 | True |

## Validation gates

| expr | G1 | G2 | G3 | G4 |
|---|---|---|---|---|
| m1_ivol_LS_no_gate | pass | pass | pass | pass |
| m3_ivol_LS_ma50_gate | pass | pass | pass | pass |
| m2_ivol_top3_no_gate | pass | pass | fail | pass |
| m4_ivol_top3_ma50_gate | pass | pass | fail | fail |
| m5_ivol_top5_ma50_gate | pass | pass | fail | fail |
| m6_ivol_top5_ma200_gate | pass | pass | fail | pass |
| m7_ivol_top5_ma50_lag5 | pass | pass | fail | fail |
| m8_total_vol_top5_ma50 | pass | pass | fail | fail |