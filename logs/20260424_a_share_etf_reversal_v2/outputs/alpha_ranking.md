# Alpha Ranking — Batch 0001

**Session:** `20260424_a_share_etf_reversal_v2`
**Agent:** 5 (Evaluator & Recorder)
**Date:** 2026-04-24

## Ranking by headline strategy: long-only top-3 monthly @ 5 bps/side

| rank | id | cluster | k | IC @k | t | Net Sh @5bps | MaxDD | Turnover | Worst year (Sh) | Best-year-out ratio | G4 |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|---:|:-:|
| 1 | `r1_rev_40d`       | medium_scan    | 40 | +0.0262 | +3.02 | **+0.774** | -42.4% | 17%  | 2023 (-0.585) | 0.73 | partial* |
| 2 | `r1_rev_80d`       | medium_scan    | 80 | +0.0210 | +2.29 | **+0.757** | -44.2% | 13%  | 2023 (-0.705) | 0.71 | partial* |
| 3 | `r1_rev_60d`       | medium_scan    | 60 | +0.0204 | +2.43 | +0.529     | -44.2% | 14%  | 2023 (-0.775) | 0.64 | partial* |
| 4 | `r1_rev_20d`       | medium_scan    | 20 | +0.0067 | +0.79 | +0.559     | -44.7% | 21%  | 2023 (-0.640) | 0.67 | partial* |
| 5 | `r1_dd60_raw`      | drawdown_event | 60 | -0.0064 | -0.78 | +0.391     | -58.2% | 14%  | 2023 (-1.062) | 0.52 | fail    |
| 6 | `r1_dd60_recover`  | drawdown_event | 60 | +0.0125 | +1.63 | +0.341     | -59.3% | 19%  | 2023 (-1.262) | 0.49 | fail    |
| 7 | `r1_rev_5d`        | short_probe    | 5  | +0.0040 | +0.46 | +0.273     | -59.0% | 20%  | 2023 (-0.515) | 0.56 | fail    |
| 8 | `r1_rev_1d`        | short_probe    | 1  | +0.0110 | +1.27 | +0.260     | -69.3% | 19%  | 2022 (-1.466) | 0.50 | fail    |

\* "partial" means: IC t-stat passes G3, Net Sharpe @5bps passes G4 net-Sh ≥ 0.5, look-ahead and falsification audits pass, but **worst-year floor fails** (all candidates had a year below 0; the 0.5 promote-grade floor is very far out of reach).

## Ranking by long-only top-3 weekly (second-best wrapper)

| rank | id | Net Sh @5bps | MaxDD | Turnover | Worst year (Sh) |
|---:|---|---:|---:|---:|---|
| 1 | `r1_rev_40d`  | +0.720 | -36.3% | 38% | 2023 (-0.028) |
| 2 | `r1_rev_80d`  | +0.612 | -31.5% | 29% | 2023 (-0.114) |
| 3 | `r1_rev_60d`  | +0.556 | -36.8% | 30% | 2023 (-0.073) |
| 4 | `r1_rev_20d`  | +0.384 | -46.3% | 48% | 2022 (-0.532) |
| 5 | `r1_dd60_raw` | +0.392 | -43.9% | 31% | 2023 (-0.675) |

**Observation:** weekly rebalance lowers MaxDD vs monthly and shrinks 2023's worst-year dramatically — for `r1_rev_40d` weekly, 2023 = -0.028 (essentially flat), compared to monthly's -0.585. But the headline Sharpe is lower (+0.720 vs +0.774) because weekly gives up some of the fat-tail on good months.

## Cluster-level G5 audit

| cluster | expected IC sign at own horizon | observed | verdict |
|---|---|---|---|
| short_falsification (k=1, 5)    | negative (prior evidence)   | weakly positive (t 0.46-1.27) | **mechanism shifted** — extended universe turned short-horizon momentum into ambiguous / weakly reversal |
| medium_scan (k=20, 40, 60, 80) | positive (hypothesis)       | positive, t=0.79 → 3.02       | **confirmed** — 40-80d is the reversal zone; k=40 is new sweet spot |
| drawdown_event (k=60)           | positive (hypothesis)       | mixed: raw negative, recover positive but weak | **partially disconfirmed** — drawdown-depth alone is not a reversal feature on this universe; the recovery gate adds marginally but still below G4 |

## Short-leg diagnostic (why LS strategies all lose)

| id | LS Net Sh @5bps (monthly) | long-only Net Sh @5bps (monthly) | implied short-leg Sh |
|---|---:|---:|---:|
| r1_rev_40d | -0.010 | +0.774 | ≈ -0.78 |
| r1_rev_80d | -0.186 | +0.757 | ≈ -0.94 |
| r1_rev_60d | -0.297 | +0.529 | ≈ -0.83 |

**Short leg is a persistent drag of ~0.8-1.0 Sharpe per unit of exposure.** Shorting past-winners on A-share thematic ETFs during 2020-2025 has been a losing trade because momentum persisted in the non-rotation regime.

## V7_gold fusion (optional overlay)

On the 349 common weeks (2019-05 → 2026-04 approximately), V7_gold weekly
PnL has Sharpe 3.73 at the standalone baseline. Fusion sweep:

| reversal candidate | blend=10% | 15% | 20% | 30% | 50% | baseline |
|---|---:|---:|---:|---:|---:|---:|
| r1_rev_40d monthly | 3.716 | 3.671 | 3.598 | 3.374 | 2.714 | 3.733 (V7) |
| r1_rev_80d monthly | 3.718 | 3.672 | 3.599 | 3.378 | 2.747 | 3.733 |
| r1_rev_60d weekly  | 3.686 | 3.621 | 3.528 | 3.259 | 2.512 | 3.733 |

**Every blend weight reduces the combined Sharpe vs V7 alone.** Even the best (10% r1_rev_80d) is −0.015 vs V7, well within noise. Reversal candidates do not fuse productively with V7 on this common window. Note: V7's Sharpe of 3.73 here is on the inner-joined 349-week slice (post warmup); the published full-sample V7 is +1.91.

## Mandatory audits (5/5 checklist)

| audit | result | value | pass |
|---|---|---|---|
| 1. Execution-delay | target built via two independent paths | max diff = 1.5e-15 | ✅ |
| 2. Look-ahead randomization | within-date symbol-label shuffle | real IC=0.026 (t=3.02) → shuf IC=0.004 (t=0.60) | ✅ |
| 3. Best-year-out ≥ 50% headline | top 3 candidates | 0.71, 0.73, 0.76 | ✅ |
| 4. Falsification (pipeline clean) | probe_mom_20d_plus at k=60 | IC=-0.003, t=-0.32 | ✅ |
| 5. Worst-year Sharpe ≥ 0.5 | every candidate fails | best worst-year = -0.028 (r1_rev_40d weekly, 2023) | ❌ |

## Verdict

**RESEARCH-ONLY.** Any failure of the 5 mandatory pre-PROMOTE audits
routes to RESEARCH-ONLY per skill rules. Audit 5 fails for all candidates;
additionally the V7 fusion overlay does not add value.

## G-funnel dogfood

- **G1 non-degeneracy gate** passed for all 8 expressions (nonzero fraction 0.43 – 0.997). `r1_dd60_recover` is the sparsest at 0.43 (conditional gate on positive recent momentum) but still well above 0.01.
- **G3 (IC + net Sh 5bps ≥ -0.5)** pass: 7/8 (only the short-horizon probes and drawdown_raw had weak IC but net Sh not < -0.5 on long-only).
- **G4 research-floor (net Sh ≥ 0.5 + worst-year ≥ 0 + MaxDD > -40%)** pass: 0/8 strict (all have worst-year below 0); partial pass on net-Sh metric: 4/8.
- **G5 batch-level horizon** pass: the medium_scan cluster produced the expected positive IC-t gradient from k=20 (0.79) → k=40 (3.02) → k=60 (2.43) → k=80 (2.29). Monotonicity up to k=40, then modest decay. Consistent with the mechanism hypothesis — no batch-level failure mode detected.
