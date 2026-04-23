# Backtest Results — Batch 0002 (Round 2)

Session: 20260423_a_share_asset_growth_investment
Parent: Round 1 winner `f5_ag_2y_ind` (IC t-stat 17.08 at h=60)
Rebalance: quarterly (63 trading days); Cost: 5 bps/side; Delay: 1
Panel: 2020-01-02 .. 2025-04-18

## Summary (long-only excess vs equal-weight universe)

```
                name     factor  sharpe_excess  ann_ret_excess  sharpe_abs  ann_ret_abs  worst_year_excess  invested_share  ann_turnover  n_rebals  n_years
0         r2_q5_ew_q         f5          0.279           0.029       0.674        0.170             -0.717           0.950         1.552        21        6
1         r2_q5_rw_q         f5          0.293           0.032       0.681        0.173             -0.746           0.950         1.574        21        6
2  r2_q5_ew_q_regime         f5         -0.014          -0.002       0.616        0.139             -1.179           0.745         1.946        21        6
3   r2_q5_ew_q_liqfl         f5         -0.523          -0.052       0.372        0.089             -3.128           0.950         1.993        21        6
4  r2_q5_ew_q_sresid  f5_sresid          0.028           0.002       0.525        0.129             -0.831           0.949         1.486        20        6
5        r2_q10_ew_q         f5          0.252           0.028       0.663        0.169             -0.727           0.950         1.660        21        6
6   r2_q5_ew_q_combo    f_combo          0.257           0.027       0.665        0.168             -0.912           0.950         1.670        21        6
7     r2_q5_ew_q_all  f5_sresid         -0.592          -0.080       0.241        0.047             -2.470           0.709         1.875        20        6
```

## Per-year Sharpe (long-only excess)

```
year               2020  2021  2022  2023  2024  2025
name                                                 
r2_q10_ew_q       -0.19  1.67  0.88  0.90  0.26 -0.73
r2_q5_ew_q        -0.06  2.13  0.75  1.35  0.14 -0.72
r2_q5_ew_q_all    -0.81 -0.82 -2.47 -2.46  0.69 -1.18
r2_q5_ew_q_combo  -0.10  1.85  0.83  1.36  0.16 -0.91
r2_q5_ew_q_liqfl  -0.28 -0.64 -1.88 -2.59 -0.26 -3.13
r2_q5_ew_q_regime -0.87  1.34  0.75  1.35  1.07 -1.18
r2_q5_ew_q_sresid -0.02  0.57 -0.23  0.02  0.18 -0.83
r2_q5_rw_q        -0.14  2.08  0.83  1.16  0.21 -0.75
```

## Per-year abs return

```
year               2020  2021   2022  2023  2024  2025
name                                                  
r2_q10_ew_q       0.210 0.361  0.002 0.127 0.103 0.325
r2_q5_ew_q        0.239 0.358 -0.012 0.131 0.089 0.341
r2_q5_ew_q_all    0.013 0.179 -0.129 0.015 0.166 0.000
r2_q5_ew_q_combo  0.230 0.348 -0.006 0.134 0.091 0.330
r2_q5_ew_q_liqfl  0.191 0.236 -0.101 0.020 0.068 0.226
r2_q5_ew_q_regime 0.029 0.409 -0.012 0.131 0.171 0.000
r2_q5_ew_q_sresid 0.181 0.273 -0.047 0.095 0.091 0.337
r2_q5_rw_q        0.222 0.373 -0.004 0.133 0.097 0.330
```

## Best-year-out audit (top 3 by headline Sharpe)

```
               name  headline_sharpe  best_year  approx_ex_best_sharpe  ratio
0        r2_q5_rw_q            0.293       2021                  0.439  1.500
1        r2_q5_ew_q            0.279       2021                  0.464  1.665
2  r2_q5_ew_q_combo            0.257       2021                  0.469  1.825
```

## Notes

- `r2_q5_ew_q_regime` uses CSI300-proxy 6m market return threshold of 20%; when triggered, position flattens (100% cash, 0% excess).
- `r2_q5_ew_q_liqfl` keeps only top 60% by circ_mv before selecting Q5.
- `r2_q5_ew_q_sresid` residualizes factor vs log(total_mv) by OLS per date (proper, unlike Round 1's failed median-demean in f3).
- `r2_q5_ew_q_combo` uses 0.6·f5_ag_2y_ind + 0.4·f2_ag_yoy_ind composite.
- `r2_q5_ew_q_all` stacks regime + liquidity + size-residualization.
