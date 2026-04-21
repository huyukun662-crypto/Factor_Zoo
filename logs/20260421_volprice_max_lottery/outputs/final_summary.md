# Final Summary — Volume-Price Lottery Demand Session

**Session:** `20260421_volprice_max_lottery`
**Date:** 2026-04-21
**Family:** volume_price
**Mechanism tested:** Lottery demand / MAX effect (Round 1) → Idiosyncratic skewness (Round 2)
**Decision:** **RESEARCH-ONLY — do not promote.**

---

## TL;DR

Two rounds × 8 alphas each (Rule-of-8) explored the A-share "lottery demand" anomaly. Headline
LS Sharpes look impressive pre-residualization (best: α_08 full LS net Sharpe = 2.21,
α_15 test LS Sharpe = 2.92), but **all 16 alphas fail the residualization audit**: once we strip
out volatility and short-term reversal from the signal, the remaining alpha is negligible
(|residual IC| < 0.02 for all). Deploying any of these factors standalone would result in
double-counting the vol and reversal premia that are likely already captured elsewhere.

This is a **legitimate research finding**, not a failure of the workflow:
> In the A-share 2018-2025 sample, behavioral "lottery demand" signals (MAX, skewness,
> jump-count) are explained almost entirely by volatility and short-term reversal. The
> cross-section does not reward lottery-like payoffs *beyond* what is already reflected
> in σ and the 1-month reversal.

---

## Round 1: MAX Effect (α_01 – α_08)

| Alpha | Definition | LS full | LS test | Q5 IR full | Residual IC | Audit |
|---|---|---:|---:|---:|---:|---|
| α_01 | −max(r) 20d | 1.71 | 1.29 | 1.20 | — | FAIL (resid) |
| α_02 | −mean(top5) 20d | 1.70 | 1.53 | 1.01 | — | FAIL (resid + worst-year) |
| α_03 | −mean(top10) 60d | 1.51 | 0.91 | 1.11 | — | n/a |
| α_04 | −(top5)/σ_20 | 0.83 | 1.46 | 0.44 | — | n/a |
| α_05 | −top5 × turnover z | 2.62 | 1.43 | 1.32 | −0.01 | FAIL (resid + worst-year) |
| α_06 | −(top5 − bot5) | 1.45 | 0.83 | 0.71 | — | n/a |
| α_07 | −(max − mean)/σ_20 | 0.07 | 0.54 | 0.02 | — | n/a |
| **α_08** | **−mean(top5 of abnormal returns) 20d** | **2.21** | **2.03** | **1.73** | **+0.02** | **FAIL (resid)** |

Residualization screen (full IC by stack):

| Alpha | vs reversal | vs vol | vs vol+rev | vs full stack |
|---|---:|---:|---:|---:|
| α_01 | 0.068 | 0.017 | 0.007 | 0.009 |
| α_02 | 0.075 | 0.028 | 0.011 | 0.009 |
| α_03 | 0.085 | 0.032 | 0.029 | 0.017 |
| α_08 | 0.085 | 0.041 | 0.027 | 0.020 |

**Round-1 verdict:** MAX and its 7 variants survive reversal-residualization (IC ≈ 0.07-0.09)
but collapse under volatility-residualization (IC ≈ 0.02-0.04). In A-share, "MAX = σ × sign."

---

## Round 2: Idiosyncratic Skewness (α_09 – α_16)

The 3rd moment (skewness) is mathematically orthogonal to the 2nd moment (σ); if lottery demand
is real beyond vol, it should appear in skew-based signals.

| Alpha | Definition | LS full | LS test | Q5 IR test | Residual IC (full) | Audit |
|---|---|---:|---:|---:|---:|---|
| α_09 | −skew(idio) 20d | 0.63 | −0.32 | −0.03 | +0.011 | FAIL (worst-year, LOYO) |
| α_10 | −skew(idio) 60d | 0.01 | −0.50 | −0.15 | +0.005 | FAIL (multi) |
| α_11 | −coskew / σ² | 0.61 | **1.21** | **1.13** | +0.006 | FAIL (worst-year) |
| α_12 | −(top5−\|bot5\|)/σ | 0.86 | **1.37** | **1.25** | +0.006 | FAIL (worst-year, resid) |
| α_13 | −BMV predictor | −0.78 | 0.50 | 0.83 | −0.011 | FAIL |
| α_14 | −3(mean−median)/σ | 0.67 | 1.29 | 1.16 | +0.005 | FAIL (worst-year, resid) |
| **α_15** | −count(r_t > 2σ_60) 20d | **1.64** | **2.92** | 0.76 | **−0.010** | FAIL (resid) |
| α_16 | −skew × turnover z | 1.95 | 0.73 | −0.35 | +0.013 | FAIL (worst-year) |

Targeted residualization (vs σ only):

| Alpha | vs σ only | vs σ + rev | vs σ + size |
|---|---:|---:|---:|
| α_15 (jump count) | **−0.005** | −0.016 | −0.009 |
| α_11 (coskew) | +0.025 | +0.013 | +0.019 |
| α_12 (tail asym) | +0.029 | +0.004 | +0.024 |
| α_16 (skew × attention) | +0.010 | +0.012 | +0.014 |

**Key Round-2 findings:**

1. **α_15's headline 2.9 test Sharpe is an artifact of volatility.** The residual IC vs σ alone
   is NEGATIVE (−0.005) — stripping vol actually FLIPS the sign. "Stocks with frequent +2σ days"
   is just "high-σ stocks with positive drift" dressed up.
2. **α_11 (coskew) is the honest winner**, retaining IC = 0.025 vs σ-only and 0.019 vs σ+size.
   But it fails worst-year floor (−0.79 in 2020 bear market) and has only 0.61 full LS Sharpe
   — not deployable.
3. **No skew variant retained meaningful signal after the full-stack residualization.**

---

## Combined verdict

Two different mathematical families of "lottery demand" (magnitude via MAX, asymmetry via skew)
both show the same pattern in A-share: they are **correlated-but-not-additive** with σ and the
20-day reversal. Any of the 16 alphas, used standalone, would roughly replicate what a simple
σ + reversal combination delivers — and likely worse, because the lottery signals carry more
noise than either σ or reversal alone.

### What to do with this finding

1. **Do not promote** any of the 16 alphas to `factors/`.
2. **Preserve the research artifacts** — the panel, backtest CSVs, and audit JSONs are useful
   benchmarks for future research.
3. **Follow-on research that might work:**
   - **Residualized α_08 × residualized α_11 interaction** — two partial signals combined
     might exceed the sum-of-parts.
   - **Conditional sorting** — skew within high-σ-quintile vs low-σ-quintile; if lottery
     demand is a retail phenomenon, it may concentrate in specific σ regimes.
   - **Short-horizon reversal (week-level)** rather than lottery-specific constructions — the
     reversal premium itself is what this data ultimately rewards.
   - **Pivot to a genuinely different family** — fundamental-to-price anomalies (Piotroski
     F-score, Gross Profitability, SUE/PEAD).

## Audits for the top candidate (α_08) — per CLAUDE.md

| Audit | Result | Pass? |
|---|---|---|
| Execution-delay invariant | target_shift = −2 by construction | ✓ |
| Look-ahead shuffle | IC real 0.104, shuffled 0.001 | ✓ |
| Worst-year Sharpe ≥ 0.5 | 0.84 (2020) | ✓ |
| LOYO ≥ 50% headline | 2.11 ≥ 0.5 × 2.21 | ✓ |
| Falsification (random α) | random IC 0.0003 | ✓ |
| **Residualization full stack** | **residual IC 0.020 < 0.3 × 0.104 = 0.031** | **✗** |

→ decision = RESEARCH-ONLY.

## Artifacts

```
logs/20260421_volprice_max_lottery/
├── inputs/                  (empty — all data from .cache from prior session)
├── outputs/
│   ├── research_brief.md
│   ├── session_metadata.yml
│   ├── expressions_batch_0001.md      (MAX family)
│   ├── expressions_batch_0002.md      (skewness family)
│   ├── backtest_results_batch_0001.csv
│   ├── backtest_results_batch_0002.csv (residualized screen)
│   ├── backtest_results_batch_0002_skew.csv (Round 2)
│   ├── residualization_screen.csv
│   ├── audits.json                    (Round 1)
│   ├── audits_round2.json             (Round 2)
│   ├── panel_volprice.parquet         (Round 1 panel, ~1.1GB)
│   ├── panel_round2.parquet           (Round 1 + residualized, ~3.3GB)
│   ├── panel_round2_skew.parquet      (Round 2 skew panel)
│   └── rebalances_alpha_NN.csv        (per-alpha monthly P/L)
├── scripts/
│   ├── 01_build_volprice_panel.py
│   ├── 02_backtest.py
│   ├── 03_audits.py
│   ├── 04_residualize_all.py
│   ├── 05_backtest_residualized.py
│   ├── 06b_build_round2_skew_fast.py
│   └── 07_backtest_audit_round2.py
├── working/
│   ├── handoff_1_to_2.json
│   ├── handoff_2_to_3.json
│   ├── handoff_3_to_4.json
│   └── handoff_4_to_5.json
├── round_0001.yml
├── round_0002.yml
└── run_state.json
```

## Cost model note

All results use the **5 bps one-side (万5)** turnover-aware cost model, consistent with the
accruals factor already in `factors/`. Average LS cost per monthly rebalance: 3-8 bps depending
on turnover (60%-80% per side for most variants). Annual cost therefore ~36-96 bps, which is
material compared to raw returns.

## Relation to the fundamental accruals factor already deployed

The deployed accruals factor (`factors/fundamental/accruals_median_ttm_ind_neutral_v2`) and
the MAX/skew family tested here are expected to be orthogonal by construction — one is a
quarterly earnings-quality signal, the other is a monthly behavioral/distribution signal.
Had a MAX variant passed audits, it would have made a natural second factor. Since none did,
the factor library remains at one fundamental factor; the next session queued (SUE/PEAD or
Gross Profitability) should pursue an uncrowded fundamental signal rather than revisit
lottery-demand.
