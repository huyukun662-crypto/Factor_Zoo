# Validation Gates — 4-Stage Funnel for Agent 4

This file is the mandatory pre-submission checklist for Agent 4 (Backtest
Operator). It exists because syntax-clean code can still produce **silent
zero-signal backtests** and **semantically wrong results** — the two most
common failure modes we have seen in practice and the ones reported across
recent LLM-quant benchmarks.

Treat this as a funnel: a batch must pass every gate before Agent 4 hands
off to Agent 5. A gate failure does NOT mean rerun-blindly; it means feed
the structured error back to Agent 3 (see `## Retry loop` below).

---

## Background — why these gates exist

Two independent benchmark results motivate this file:

1. **QuantCode-Bench (Lime, 2026)** — collected 400 strategy tasks and ran
   them through a 4-stage funnel: syntax check → runs without error →
   actually trades → behavioral fidelity. Best single-shot model passed
   only ~76%. With multi-round retry and structured error feedback (up to
   10 attempts), pass rate reached 95-98%.
2. **AlphaForgeBench (2026)** — LLMs used as direct traders showed neurotic
   and self-contradictory behavior; LLMs used as factor/expression
   generators (reasoning separated from execution) were stable and useful.

Translation for this workflow:
- Agent 3 IS the factor generator (reasoning). Keep it that way.
- Agent 4 IS the harness. Its job is to catch the 24% silent-failure tail
  **before** Agent 5 ever sees a corrupt result.
- Cheap 5-round retries with structured errors beat one perfect prompt.

---

## The 4 gates

Every one of the 8 expressions in a batch must pass gates G1–G4. If any
expression fails, the WHOLE batch returns to Agent 3 for repair.

### G1 — Importable & syntactically sound

Trivial in modern setups but still non-zero. Grep for the usual culprits:

- `import` statements resolve (no missing package)
- Parquet columns referenced actually exist in `.cache/*.parquet`
- Tushare endpoint names are real (`daily`, `daily_basic`, `balancesheet`,
  `stock_basic`, etc. — not hallucinated)
- No f-string syntax errors, unbalanced brackets, stale variable names

**Failure mode**: trivially obvious. Fix by re-reading the expression.

### G2 — Runs end-to-end without exception

The script must complete a full backtest loop without raising. Common
silent-killer exceptions:

- `KeyError` on a column that was renamed between caches
- `ValueError` when winsor/zscore is applied to an all-NaN column
- `TypeError` on `np.polyfit` when residualization input is all-NaN
- `IndexError` from `shift(N)` when there is insufficient history
- Timezone mismatch in `merge_asof`
- `numpy.linalg.LinAlgError` from a singular matrix

**Failure mode**: the script raises. Fix the specific line.

### G3 — Non-degenerate backtest (the critical gate)

This is the one that catches the 17.8% "zero-signal" silent-failure class.
The backtest ran, but it didn't actually do anything meaningful. Required
invariants:

| Invariant | Threshold | Why it matters |
|---|---|---|
| Non-NaN signal coverage per date | ≥ 50 stocks on ≥ 90% of trading days | Below this, cross-section is too sparse for stable z-scores |
| Q5 membership size per date | ≥ 30 stocks on ≥ 95% of trading days | Below this, Q5 return is dominated by 1-2 names and Sharpe is noise |
| Annual turnover | 10% ≤ turnover ≤ 2000% | Below 10%: signal is frozen (always-long). Above 2000%: factor is noise-driven |
| Fraction of trading days with zero rebalancing | ≤ 5% | Sustained zero-rebalance days usually means the signal collapsed to a tie |
| Unique Q5 names over full window | ≥ 3× headline portfolio size | Below this, the "portfolio" is the same handful of names forever — essentially a static bet |
| Signal std(cross-section) per date | > 0 on ≥ 99% of days | Catches the "all stocks get the same score" bug (usually from a broken neutralization) |

Optional but strongly recommended:

- Plot Q5 vs Q1 cumulative returns on a single chart before declaring
  success. A flat Q5-Q1 line with non-zero Sharpe is almost always a
  zero-trade artifact.

**Failure mode**: script completes, numbers exist, but they don't
represent an actual strategy. This is the single most-expensive class of
bug because it looks like success.

### G4 — Behavioral fidelity

The expression does what Agent 2's economic thesis said it would do.
Verify by checking SIGNED invariants:

- **Sign of IC matches thesis**: if the thesis said "low investment →
  high future return", the IC of the unsigned factor vs `fwd_ret` must
  be NEGATIVE. If positive, the expression has the sign wrong. (Rule of
  thumb: always negate at source so "high signal = long" holds by
  construction.)
- **Monotonicity across deciles**: Q1 < Q2 < ... < Q5 on average return
  over the full window. Allow one inversion (e.g., Q3/Q4 crossed) but
  not two. Non-monotonic factors are either too weak for deployment or
  have a bug.
- **Horizon consistency with neutralization claim**: if `session_metadata.yml`
  claims "industry-neutralized 20-day horizon", IC at 20d must be
  materially larger than IC at 1d (otherwise the factor is really
  a 1-day signal with noise).
- **No trivial classic-factor clone**: compute |corr| with size, 20d
  momentum, and the universe-EW return. If any |corr| > 0.85, the
  "new" factor is not new — it is the classic factor renamed.

**Failure mode**: the factor is real but different from the thesis. Agent
5 would later catch this with correlation analysis, but catching it here
saves a round.

---

## Retry loop (Agent 3 ↔ Agent 4)

If gates G1–G4 fail, DO NOT re-run the same expression hoping for better
luck. Feed the structured error back to Agent 3 with a bounded retry
budget.

### Retry contract

- **Budget**: up to 5 rounds per batch. After round 5, promote the batch
  to RESEARCH-ONLY and document the residual failure mode — do not
  silently drop failing expressions to get to 8.
- **Error payload**: `working/agent4_repair_NNNN.json` with the schema:
  ```json
  {
    "retry_round": 2,
    "expression_id": "r3_ag_orth_nsi",
    "failed_gate": "G3",
    "invariant": "Q5 membership size",
    "observed": 12,
    "threshold": 30,
    "diagnostic_snippet": "Q5 size by quarter: 2020Q1=8 2020Q2=11 2020Q3=14 ...",
    "suspected_cause": "staleness filter of 60 days is too tight; most stocks have staleness 90-180 days for annual reports",
    "suggested_fix": "relax staleness to 200 days OR use merge_asof with backward direction"
  }
  ```
- **Hand back to Agent 3**: the expression + the error payload. Agent 3
  returns a revised expression (counting against the retry budget), NOT
  a brand new one. Brand new expressions start a new batch.

### What Agent 3 should NOT do on retry

- Loosen thresholds in Agent 4's validator to make the gate pass. If G3
  fails because Q5 is too thin, fix the expression; do not lower the
  Q5 floor.
- Swap mechanism mid-retry. If the expression is fundamentally the wrong
  mechanism, that's a round decision, not a retry decision.
- Silently remove problematic dates from the panel. "Drop 2020" is not
  a fix; it is a confession that the factor is regime-dependent.

### When to stop retrying and escalate

- 2 consecutive retries fail the same gate with the same invariant →
  escalate to Agent 5 for round-level decision (pivot mechanism, change
  horizon, drop mechanism, etc.).
- Retry count ≥ 5 for any single expression → mark that expression as
  RESEARCH-ONLY in the batch report; do not promote to Agent 5 as a
  candidate.

---

## Handoff augmentation

`handoff_4_to_5.json` MUST include the per-expression gate table:

```json
{
  "expressions": [
    {
      "id": "r3_ag_orth_nsi",
      "gates": {"G1": "pass", "G2": "pass", "G3": "pass", "G4": "pass"},
      "retry_count": 1,
      "notes": "G3 initially failed on Q5 size; relaxed staleness gate to 200 days"
    }
  ]
}
```

Agent 5 is allowed to downgrade any candidate whose `retry_count > 2`
regardless of headline metrics, because high retry counts correlate with
fragile implementations.

---

## Relationship to other reference files

- `common-pitfalls.md` — documents real post-hoc failures. G3/G4 are
  designed to catch Pitfalls 1, 6, 7, 9, 11, 12 *before* they reach Agent 5.
- `execution-delay-audit.md` — runs INSIDE gate G4 as a specific fidelity
  check for the delay invariant.
- `execution-plan.md` — the retry loop described here slots between
  Step 3 and Step 4 of the coordinator procedure.
- `tvt-split-template.md` — runs AFTER all four gates pass, on the subset
  of candidates Agent 5 keeps.

---

## One-line summary

If Agent 4 hands anything to Agent 5 without a clean G1/G2/G3/G4 table in
`handoff_4_to_5.json`, the workflow is operating in pre-funnel mode and
every downstream decision is suspect.
