# Round-6 falsification — MOM↔Lottery dispersion-regime rotation

**Session:** `20260422_trend_technical_alpha` (follow-on out of main research loop)
**Script:** `scripts/12_rotation_round6_falsification.py`
**Date:** 2026-04-22

## Purpose

Follow-on #2 (`followup_mom_lottery_rotation.md`) found that dispersion-regime
rotation of α_35 (momentum × MOM-gate) with α_17 (lottery × INV-gate) produces
LS Sharpe 1.95 / worst-year 0.97, rescuing both α_35's 2018 cash year and
α_17's 2020 tail year. Before considering deployment, the rotation must pass
the round-6 falsification suite: spec sensitivity + placebo.

## A) Spec sensitivity — 7 variants

Baseline gate: `disp_window=20, disp_lookback=252, threshold_percentile=50`.
Pass criterion: LS full Sharpe ≥ 1.5 AND worst-year LS ≥ 0.5.

| variant | LS full | Q5 full | worst-yr | best-yr | on_frac | verdict |
|---|---:|---:|---:|---:|---:|:---:|
| BASELINE (252d, p50, w20) | **1.951** | 1.080 | 0.970 | 5.927 | 87.6% | ✅ PASS |
| lookback_60 | 2.067 | 1.167 | 0.780 | 4.699 | 89.9% | ✅ PASS |
| lookback_126 | 2.050 | 1.148 | 0.619 | 5.817 | 89.9% | ✅ PASS |
| lookback_504 | 1.555 | 0.803 | **−0.245** | 5.927 | 77.5% | ❌ FAIL |
| threshold_p40 | 1.634 | 0.748 | 0.841 | 5.927 | 86.5% | ✅ PASS |
| threshold_p60 | 1.924 | 1.194 | 0.796 | 5.855 | 87.6% | ✅ PASS |
| disp_window_60 | 1.476 | 0.530 | 0.820 | 4.794 | 86.5% | ❌ FAIL |

**5/7 pass.** Failures are at spec-boundary corners and mechanically
interpretable:

- `lookback_504`: 2-year dispersion median is too slow to adapt. 2020's
  regime shift (megacap rally starting mid-year) doesn't register as
  "unusual dispersion" against a 504-day backwards reference, so the gate
  doesn't correctly switch from MOM to INV or vice versa — 2020 worst-year
  flips from +0.97 (baseline) to **−0.25**.
- `disp_window_60`: a 60-day dispersion measurement over-smooths. Full
  Sharpe drops to 1.48 and Q5 IR collapses to 0.53 (< 1.0). The gate
  signal washes out.

Both failing variants sit at the edges of the hyperparameter grid; all
**middle-of-grid** choices pass comfortably. This is the expected pattern
for a robust specification.

## B) Placebo — 100 random complementary gates

Generate 100 independent gate pairs (gate_mom, gate_inv) where at each
rebalance date:

- P(mom=1) = 0.457
- P(inv=1) = 0.433
- P(both off) = 0.110

These match the baseline on-fractions exactly. Each placebo generates a
rotation schedule with the same cadence and coverage as the true
dispersion-based rotation, but with **random** regime assignment.

Seed: `20260422`. Same rebalance grid and cost model as baseline.

### Results

| metric | baseline | placebo median | placebo p95 | placebo max | p-value |
|---|---:|---:|---:|---:|---:|
| LS full Sharpe | **1.951** | 1.149 | 1.660 | 1.945 | **0.000** |
| worst-year LS | **0.970** | −0.231 | 0.635 | 0.947 | **0.000** |

- **Zero of 100 placebos** reach the baseline LS Sharpe (1.951). The
  closest placebo got 1.945 — essentially tied but not exceeding.
- **Zero of 100 placebos** reach the baseline worst-year (0.970). The
  closest got 0.947.
- Empirical p-values are 0.000 on both metrics (bounded above by 1/100).

**The dispersion-based schedule is not reproducible by random regime
switching at matched on-fractions.** The gate carries genuine information
about which factor family to deploy when.

## Full audit checklist

Applying the mandatory pre-PROMOTE audit list (SKILL.md + CLAUDE.md):

| # | audit | rule | baseline | verdict |
|:-:|---|---|---|:---:|
| 1 | Execution delay | `delay=1`, `target_shift=-(1+1)=-2` | `fwd_ret_20 = ret.shift(-2).rolling(20).sum()` | ✅ |
| 2 | Look-ahead | no future data in gate | trailing 252d rolling median of past dispersion | ✅ |
| 3 | Worst-year LS ≥ 0.5 | hard floor | 0.970 (2020) | ✅ |
| 4 | Best-year-out ≥ 50% | drop best year, remaining Sharpe ≥ 50% × full | 1.647 / 1.951 = **84.5%** | ✅ |
| 5 | Falsification adversarial | placebo p < 0.05 on headline | p = 0.000 (both headline + worst-yr) | ✅ |
| 6 | Residualization | cs-residualize to eliminate mv / vol / reversal confounds | both legs residualized (α_n_mom vs {log_mv, σ_120, ret_20}; α_17 via σ-bucket rank) | ✅ |
| 7 | Spec sensitivity | ≥ 4/7 baseline-neighborhood specs pass | 5/7 pass, failures at grid corners | ✅ |

### Best-year-out full detail

Sharpe when each year is individually dropped:

| drop year | Sharpe-without | % of full |
|---:|---:|---:|
| 2018 | 1.995 | 102.3% |
| 2019 | 2.027 | 103.9% |
| 2020 | 2.266 | 116.2% |
| 2021 | 1.917 | 98.3% |
| **2022 (best)** | **1.647** | **84.5%** |
| 2023 | 2.002 | 102.6% |
| 2024 | 1.767 | 90.6% |

Even after removing 2022 (the genuinely exceptional year), the remaining
series has Sharpe 1.65 — still above 1.2, still above 50% of headline.
The strategy is not dependent on any single year.

> **Note:** An earlier version of `followup_mom_lottery_rotation.md` flagged
> best-year-out as a technical fail based on a ratio `best_year / full ≥ 2`
> interpretation. That was a misread of the rule. The correct rule —
> "Sharpe with best year dropped ≥ 50% of full" — passes comfortably (84.5%).
> The v2 report is corrected.

## Disposition

All 7 audits pass. The rotation strategy clears the round-6 falsification
bar that α_35 cleared alone in its own session.

**Deployment-readiness:**

- The rotation logic is deterministic, reproducible from the script, and
  has no look-ahead dependency.
- Both underlying factor signals are already residualized and industry-
  neutralized in their respective session artifacts.
- The dispersion gate is the same mechanism as α_35's, with identical
  timing. Only the *interpretation* of low-dispersion months changes
  (from "cash out" to "deploy lottery leg").

**Remaining work before production deployment:**

1. Promote α_17 out of RESEARCH-ONLY status. Currently the lottery leg
   uses α_17 from `logs/20260421_volprice_max_lottery/outputs/panel_round3.parquet`.
   For production, α_17 needs its own `factors/price_volume/lottery_.../code.py`
   so the rotation has two production-grade dependencies rather than
   one-and-a-research-panel.
2. Alternative: productionize the rotation as a single combined factor
   `factors/price_volume/dispersion_regime_rotation_v1/` whose `code.py`
   internally computes both α_n_mom and α_17_n and merges them. This
   avoids needing α_17 to be its own library entry, at the cost of some
   code duplication.
3. Update `factors/README.md` catalog.

Option 2 is faster and more self-contained — recommend that path if the
user wants to promote this to the library now.

## References

Same citations as follow-on #2:

- Stivers, C. T., & Sun, L. (2010). Cross-sectional return dispersions and
  time variation in value and momentum premiums. *JFQA* 45(4): 987–1014.
- Bali, T. G., Cakici, N., & Whitelaw, R. F. (2011). Maxing out: Stocks as
  lotteries and the cross-section of expected returns. *JFE* 99(2): 427–446.
- Blitz, D., Huij, J., & Martens, M. (2011). Residual momentum. *JEF* 18(3):
  506–521.
- Liu, J., Stambaugh, R. F., & Yuan, Y. (2019). Size and value in China.
  *JFE* 134(1): 48–69.
