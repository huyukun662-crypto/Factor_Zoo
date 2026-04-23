# Executable Plan for the WorldQuant 5-Agent Workflow

This file turns the conceptual workflow into an operational runbook.

## Runtime model

Use one coordinator plus five role agents. The coordinator does not replace the role agents; it only:
- creates the session folder
- chooses which agent runs next
- validates handoff completeness
- decides whether to continue another round

## Recommended session folder

```text
logs/
└── YYYYMMDD_topic_model/
    ├── inputs/
    │   └── objective.md
    ├── working/
    │   ├── handoff_1_to_2.json
    │   ├── handoff_2_to_3.json
    │   ├── handoff_3_to_4.json
    │   └── handoff_4_to_5.json
    ├── outputs/
    │   ├── research_brief.md
    │   ├── session_metadata.yml
    │   ├── expressions_batch_0001.md
    │   ├── backtest_results_batch_0001.md
    │   ├── alpha_ranking.md
    │   └── final_summary.md
    ├── round_0001.yml
    └── run_state.json
```

## Coordinator procedure

### Step 0 — Initialize session

Create:
- `inputs/objective.md`
- `working/`
- `outputs/`
- `run_state.json`

`run_state.json` example:

```json
{
  "session_id": "20260408_sentiment_gpt",
  "current_round": 1,
  "current_stage": "research",
  "status": "running",
  "selected_mechanism": null,
  "best_alpha_id": null,
  "continue_research": true
}
```

### Step 1 — Run Research Librarian

Input source:
- `inputs/objective.md`
- any attached paper, note, or prior alpha

Expected output:
- `outputs/research_brief.md`
- `working/handoff_1_to_2.json`

Validation before next step:
- at least one mechanism candidate
- at least one dataset or operator recommendation
- at least one caveat

After validation succeeds:
- call `C:\Users\Hu\.openclaw\workspace-evaluator\scripts\worldquant_stage_notify.py --stage 1 --title "Stage 1 complete" --summary "Research brief and handoff are ready." --session-id <session_id> --artifact <session_folder>\outputs\research_brief.md`

### Step 2 — Run Hypothesis Architect

Input source:
- `outputs/research_brief.md`
- `working/handoff_1_to_2.json`

Expected output:
- `outputs/session_metadata.yml`
- `working/handoff_2_to_3.json`

Validation before next step:
- one dominant mechanism selected
- horizon and regime defined
- target metrics defined

After validation succeeds:
- call `C:\Users\Hu\.openclaw\workspace-evaluator\scripts\worldquant_stage_notify.py --stage 2 --title "Stage 2 complete" --summary "Session metadata and planning handoff are ready." --session-id <session_id> --artifact <session_folder>\outputs\session_metadata.yml`

### Step 3 — Run Alpha Builder

Input source:
- `outputs/session_metadata.yml`
- `working/handoff_2_to_3.json`

Expected output:
- `outputs/expressions_batch_0001.md`
- draft expression section in `round_0001.yml`
- `working/handoff_3_to_4.json`

Validation before next step:
- exactly 8 expressions
- every expression has a short rationale
- no empty expression slot

After validation succeeds:
- call `C:\Users\Hu\.openclaw\workspace-evaluator\scripts\worldquant_stage_notify.py --stage 3 --title "Stage 3 complete" --summary "Exactly 8 expressions were generated and validated for handoff." --session-id <session_id> --artifact <session_folder>\outputs\expressions_batch_0001.md`

### Step 4 — Run Backtest Operator

Input source:
- `outputs/expressions_batch_0001.md`
- `working/handoff_3_to_4.json`

Expected output:
- `outputs/backtest_results_batch_0001.md`
- backtest section in `round_0001.yml`
- `working/handoff_4_to_5.json` including per-expression gate table
  (see `references/validation-gates.md`)

Validation before next step — run the 4-gate funnel from
`references/validation-gates.md`:

- G1 Importable & syntactically sound
- G2 Runs end-to-end without exception
- G3 Non-degenerate backtest (Q5 size, turnover, signal dispersion, unique
  names — this is the gate that catches silent zero-signal backtests,
  the single highest-cost failure class)
- G4 Behavioral fidelity (IC sign matches thesis, monotonic deciles, not
  a classic-factor clone)

If ANY expression fails ANY gate, do NOT proceed to Step 5. Invoke the
repair loop below.

#### Step 4b — Repair loop (Agent 3 ↔ Agent 4)

The benchmark data is explicit: one-shot Agent 3 output passes all gates
on roughly 75% of expressions; up to 5 rounds of structured-error
feedback pushes that to ~95%. Use the budget.

Procedure per failing expression:

1. Agent 4 writes `working/agent4_repair_NNNN.json` with `retry_round`,
   `expression_id`, `failed_gate`, `invariant`, `observed`, `threshold`,
   `diagnostic_snippet`, `suspected_cause`, `suggested_fix`. Schema in
   `validation-gates.md`.
2. Agent 3 returns a revised expression (same `id`, incremented
   `retry_round`). Not a brand-new mechanism.
3. Agent 4 re-runs gates G1–G4 on the revised expression only.
4. Repeat until pass OR retry_count reaches 5.

Stop conditions:
- 2 consecutive retries fail the same gate on the same invariant →
  escalate to Agent 5 for a round-level decision (pivot mechanism,
  change horizon, drop the expression).
- retry_count ≥ 5 → mark expression RESEARCH-ONLY; do not present as
  a candidate to Agent 5.

What NOT to do in the repair loop:
- Do not lower the gate thresholds in `validation-gates.md` to make
  a failing expression pass.
- Do not silently drop failing expressions to preserve the "8 expressions"
  Rule of 8. Better to return a batch of 5 + 3 RESEARCH-ONLY than a batch
  of 8 with 3 silently corrupted.
- Do not swap to a different mechanism mid-retry — that is a new batch.

After all gates pass (or retry budgets exhaust):
- call `C:\Users\Hu\.openclaw\workspace-evaluator\scripts\worldquant_stage_notify.py --stage 4 --title "Stage 4 complete" --summary "Backtest validation and result capture are complete." --session-id <session_id> --artifact <session_folder>\outputs\backtest_results_batch_0001.md`

### Step 5 — Run Evaluator & Recorder

Input source:
- `outputs/backtest_results_batch_0001.md`
- `working/handoff_4_to_5.json`
- `round_0001.yml`

Expected output:
- `outputs/alpha_ranking.md`
- completed `round_0001.yml`
- optional `outputs/final_summary.md`
- updated `run_state.json`

Validation before next step:
- ranked candidate list exists
- best candidate or failure reason exists
- next-step decision exists

After validation succeeds:
- call `C:\Users\Hu\.openclaw\workspace-evaluator\scripts\worldquant_stage_notify.py --stage 5 --title "Stage 5 complete" --summary "Evaluation, ranking, and round decision are ready." --session-id <session_id> --artifact <session_folder>\outputs\alpha_ranking.md`

## Continue / stop logic

Continue another round when:
- at least one expression shows signal promise but needs refinement
- failure is fixable by syntax repair, turnover control, or neutralization adjustment
- mechanism still looks economically plausible

Stop when:
- the best candidate already meets the objective
- the mechanism is repeatedly weak across coherent variants
- results suggest the hypothesis is structurally wrong
