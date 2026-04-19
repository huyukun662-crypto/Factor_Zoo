# sessions_send Templates

Use these templates from the evaluator-coordinator.

## To worldquant-knowledge

```text
Run Stage 1 as Research Librarian.

Read from the session folder:
- inputs/objective.md

Write these outputs:
- outputs/research_brief.md
- working/handoff_1_to_2.json

Constraints:
- Return 1-3 mechanism candidates.
- Recommend datasets/operators.
- Include caveats.
- Do not choose the final mechanism.
```

## To worldquant-planner

```text
Run Stage 2 as Hypothesis Architect.

Read from the session folder:
- outputs/research_brief.md
- working/handoff_1_to_2.json

Write these outputs:
- outputs/session_metadata.yml
- working/handoff_2_to_3.json

Constraints:
- Choose exactly one dominant mechanism.
- Define causal chain, regime, horizon, and target metrics.
- If the brief is too vague, stop and report why.
```

## To worldquant-generator

```text
Run Stage 3 as Alpha Builder.

Read from the session folder:
- outputs/session_metadata.yml
- working/handoff_2_to_3.json

Write these outputs:
- outputs/expressions_batch_0001.md
- working/handoff_3_to_4.json
- round_0001.yml expression section

Constraints:
- Produce exactly 8 expressions.
- Keep all expressions aligned to one mechanism.
- Add rationale and expected turnover direction for each expression.
```

## To worldquant-backtest

```text
Run Stage 4 as Backtest Operator.

Read from the session folder:
- outputs/expressions_batch_0001.md
- working/handoff_3_to_4.json

Write these outputs:
- outputs/backtest_results_batch_0001.md
- working/handoff_4_to_5.json
- round_0001.yml backtest section

Constraints:
- Validate all 8 expressions before submission.
- If validation fails, stop and report explicit fixes needed.
- Use conservative polling.
- Separate syntax failure, platform failure, and weak performance.
```
