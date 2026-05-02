# Backtest R2 — IVOL-momentum standalone PROMOTE attempt

Targeted at rescuing 2024 worst-year via narrative-collapse-aware gates.

## Summary

| expr | type | gross | net@5bps | excess | s_train | s_val | s_test | turnover% |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| r2_topN_no_gate | topN | 0.76 | 0.75 | 0.38 | 1.26 | -0.25 | 0.68 | 464 |
| r2_topN_RS_gate | topN | 0.63 | 0.61 | -0.12 | 1.02 | 0.17 | 0.40 | 464 |
| r2_topN_disp_gate | topN | 0.27 | 0.24 | -0.50 | 0.83 | -1.00 | 0.06 | 464 |
| r2_topN_persist | topN | 0.69 | 0.68 | 0.51 | 1.23 | -0.35 | 0.60 | 387 |
| r2_topN_RS_persist | topN | 0.54 | 0.53 | -0.08 | 0.94 | 0.06 | 0.29 | 387 |
| r2_LS_voltarget_10 | LS_vt | 0.85 | 0.81 | n/a | 0.99 | 0.16 | 0.94 | 302 |
| r2_topN_RS_voltarget | topN_vt | 0.59 | 0.57 | -0.26 | 1.01 | 0.26 | 0.32 | 392 |
| r2_kitchen_sink | topN_vt | 0.45 | 0.44 | -0.32 | 0.81 | 0.18 | 0.24 | 314 |

## Per-year Sharpe

| expr                 |   2019 |   2020 |   2021 |   2022 |   2023 |   2024 |   2025 |   2026 |
|:---------------------|-------:|-------:|-------:|-------:|-------:|-------:|-------:|-------:|
| r2_LS_voltarget_10   |   2.31 |   1    |   0.5  |   0.16 |   0.41 |   0.42 |   2.31 | nan    |
| r2_kitchen_sink      |   1.09 |   1.26 |   0.43 |   0.18 |  -0.46 |  -0.07 |   1.48 | nan    |
| r2_topN_RS_gate      |   1.69 |   1.08 |   0.7  |   0.17 |  -0.2  |  -0.24 |   1.35 |   0.75 |
| r2_topN_RS_persist   |   1.16 |   1.08 |   0.71 |   0.06 |  -0.19 |  -0.45 |   1.14 | nan    |
| r2_topN_RS_voltarget |   2.16 |   1.27 |   0.44 |   0.26 |  -0.51 |   0.06 |   1.69 | nan    |
| r2_topN_disp_gate    | nan    |   0.89 |   1.06 |  -1    |  -0.76 |   0.12 |   0.64 |   0.75 |
| r2_topN_no_gate      |   2.53 |   1.69 |   0.44 |  -0.25 |  -0.06 |   0.46 |   2.03 |   0.75 |
| r2_topN_persist      |   1.41 |   1.74 |   0.67 |  -0.35 |  -0.11 |   0.38 |   1.83 | nan    |

## Floors (worst-year >= 0.5 is the binding gate)

| expr | wy | wy_pass | byo_avg | byo_pass |
|---|---:|---|---:|---|
| r2_topN_no_gate | -0.25 | False | 0.72 | True |
| r2_topN_RS_gate | -0.24 | False | 0.52 | True |
| r2_topN_disp_gate | -1.00 | False | 0.11 | False |
| r2_topN_persist | -0.35 | False | 0.62 | True |
| r2_topN_RS_persist | -0.45 | False | 0.39 | True |
| r2_LS_voltarget_10 | 0.16 | False | 0.80 | True |
| r2_topN_RS_voltarget | -0.51 | False | 0.53 | True |
| r2_kitchen_sink | -0.46 | False | 0.40 | True |