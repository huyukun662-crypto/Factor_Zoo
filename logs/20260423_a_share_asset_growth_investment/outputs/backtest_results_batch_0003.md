# Backtest Results — Batch 0003 (Round 3)

Session: 20260423_a_share_asset_growth_investment
Mechanism: Investment anomaly / NSI (financing channel) + AG-NSI composite
Rebalance: monthly (21 trading days); Cost: 5 bps/side; Delay: 1
Panel: 2020-01-02 .. 2025-04-18

## Correlations (candidate factors vs AG 1y/2y)

```
                    f2    f5    g1    g2    g3    g4  cma_2y  cma_triple  ag_orth_plus_nsi    g5
f2               1.000 0.629 0.393 0.393 0.402 0.290   0.535       0.798             0.608 0.347
f5               0.629 1.000 0.323 0.323 0.325 0.486   0.849       0.821             0.942 0.262
g1               0.393 0.323 1.000 0.999 0.995 0.671   0.593       0.714             0.483 0.675
g2               0.393 0.323 0.999 1.000 0.996 0.671   0.593       0.714             0.483 0.678
g3               0.402 0.325 0.995 0.996 1.000 0.669   0.594       0.720             0.485 0.706
g4               0.290 0.486 0.671 0.671 0.669 1.000   0.859       0.623             0.706 0.461
cma_2y           0.535 0.849 0.593 0.593 0.594 0.859   1.000       0.848             0.961 0.436
cma_triple       0.798 0.821 0.714 0.714 0.720 0.623   0.848       1.000             0.870 0.543
ag_orth_plus_nsi 0.608 0.942 0.483 0.483 0.485 0.706   0.961       0.870             1.000 0.370
g5               0.347 0.262 0.675 0.678 0.706 0.461   0.436       0.543             0.370 1.000
```

## IC by horizon (Spearman)

```
horizon          fwd_ret_1  fwd_ret_20  fwd_ret_5  fwd_ret_60
factor                                                       
r3_ag_orth_nsi      0.0078      0.0249     0.0137      0.0446
r3_cma_2y           0.0079      0.0227     0.0131      0.0428
r3_cma_triple       0.0050      0.0288     0.0112      0.0462
r3_nsi_2y_ind       0.0064      0.0139     0.0092      0.0266
r3_nsi_log_ind      0.0077      0.0217     0.0125      0.0373
r3_nsi_rank_ind     0.0073      0.0203     0.0117      0.0345
r3_nsi_yoy_ind      0.0077      0.0217     0.0125      0.0373
r3_nsi_yoy_raw      0.0085      0.0239     0.0139      0.0415
```

### IC t-stat

```
horizon          fwd_ret_1  fwd_ret_20  fwd_ret_5  fwd_ret_60
factor                                                       
r3_ag_orth_nsi        3.41       10.17       5.84       18.24
r3_cma_2y             3.70        9.74       5.97       18.86
r3_cma_triple         1.66        9.45       3.85       14.23
r3_nsi_2y_ind         4.97        9.84       6.95       20.70
r3_nsi_log_ind        5.16       13.47       7.97       24.70
r3_nsi_rank_ind       5.04       13.15       7.75       23.87
r3_nsi_yoy_ind        5.16       13.47       7.97       24.70
r3_nsi_yoy_raw        5.02       13.06       7.84       24.18
```

## Q5 long-only excess (monthly rebal, 5 bps/side)

```
              name        factor_col  sharpe_excess  ann_ret_excess  sharpe_abs  ann_ret_abs  worst_year_sharpe  ann_turnover  n_years
0   r3_nsi_yoy_raw                g1          0.186           0.007       0.614        0.140             -2.266         1.741        6
1   r3_nsi_yoy_ind                g2          0.178           0.005       0.587        0.138             -2.681         2.461        6
2   r3_nsi_log_ind                g3          0.178           0.005       0.587        0.138             -2.681         2.461        6
3    r3_nsi_2y_ind                g4          0.069           0.007       0.583        0.148             -0.375         2.677        6
4        r3_cma_2y            cma_2y          0.284           0.028       0.670        0.169             -0.535         2.364        6
5    r3_cma_triple        cma_triple          0.255           0.026       0.659        0.167             -0.695         2.486        6
6   r3_ag_orth_nsi  ag_orth_plus_nsi          0.860           0.052       0.700        0.179             -0.609         2.189        6
7  r3_nsi_rank_ind                g5          0.178           0.005       0.587        0.138             -2.681         2.461        6
```

## Annual Sharpe (Q5-excess)

```
year             2020  2021  2022  2023  2024  2025
name                                               
r3_ag_orth_nsi   1.04  2.02  0.97  1.52  0.24 -0.61
r3_cma_2y       -0.12  2.10  0.84  1.50  0.28 -0.53
r3_cma_triple   -0.17  1.90  0.84  1.54  0.07 -0.70
r3_nsi_2y_ind   -0.13  0.91 -0.27 -0.38  0.92  0.63
r3_nsi_log_ind   0.29  0.89  1.08 -0.70  0.40 -2.68
r3_nsi_rank_ind  0.29  0.89  1.08 -0.70  0.40 -2.68
r3_nsi_yoy_ind   0.29  0.89  1.08 -0.70  0.40 -2.68
r3_nsi_yoy_raw  -0.07  1.28  0.75 -0.00  0.16 -2.27
```

## Annual abs return

```
year             2020  2021   2022  2023  2024  2025
name                                                
r3_ag_orth_nsi  0.283 0.351 -0.004 0.135 0.097 0.345
r3_cma_2y       0.226 0.351 -0.011 0.133 0.099 0.349
r3_cma_triple   0.216 0.350 -0.004 0.139 0.084 0.342
r3_nsi_2y_ind   0.225 0.289 -0.050 0.082 0.122 0.406
r3_nsi_log_ind  0.217 0.270 -0.013 0.078 0.099 0.278
r3_nsi_rank_ind 0.217 0.270 -0.013 0.078 0.099 0.278
r3_nsi_yoy_ind  0.217 0.270 -0.013 0.078 0.099 0.278
r3_nsi_yoy_raw  0.211 0.280 -0.011 0.094 0.090 0.273
```

## Best-year-out audit (proper, from daily series)

```
              name  headline  best_year  ex_best_sharpe  ratio
0   r3_nsi_yoy_raw     0.186       2021           0.059  0.319
1   r3_nsi_yoy_ind     0.178       2022          -0.012 -0.068
2   r3_nsi_log_ind     0.178       2022          -0.012 -0.068
3    r3_nsi_2y_ind     0.069       2024          -0.018 -0.265
4        r3_cma_2y     0.284       2021           0.119  0.420
5    r3_cma_triple     0.255       2021           0.091  0.357
6   r3_ag_orth_nsi     0.860       2021           0.661  0.769
7  r3_nsi_rank_ind     0.178       2022          -0.012 -0.068
```
