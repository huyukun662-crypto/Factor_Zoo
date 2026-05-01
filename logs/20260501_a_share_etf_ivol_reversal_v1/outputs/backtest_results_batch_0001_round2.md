# Round 2 — IVOL evaluated at k=1 (revised primary horizon)

## Round-2 LS / long-only at k=1, daily rebalance, 5 bps/side

| expr | LS gross | LS net@5bps | LS train | LS val | LS test | longonly | excess | turnover% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| f1_ivol_resid_20d | -0.61 | -0.73 | -0.97 | 0.73 | -0.60 | 0.47 | -0.69 | 1074 |
| f2_total_vol_20d | -0.67 | -0.82 | -0.98 | -0.35 | -0.51 | 0.68 | -0.61 | 1622 |
| f3_ivol_resid_10d | -0.59 | -0.80 | -1.30 | 0.59 | -0.25 | 0.44 | -0.53 | 2102 |
| f4_ivol_resid_40d | -0.66 | -0.72 | -1.05 | -0.28 | -0.44 | 0.56 | -0.55 | 555 |
| f5_ivol_resid_amp_20d | -0.67 | -0.79 | -0.98 | -0.08 | -0.55 | 0.44 | -0.72 | 1147 |
| f6_ivol_lag5_20d | -0.67 | -0.79 | -0.88 | -0.18 | -0.58 | 0.43 | -0.72 | 1066 |
| f7_vol_of_vol_20m40 | -0.29 | -0.61 | 0.28 | 0.39 | -1.06 | 0.61 | -0.06 | 3810 |
| f8_kitchen_sink_rank | -0.65 | -0.86 | -0.83 | -0.46 | -0.53 | 0.41 | -0.78 | 2254 |

## Per-year LS Sharpe

| expr                  |   2019 |   2020 |   2021 |   2022 |   2023 |   2024 |   2025 |   2026 |
|:----------------------|-------:|-------:|-------:|-------:|-------:|-------:|-------:|-------:|
| f1_ivol_resid_20d     |  -1.5  |  -1.35 |  -0.42 |   0.73 |  -0.19 |  -0.33 |  -1.47 | nan    |
| f2_total_vol_20d      |  -1.23 |  -1.32 |  -0.24 |  -0.35 |  -0.2  |   0.06 |  -1.59 |  -1.43 |
| f3_ivol_resid_10d     |  -0.84 |  -1.97 |  -0.96 |   0.59 |  -0.3  |   0.38 |  -1.69 |   1.36 |
| f4_ivol_resid_40d     |  -1.56 |  -1.65 |  -0.29 |  -0.28 |  -0.32 |   0.22 |  -1.83 | nan    |
| f5_ivol_resid_amp_20d |  -1.49 |  -1.25 |  -0.51 |  -0.08 |  -0.51 |  -0.1  |  -1.14 | nan    |
| f6_ivol_lag5_20d      |  -1.39 |  -1.4  |  -0.35 |  -0.18 |  -0.85 |   0.33 |  -1.32 | nan    |
| f7_vol_of_vol_20m40   |   0.19 |   0.52 |   0.19 |   0.39 |  -0.24 |  -1.96 |   0.03 | nan    |
| f8_kitchen_sink_rank  |  -0.86 |  -1.26 |  -0.58 |  -0.46 |  -0.3  |  -0.4  |  -0.85 | nan    |

## Floors

| expr | wy_sharpe | wy_pass | byo_avg | byo_pass |
|---|---:|---|---:|---|
| f1_ivol_resid_20d | -1.50 | False | -0.88 | False |
| f2_total_vol_20d | -1.59 | False | -0.91 | False |
| f3_ivol_resid_10d | -1.97 | False | -0.68 | False |
| f4_ivol_resid_40d | -1.83 | False | -0.99 | False |
| f5_ivol_resid_amp_20d | -1.49 | False | -0.83 | False |
| f6_ivol_lag5_20d | -1.40 | False | -0.91 | False |
| f7_vol_of_vol_20m40 | -1.96 | False | -0.23 | False |
| f8_kitchen_sink_rank | -1.26 | False | -0.73 | False |