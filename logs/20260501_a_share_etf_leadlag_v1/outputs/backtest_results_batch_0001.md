# Backtest Results — Batch 0001 (LeadLag Spillover v1)

Window: 2019-01-02 → 2026-04-30 | Universe: 30 ETFs | Leaders: ['510300.SS', '510500.SS', '159915.SZ'] | Beta window: 60d | Primary k: 1 | Delay: 1 | Cost: 5.0 bps/side

## IC table (mean / t-stat by horizon)

| expr | k | ic_mean | ic_t | n_days |
|---|---:|---:|---:|---:|
| g1_spillover_3leader_lag1 | 1 | 0.0006 | 0.05 | 1650 |
| g1_spillover_3leader_lag1 | 2 | 0.0005 | 0.05 | 1648 |
| g1_spillover_3leader_lag1 | 3 | -0.0048 | -0.44 | 1646 |
| g1_spillover_3leader_lag1 | 5 | -0.0083 | -0.77 | 1642 |
| g2_spillover_510300only_lag1 | 1 | 0.0212 | 2.09 | 1645 |
| g2_spillover_510300only_lag1 | 2 | 0.0168 | 1.69 | 1643 |
| g2_spillover_510300only_lag1 | 3 | 0.0112 | 1.12 | 1641 |
| g2_spillover_510300only_lag1 | 5 | -0.0044 | -0.44 | 1637 |
| g3_spillover_3leader_lag1to2_decay | 1 | 0.0052 | 0.47 | 1650 |
| g3_spillover_3leader_lag1to2_decay | 2 | -0.0082 | -0.76 | 1648 |
| g3_spillover_3leader_lag1to2_decay | 3 | -0.0042 | -0.38 | 1646 |
| g3_spillover_3leader_lag1to2_decay | 5 | -0.0082 | -0.76 | 1642 |
| g4_spillover_residual_leader_lag1 | 1 | 0.0072 | 0.66 | 1650 |
| g4_spillover_residual_leader_lag1 | 2 | -0.0035 | -0.32 | 1648 |
| g4_spillover_residual_leader_lag1 | 3 | -0.0061 | -0.56 | 1646 |
| g4_spillover_residual_leader_lag1 | 5 | -0.0148 | -1.37 | 1642 |
| g5_spillover_3leader_lag1_volscaled | 1 | -0.0008 | -0.09 | 1650 |
| g5_spillover_3leader_lag1_volscaled | 2 | 0.0010 | 0.12 | 1648 |
| g5_spillover_3leader_lag1_volscaled | 3 | 0.0059 | 0.71 | 1646 |
| g5_spillover_3leader_lag1_volscaled | 5 | -0.0012 | -0.15 | 1642 |
| g6_spillover_3leader_orthogonalized | 1 | -0.0021 | -0.24 | 1650 |
| g6_spillover_3leader_orthogonalized | 2 | -0.0058 | -0.64 | 1648 |
| g6_spillover_3leader_orthogonalized | 3 | -0.0038 | -0.41 | 1646 |
| g6_spillover_3leader_orthogonalized | 5 | -0.0077 | -0.84 | 1642 |
| g7_spillover_signonly_3leader | 1 | 0.0070 | 0.64 | 1650 |
| g7_spillover_signonly_3leader | 2 | 0.0030 | 0.28 | 1648 |
| g7_spillover_signonly_3leader | 3 | 0.0011 | 0.10 | 1646 |
| g7_spillover_signonly_3leader | 5 | -0.0063 | -0.58 | 1642 |
| g8_kitchen_sink_rank | 1 | 0.0049 | 0.46 | 1650 |
| g8_kitchen_sink_rank | 2 | 0.0015 | 0.14 | 1648 |
| g8_kitchen_sink_rank | 3 | -0.0011 | -0.11 | 1646 |
| g8_kitchen_sink_rank | 5 | -0.0071 | -0.68 | 1642 |

## Long-Short summary (k=1)

| expr | sharpe_full | net_5bps | turnover_pct | s_train | s_val | s_test |
|---|---:|---:|---:|---:|---:|---:|
| g1_spillover_3leader_lag1 | -0.21 | -1.21 | 14349.8 | -0.17 | -1.22 | 0.03 |
| g2_spillover_510300only_lag1 | 0.45 | -0.49 | 12467.8 | 0.66 | 0.13 | 0.34 |
| g3_spillover_3leader_lag1to2_decay | 0.01 | -0.75 | 10818.4 | -0.39 | -0.87 | 0.68 |
| g4_spillover_residual_leader_lag1 | -0.01 | -1.00 | 14365.8 | -0.17 | -0.46 | 0.30 |
| g5_spillover_3leader_lag1_volscaled | 0.10 | -1.15 | 15123.8 | 0.01 | -0.14 | 0.27 |
| g6_spillover_3leader_orthogonalized | -0.42 | -1.76 | 17793.1 | -1.14 | -0.35 | 0.34 |
| g7_spillover_signonly_3leader | -0.05 | -1.10 | 14154.9 | -0.19 | -0.95 | 0.34 |
| g8_kitchen_sink_rank | 0.17 | -0.93 | 15096.2 | 0.10 | -0.53 | 0.44 |

## Long-only Q5 excess (k=1)

| expr | sharpe_longonly | sharpe_excess | s_excess_train | s_excess_val | s_excess_test |
|---|---:|---:|---:|---:|---:|
| g1_spillover_3leader_lag1 | 0.49 | -0.06 | -0.11 | -0.55 | 0.16 |
| g2_spillover_510300only_lag1 | 0.59 | 0.10 | 0.19 | 0.28 | -0.05 |
| g3_spillover_3leader_lag1to2_decay | 0.54 | 0.00 | -0.32 | -0.60 | 0.65 |
| g4_spillover_residual_leader_lag1 | 0.62 | 0.11 | -0.18 | -0.30 | 0.67 |
| g5_spillover_3leader_lag1_volscaled | 0.63 | 0.09 | -0.17 | -0.57 | 0.70 |
| g6_spillover_3leader_orthogonalized | 0.33 | -0.31 | -0.97 | -0.56 | 0.61 |
| g7_spillover_signonly_3leader | 0.36 | -0.29 | -0.64 | -0.20 | 0.13 |
| g8_kitchen_sink_rank | 0.57 | 0.06 | -0.25 | 0.11 | 0.48 |

## Per-year LS Sharpe

| expr                                |   2019 |   2020 |   2021 |   2022 |   2023 |   2024 |   2025 |   2026 |
|:------------------------------------|-------:|-------:|-------:|-------:|-------:|-------:|-------:|-------:|
| g1_spillover_3leader_lag1           |  -0.52 |  -0.02 |  -0.08 |  -1.22 |   0.68 |  -0.04 |  -0.66 |   0.46 |
| g2_spillover_510300only_lag1        |   0.61 |   1.17 |   0.3  |   0.13 |   1.26 |   0.09 |   1.5  |  -3.53 |
| g3_spillover_3leader_lag1to2_decay  |  -1.73 |   0.05 |   0.09 |  -0.87 |   1.3  |  -0.07 |   0.61 |   1.92 |
| g4_spillover_residual_leader_lag1   |  -1.21 |   0.17 |   0.19 |  -0.46 |   0.41 |   0.33 |  -0.04 |   0.92 |
| g5_spillover_3leader_lag1_volscaled |   0.31 |  -0.22 |   0.01 |  -0.14 |   0.69 |   1.24 |  -2.24 |   0.5  |
| g6_spillover_3leader_orthogonalized |  -0.68 |  -0.31 |  -2    |  -0.35 |   0.5  |   0.36 |   1.08 |  -1.68 |
| g7_spillover_signonly_3leader       |  -0.21 |   0.46 |  -0.87 |  -0.95 |   0.31 |   0.58 |   0.3  |  -0.48 |
| g8_kitchen_sink_rank                |  -0.15 |   0.26 |   0.14 |  -0.53 |   0.67 |   0.98 |  -0.62 |   0.49 |

## Validation gates

| expr | G1 | G2 | G3 | G4 | ic_t@k=0 | ic_t@k=1 |
|---|---|---|---|---|---:|---:|
| g1_spillover_3leader_lag1 | pass | pass | fail | fail | -3.58 | 0.05 |
| g2_spillover_510300only_lag1 | pass | pass | fail | pass | -4.10 | 2.09 |
| g3_spillover_3leader_lag1to2_decay | pass | pass | fail | fail | -3.46 | 0.47 |
| g4_spillover_residual_leader_lag1 | pass | pass | fail | fail | -2.80 | 0.66 |
| g5_spillover_3leader_lag1_volscaled | pass | pass | fail | fail | -1.77 | -0.09 |
| g6_spillover_3leader_orthogonalized | pass | pass | fail | fail | -0.13 | -0.24 |
| g7_spillover_signonly_3leader | pass | pass | fail | fail | -3.80 | 0.64 |
| g8_kitchen_sink_rank | pass | pass | fail | fail | -3.59 | 0.46 |

G5 (batch-level horizon consistency): **pass** (7/8 peak at primary k=1)

## Floors

| expr | wy_sharpe | wy_pass | byo_avg | byo_pass |
|---|---:|---|---:|---|
| g1_spillover_3leader_lag1 | -1.22 | False | -0.30 | False |
| g2_spillover_510300only_lag1 | -3.53 | False | 0.00 | False |
| g3_spillover_3leader_lag1to2_decay | -1.73 | False | -0.09 | False |
| g4_spillover_residual_leader_lag1 | -1.21 | False | -0.09 | False |
| g5_spillover_3leader_lag1_volscaled | -2.24 | False | -0.16 | False |
| g6_spillover_3leader_orthogonalized | -2.00 | False | -0.59 | False |
| g7_spillover_signonly_3leader | -0.95 | False | -0.21 | False |
| g8_kitchen_sink_rank | -0.62 | False | 0.04 | False |