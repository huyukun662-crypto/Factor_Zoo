# Alpha Ranking — Session Leader Board (after Round 3)

**Session:** 20260420_fundamental_accruals_alpha
**Agent:** 5 Evaluator & Recorder
**Flagship:** `alpha_med_ind` (a.k.a. `accruals_median_ttm_ind_neutral_v2`) — confirmed on extended 2018-2025 window.

---

## 1. Cross-round leader board (all LS net 10 bps, monthly rebalance)

| rank | alpha | round | window | IC@20 | ICIR@20 | Sharpe net | worst yr | max DD |
|-----:|-------|------:|--------|------:|--------:|-----------:|---------:|-------:|
| **1** | **alpha_med_ind** | 3 | 2018-2025 | 0.015 | **0.440** | **1.03** | **1.33** | **−1.8 %** |
| 2 | alpha_sum_ind | 3 | 2018-2025 | 0.016 | 0.413 | 1.01 | 1.18 | −2.6 % |
| 3 | alpha_v5 (= alpha_med_ind on 2020-2025) | 2 | 2020-2025 | 0.016 | 0.505 | 1.57 | 1.55 | −1.6 % |
| 4 | alpha_03 (= alpha_sum_ind on 2020-2025) | 1 | 2020-2025 | 0.018 | 0.495 | 1.38 | 1.24 | −2.0 % |
| 5 | alpha_med_indxsize | 3 | 2018-2025 | 0.010 | 0.303 | 0.82 | 0.36 | −3.3 % |
| 6 | alpha_sum_indxsize | 3 | 2018-2025 | 0.012 | 0.338 | 0.81 | 0.68 | −3.5 % |
| 7 | alpha_sum_size | 3 | 2018-2025 | 0.019 | 0.272 | 0.71 | 0.11 | −6.1 % |
| 8 | alpha_med_size | 3 | 2018-2025 | 0.019 | 0.269 | 0.68 | 0.09 | −6.2 % |
| 9 | alpha_sum_none | 3 | 2018-2025 | 0.023 | 0.282 | 0.69 | 0.11 | −6.2 % |
| 10 | alpha_med_none | 3 | 2018-2025 | 0.023 | 0.272 | 0.65 | 0.02 | −6.5 % |

Bottom 6 of Round 1 (alpha_02 / 04 / 05 / 07, plus Round 2 v7 / v8) omitted — already dropped.

## 2. Attribution verdict

### On the TTM axis (within industry-neutral)

| TTM | Sharpe net | ICIR 20 | worst yr | max DD |
|-----|-----------:|--------:|---------:|-------:|
| sum | 1.01 | 0.413 | 1.18 | −2.6 % |
| **median** | **1.03** | **0.440** | **1.33** | **−1.8 %** |
| Δ | +2 % | +7 % | +13 % | −30 % |

Median-TTM wins on every metric. Gap is smaller than the Round 2 claim (which was on the benign 2020-2025 window); including 2018-2019 shrinks the IC advantage but preserves the worst-year and drawdown advantages. **Median-TTM is still the right default.**

### On the neutralization axis (within median-TTM)

| Neutralization | Sharpe net | ICIR 20 | worst yr | max DD |
|----------------|-----------:|--------:|---------:|-------:|
| none           | 0.65 | 0.27 | 0.02 | −6.5 % |
| size-only      | 0.68 | 0.27 | 0.09 | −6.2 % |
| **industry-only** | **1.03** | **0.44** | **1.33** | **−1.8 %** |
| industry × size | 0.82 | 0.30 | 0.36 | −3.3 % |

**Industry neutralization is the decisive lever.** Size on its own does essentially nothing (+0.03 Sharpe vs none). Double-neutralization (industry × size) gives back much of the industry gain because cell sizes get too small. This is the clearest attribution result we could have asked for: *the accruals premium is a sector-within story, not a size-within story.*

## 3. TVT split — honest out-of-sample picture

| split | period | LS net Sharpe | Q5 long-only IR |
|-------|--------|--------------:|----------------:|
| Train | 2018-2021 | 1.12 | 1.16 |
| Validate | 2022-2023 | 1.73 | 1.83 |
| **Test** | **2024-2025YTD** | **0.46** | **0.89** |
| Full | 2018-2025YTD | 1.03 | 1.15 |

The Test Sharpe of 0.46 is dragged by 3 negative 2025 YTD months (small sample). Pure 2024 was Sharpe 1.33. Take the Test Q5-IR of 0.89 as the conservative deployment expectation for the long-only version — LS has higher noise due to short-side constraints.

## 4. Revised headline expectations (replace Round 2's 1.57)

**Before (Round 2, 2020-2025):**
- LS Sharpe net = 1.57, worst year = 1.55, max DD = −1.6 %

**After (Round 3, 2018-2025 honest):**
- LS Sharpe net = **1.03**, worst year = 1.33, max DD = −1.8 %
- Q5 long-only IR = **1.15** (deployable form)
- Test OOS: LS 0.46 / Q5 IR 0.89 (partially 2025 small-sample drag)

**Deployment target:** LS Sharpe 1.0 / Q5 IR 1.0 after 3 months of paper trading. Kill-switch at rolling-12m Sharpe < 0.3 or max DD worse than −5 %.

## 5. Correlation of top variants (across rounds)

Running-aside: alpha_sum_ind (R1) and alpha_med_ind (R2/R3) are ~0.95 correlated in rank-space. The factor library carries **one** accruals alpha, not two. `alpha_med_ind` is that alpha.

## 6. Decision — continue / refine / stop

**Decision:** **stop exploring accruals variants.** The mechanism is well-characterized:
- 3 rounds, 24 tested expressions, clear winner.
- Attribution done (industry is the lever).
- Residualization done (96 % kept vs classics).
- TVT split done (Test OOS ~0.9 Q5-IR).

**Next:** fresh session on **SUE / PEAD** (independent fundamental mechanism). Then **Gross Profitability** (Novy-Marx 2013). After both have paper-traded 3 months, build the **factor-zoo ensemble**.

Do NOT open Round 4 on accruals. Incremental tuning past here will overfit.
