# Backtest Results — Batch 0001

Session: 20260423_a_share_asset_growth_investment
Agent: 4 Backtest Operator
Rebalance: monthly (21 trading days); Cost: 5 bps/side; Delay: 1
Panel: 2020-01-02 .. 2025-04-18 (inherited from accruals session)

## Execution-delay audit
- invariant: fwd_ret_1 at t = close_{t+1}/close_t - 1, compatible with delay=1 (signal at t, trade at t+1)
- future-perturbation test: **PASSED**
- last-day fwd_ret_1 NaN share: 1.00 (expected high — can't observe t+1 close)
- panel inherited from: 20260420_fundamental_accruals_alpha

## IC by horizon (Spearman rank-IC, full sample)

```
horizon             fwd_ret_1  fwd_ret_20  fwd_ret_5  fwd_ret_60
factor                                                          
f1_ag_yoy_raw          0.0052      0.0209     0.0101      0.0423
f2_ag_yoy_ind          0.0042      0.0183     0.0085      0.0352
f3_ag_yoy_ind_size     0.0018      0.0090     0.0033      0.0193
f4_ag_log_yoy_ind      0.0042      0.0183     0.0084      0.0352
f5_ag_2y_ind           0.0064      0.0231     0.0115      0.0438
f6_ag_qoq_ind         -0.0007      0.0006    -0.0005      0.0038
f7_ag_rank_ind         0.0035      0.0157     0.0071      0.0299
f8_ag_composite        0.0042      0.0183     0.0085      0.0352
```

### IC t-stat (full sample)

```
horizon             fwd_ret_1  fwd_ret_20  fwd_ret_5  fwd_ret_60
factor                                                          
f1_ag_yoy_raw            1.92        6.62       3.56       12.86
f2_ag_yoy_ind            1.99        7.14       3.76       12.70
f3_ag_yoy_ind_size       1.19        4.98       2.03       10.30
f4_ag_log_yoy_ind        1.97        7.14       3.75       12.70
f5_ag_2y_ind             2.78        9.19       4.89       17.08
f6_ag_qoq_ind           -0.47        0.34      -0.30        1.96
f7_ag_rank_ind           1.82        6.64       3.46       11.65
f8_ag_composite          1.98        7.14       3.75       12.70
```

## LS + Q5 long-only (monthly rebal, after 5 bps/side)

```
               factor  sharpe_ls  ann_ret_ls  sharpe_q5_excess  ann_ret_q5_excess  worst_year_sharpe_ls  worst_year_sharpe_q5_excess  n_years
0       f1_ag_yoy_raw      0.619       0.064             0.395              0.022                -1.594                       -1.410        6
1       f2_ag_yoy_ind      0.637       0.054             0.299              0.014                -1.710                       -1.541        6
2  f3_ag_yoy_ind_size      0.241       0.015            -0.471             -0.014                -2.443                       -2.138        6
3   f4_ag_log_yoy_ind      0.655       0.056             0.319              0.015                -1.694                       -1.582        6
4        f5_ag_2y_ind      0.825       0.074             0.594              0.029                -1.244                       -0.636        6
5       f6_ag_qoq_ind     -0.032      -0.002            -0.247             -0.007                -2.452                       -2.257        6
6      f7_ag_rank_ind      0.524       0.038             0.286              0.012                -1.908                       -1.757        6
7     f8_ag_composite      0.651       0.056             0.311              0.014                -1.673                       -1.536        6
```

## Annual LS Sharpe

```
year                2020  2021  2022  2023  2024  2025
factor                                                
f1_ag_yoy_raw      -1.56  1.62  1.37  1.54  0.24 -1.59
f2_ag_yoy_ind      -1.68  1.85  1.36  2.19  0.21 -1.71
f3_ag_yoy_ind_size -2.03  1.66  0.94  1.02  0.01 -2.44
f4_ag_log_yoy_ind  -1.67  1.95  1.38  2.17  0.19 -1.69
f5_ag_2y_ind       -1.18  1.83  1.37  1.57  0.67 -1.24
f6_ag_qoq_ind      -2.45  1.11  0.42  1.76 -0.58 -0.39
f7_ag_rank_ind     -1.91  1.97  1.16  2.30  0.37 -1.70
f8_ag_composite    -1.67  1.95  1.37  2.13  0.20 -1.66
```

## Annual Q5-excess Sharpe

```
year                2020  2021  2022  2023  2024  2025
factor                                                
f1_ag_yoy_raw      -1.41  1.57  1.24  0.81  0.07 -1.26
f2_ag_yoy_ind      -1.54  1.78  0.83  1.65 -0.06 -1.28
f3_ag_yoy_ind_size -2.14  1.30 -0.67 -0.05 -0.30 -1.76
f4_ag_log_yoy_ind  -1.58  1.81  0.92  1.62 -0.07 -1.18
f5_ag_2y_ind       -0.64  2.06  0.77  1.38  0.18 -0.59
f6_ag_qoq_ind      -2.26  1.47 -0.32  0.65 -0.61  0.00
f7_ag_rank_ind     -1.76  1.84  0.59  2.03 -0.08 -0.85
f8_ag_composite    -1.54  1.84  0.86  1.57 -0.07 -1.26
```
