# Run-Mode Orchestration Spec

This is the recommended production path for the current environment.

## Why run mode is primary

Use run mode as the default because it has already been validated in the current environment:
- `agentId` spawning works
- `runtime="subagent"` works
- `mode="run"` works
- `mode="session"` remains unavailable on the current QQBot target

## Recommended coordinator model

- The evaluator remains the parent coordinator.
- Each stage uses a one-shot subagent run.
- Artifacts are written to the session folder between stages.
- The evaluator reads artifacts, validates them, and decides the next action.

## Stage sequence

1. knowledge run
2. planner run
3. generator run
4. backtest run
5. evaluator local closeout

## Required artifacts

```text
logs/{session_id}/
  inputs/objective.md
  outputs/research_brief.md
  outputs/session_metadata.yml
  outputs/expressions_batch_0001.md
  outputs/backtest_results_batch_0001.md
  outputs/alpha_ranking.md
  working/handoff_1_to_2.json
  working/handoff_2_to_3.json
  working/handoff_3_to_4.json
  working/handoff_4_to_5.json
  round_0001.yml
  run_state.json
```

## Coordinator rules

- Always spawn each stage as a fresh run.
- Always validate artifacts before advancing.
- Never let generation advance without exactly 8 expressions.
- Never let backtest advance without validation being recorded.
- Always write a visible round summary for the user.

## Session mode status

Session mode is not the primary path in this skill because the current QQBot target has not passed thread-bound subagent session validation.
Treat session mode as a future enhancement, not a current dependency.
