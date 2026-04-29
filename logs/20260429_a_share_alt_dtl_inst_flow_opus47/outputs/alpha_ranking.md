# Alpha ranking — batch 0001 (round 1)
Universe: CSI All-Share ex-IPO<250d, 2023-01-03 → 2025-12-31, delay=1.
Primary horizon h=10. Decision metric: monthly-rebalance Q5 long-only excess Sharpe.

## Headline (h=10)

| alpha    |   ic_mean |   ic_t |   ic_ir |   ls_sr_daily |   q5e_sr_daily |   ls_sr_monthly |   q5e_sr_monthly |   q5_size_mean |
|:---------|----------:|-------:|--------:|--------------:|---------------:|----------------:|-----------------:|---------------:|
| alpha_01 |    -0.005 | -1.405 |  -0.053 |       nan     |        nan     |           0.25  |            0.352 |        894.333 |
| alpha_06 |     0.009 |  2.105 |   0.079 |        -2.399 |         -2     |           0.335 |            0.259 |        244.926 |
| alpha_02 |     0.002 |  0.624 |   0.023 |        -0.288 |         -0.596 |           0.34  |            0.235 |        948.572 |
| alpha_07 |    -0.009 | -2.573 |  -0.097 |         0.142 |         -0.444 |           0.005 |            0.159 |        962.903 |
| alpha_08 |     0.001 |  0.35  |   0.013 |         0.127 |         -0.265 |           0.13  |            0.052 |        952.311 |
| alpha_04 |    -0.007 | -2.674 |  -0.1   |        -0.495 |         -1.352 |           0.041 |            0.047 |        934.72  |
| alpha_05 |     0.008 |  3.14  |   0.118 |         0.569 |         -0.393 |          -0.167 |           -0.028 |        954.507 |
| alpha_03 |    -0.005 | -1.521 |  -0.057 |         0.019 |          0.307 |          -0.078 |           -0.039 |         35.642 |

## Per-year h=10 (daily LS / Q5 excess)

| alpha    |   2023 |   2024 |   2025 |
|:---------|-------:|-------:|-------:|
| alpha_01 | nan    | nan    | nan    |
| alpha_02 |   0.09 |   4.15 |  -2.61 |
| alpha_03 |   0.53 |  -0.1  |  -0.18 |
| alpha_04 |  -4.59 |  -0.34 |  -1.41 |
| alpha_05 |   6.77 |  -1.67 |   1.09 |
| alpha_06 |  -9.5  |  -6.87 |  -7.18 |
| alpha_07 |   0.21 |   1.24 |   0.1  |
| alpha_08 |   2.9  |  -0.08 |  -0.64 |

## Audit floors

| alpha | worst_year_LS | worst_year_Q5e | best_year_out_LS | residualized_LS_pct_of_raw |
|---|---|---|---|---|
| alpha_01 | None | None | -0.9005680590200877 | -1.022483085946427 |
| alpha_02 | -2.608379853420145 | -7.2555353588449885 | -0.18963507777233596 | 2.684078079304056 |
| alpha_03 | -0.1802463356838399 | -0.0596163090306354 | -0.36294129827076904 | -6.943664783647039 |
| alpha_04 | -4.588681880003112 | -6.266935682413893 | -1.0218984193600467 | -2.254714518180812 |
| alpha_05 | -1.674020184547112 | -4.991045202899286 | -0.1096823573274148 | -0.4996981159996144 |
| alpha_06 | -9.500449938432338 | -6.8569075968062005 | -0.927279409221707 | 0.546405710139359 |
| alpha_07 | 0.1038776445126918 | -3.363081766778325 | 0.07862673526064236 | 0.719090480421636 |
| alpha_08 | -0.6438371813311193 | -2.172321850487792 | 0.025171705089215245 | 0.43843249366202525 |


## Decision per alpha

### alpha_01 → **RESEARCH_ONLY**

- ✗ worst_year_LS>=0.5
- ✗ worst_year_Q5e>=0.4
- ✓ best_year_out>=50%
- ✗ residualized>=50%

### alpha_02 → **RESEARCH_ONLY**

- ✗ worst_year_LS>=0.5
- ✗ worst_year_Q5e>=0.4
- ✗ best_year_out>=50%
- ✓ residualized>=50%

### alpha_03 → **RESEARCH_ONLY**

- ✗ worst_year_LS>=0.5
- ✗ worst_year_Q5e>=0.4
- ✓ best_year_out>=50%
- ✗ residualized>=50%

### alpha_04 → **RESEARCH_ONLY**

- ✗ worst_year_LS>=0.5
- ✗ worst_year_Q5e>=0.4
- ✓ best_year_out>=50%
- ✗ residualized>=50%

### alpha_05 → **RESEARCH_ONLY**

- ✗ worst_year_LS>=0.5
- ✗ worst_year_Q5e>=0.4
- ✗ best_year_out>=50%
- ✗ residualized>=50%

### alpha_06 → **RESEARCH_ONLY**

- ✗ worst_year_LS>=0.5
- ✗ worst_year_Q5e>=0.4
- ✓ best_year_out>=50%
- ✓ residualized>=50%

### alpha_07 → **RESEARCH_ONLY**

- ✗ worst_year_LS>=0.5
- ✗ worst_year_Q5e>=0.4
- ✗ best_year_out>=50%
- ✓ residualized>=50%

### alpha_08 → **RESEARCH_ONLY**

- ✗ worst_year_LS>=0.5
- ✗ worst_year_Q5e>=0.4
- ✗ best_year_out>=50%
- ✗ residualized>=50%

