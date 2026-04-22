# Alpha Expressions — Batch 0003 — σ-Decoupled Iteration of α_05/08/15

**Session:** `20260421_volprice_max_lottery` — Round 3
**Parent alphas:** α_05 (top5 × turnover), α_08 (abnormal top5), α_15 (jump count)
**Goal:** Keep their raw signal strength while **passing the residualization audit**
vs {ret_5, ret_20, σ_20, turnover_20, log_mv}.

## Why a pivot in construction style
Round 1-2 results showed the 3 candidates share one failure mode: their raw form is ~80% absorbed
by σ_20. The fix is not re-parameterization — it's **non-parametric decoupling**: compute the
signal *conditional on* σ bucket or with σ explicitly removed from the construction.

## The 8 variants

### α_17 — σ-bucket conditional rank of α_08 (Bali-original methodology)
```
per trade_date:
    σ_bucket(i) = qcut(σ_20(i), 5)
    per σ_bucket b:
        rank_within = rank(α_08(i) | σ_bucket = b) / size(b)
α_17 = cs_z(ind_demean(rank_within - 0.5))
```
Rationale: by construction, within a σ-bucket the remaining signal is σ-orthogonal.
This IS the methodology of Bali, Cakici, Whitelaw (2011) for isolating MAX from vol.

### α_18 — σ-bucket conditional rank of α_05
Same as α_17 but using α_05 as the base signal.

### α_19 — σ-bucket conditional rank of α_15
Same as α_17 but using α_15 (jump count) as the base signal.

### α_20 — Interaction of σ-bucket ranked α_08 × α_15
```
raw = zscore(α_17) × zscore(α_19)
α_20 = cs_z(ind_demean(raw))
```
If α_08 and α_15 capture related but non-identical retail-attention phenomena,
their (σ-bucket-residualized) product should be a stronger filter.

### α_21 — Fixed-threshold jump count (no σ scaling in construction)
```
raw = -count(|log_ret| > 0.05 AND log_ret > 0) over w(20)
```
Replaces α_15's σ-scaled threshold (r > 2σ_60) with a constant 5% threshold.
This removes σ from the counting rule itself, not just from the post-hoc residualization.

### α_22 — Fixed-threshold idiosyncratic jump count
```
raw = -count(idio_ret > 0.03) over w(20)
```
Like α_21 but on idio returns (already market-residualized). 3% threshold is roughly
one daily standard deviation for a median A-share stock.

### α_23 — Time-series pre-residualized top5
```
per stock:
    fit OLS: top5_20(t) = α_i + β_i * σ_20(t) + ε(t)
raw = -ε(t) over last observed value
```
Stock-specific σ-orthogonalization in the time series, before any cross-sectional step.

### α_24 — σ × turnover double conditional sort on α_08
```
per trade_date:
    σ_bucket(i) = qcut(σ_20, 5)
    turnover_bucket(i) = qcut(turnover_20, 5)
    per (σ_bucket, turnover_bucket):
        rank_within_cell = rank(α_08) / cell_size
α_24 = cs_z(ind_demean(rank_within_cell - 0.5))
```
Double decoupling: σ-orthogonal AND turnover-orthogonal. If the residualization failure
was also about turnover_20, this variant should fully pass.

## Pre-submission checks
For each alpha: coverage ≥ 70%, xsection std ~ 1 after z-score, validate IC sign consistent.

## Audit bar
Same as Rounds 1-2:
- look-ahead, falsification, execution-delay: expected ✓
- worst-year Sharpe ≥ 0.5
- LOYO ≥ 50% headline
- **residualization full stack: residual IC ≥ 0.3 × raw IC**

Any variant passing all 5 audits AND LS Sharpe ≥ 1.0 → candidate for deployment.
