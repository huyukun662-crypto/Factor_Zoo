# Alpha ranking — batch 0002 (round 2)
Universe: A-share ex-IPO<250d, 2023-01 → 2025-12, delay=1.
Tests: A=post-DTL window (alpha_09..12), B=northbound regime overlay (alpha_13..15), ensemble (alpha_16).

## Headline (h=10)

| alpha    |   ic_mean |   ic_t |   ic_ir |   ls_sr_daily |   q5e_sr_daily |   ls_sr_monthly |   q5e_sr_monthly |   q5_size_mean |
|:---------|----------:|-------:|--------:|--------------:|---------------:|----------------:|-----------------:|---------------:|
| alpha_15 |     0.001 |  0.185 |   0.01  |        -0.021 |         -0.211 |           0.083 |            0.107 |        1015.68 |
| alpha_10 |     0.011 |  3.868 |   0.145 |         0.553 |         -0.207 |          -0.161 |           -0.069 |        1016.4  |
| alpha_14 |    -0.002 | -0.819 |  -0.031 |        -0.316 |         -0.625 |          -0.026 |           -0.059 |        1016.36 |
| alpha_12 |    -0.013 | -3.882 |  -0.145 |        -0.389 |         -0.624 |          -0.182 |           -0.056 |        1016.68 |
| alpha_11 |     0.006 |  1.858 |   0.07  |         0.303 |          0.059 |          -0.043 |           -0.121 |        1016.4  |
| alpha_13 |    -0.001 | -0.512 |  -0.02  |        -0.199 |         -0.549 |          -0.066 |           -0.095 |        1016.36 |
| alpha_09 |     0.007 |  2.416 |   0.091 |         0.428 |          0.001 |          -0.081 |           -0.157 |        1016.4  |
| alpha_16 |     0.006 |  1.922 |   0.072 |         0.377 |          0.269 |          -0.172 |           -0.158 |        1020.11 |

## Per-year LS Sharpe (h=10)

| alpha    |   2023 |   2024 |   2025 |
|:---------|-------:|-------:|-------:|
| alpha_09 |   2.36 |   2.34 |   0.7  |
| alpha_10 |   6.32 |   0.04 |  -0.27 |
| alpha_11 |   1.96 |   1.13 |   0.54 |
| alpha_12 |  -1.75 |   0.48 |  -2.03 |
| alpha_13 |  -0.61 |  -0.27 |  -0.91 |
| alpha_14 |  -0.59 |  -0.52 |  -1.66 |
| alpha_15 |   0.7  |   2.14 |  -2.08 |
| alpha_16 |   1.7  |   0.85 |   1.37 |

## Audit floors

| alpha | worst_year_LS | worst_year_Q5e | best_year_out_LS | resid_LS_pct_of_raw |
|---|---|---|---|---|
| alpha_09 | 0.6978954001288269 | -1.4933080600810118 | 1.097194276073264 | 0.6048458972762483 |
| alpha_10 | -0.2680238146127831 | -2.5126000916833475 | -0.1315411580254716 | 0.26217983675395895 |
| alpha_11 | 0.5391224681057877 | -0.577918428031967 | 0.6733590880467785 | -0.02497259247103448 |
| alpha_12 | -2.0335021107660074 | -2.6238012718843606 | -1.8995761624411487 | 1.4594387027986948 |
| alpha_13 | -0.9111666862276715 | -3.488379882079986 | -0.7763777527997144 | 0.9525921067179364 |
| alpha_14 | -1.6560860788594982 | -3.538352930686118 | -1.1985165266630615 | 0.790045110127437 |
| alpha_15 | -2.082450380413892 | -1.3234965602325341 | -0.990548056664342 | 0.9173235372821602 |
| alpha_16 | 0.8455361140005418 | -0.8780658830088561 | 1.1192052162906574 | 0.334031050235894 |


## Decision per alpha

### alpha_09 → **RESEARCH_ONLY**

- ✓ worst_year_LS>=0.5
- ✗ worst_year_Q5e>=0.4
- ✓ best_year_out>=50%
- ✓ residualized>=50%

### alpha_10 → **RESEARCH_ONLY**

- ✗ worst_year_LS>=0.5
- ✗ worst_year_Q5e>=0.4
- ✗ best_year_out>=50%
- ✗ residualized>=50%

### alpha_11 → **RESEARCH_ONLY**

- ✓ worst_year_LS>=0.5
- ✗ worst_year_Q5e>=0.4
- ✓ best_year_out>=50%
- ✗ residualized>=50%

### alpha_12 → **RESEARCH_ONLY**

- ✗ worst_year_LS>=0.5
- ✗ worst_year_Q5e>=0.4
- ✓ best_year_out>=50%
- ✓ residualized>=50%

### alpha_13 → **RESEARCH_ONLY**

- ✗ worst_year_LS>=0.5
- ✗ worst_year_Q5e>=0.4
- ✓ best_year_out>=50%
- ✓ residualized>=50%

### alpha_14 → **RESEARCH_ONLY**

- ✗ worst_year_LS>=0.5
- ✗ worst_year_Q5e>=0.4
- ✓ best_year_out>=50%
- ✓ residualized>=50%

### alpha_15 → **RESEARCH_ONLY**

- ✗ worst_year_LS>=0.5
- ✗ worst_year_Q5e>=0.4
- ✓ best_year_out>=50%
- ✓ residualized>=50%

### alpha_16 → **RESEARCH_ONLY**

- ✓ worst_year_LS>=0.5
- ✗ worst_year_Q5e>=0.4
- ✓ best_year_out>=50%
- ✗ residualized>=50%

