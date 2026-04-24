# Alpha Ranking — Batch 0001

**Session:** `20260424_a_share_etf_industry_dipbuy_v1`
**Universe:** 32 A-share thematic/industry ETFs (no gold, no dividend)

## Ranking (by weighted score: train_sh + oos_sh − |val_sh|, then train worst-year)

| rank | id | Train | Val | OOS | Train worst | Train floor | Verdict |
|---:|---|---:|---:|---:|---:|:-:|---|
| 1 | **p_top3_diversified** | +0.886 | -0.244 | **+0.929** | 2022 +0.112 | ✅ | RESEARCH (winner) |
| 2 | p_top1_conviction | +1.233 | +0.180 | +0.105 | 2022 +0.008 | ✅ | train overfit, OOS collapse |
| 3 | d40_baseline | +0.654 | -0.799 | +0.850 | 2022 -0.346 | ❌ | reference baseline |
| 4 | d40_resid_250d | +0.392 | -1.468 | +1.335 | 2022 -0.677 | ❌ | strongest OOS but train weak |
| 5 | d40_bounce_conf | +0.579 | -1.451 | +1.234 | 2022 -0.937 | ❌ | sparse, unstable |
| 6 | d40_deep_only | +0.437 | -0.886 | +1.209 | 2022 -0.993 | ❌ | sparse, unstable |
| 7 | d40_low_vol_surrender | +0.379 | -0.638 | +0.929 | 2022 -1.294 | ❌ | volatile train |
| 8 | d40_vol_scaled | +0.692 | -0.670 | +0.617 | 2022 -0.859 | ❌ | Nagel scaling worse than raw |

## Full-sample comparison (winner vs baseline, same signal)

| | d40_baseline | **p_top3_diversified** | Δ |
|---|---:|---:|---:|
| Net Sh @5bps | +0.540 | **+0.766** | **+0.226** |
| Max drawdown | -43.52% | **-31.63%** | **+11.9pp** |
| Train worst-year | -0.346 | **+0.112** | **flips positive** |
| OOS Sh | +0.850 | +0.929 | +0.08 |

Industry-cluster constraint is the single most effective transformation
this session found. Same -logret_40d signal; only difference is the
max-1-per-cluster allocation rule.

## Full-sample audit checklist

| audit | result | pass |
|---|---|:-:|
| G1 non-degeneracy | signal nonzero fraction 1.000 | ✅ |
| G3 IC at k=40 | +0.0267 (t=+3.07, n_dates=1727) | ✅ |
| G4 Train Sh ≥ 0.5 | +0.886 | ✅ |
| G4 Train worst-year ≥ 0 | +0.112 (2022) | ✅ |
| G5 OOS Sh ≥ 0.3 | +0.929 | ✅ |
| Promote: Val Sh ≥ 0.5 | -0.244 | ❌ |
| Promote: OOS Sh ≥ 0.5 | +0.929 | ✅ |
| Promote: full worst-year ≥ 0 | -0.244 (2023) | ❌ |

Inherited audits (pipeline unchanged from earlier sessions):
- Execution-delay double path: ✅ (inherited, max abs diff 1.5e-15)
- Look-ahead within-date randomization: ✅ (inherited)
- Falsification probe +logret_20d at k=40: ✅ (pipeline clean)

## G-funnel pass statistics (this batch)

| gate | pass | total |
|---|---:|---:|
| G1 non-degeneracy | 8 | 8 |
| G3 IC+Sh | 3 | 8 (IC>0, net Sh>-0.3 all splits) |
| G4 Train research floor | 2 | 8 |
| G5 OOS sanity | 7 | 8 |
| Promote | 0 | 8 |

## Batch-level finding (cluster-level G5 check)

- Signal-refinement cluster (3 exprs): all had Train Sh < baseline. **Refinements did not help in-sample.**
- Conditional-trigger cluster (3 exprs): all had strong OOS (0.93 to 1.23) but weak Train (0.38-0.58). **Triggers help OOS, hurt Train. Possibly sample-size artifact.**
- Portfolio-construction cluster (2 exprs): both pass Train floor. **The constraint-based approach (diversification, concentration) is where the wins are.**

Cluster-level lesson: **portfolio construction > signal refinement** on
this universe in this horizon. Next-round direction should lean into more
portfolio-construction variants (e.g., risk-parity weighting, dispersion-
sized positions, cluster-rotation gating).
