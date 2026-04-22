# Alpha Ranking — Trend / Technical Session

**Session:** `20260422_trend_technical_alpha`
**Author:** Agent 5 — Evaluator
**Cost:** 5 bps per side, turnover-aware. Monthly rebalance. Industry-neutral.
**Splits:** Train 2018-2022 / Validate 2023 / Test 2024 – 2025-04-18.

## Ranked by **after-cost test LS Sharpe** (industry-neutral, monthly rebal)

| rank | alpha | construction | test LS | test Q5 IR | full LS | IC IR | maxDD | worst-year | verdict |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | **α_29** | 12-3 idio momentum (cum_252−cum_63, cs-resid vs {log_mv,σ_120,ret_20}) | **2.06** | **1.16** | 1.00 | **14.5** | **−7.1 %** | **0.04** | RESEARCH-ONLY (worst-year fail) |
| 2 | α_19 | 12-2 idio momentum (cum_252−cum_42, cs-resid vs {log_mv,σ_120,ret_42}) | 1.24 | 0.65 | 0.84 | 11.8 | −7.3 % | 0.16 | RESEARCH-ONLY (worst-year fail) |
| 3 | α_28 | 12-2 idio with σ_60 control | 1.20 | 0.61 | 0.61 | 9.4 | −7.5 % | −0.14 | RESEARCH-ONLY |
| 4 | α_32 | 12-2 industry-relative + double-resid (σ_60+ret_20+ret_42) | 1.17 | 0.60 | 0.48 | 6.6 | −7.9 % | −0.54 | RESEARCH-ONLY |
| 5 | α_27 | industry-relative 12-2 idio | 0.99 | 0.50 | 0.50 | 7.4 | −8.3 % | −0.42 | RESEARCH-ONLY |
| 6 | α_30 | 18-1 idio momentum | 0.94 | 0.62 | 0.33 | 5.5 | −17.0 % | −1.01 | RESEARCH-ONLY |
| 7 | α_31 | combo 50/50 z-mean of α_19 + α_21 | 0.90 | 0.30 | 0.68 | 10.1 | −7.5 % | 0.26 | RESEARCH-ONLY |
| 8 | α_15 | idio 12-1 momentum (cum_252−cum_21, cs-resid) | 0.88 | 0.38 | 0.57 | 9.5 | −7.1 % | −0.10 | RESEARCH-ONLY |
| 9 | α_26 | α_19 large-cap top-30% only | 0.56 | −0.01 | 0.55 | 8.1 | −13.0 % | 0.23 | rejected (no Q5 alpha) |
| 10 | α_12 | idio MA-crossover stack | 0.53 | −0.10 | 1.02 | 9.1 | −5.6 % | 0.40 | rejected (test weak) |

(Rounds 1 raw-trend alphas all had negative LS Sharpe — see falsification block in `final_summary.md`.)

## PROMOTE thresholds (none met, all rounds)

| threshold | required | best in session | gap |
|---|---:|---:|---:|
| test LS Sharpe (after cost, monthly) | ≥ 1.0 | 2.06 (α_29) | ✓ pass |
| test Q5 excess IR (after cost) | ≥ 0.5 | 1.16 (α_29) | ✓ pass |
| worst-year LS Sharpe | ≥ 0.5 | 0.40 (α_12) / 0.16 (α_19) / 0.04 (α_29) | ✗ fail by ≥ 0.10 in best LS-Sharpe candidate |
| best-year-out LS Sharpe % of full | ≥ 50 % | 67 % (α_19) | ✓ pass |
| residual IC (mechanism strength) | ≥ 30 % of raw | n/a — sign-flipped after residualization | n/a |

The blocker is **uniformly worst-year-Sharpe**. Every strong α_29-family alpha has at least one year (2019 or 2023) in which the trend signal stalls.

## Mechanism narrative

1. **Raw cross-sectional trend signals are anti-predictive in A-share.** All 8 raw trend factors in batch 0001 (Han-Zhou-Zhu, MA crossover, t-stat, 52-week proximity, frog-in-the-pan, trend Sharpe, 12-1 momentum) had **negative** rank-IC with t-stats between |6| and |25|. Replicates Liu-Stambaugh-Yuan 2019 finding that A-share is reversal-dominated.

2. **Idiosyncratic trend exists** but is much weaker than residual returns from controls suggest. After cross-sectional residualization vs {log_mv, σ_120, ret_20}, sign flips from negative to positive for 7 of 7 trend signals (batch 0002). IC IR ranges 5-10. Best raw idio alpha is α_15 (idio 12-1 momentum) with IC +0.022.

3. **Skip-window matters.** 12-2 (skip 42 days) > 12-1 (skip 21 days) > 12-3 (skip 63 days, IC IR but worse worst-year). The marginal extra month of skip beyond 1 captures more reversal contamination.

4. **Industry-relative form does not help.** α_27/α_32 (industry-demean before idio) have similar IC but worse worst-year than stock-level α_19/α_29.

5. **Large-cap filter trades signal strength for stability.** α_25/α_26 (mv ≥ median or 70th pctile) lift worst-year ~+0.07 but cut test LS Sharpe in half.

6. **Combo signals do not produce alpha beyond the components.** α_21 (12+15), α_22 (11+12+15), α_31 (19+21) all stay between the components' performance.

## Deployment note

If user lowers worst-year-Sharpe floor from 0.5 to 0.0 (i.e., accepts a flat year as long as it is not a losing year), **α_29 is deployable** as the trend-family candidate:
- Construction: `(cum_252 − cum_63)` per stock, then per-date OLS residualize against `{log_mv, σ_120, ret_20}`, then industry-demean, then monthly rebal Q5 long / Q1 short with 5 bps per side cost.
- Expected after-cost LS Sharpe ≈ 1.0 full / 2.0+ test, max DD ≈ −7 %, but with one-year stalls in regime-shift years (2019 / 2023).
- Long-only Q5 excess IR test = 1.16 — a strong index-enhancement signal in trending years; expect drag in choppy years.

Strict audit verdict (worst-year ≥ 0.5): RESEARCH-ONLY.
