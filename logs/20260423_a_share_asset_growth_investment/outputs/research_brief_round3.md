# Research Brief — Round 3: Net Share Issuance + AG⊕NSI composite

**Session**: 20260423_a_share_asset_growth_investment
**Round**: 3
**Mechanism**: Investment anomaly, *issuance channel* (sibling of Round 1's AG / real-investment channel)

## Why NSI

Cooper-Gulen-Schill 2008's Asset Growth decomposes into two channels:
1. **Real-investment channel**: capex → PP&E → TA grows (explored Rounds 1+2 via `ag_yoy_ind`)
2. **Financing channel**: share issuance dilutes existing holders (Pontiff-Woodgate 2008; Daniel-Titman 2006)

Daniel-Titman 2006 show the **issuance channel alone explains ~50% of CGS's return spread globally**. In A-share this channel is particularly strong due to:
- Heavy SPO (follow-on) activity in 2020-2021 and 2024-2025
- Convertible bond conversions
- Employee stock incentive vesting
- State-directed equity refinancing ("定增")

All of these show up in `total_share` (from `balancesheet.parquet`).

## Hypothesis for Round 3

**H1**: NSI has IC magnitude comparable to AG (t-stat > 10 at h=60), with **different timing** — issuance shocks are announcement-driven events (concentrated), while AG is a continuous balance-sheet drift.

**H2**: The **AG ⊕ NSI composite** is meaningfully stronger than either alone — they are different measurements of the same underlying q-theory signal (low expected return → cheap financing → firm issues/invests). Fama-French CMA composites typically add 30-60% to standalone-factor Sharpe.

**H3**: NSI may work in 2025 where AG broke, because the 2025 regime break looks driven by AI-theme capex acceleration (high AG, high current profit) — but those firms often also issued equity aggressively. NSI would still short them.

## Data

- `balancesheet.parquet` field `total_share` — quarterly, 143K rows, 6334 stocks
- Coverage: 2017-12-31 to 2024-12-31
- Primary signal: `nsi_yoy = -(total_share_t - total_share_{t-4q}) / total_share_{t-4q}` (negate so low-issuance → long)

## Round 2 lessons absorbed

From `round_0002.yml` failures:
- **Monthly rebal, not quarterly**: IC at h=60 does not justify 63d rebal
- **No liquidity floor**: signal lives in small caps
- **No size residualization**: size exposure is a feature
- **Industry demean is good**: use `industry` column (110 groups)
- **Composite with very-correlated factors hurts**: R2's 0.6·f5 + 0.4·f2 failed (80% correlation). NSI should have lower correlation to AG (financing vs investment channel).

## 8 Expressions for Round 3 (Rule of 8)

All **monthly rebal, long-only Q5 equal-weight, 5bps/side**, industry-demeaned (except #1 as benchmark):

| # | name | formula | mechanism layer |
|---|------|---------|-----------------|
| 1 | `r3_nsi_yoy_raw` | `-ΔShares_4q / Shares_{t-4q}`, no demean | NSI benchmark |
| 2 | `r3_nsi_yoy_ind` | `r3_nsi_yoy_raw` industry-demean | **primary NSI candidate** |
| 3 | `r3_nsi_log_ind` | `-log(Shares_t/Shares_{t-4q})` industry-demean | NSI tail control |
| 4 | `r3_nsi_2y_ind` | `-ΔShares_8q / Shares_{t-8q}` industry-demean | NSI slow variant (matches R1's f5 window) |
| 5 | `r3_cma_combo` | `0.5·z(f5_ag_2y_ind) + 0.5·z(r3_nsi_2y_ind)` | **primary CMA-style composite** |
| 6 | `r3_cma_triple` | `(z(f2)+z(f5)+z(r3_nsi_yoy_ind))/3` | 3-way fundamental investment basket |
| 7 | `r3_ag_orth_nsi` | AG ⊥ NSI per date via OLS, then combine | residualized composite — checks orthogonality |
| 8 | `r3_nsi_rank_ind` | `rank(nsi_yoy_q)` industry-demean | NSI rank-normalized (robustness) |

## Expected outcomes

- **Base case** (H1 confirmed): NSI standalone Sharpe 0.5-0.9 Q5-excess — similar to AG
- **Bull case** (H2 confirmed): AG⊕NSI composite Sharpe 0.8-1.2 — **PROMOTE-eligible** if worst year > 0
- **Bear case** (2025 regime break bleeds into NSI): NSI also negative in 2025 → composite still fails → session closes with RESEARCH-ONLY

## Required audits (inherited from SKILL.md)

1. Execution-delay: PIT via `f_ann_date + 1` (same as Rounds 1+2)
2. Look-ahead: balance-sheet only uses past dates, future-perturbation invariant
3. Worst-year Sharpe ≥ 0 for Q5-excess (relaxed from 0.5 since one-sided)
4. Best-year-out Sharpe ≥ 50% of headline
5. IC t-stat ≥ 3 on Test window (2023-2025)
6. **New**: NSI-AG correlation check — if > 0.7, composite adds nothing; if < 0.3, the composite is the interesting object
