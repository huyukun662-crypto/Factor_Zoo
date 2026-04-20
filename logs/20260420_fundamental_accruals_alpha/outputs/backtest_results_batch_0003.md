# Backtest Report — Batch 0003  (Round 3, extended 2018-2025 + TVT split)

**Session:** 20260420_fundamental_accruals_alpha
**Agent:** 4 Backtest Operator
**Window:** 2018-07-11 → 2025-04-18  (82 monthly rebalances, 6.7M stock-days, 5,285 stocks)
**Status:** `validation_passed = true`, `submission_made = true`

Runtime / universe / cost / delay identical to Round 1.5 & Round 2; the only change is the extended time window.

---

## 1. IC & ICIR (horizon = 20, 60)

| variant | IC 20 | IC 60 | ICIR 20 | ICIR 60 |
|---------|------:|------:|--------:|--------:|
| sum_none      | 0.023 | 0.040 | 0.282 | 0.507 |
| sum_size      | 0.019 | 0.036 | 0.272 | 0.558 |
| **sum_ind**   | 0.016 | 0.032 | 0.413 | 0.848 |
| sum_indxsize  | 0.012 | 0.025 | 0.338 | 0.752 |
| med_none      | 0.023 | 0.039 | 0.272 | 0.471 |
| med_size      | 0.019 | 0.035 | 0.269 | 0.564 |
| **med_ind**   | 0.015 | 0.030 | **0.440** | **0.944** |
| med_indxsize  | 0.010 | 0.022 | 0.303 | 0.698 |

**Interpretation:** non-neutralized variants have *higher* absolute IC but *lower* ICIR — they pick up industry-level mean differences that carry noise. Industry-neutralizing trades a few bps of IC for much cleaner stability (ICIR 0.44 vs 0.27).

## 2. LS portfolio summary (82 rebalances, 10 bps cost, full window)

| variant | Sharpe gross | Sharpe net | LS ann ret | LS ann vol | worst yr | best yr | kept no-best | max DD | Q5ex IR | Q5ex ann |
|---------|-------------:|-----------:|-----------:|-----------:|---------:|--------:|-------------:|-------:|--------:|---------:|
| sum_none      | 0.92 | 0.69 | 9.7 % | 10.0 % | 0.11 | 3.69 | 82 % | −6.2 % | 0.80 | 4.2 % |
| sum_size      | 0.96 | 0.71 | 9.9 % |  9.9 % | 0.11 | 3.80 | 85 % | −6.1 % | 0.79 | 4.1 % |
| **sum_ind**   | 1.33 | 1.01 | 10.5 % |  7.6 % | **1.18** | 5.39 | 91 % | −2.6 % | 1.13 | 4.8 % |
| sum_indxsize  | 1.12 | 0.81 |  8.9 % |  7.7 % | 0.68 | 3.05 | 88 % | −3.5 % | 1.12 | 4.3 % |
| med_none      | 0.89 | 0.65 |  9.4 % | 10.2 % | 0.02 | 4.84 | 77 % | −6.5 % | 0.76 | 4.1 % |
| med_size      | 0.92 | 0.68 |  9.6 % | 10.0 % | 0.09 | 4.07 | 82 % | −6.2 % | 0.76 | 4.0 % |
| **med_ind**   | **1.36** | **1.03** | 10.5 % |  7.4 % | **1.33** | 5.32 | **92 %** | **−1.8 %** | **1.15** | 4.5 % |
| med_indxsize  | 1.13 | 0.82 |  9.0 % |  7.6 % | 0.36 | 3.11 | 88 % | −3.3 % | 1.10 | 4.2 % |

**Ranking (by net Sharpe): `alpha_med_ind` (1.032) > `alpha_sum_ind` (1.009) > everything else.**

`alpha_med_ind` is the winner on all three primary gates:
- Worst-year floor: **1.33** (far above 0.5)
- Best-year-out kept: **92 %**
- Max drawdown: **−1.8 %** (smallest across all 8 variants and both rounds)

## 3. **Attribution summary** (what each lever buys)

Comparing the 4 neutralization choices on the median-TTM row:

| neutralization | Sharpe net | ICIR 20 | worst yr | max DD | Δ vs none |
|----------------|-----------:|--------:|---------:|-------:|:---------:|
| none           | 0.65 | 0.27 | 0.02 | −6.5 % | — |
| size only      | 0.68 | 0.27 | 0.09 | −6.2 % | +0.03 |
| **industry only** | **1.03** | **0.44** | **1.33** | **−1.8 %** | **+0.38** |
| industry × size | 0.82 | 0.30 | 0.36 | −3.3 % | +0.17 |

**Industry neutralization is the decisive lever.** Size-only brings almost nothing. Double (industry × size) *gives back* some of the industry gain — the size bins inside already-thin industries become noisy.

And on the TTM axis (industry-neutral row):

| TTM type | Sharpe net | ICIR 20 | worst yr | max DD |
|----------|-----------:|--------:|---------:|-------:|
| sum      | 1.01 | 0.41 | 1.18 | −2.6 % |
| **median** | **1.03** | **0.44** | **1.33** | **−1.8 %** |

Median-TTM gains are modest but directionally consistent with Round 2 (IC and Sharpe basically equal, but drawdown and worst-year improvement are what drove the Round 2 win).

## 4. TVT split on the winner `alpha_med_ind`

Using canonical split `Train: 2018-2021, Validate: 2022-2023, Test: 2024-2025YTD`:

### LS (Q5 − Q1) net 10 bps

| split | period | n reb | Ann ret | Ann vol | **Sharpe** |
|-------|--------|------:|--------:|--------:|-----------:|
| Train    | 2018-2021    | 43 | 11.23 % | 9.51 % | **1.12** |
| Validate | 2022-2023    | 24 |  5.67 % | 3.19 % | **1.73** |
| **Test** | **2024-2025YTD** | **15** | **2.17 %** | **4.66 %** | **0.46** |
| Full     | 2018-2025YTD | 82 |  7.89 % | 7.38 % | 1.03 |

### Q5 long-only excess vs equal-weighted universe (the deployable form)

| split | period | n reb | Ann excess | Ann vol | **IR** |
|-------|--------|------:|-----------:|--------:|-------:|
| Train    | 2018-2021    | 43 | 5.75 % | 4.85 % | **1.16** |
| Validate | 2022-2023    | 24 | 3.47 % | 1.87 % | **1.83** |
| **Test** | **2024-2025YTD** | **15** | **2.46 %** | **2.73 %** | **0.89** |
| Full     | 2018-2025YTD | 82 | 4.48 % | 3.83 % | 1.15 |

**Test 2024-2025YTD reality check:**
- Pure 2024 LS Sharpe was **1.33** (strong); 2025 YTD has only 3 data points, all negative, dragging Test Sharpe to 0.46.
- Q5 long-only IR 0.89 on Test is more stable — confirms A-share short-constraint analysis (SKILL.md lesson): deployable form is the long-only side, not LS.

## 5. Audit on winner `alpha_med_ind` (extended window)

- Shuffle test: clean IC 0.0149 vs shuffled IC 0.000065 → **229× ratio** ✅
- ICIR@60d: **0.944** (near-perfect stability) ✅
- Worst-year floor: 1.33 ≥ 0.5 ✅
- Best-year-out: 92 % kept ≥ 50 % ✅

## 6. Anomalies / caveats

1. **Test 2024-2025YTD Sharpe 0.46 is partly 2025 YTD noise.** Pure 2024 Sharpe is 1.33 and would pass every gate cleanly. Reporting 0.46 is the honest small-sample number; 1.33 is the clean annual.
2. **Non-neutralized variants fail worst-year floor** (sum_none 0.11, med_none 0.02 both in 2019). Without industry demean the signal is dominated by sector rotation.
3. **Double-neutralization (ind × size) is consistently worse than ind-only** on both TTM forms. Over-slicing cell sizes below ~10 stocks makes rank noisy.
4. **Sum vs median:** on full 2018-2025 window the gap between sum_ind and med_ind closes (Sharpe 1.01 vs 1.03). The Round 2 claim that median dominates was correct but the magnitude is smaller once 2018-2019 data is included. The worst-year-floor (1.18 vs 1.33) and max-DD (−2.6 % vs −1.8 %) advantages persist.

## 7. Decision passed to Stage 5

- `alpha_med_ind` remains the winner on the extended window.
- Honest full-cycle expectations: **LS net Sharpe 1.03, Q5-long-only IR 1.15, Max DD −1.8 %**. These should replace the Round 2 headline of 1.57 when communicating to downstream users.
- Test period IR 0.89 confirms the factor decays but doesn't die outside the research window.
- The mechanism is well-characterized. **Stop searching accruals-family variants.** Move on: add a second independent mechanism (SUE / PEAD) in a fresh session and ensemble.
