# Alpha Ranking — Round 2 (Phase-Rotation Adversarial)

Session: 20260502_a_share_etf_anchor_high_v1
Round 2 ran 8 E3-centric variants AND a phase-rotation audit on the
R1 lead candidate.

## Headline finding (adversarial)

R1 reported E3 (range_pos_252) LS Sharpe = **0.628** — the single-best
result among 21 possible rebalance phase offsets. When averaged over
all 21 phases (the honest measure), the LS Sharpe collapses to
**0.239**. The factor mechanism is real but considerably weaker than
R1 implied.

### Phase-rotation distribution for `range_pos_252` (LS Q5, k=20, rebal=21)

| stat            | LS    | top-3 | top-5 |
|-----------------|-------|-------|-------|
| mean            | 0.239 | 0.180 | 0.121 |
| std             | 0.245 | 0.218 | 0.227 |
| min             | -0.230| -0.194| -0.373|
| 25 %ile         | 0.075 | 0.027 | -0.037|
| median          | 0.230 | 0.151 | 0.100 |
| 75 %ile         | 0.395 | 0.314 | 0.243 |
| max             | 0.637 | 0.608 | 0.602 |
| best phase      | 0     | 1     | 2     |
| R1 phase        | 0     | 0     | 0     |

R1's E3 corresponds to phase 0 — the LS-best phase. This is not
fraud (the implementation just uses the natural starting offset),
but it is **selection bias relative to what production would
realize**, since live trading does not get to pick the phase.

### Phase-averaged ensemble portfolio per-year LS Sharpe

|              | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|--------------|------|------|------|------|------|------|
| LS           | 1.12 | -0.16| -0.62| 1.34 | 0.19 | 0.56 |
| top-5 excess | 1.19 | -0.15| -0.63| 1.34 | -0.23| -0.54|

Compared to R1 (phase 0): worst-year does NOT improve under phase
averaging (still negative; 2022 LS = -0.62 is the floor). 2021 and
2025 also fall below zero — R1 phase 0 happened to catch the
positive portion of those years.

## R2 variants (phase 0 only — same caveat applies to all)

| ID | label                       | LS net5 | top-5 net5 | Worst yr | Test LS | verdict             |
|----|----------------------------|---------|------------|----------|---------|---------------------|
| F2 | range_pos_120              | 0.406   | 0.416      | -1.57    | 0.24    | rejected (worst yr) |
| F3 | range_pos_60               | 0.415   | 0.091      | -0.68    | 0.26    | rejected (worst yr) |
| F4 | multi-window rank composite| 0.312   | 0.654      | -1.17    | -0.04   | rejected (test)     |
| F6 | MA200 risk-on gate         | 0.255   | 0.103      | -0.19    | -0.08   | best worst-year     |
| F1 | range_pos_252 (rerun)      | 0.228   | 0.410      | -0.64    | 0.17    | (= R1 E3, phase 0)  |
| F7 | range_pos_252 res-mom_252  | 0.110   | -0.241     | -1.61    | 0.41    | momentum-only ≈ 52% |
| F5 | range_pos_252 / vol_60     | 0.033   | -0.071     | -0.92    | 0.37    | rejected            |
| F8 | range_pos_252 rebal=42d    | -0.110  | 0.043      | NaN      | -0.11   | rejected (zero info)|

None of the 8 R2 variants clears the PROMOTE floor of LS Sharpe ≥ 0.5
*and* worst-year ≥ 0.5 simultaneously. F6 has the best worst-year
(-0.19) but its test-window Sharpe is -0.08.

## Why does F4 (multi-window) have top-5 0.65 but LS only 0.31?

Looking at top-5 long-only excess: F4 0.654 net beats F1 0.410.
The multi-window rank average smooths phase noise *for the long
leg*. The LS leg is dragged down because the bottom quintile gets
diluted across windows and contains low-conviction shorts that
sometimes outperform (Pitfall 7: bull-market short-leg destruction).

This suggests the cleanest deployable form is **F4 long-only
top-5**, not F1 LS, IF we can confirm robustness under phase
rotation (not done in this round; recommended for R3 if pursued).

## Falsification: F7 momentum residualization

F7 = F1 with daily cross-sectional regression on 252d momentum.
Residual LS Sharpe = 0.110, which is 48 % of F1's 0.228.
Interpretation: about half of the range-position signal is
explained by 252d momentum, half is incremental. Genuine but
modest residual signal.

## Final ranking (R2)

| Rank | Candidate                                    | Honest headline                | Verdict        |
|------|----------------------------------------------|--------------------------------|----------------|
| 1    | F4 multi-window rank, top-5 long excess      | net 0.65 *single-phase*        | research-grade |
| 2    | F1 / E3 range_pos_252, top-5 long excess     | phase-avg 0.12, single-phase 0.41 | research-only |
| 3    | F1 LS Q5                                     | phase-avg 0.24, single-phase 0.23 | research-only |
| 4    | F6 MA200-gated F1                            | LS 0.26, worst -0.19           | weakest worst-yr |
| —    | F2/F3/F5/F7/F8                               | dominated                      | rejected       |

## R2 Decision

**RESEARCH-ONLY remains.** The mechanism is genuine but the headline
in R1 was driven by phase-selection bias. Honest LS Sharpe is
≈ 0.24, top-5 long-only excess is ≈ 0.12, and worst-year is
negative under any phase choice.

For deployment as a sleeve component, F4 (multi-window top-5
long-only excess) deserves a phase-rotation re-evaluation in a
hypothetical R3 — but absent that, it should not be promoted.
