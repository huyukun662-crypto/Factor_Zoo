# Run-Mode Call Examples

Use these examples from the evaluator coordinator.

## Stage 1: knowledge run

```json
{
  "tool": "sessions_spawn",
  "arguments": {
    "task": "Run Stage 1 as Research Librarian. Read logs/{session_id}/inputs/objective.md. Write outputs/research_brief.md and working/handoff_1_to_2.json. Return 1-3 mechanism candidates, recommended datasets/operators, and caveats.",
    "label": "worldquant-knowledge-run",
    "runtime": "subagent",
    "agentId": "knowledge",
    "mode": "run",
    "cleanup": "keep",
    "sandbox": "inherit"
  }
}
```

## Stage 2: planner run

```json
{
  "tool": "sessions_spawn",
  "arguments": {
    "task": "Run Stage 2 as Hypothesis Architect. Read outputs/research_brief.md and working/handoff_1_to_2.json. Write outputs/session_metadata.yml and working/handoff_2_to_3.json. Choose exactly one dominant mechanism and define target metrics.",
    "label": "worldquant-planner-run",
    "runtime": "subagent",
    "agentId": "planner",
    "mode": "run",
    "cleanup": "keep",
    "sandbox": "inherit"
  }
}
```

## Stage 3: generator run

```json
{
  "tool": "sessions_spawn",
  "arguments": {
    "task": "Run Stage 3 as Alpha Builder. Read outputs/session_metadata.yml and working/handoff_2_to_3.json. Write outputs/expressions_batch_0001.md and working/handoff_3_to_4.json. Produce exactly 8 expressions with rationale and expected turnover direction.",
    "label": "worldquant-generator-run",
    "runtime": "subagent",
    "agentId": "generator",
    "mode": "run",
    "cleanup": "keep",
    "sandbox": "inherit"
  }
}
```

## Stage 4: backtest run

```json
{
  "tool": "sessions_spawn",
  "arguments": {
    "task": "Run Stage 4 as Backtest Operator. Read outputs/expressions_batch_0001.md and working/handoff_3_to_4.json. Validate before any submission. Write outputs/backtest_results_batch_0001.md and working/handoff_4_to_5.json.",
    "label": "worldquant-backtest-run",
    "runtime": "subagent",
    "agentId": "backtest",
    "mode": "run",
    "cleanup": "keep",
    "sandbox": "inherit"
  }
}
```

## Stage 5: evaluator local closeout

```text
Read:
- outputs/backtest_results_batch_0001.md
- working/handoff_4_to_5.json
- outputs/session_metadata.yml
- round_0001.yml

Then:
- rank candidates
- select best alpha
- decide continue / refine / stop
- write alpha_ranking.md
- update round_0001.yml
- update run_state.json
```
