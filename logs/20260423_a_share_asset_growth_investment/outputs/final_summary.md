# Final Summary — Round 1 Closed

**Session**: 20260423_a_share_asset_growth_investment
**Mechanism**: Asset Growth / Investment Anomaly (Cooper-Gulen-Schill 2008)
**Rounds completed**: 1 of N (session remains open for round 2 refinement)
**Decision**: **RESEARCH-ONLY**, refinement queued

## TL;DR

We mined an A-share fundamental factor using the full WorldQuant 5-agent workflow. The **Asset Growth** mechanism is confirmed statistically (IC t-stat up to 17 at 60-day horizon) but **fails the promotion bar** because the short leg is destroyed in bull-market years (2020 and 2025 YTD), violating the worst-year Sharpe ≥ 0.5 floor.

**Best factor**: `f5_ag_2y_ind` — 2-year asset growth, industry-neutralized, PIT-lagged.
- IC t-stat (h=60): **17.08**
- Headline LS Sharpe (2020-2025): **0.825**
- Q5 long-only excess Sharpe: **0.594**
- Worst year: 2020, LS Sharpe **-1.24**

## Workflow execution

| Agent | Artifact | Status |
|-------|----------|--------|
| 1 Research Librarian | `research_brief.md` | ✅ |
| 2 Hypothesis Architect | `session_metadata.yml` | ✅ |
| 3 Alpha Builder | `expressions_batch_0001.md` (8 expressions) | ✅ |
| 4 Backtest Operator | `backtest_results_batch_0001.md` + audits | ✅ |
| 5 Evaluator & Recorder | `alpha_ranking.md` + `round_0001.yml` | ✅ |

All 5 Rule-of-8 expressions built; execution-delay and look-ahead audits both PASSED.

## Why RESEARCH-ONLY (SKILL.md audit gate)

| # | Audit | Result |
|---|-------|--------|
| 1 | Execution-delay audit | ✅ PASSED |
| 2 | Look-ahead audit | ✅ PASSED |
| 3 | Worst-year Sharpe ≥ 0.5 | ❌ FAILED (-1.24) |
| 4 | Best-year-out Sharpe ≥ 50% | — skipped (3 already failed) |
| 5 | Falsification-first | ✅ confirmed: 2021-2023 dominates headline |

Per `SKILL.md` rule: any failure → RESEARCH-ONLY. No deployment recommendation.

## Signal is real — why we're not giving up

IC behavior is textbook fundamental factor:
- Monotonically rising with horizon (h=1 → 0.0064, h=60 → 0.0438)
- Industry neutralization preserves signal
- 2-year window outperforms 1-year (consistent with "slow accumulation of empire-building" hypothesis)
- Cross-sectional rank variant is close behind raw (not an outlier-driven artifact)

Annual LS Sharpe in normal/bear years:
```
2021: 1.83    2022: 1.37    2023: 1.57
```
These are strong numbers. The signal works; the packaging (dollar-neutral LS, monthly rebal) doesn't.

## Next-round refinement plan (queued, not yet executed)

**Round 2** — same mechanism, deployable variant:
1. Quarterly rebal (63d) matching IC peak horizon
2. Long-only Q5 with rank weighting (short leg dropped)
3. Regime filter based on 6m CSI300 return
4. OLS residualization vs log(total_mv) (replaces f3's failed median-demean)

**Round 3** — sibling mechanism pivot:
- Net Share Issuance (data cached, clean orthogonal channel)
- Then composite of AG + NSI (classical CMA-style investment factor)

## Known limitations of this round

1. **Panel inheritance** — used `panel.parquet` from accruals session, which ends 2025-04-18. For 2025-04-19 → 2026-04-22 (current), a fresh panel build is needed.
2. **Industry field** — used free-tier 110-group `industry` column, not proper SW L1. PIT SW L1 (`sw_l1_map.parquet`) is cached but unused in this round; promote in round 2.
3. **Size bin** — `size_bin` is s1..s5 as of panel build date, not per-date cross-sectional; survivorship mild.
4. **Universe filter** — inherited from panel; no explicit ST re-exclusion this round.
5. **No residualization against Momentum** — recommended audit not performed (will do in round 2).

## Handoff to round 2

Owner: same evaluator (this session continues).
Script seed: `scripts/03_build_and_backtest.py` (adapt for quarterly rebal + long-only-Q5 + regime filter).
Expected round 2 headline: if mechanism holds outside 2020, long-only Q5 quarterly should reach Sharpe ~1.0-1.2 with worst-year floor ≥ 0.0.

---

**End of Round 1, 2026-04-23.**
