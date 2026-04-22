# Extended stress test — 2018-01 → 2026-04

**Session:** `20260422_trend_technical_alpha` (follow-on out of main research loop)
**Date:** 2026-04-22
**Data extension:** cache extended 2025-04-21 → 2026-04-22 via
`scripts/13_extend_data_forward.py` (+244 trade days, +1.3M rows). Lottery
`panel_round3.parquet` rebuilt by re-running
`logs/20260421_volprice_max_lottery/scripts/{01, 06b, 08}` on the extended cache.

## Why run this

Rotation follow-on (`followup_mom_lottery_rotation.md`) and round-6
falsification (`rotation_round6_falsification.md`) were run on data through
2025-04-18. User requested extending the backtest "from 2025 to now" —
2025 was entirely OOS, and 2026 Q1 is newly available. This is a pure
out-of-sample stress test of conclusions drawn before 2025 data existed.

## Headline — α_35 (DEPLOYED) degradation

Extended full-sample LS (5 bps/side, monthly rebalance):

| metric | original (→2025-04) | **extended (→2026-04)** | delta |
|---|---:|---:|---:|
| LS full Sharpe | 1.22 | **1.13** | −0.09 |
| LS ann net | 6.41% | 6.04% | −0.37 pp |
| LS Max DD | −5.53% | −6.21% | deeper |
| LS worst-year | 0.04 (2023) | **−1.44 (2025)** | huge |

### α_35 per-year

| year | n | ann net | Sharpe | MaxDD | note |
|---:|---:|---:|---:|---:|---|
| 2018 | 13 | 0.00% | 0.00 | 0.00% | gate all-off (cash) |
| 2019 | 12 | +4.44% | +1.36 | −1.05% | |
| 2020 | 12 | +11.91% | +1.28 | −5.08% | megacap rally headwind weathered |
| 2021 | 12 | +7.58% | +1.78 | −0.37% | |
| 2022 | 12 | +8.03% | +1.80 | −0.10% | |
| 2023 | 12 | +2.61% | +0.96 | −1.51% | worst-year fix from α_29→α_35 held |
| 2024 | 12 | +15.26% | +2.06 | −1.54% | banner year (original test year) |
| **2025** | 13 | **−3.62%** | **−1.44** | **−3.05%** | **FAIL** |
| 2026 YTD | 3 | +19.55% | +3.11 | −0.10% | recovery (3 rebalances only) |

### α_35 rolling-12m Sharpe trajectory

| as of | rolling-12m Sharpe | 12m cum ret | rolling-12m MaxDD |
|---|---:|---:|---:|
| 2024-12-31 | +2.06 | +16.06% | −1.54% |
| 2025-03-31 | +0.28 | +1.25% | −3.65% |
| 2025-06-30 | **−0.80** ⚠️ | −3.09% | −4.12% |
| 2025-09-30 | **−0.93** ⚠️ | −3.71% | −6.12% |
| 2025-12-31 | **−1.44** ⚠️ | −3.88% | −3.05% |
| 2026-03-31 | +0.70 | +3.16% | −3.05% |

## Kill-switch evaluation (α_35 README rules)

α_35's README specified three kill-switch triggers:

| rule | status | evidence |
|---|---|---|
| 1. rolling-12m Sharpe < 0 | ⚠️ **TRIGGERED** | Q2–Q4 2025 (3 consecutive quarter-ends negative) |
| 2. Max DD < −8% | ✅ safe | peak intra-2025 DD −3.05%, full-sample −6.21% |
| 3. 3 consecutive negative quarters (of returns) | ❌ not quite | Q1 2025 slightly positive per rolling-12m; need direct quarterly-return check |

**Rule 1 alone is sufficient to pause deployment per the specification.**
2026 Q1 is recovering (+3.11 Sharpe over 3 rebalances → +19.55% annualized)
but that's only 3 data points.

## Rotation strategy — 2025 impact

| strategy | 2025 Sharpe | 2025 ann | 2025 role in rotation |
|---|---:|---:|---|
| S1 α_35 (MOM + gate) | **−1.44** | −3.62% | active ~50% of 2025 months |
| S2 α_17 × INV-gate | +0.53 | ~+3% | salvaged ~50% |
| S3 Rotation | **−0.18** | ~−1% | MOM-leg losses outweighed lottery gains |
| S4 Static 50/50 (ungated) | **+1.19** | ~+7% | **beat rotation in 2025** |

**Key finding:** S4 static 50/50 (which deploys both factors ungated and
takes 50/50 of their LS returns) outperformed S3 rotation in 2025 (+1.19
vs −0.18). The dispersion gate carried **negative information** in 2025 —
turning MOM-leg on precisely when it was bleeding, and the INV-gate turning
lottery on during months where lottery also lost money.

This is consistent with a regime change where the Stivers-Sun 2010 "dispersion
proxies momentum opportunity set" relationship weakens or inverts in A-shares.

## Rotation extended per-year table

Reproduced from `followup_mom_lottery_rotation_extended_202604.json`:

| year | S1 MOM | S2 INV | S3 ROT | S4 50/50 |
|---:|---:|---:|---:|---:|
| 2018 | 0.00 | +1.72 | +1.72 | +3.33 |
| 2019 | +1.36 | +0.70 | +1.45 | +0.58 |
| 2020 | +1.28 | −0.47 | +0.97 | +1.29 |
| 2021 | +1.78 | +1.02 | +2.32 | +1.77 |
| 2022 | +1.80 | +3.47 | +5.93 | +5.86 |
| 2023 | +0.96 | +1.23 | +1.62 | +2.00 |
| 2024 | +2.06 | +1.95 | +3.26 | +2.20 |
| **2025** | **−1.44** | **+0.53** | **−0.18** | **+1.19** |

Rotation extended audit:

| audit | threshold | baseline 2018→2025-04 | **extended 2018→2026-04** |
|---|---|---:|---:|
| LS full Sharpe ≥ 1.2 | 1.2 | 1.95 ✅ | **1.81 ✅** |
| Worst-year LS ≥ 0.5 | 0.5 | 0.97 ✅ | **−0.18 ❌** |
| Best-year-out ≥ 50% | 50% | 84.5% ✅ | recompute; 2022 still best |
| Q5 IR ≥ 1.0 | 1.0 | 1.08 ✅ | **0.97 ❌** (marginal) |

The rotation **no longer passes** the strict worst-year audit under
the extended sample.

## Recommendations

Three decision points, listed by urgency:

### 1. α_35 DEPLOYED status (urgent, small action)

Rule 1 of the kill-switch is triggered. Options:

- **PAUSED** — stop new deployments, monitor live. Preserve the code so it
  can be un-paused if 2026 recovery continues.
- **DEGRADED** — document the 2025 failure, halve position size or exposure
  while retaining the factor in rotation.
- Keep as DEPLOYED with a footnote — **not recommended**, violates the
  stated kill-switch rule.

Suggest **PAUSED** with a 2025-regime-failure appendix added to
`factors/price_volume/idio_12_3_momentum_disp_gated_v1/factor.md`. Revisit
after 2026 Q2.

### 2. Rotation strategy — postpone deployment discussion

The "rotation passes all 7 audits" conclusion from `rotation_round6_falsification.md`
is **sample-dependent**. Do NOT promote rotation to `factors/` until a
separate investigation:

- re-runs round-6 falsification on extended sample
- quantifies whether 2025 was an extreme tail year or a true regime break
- designs an additional guardrail (e.g., concentrate/dilution gate tied to
  realized rolling-12m Sharpe of each leg) that would have caught 2025 live

### 3. Research question — why did the gate fail in 2025?

S4 beat S3 in 2025. This is a direct attack on the Stivers-Sun mechanism
for A-shares. Hypotheses to investigate in a dedicated session:

- A-share 2025 specifically: was there a size/style regime change (e.g.,
  small-cap dominance, low-vol dominance) that broke both legs' signals?
- Dispersion measurement: is `cs_std(ret_20)` still a good opportunity-set
  proxy? Possibly needs a micro-structure update (e.g., liquidity-weighted
  dispersion, or sector-level dispersion).
- The placebo test may need to be rerun — the rotation's "alpha" over
  matched random gates was highly significant through 2024, but 2025 may
  have shifted the placebo distribution.

## Artifacts in this stress test

- `scripts/13_extend_data_forward.py` — cache extension
- `outputs/_extend_fwd.log` — fetch log
- `outputs/_fu2_extended_run.log` — rotation re-run log
- `outputs/followup_mom_lottery_rotation_extended_202604.json` — extended metrics
- `outputs/followup_mom_lottery_rotation_tape_extended_202604.csv` — extended tape
- `outputs/extended_stress_test.md` — this report

Originals (2018→2025-04) left intact at:
- `outputs/followup_mom_lottery_rotation.json` / `.csv`
- `outputs/rotation_round6_falsification.json` / `.md`
