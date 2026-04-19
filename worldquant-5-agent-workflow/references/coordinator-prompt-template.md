# Coordinator Prompt Template

Use this as the parent orchestrator prompt.

## Mission
Run one round of the WorldQuant 5-agent workflow using the existing OpenClaw agents:
`knowledge`, `planner`, `generator`, `backtest`, `evaluator`.

## Rules
- Execute stages in order.
- Do not skip handoff validation.
- Do not let the generator send fewer or more than 8 expressions.
- Do not let the backtest stage proceed if validation failed.
- Require the evaluator to return `continue`, `refine`, or `stop`.
- Persist artifacts after every stage.

## Stage sequence
1. Ask `knowledge` for a research brief.
2. Ask `planner` to choose one mechanism and create the session plan.
3. Ask `generator` for exactly 8 expressions.
4. Ask `backtest` to validate and run the batch.
5. Ask `evaluator` to rank and decide the next action.

## Required artifacts
- `research_brief.md`
- `session_metadata.yml`
- `expressions_batch_0001.md`
- `backtest_results_batch_0001.md`
- `alpha_ranking.md`
- `round_0001.yml`
- `run_state.json`

## Required final decision
At the end of the round, update state with:
- best candidate
- reason
- continue/refine/stop
- next-round focus
