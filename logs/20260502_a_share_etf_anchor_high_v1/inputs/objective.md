# Objective — A-share ETF Anchor / 52-Week-High Proximity v1

Mine a deployable cross-sectional factor on the 34-ETF A-share universe based
on **proximity to the 52-week high** (George & Hwang 2004) and related
range-position constructions.

Hypothesis: ETFs trading near a multi-month high have higher expected
forward returns than ETFs trading near a multi-month low, because the
disposition / anchoring effect causes systematic underreaction to good
news in the names that have already broken out. The same effect should
be cleaner on baskets (ETFs) than on single stocks because basket
returns smooth out idiosyncratic news, leaving anchoring as a more
dominant driver.

## Why this is distinct from prior ETF sessions in this repo

Prior 6 ETF sessions cover: short-term reversal, weekly TQPB momentum,
daily flow accumulation, IVOL momentum, IVOL reversal, lead-lag. None
of them tests anchoring or 52-week-high proximity, which is its own
documented anomaly with different correlation structure.

## Constraints

- Universe: 34 A-share ETFs in `_shared_cache/etf_daily.parquet`.
  Drop `512800.SS` and `515170.SS` (only 137 bars).
- Period: 2019-01-02 to 2026-04-30 (Yahoo end-of-day adjusted).
- Execution delay: `delay = 1` bar.
- Cost: 5 bps per side (round-trip 10 bps).
- Primary horizon: monthly (`k=20` trading days).
- TVT split: Train 2019-01..2021-12, Validate 2022-01..2022-12,
  Test 2023-01..2026-04.

## Deliverables

- 8 expressions in one batch.
- Validation gates G1..G5 + the 5 mandatory audits before any PROMOTE.
- Per-year Sharpe table for both LS and Q5/top-N long-only excess.
- Cost sensitivity at 0 / 5 / 10 / 20 bps/side.
- Decision in `final_summary.md`.
