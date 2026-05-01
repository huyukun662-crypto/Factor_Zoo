# Backtest Results — Batch 0001 (IVOL-Reversal v1)

Window: 2019-01-02 → 2026-04-30 | Universe: 30 ETFs | Bench beta target: 510300.SS | Beta window: 60d | Primary k: 5 | Delay: 1 | Cost: 5.0 bps/side

## IC table (mean / t-stat by horizon)

| expr | k | ic_mean | ic_t | n_days |
|---|---:|---:|---:|---:|
| f1_ivol_resid_20d | 1 | 0.0271 | 3.19 | 1612 |
| f1_ivol_resid_20d | 5 | 0.0090 | 1.08 | 1604 |
| f1_ivol_resid_20d | 10 | -0.0052 | -0.62 | 1594 |
| f1_ivol_resid_20d | 20 | -0.0139 | -1.63 | 1574 |
| f2_total_vol_20d | 1 | 0.0148 | 1.57 | 1730 |
| f2_total_vol_20d | 5 | -0.0147 | -1.54 | 1722 |
| f2_total_vol_20d | 10 | -0.0196 | -2.05 | 1712 |
| f2_total_vol_20d | 20 | -0.0212 | -2.14 | 1692 |
| f3_ivol_resid_10d | 1 | 0.0252 | 3.01 | 1632 |
| f3_ivol_resid_10d | 5 | 0.0069 | 0.85 | 1624 |
| f3_ivol_resid_10d | 10 | -0.0108 | -1.31 | 1614 |
| f3_ivol_resid_10d | 20 | -0.0165 | -1.96 | 1594 |
| f4_ivol_resid_40d | 1 | 0.0251 | 2.91 | 1572 |
| f4_ivol_resid_40d | 5 | 0.0015 | 0.18 | 1564 |
| f4_ivol_resid_40d | 10 | -0.0143 | -1.68 | 1554 |
| f4_ivol_resid_40d | 20 | -0.0206 | -2.38 | 1534 |
| f5_ivol_resid_amp_20d | 1 | 0.0261 | 3.00 | 1612 |
| f5_ivol_resid_amp_20d | 5 | 0.0095 | 1.12 | 1604 |
| f5_ivol_resid_amp_20d | 10 | -0.0056 | -0.66 | 1594 |
| f5_ivol_resid_amp_20d | 20 | -0.0146 | -1.68 | 1574 |
| f6_ivol_lag5_20d | 1 | 0.0285 | 3.36 | 1607 |
| f6_ivol_lag5_20d | 5 | 0.0094 | 1.12 | 1599 |
| f6_ivol_lag5_20d | 10 | -0.0046 | -0.55 | 1589 |
| f6_ivol_lag5_20d | 20 | -0.0144 | -1.68 | 1569 |
| f7_vol_of_vol_20m40 | 1 | -0.0015 | -0.18 | 1572 |
| f7_vol_of_vol_20m40 | 5 | -0.0043 | -0.53 | 1564 |
| f7_vol_of_vol_20m40 | 10 | 0.0026 | 0.33 | 1554 |
| f7_vol_of_vol_20m40 | 20 | 0.0053 | 0.68 | 1534 |
| f8_kitchen_sink_rank | 1 | 0.0208 | 2.38 | 1572 |
| f8_kitchen_sink_rank | 5 | 0.0023 | 0.27 | 1564 |
| f8_kitchen_sink_rank | 10 | -0.0108 | -1.25 | 1554 |
| f8_kitchen_sink_rank | 20 | -0.0198 | -2.21 | 1534 |

## Long-Short summary (k=5)

| expr | sharpe_full | net_5bps | turnover_pct | s_train | s_val | s_test |
|---|---:|---:|---:|---:|---:|---:|
| f1_ivol_resid_20d | -0.76 | -0.77 | 493.5 | -1.14 | 0.13 | -0.64 |
| f2_total_vol_20d | -0.60 | -0.62 | 781.1 | -0.87 | -0.83 | -0.32 |
| f3_ivol_resid_10d | -0.67 | -0.70 | 948.0 | -1.29 | 0.21 | -0.33 |
| f4_ivol_resid_40d | -0.63 | -0.64 | 293.5 | -1.05 | -0.09 | -0.40 |
| f5_ivol_resid_amp_20d | -0.80 | -0.81 | 527.4 | -1.09 | -0.24 | -0.67 |
| f6_ivol_lag5_20d | -0.65 | -0.66 | 493.8 | -0.97 | -0.26 | -0.45 |
| f7_vol_of_vol_20m40 | -0.45 | -0.48 | 1838.2 | 0.26 | -0.67 | -1.06 |
| f8_kitchen_sink_rank | -0.68 | -0.71 | 970.4 | -0.78 | -0.60 | -0.62 |

## Long-only Q5 excess (k=5)

| expr | sharpe_longonly | sharpe_excess | s_excess_train | s_excess_val | s_excess_test |
|---|---:|---:|---:|---:|---:|
| f1_ivol_resid_20d | 0.40 | -0.97 | -1.86 | 0.30 | -0.39 |
| f2_total_vol_20d | 0.59 | -0.79 | -1.51 | -0.48 | -0.17 |
| f3_ivol_resid_10d | 0.36 | -0.89 | -1.65 | 0.12 | -0.31 |
| f4_ivol_resid_40d | 0.51 | -0.69 | -1.66 | 0.06 | -0.12 |
| f5_ivol_resid_amp_20d | 0.39 | -0.96 | -1.83 | -0.00 | -0.32 |
| f6_ivol_lag5_20d | 0.42 | -0.93 | -1.84 | -0.16 | -0.17 |
| f7_vol_of_vol_20m40 | 0.57 | -0.22 | 0.52 | -0.85 | -0.81 |
| f8_kitchen_sink_rank | 0.40 | -0.91 | -1.48 | -0.89 | -0.43 |

## Per-year LS Sharpe

| expr                  |   2019 |   2020 |   2021 |   2022 |   2023 |   2024 |   2025 |   2026 |
|:----------------------|-------:|-------:|-------:|-------:|-------:|-------:|-------:|-------:|
| f1_ivol_resid_20d     |  -1.38 |  -1.49 |  -0.66 |   0.13 |  -0.47 |  -0.19 |  -1.27 | nan    |
| f2_total_vol_20d      |  -1.12 |  -1.36 |  -0.01 |  -0.83 |   0.03 |   0.34 |  -1.37 |  -1.27 |
| f3_ivol_resid_10d     |  -1.01 |  -1.54 |  -1.2  |   0.21 |  -0.26 |   0.23 |  -1.39 |   0.43 |
| f4_ivol_resid_40d     |  -1.58 |  -1.4  |  -0.38 |  -0.09 |  -0.23 |   0.22 |  -1.47 | nan    |
| f5_ivol_resid_amp_20d |  -1.54 |  -1.13 |  -0.85 |  -0.24 |  -0.5  |  -0.38 |  -1.12 | nan    |
| f6_ivol_lag5_20d      |  -1.84 |  -1.25 |  -0.3  |  -0.26 |  -0.52 |   0.47 |  -1.26 | nan    |
| f7_vol_of_vol_20m40   |  -0.23 |   0.55 |   0.25 |  -0.67 |  -0.48 |  -2.16 |  -0.09 | nan    |
| f8_kitchen_sink_rank  |  -1.3  |  -1.2  |  -0.22 |  -0.6  |  -0.24 |  -0.59 |  -1.01 | nan    |

## Validation gates

| expr | G1 | G2 | G3 | G4 |
|---|---|---|---|---|
| f1_ivol_resid_20d | pass | pass | fail | fail |
| f2_total_vol_20d | pass | pass | fail | fail |
| f3_ivol_resid_10d | pass | pass | fail | fail |
| f4_ivol_resid_40d | pass | pass | fail | fail |
| f5_ivol_resid_amp_20d | pass | pass | fail | fail |
| f6_ivol_lag5_20d | pass | pass | fail | fail |
| f7_vol_of_vol_20m40 | pass | pass | fail | fail |
| f8_kitchen_sink_rank | pass | pass | fail | fail |

G5 (batch-level horizon consistency): **fail** (0/8 peak at primary k=5)

## Floors (worst year, best-year-out)

| expr | wy_sharpe | wy_pass | byo_avg | byo_pass |
|---|---:|---|---:|---|
| f1_ivol_resid_20d | -1.49 | False | -0.91 | False |
| f2_total_vol_20d | -1.37 | False | -0.85 | False |
| f3_ivol_resid_10d | -1.54 | False | -0.71 | False |
| f4_ivol_resid_40d | -1.58 | False | -0.86 | False |
| f5_ivol_resid_amp_20d | -1.54 | False | -0.92 | False |
| f6_ivol_lag5_20d | -1.84 | False | -0.90 | False |
| f7_vol_of_vol_20m40 | -2.16 | False | -0.56 | False |
| f8_kitchen_sink_rank | -1.30 | False | -0.82 | False |