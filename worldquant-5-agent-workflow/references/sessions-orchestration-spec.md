# Sessions Orchestration Spec

This file defines how the evaluator-coordinator can actually orchestrate the 5-agent workflow using OpenClaw session tools.

## Preferred model

Use the current evaluator session as the coordinator.

Dispatch role work in one of two ways:

1. **Persistent role sessions**
   - Create one long-lived session for each role agent.
   - Use `sessions_send` for each stage handoff.
   - Best for multi-round iterative research.

2. **One-shot spawned runs**
   - Use `sessions_spawn` per stage.
   - Best for isolated, stateless runs.
   - Simpler, but less continuity.

For this workflow, prefer **persistent role sessions**.

## Session bootstrap

Create or reuse these role sessions:
- `worldquant-knowledge`
- `worldquant-planner`
- `worldquant-generator`
- `worldquant-backtest`

Target agent ids:
- `knowledge`
- `planner`
- `generator`
- `backtest`

The current evaluator session remains the coordinator and final reporter.

## Bootstrap procedure

### Step 1
Spawn persistent sessions if missing:
- label: `worldquant-knowledge`, agentId: `knowledge`
- label: `worldquant-planner`, agentId: `planner`
- label: `worldquant-generator`, agentId: `generator`
- label: `worldquant-backtest`, agentId: `backtest`

Use:
- `runtime: subagent`
- `mode: session`
- `thread: false`
- `cleanup: keep`

### Step 2
Store or recover the session labels in `run_state.json`.

## Dispatch protocol

### Dispatch to knowledge
Use `sessions_send` to label `worldquant-knowledge` with:
- current objective
- constraints
- session folder path
- required artifacts

Expected outputs:
- `outputs/research_brief.md`
- `working/handoff_1_to_2.json`

### Dispatch to planner
Use `sessions_send` to label `worldquant-planner` with:
- session folder path
- instruction to read `research_brief.md` and `handoff_1_to_2.json`
- instruction to produce session metadata and planning handoff

Expected outputs:
- `outputs/session_metadata.yml`
- `working/handoff_2_to_3.json`

### Dispatch to generator
Use `sessions_send` to label `worldquant-generator` with:
- session folder path
- selected mechanism
- instruction to produce exactly 8 expressions

Expected outputs:
- `outputs/expressions_batch_0001.md`
- `working/handoff_3_to_4.json`
- `round_0001.yml` expression section

### Dispatch to backtest
Use `sessions_send` to label `worldquant-backtest` with:
- session folder path
- instruction to validate before submission
- backtest configuration constraints

Expected outputs:
- `outputs/backtest_results_batch_0001.md`
- `working/handoff_4_to_5.json`
- `round_0001.yml` backtest section

## Completion checks

Before moving to the next stage, the coordinator should verify the required artifacts exist and are not empty.

If outputs are missing:
- send a corrective follow-up to the same role session
- do not advance stages prematurely

## Evaluator closeout

After the backtest stage completes, the current evaluator session reads:
- `outputs/backtest_results_batch_0001.md`
- `working/handoff_4_to_5.json`
- `round_0001.yml`
- `outputs/session_metadata.yml`

Then it produces:
- `outputs/alpha_ranking.md`
- updated `round_0001.yml`
- updated `run_state.json`
- optional `outputs/final_summary.md`

## Suggested message style

Messages sent with `sessions_send` should be short, imperative, and artifact-oriented.

Always specify:
- what to read
- what to write
- hard constraints
- when to stop and report failure
