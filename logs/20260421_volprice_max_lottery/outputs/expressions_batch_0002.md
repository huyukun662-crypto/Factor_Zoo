# Alpha Expressions — Batch 0002 — Idiosyncratic Skewness (Lottery Demand II)

**Session:** `20260421_volprice_max_lottery` — Round 2
**Mechanism pivot rationale:** Round 1 found that raw MAX in A-share is ~85% absorbed by
{sigma_20, ret_20}. Skewness is mathematically orthogonal to sigma (third moment vs second),
so we expect the "pure lottery demand" signal — if real — to survive vol residualization.
**Direction:** SHORT high-skew (lottery profile = retail overpayment → underperform).
**Anchor papers:** Boyer, Mitton, Vorkink (2010 RFS); Kumar (2009 JoFQA).

## α_09 — idio_skew_20
```
r_res_t = ret_t - mkt_ret_t                        # cross-sectional demean already ≈ idio
raw = -skew(r_res_t over w(20))
```

## α_10 — idio_skew_60 (longer window)
```
raw = -skew(r_res_t over w(60))
```

## α_11 — coskew (Harvey & Siddique 2000)
```
raw = -E[(r_i - mean) (mkt - mkt_mean)^2]  over w(60) / sigma_20^2
```

## α_12 — tail_asymmetry (top5 vs bot5)
```
raw = -(mean(top5) - |mean(bot5)|) / sigma_20     over w(20)
```

## α_13 — expected_skew (Boyer-Mitton-Vorkink 2010 predictor)
```
# proxy: recent realized skew + recent MAX (simple linear combo)
raw = -(skew_20 + 0.5 * max_avg5_20 / sigma_20)
```

## α_14 — pearson_skew (alternative skewness measure)
```
raw = -(3 * (mean - median)) / sigma_20   over w(20)
```

## α_15 — jump_up_freq (count of +2σ events)
```
sigma_60 = std(ret_t over w(60))
raw = -count(ret_t > 2*sigma_60) over w(20)
```

## α_16 — skew_attention (turnover-weighted skew)
```
raw = -skew_20 * zscore(turnover_20)
```

## Post-build
All 8 alphas: industry-demean per trade_date → winsorize 1%/99% → cross-sectional z-score.
Pre-submission: coverage, IC sign (positive, since α has negative sign already), residualization
screen against the full stack {ret_5, ret_20, sigma_20, turnover_20, log_mv}.

## Hypothesis
At least one of α_09–α_16 should retain >50% of its IC after full-stack residualization. If not,
we conclude A-share lottery demand is fully captured by volatility and reversal factors, and the
session closes RESEARCH-ONLY.
