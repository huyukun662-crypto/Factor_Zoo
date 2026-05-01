# Alpha Ranking — LeadLag Spillover v1, Batch 0001

Owner: Agent 5 (Evaluator & Recorder).
Generated: 2026-05-01.

## Summary verdict

**STOP — cost-unviable. Mechanism partially confirmed but not deployable.**

The broad-ETF lead-lag spillover hypothesis is *partially* present in
A-share ETFs (single-leader IC@k=1 = +2.09 t-stat for the 510300-only
variant), but two findings rule out promotion:

1. **All 8 expressions have negative net-Sharpe @ 5 bps/side.** Daily
   rebalance with rank-based factors generates 12k-18k% annualized
   turnover; 5 bps/side cost erases the gross signal.
2. **Contemporaneous IC@k=0 is large and negative (t = -3 to -4).**
   Cross-section mean-reverts within the trading day after responding
   to the leader's t-1 move. The "next-day diffusion" signal is small
   relative to this contemporaneous overreaction-and-revert pattern.

## Validation gates (Round 1)

| expr | G1 | G2 | G3 | G4 | ic_t@k=0 | ic_t@k=1 |
|---|---|---|---|---|---:|---:|
| g1_spillover_3leader_lag1            | pass | pass | fail | fail | -3.58 | +0.05 |
| g2_spillover_510300only_lag1         | pass | pass | fail | pass | -4.10 | +2.09 |
| g3_spillover_3leader_lag1to2_decay   | pass | pass | fail | fail | -3.46 | +0.47 |
| g4_spillover_residual_leader_lag1    | pass | pass | fail | fail | -2.80 | +0.66 |
| g5_spillover_3leader_lag1_volscaled  | pass | pass | fail | fail | -1.77 | -0.09 |
| g6_spillover_3leader_orthogonalized  | pass | pass | fail | fail | -0.13 | -0.24 |
| g7_spillover_signonly_3leader        | pass | pass | fail | fail | -3.80 | +0.64 |
| g8_kitchen_sink_rank                 | pass | pass | fail | fail | -3.59 | +0.46 |

G3 fails uniformly because **net-Sharpe@5bps < 0** is below the -0.5
G3 floor (some expressions just barely pass; g6 at -1.76 violates by
a wide margin).

G5 (batch-level horizon consistency) **PASSES** — 7/8 expressions peak
IC at the declared primary k=1, and 7/8 are at the same horizon.
Hypothesis horizon was correctly specified.

## LS Sharpe summary (k=1, daily rebalance, 5 bps/side cost)

| expr | LS gross | LS net@5bps | turnover% | LS train | LS val | LS test | wy_pass |
|---|---:|---:|---:|---:|---:|---:|---|
| g1_spillover_3leader_lag1            | -0.21 | -1.21 | 14350 | -0.17 | -1.22 | +0.03 | False |
| g2_spillover_510300only_lag1         | +0.45 | -0.49 | 12468 | +0.66 | +0.13 | +0.34 | False |
| g3_spillover_3leader_lag1to2_decay   | +0.01 | -0.75 | 10818 | -0.39 | -0.87 | +0.68 | False |
| g4_spillover_residual_leader_lag1    | -0.01 | -1.00 | 14366 | -0.17 | -0.46 | +0.30 | False |
| g5_spillover_3leader_lag1_volscaled  | +0.10 | -1.15 | 15124 | +0.01 | -0.14 | +0.27 | False |
| g6_spillover_3leader_orthogonalized  | -0.42 | -1.76 | 17793 | -1.14 | -0.35 | +0.34 | False |
| g7_spillover_signonly_3leader        | -0.05 | -1.10 | 14155 | -0.19 | -0.95 | +0.34 | False |
| g8_kitchen_sink_rank                 | +0.17 | -0.93 | 15096 | +0.10 | -0.53 | +0.44 | False |

Best gross is g2 (single-leader 510300) at +0.45. Best net is also g2
at -0.49. The cost wall is the binding constraint.

## Per-year LS Sharpe

| 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| g1 | -0.52 | -0.02 | -0.08 | -1.22 | +0.68 | -0.04 | -0.66 | +0.46 |
| g2 | +0.61 | +1.17 | +0.30 | +0.13 | +1.26 | +0.09 | +1.50 | -3.53 |
| g3 | -1.73 | +0.05 | +0.09 | -0.87 | +1.30 | -0.07 | +0.61 | +1.92 |
| g4 | -1.21 | +0.17 | +0.19 | -0.46 | +0.41 | +0.33 | -0.04 | +0.92 |
| g5 | +0.31 | -0.22 | +0.01 | -0.14 | +0.69 | +1.24 | -2.24 | +0.50 |
| g6 | -0.68 | -0.31 | -2.00 | -0.35 | +0.50 | +0.36 | +1.08 | -1.68 |
| g7 | -0.21 | +0.46 | -0.87 | -0.95 | +0.31 | +0.58 | +0.30 | -0.48 |
| g8 | -0.15 | +0.26 | +0.14 | -0.53 | +0.67 | +0.98 | -0.62 | +0.49 |

g2 is the only expression with consistently positive yearly Sharpe in
the test window (2023-2025) but craters in 2026 partial year (-3.53)
and the gross-not-net story is misleading.

## Mandatory audits

| Audit | Result |
|---|---|
| Execution-delay (target_shift = -(1+1) = -2 for k=1) | PASS |
| Look-ahead (permute leader 510300 last-30d, check past unchanged) | PASS (max diff = 0.0) |
| Worst-year floor (≥ 0.5) | FAIL — every expression has at least one negative year |
| Best-year-out (≥ 50% headline) | N/A — most headlines near zero |
| Falsification-first | "If LS Sharpe is wrong by 50%, what's the most likely cause?" Pre-run answer: cost wall. Confirmed: net@5bps is negative for all 8. |
| Contemporaneous IC@k=0 vs IC@k=1 | k=0 dominates (|t|≈3-4) vs k=1 (|t|≤2.1). The "diffusion" interpretation is weak — most of the spillover is contemporaneous, with reversion at t+1. |

## Why g2 (single-leader 510300) was best

- 510300 is the most liquid A-share ETF and the broadest signal.
- Multi-leader aggregation (g1, g3, g7) added noise from 510500 and
  159915 — those leaders are themselves followers of 510300 most days.
- Negative correlation between the spillover signal and contemporaneous
  return at t (IC@k=0 = -4.10) means the cross-section already
  overreacted to the leader move on day t. The +2.09 t-stat at k=1
  is the *residual unfinished diffusion* but is small in magnitude.

## Ranking

1. g2_spillover_510300only_lag1   — IC t@k=1 = +2.09, gross +0.45 / net -0.49 — best of a weak set
2. g8_kitchen_sink_rank           — gross +0.17 / net -0.93
3. g5_spillover_3leader_lag1_volscaled — gross +0.10 / net -1.15
4. g3_spillover_3leader_lag1to2_decay  — gross +0.01 / net -0.75
5. g4_spillover_residual_leader_lag1   — gross -0.01 / net -1.00
6. g7_spillover_signonly_3leader       — gross -0.05 / net -1.10
7. g1_spillover_3leader_lag1           — gross -0.21 / net -1.21
8. g6_spillover_3leader_orthogonalized — gross -0.42 / net -1.76

## Decision

**STOP.** None of the 8 expressions passes a single floor:
- IC t-stat ≥ 3.0: best is +2.09 (g2)
- Net Sharpe @ 5bps > 0.3: best is -0.49 (g2)
- Worst-year ≥ 0.5: failed by all
- Annual turnover ≤ 1500%: failed by all (10k-18k%)

The mechanism has a real *kernel* — the single-leader g2 IC at k=1
is non-trivial — but the kernel is buried under contemporaneous
overreaction and the cost wall. Bringing this to deployable would
require:

1. Lower turnover (e.g., trade only when |signal| > threshold to skip
   small-flips), but this kills the cross-sectional discipline.
2. Subtract the contemporaneous overreaction pattern from the signal
   (Ang-Boudoukh adjustment), but doing so explicitly will likely
   eat the +2.09 t-stat.
3. Move to weekly rebalance — but at k=1 the signal decays so weekly
   misses the window.

Open thread: the *contemporaneous overreaction* finding (IC@k=0 = -4)
is the **deployable** signal here, not the lead-lag. A future session
should test "high t-1 leader move → ETF underperforms at t" as a
contrarian intra-day execution overlay (requires intra-day data,
out of scope for daily-bar workflow).
