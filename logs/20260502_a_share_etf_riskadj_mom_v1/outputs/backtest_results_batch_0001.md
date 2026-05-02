# Backtest Results — Batch 0001 — Risk-Adjusted Momentum on A-Share ETFs

**Agent 4 (Backtest Operator)** — generated programmatically.

- Universe: 158 ETFs (≥ 1000 bars)
- Window: 2019-01-02 → 2026-04-30
- Cost: 5 bps/side, monthly rebalance, hold 21d, delay 1d
- EW-universe Sharpe (gross): 0.594

## Headline metrics (net of 5 bps/side cost)

| expression                       |   sharpe_gross |   sharpe_net |   sharpe_excess_vs_EW |   sharpe_best_year_out |   best_year |   worst_year |   worst_year_sharpe |   annual_turnover |   IC_mean |   IC_t_stat |   IC_n |   ann_return_net |   ann_vol_net |   max_drawdown |
|:---------------------------------|---------------:|-------------:|----------------------:|-----------------------:|------------:|-------------:|--------------------:|------------------:|----------:|------------:|-------:|-----------------:|--------------:|---------------:|
| m1_riskadj_mom_60_top5           |          0.115 |        0.099 |                -0.383 |                 -0.134 |        2020 |         2026 |              -2.151 |             7.827 |   -0.0231 |      -0.68  |     83 |           0.025  |        0.2526 |        -0.4607 |
| m2_riskadj_mom_60_top3           |         -0.014 |       -0.029 |                -0.457 |                 -0.241 |        2020 |         2026 |              -2.886 |             8.305 |   -0.0231 |      -0.68  |     83 |          -0.008  |        0.2796 |        -0.5088 |
| m3_riskadj_mom_120_top5          |          0.401 |        0.389 |                -0.055 |                  0.128 |        2020 |         2022 |              -1.127 |             5.894 |    0.0254 |       0.672 |     80 |           0.0952 |        0.2445 |        -0.4424 |
| m4_riskadj_mom_20_top5           |          0.381 |        0.357 |                -0.088 |                  0.204 |        2025 |         2026 |              -2.032 |            11.402 |   -0.0016 |      -0.044 |     86 |           0.0864 |        0.2417 |        -0.3642 |
| m5_riskadj_mom_60_top5_ma50_gate |          0.206 |        0.192 |                -0.372 |                 -0.134 |        2020 |         2022 |              -2.733 |             5.011 |   -0.0231 |      -0.68  |     83 |           0.0347 |        0.1811 |        -0.395  |
| m6_riskadj_mom_60_skip5_top5     |          0.285 |        0.269 |                -0.209 |                 -0.061 |        2020 |         2022 |              -1.172 |             7.634 |   -0.0127 |      -0.38  |     83 |           0.065  |        0.2416 |        -0.3949 |
| m7_plain_mom_60_top5             |          0.355 |        0.343 |                -0.015 |                  0.101 |        2020 |         2026 |              -1.134 |             6.833 |   -0.037  |      -1.033 |     83 |           0.1019 |        0.297  |        -0.471  |
| m8_sortino_mom_60_top5           |          0.191 |        0.176 |                -0.283 |                 -0.026 |        2020 |         2026 |              -2.256 |             7.772 |   -0.0192 |      -0.568 |     83 |           0.0448 |        0.2548 |        -0.462  |

## Per-year Sharpe (net)

|   year |   m1_riskadj_mom_60_top5 |   m2_riskadj_mom_60_top3 |   m3_riskadj_mom_120_top5 |   m4_riskadj_mom_20_top5 |   m5_riskadj_mom_60_top5_ma50_gate |   m6_riskadj_mom_60_skip5_top5 |   m7_plain_mom_60_top5 |   m8_sortino_mom_60_top5 |
|-------:|-------------------------:|-------------------------:|--------------------------:|-------------------------:|-----------------------------------:|-------------------------------:|-----------------------:|-------------------------:|
|   2019 |                     0.54 |                     0.38 |                      0.7  |                     1.13 |                              -0.2  |                           0.46 |                   0.48 |                     0.5  |
|   2020 |                     1.3  |                     1.1  |                      1.64 |                     0.28 |                               2.14 |                           1.96 |                   1.59 |                     1.32 |
|   2021 |                    -0.35 |                    -0.15 |                     -0.94 |                     0.84 |                               1.04 |                          -0.4  |                  -0.1  |                     0.04 |
|   2022 |                    -1.05 |                    -0.64 |                     -1.13 |                    -0.57 |                              -2.73 |                          -1.17 |                  -1    |                    -0.98 |
|   2023 |                     0.06 |                     0.22 |                      0.63 |                     0.53 |                               0.12 |                           0.44 |                   0.44 |                    -0.04 |
|   2024 |                     0.72 |                     0.24 |                      0.94 |                     0.42 |                               0.11 |                           0.59 |                   0.22 |                     0.86 |
|   2025 |                     0.44 |                     0.22 |                      1.16 |                     1.4  |                               0.8  |                           0.23 |                   1.17 |                     0.65 |
|   2026 |                    -2.15 |                    -2.89 |                     -0.42 |                    -2.03 |                              -1.29 |                          -0.38 |                  -1.13 |                    -2.26 |

## Cost sensitivity (annualised Sharpe)

|   cost_bps |   m1_riskadj_mom_60_top5 |   m2_riskadj_mom_60_top3 |   m3_riskadj_mom_120_top5 |   m4_riskadj_mom_20_top5 |   m5_riskadj_mom_60_top5_ma50_gate |   m6_riskadj_mom_60_skip5_top5 |   m7_plain_mom_60_top5 |   m8_sortino_mom_60_top5 |
|-----------:|-------------------------:|-------------------------:|--------------------------:|-------------------------:|-----------------------------------:|-------------------------------:|-----------------------:|-------------------------:|
|          0 |                     0.12 |                    -0.01 |                      0.4  |                     0.38 |                               0.21 |                           0.28 |                   0.36 |                     0.19 |
|          5 |                     0.1  |                    -0.03 |                      0.39 |                     0.36 |                               0.19 |                           0.27 |                   0.34 |                     0.18 |
|         10 |                     0.08 |                    -0.04 |                      0.38 |                     0.33 |                               0.18 |                           0.25 |                   0.33 |                     0.16 |
|         20 |                     0.05 |                    -0.07 |                      0.35 |                     0.28 |                               0.15 |                           0.22 |                   0.31 |                     0.13 |

## Validation gates

| expression | G2 e2e | G3 non-degen | G4 fidelity | overall |
|---|---|---|---|---|
| m1_riskadj_mom_60_top5 | True | False | False | False |
| m2_riskadj_mom_60_top3 | True | False | False | False |
| m3_riskadj_mom_120_top5 | True | False | True | False |
| m4_riskadj_mom_20_top5 | True | False | False | False |
| m5_riskadj_mom_60_top5_ma50_gate | True | False | False | False |
| m6_riskadj_mom_60_skip5_top5 | True | False | False | False |
| m7_plain_mom_60_top5 | True | False | False | False |
| m8_sortino_mom_60_top5 | True | False | False | False |

## Mandatory audits (reported here for transparency; full evaluation in Agent 5)

### Look-ahead audit (on m1 baseline)
```json
{
  "T0": "2022-08-29",
  "bit_equal_on_past": true,
  "interpretation": "PASS"
}
```

### Execution-delay audit
```json
{
  "delay": 1,
  "target_shift_invariant_required": -2,
  "explanation": "forward 21d return uses logp.shift(-(1+delay)) - logp.shift(-1), so target_shift on the held leg is -(1+delay) = -2 \u2713",
  "pass": true
}
```

### Falsification-first audit
```json
{
  "ic_real_mean": -0.023143740799645394,
  "ic_shuf_mean": 0.012322403837256557,
  "ic_shuf_abs_mean": 0.07171015891916759,
  "pass": false
}
```
