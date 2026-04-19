# Coordinator Execution Spec

## Purpose

This document tells the evaluator-coordinator exactly how to manage one full research round using the existing OpenClaw agent set.

## Coordinator responsibilities

1. Parse user objective.
2. Create or resume the session folder.
3. Decide the current stage.
4. Dispatch the correct task to the correct agent.
5. Validate returned artifacts.
6. Persist outputs.
7. Decide whether to continue, refine, or stop.

## State machine

Stages:
- `research`
- `planning`
- `generation`
- `backtest`
- `evaluation`
- `done`

Allowed transitions:
- `research` -> `planning`
- `planning` -> `generation`
- `generation` -> `backtest`
- `backtest` -> `evaluation`
- `evaluation` -> `generation` when continuing/refining
- `evaluation` -> `done` when stopping

## Resume rules

If user says “continue from X stage”, the coordinator must:
- inspect existing artifacts
- confirm the requested stage is logically consistent
- reuse earlier outputs unless they are invalidated

## Failure handling

### Knowledge-stage failure
Action:
- ask for narrower objective or better source material

### Planning-stage failure
Action:
- force one mechanism selection; reject vague multi-mechanism plans

### Generation-stage failure
Action:
- reject outputs with fewer or more than 8 expressions
- reject batches that drift away from the selected mechanism

### Backtest-stage failure
Action:
- separate syntax failure, platform failure, and weak-performance failure
- only syntax/platform failures return to fix mode automatically

### Evaluation-stage failure
Action:
- if results are incomplete, request missing metrics
- if results are sufficient, still produce a ranked best-effort assessment

## QQBot per-stage DM notification rule

When the workflow is running in the current QQBot multi-bot setup and the user wants each agent to visibly report in its own conversation, send a stage-complete DM from the stage owner bot immediately after artifact validation.

Routing rule:
- Stage 1 (`research`) -> `bot1` / `knowledge`
- Stage 2 (`planning`) -> `bot2` / `planner`
- Stage 3 (`generation`) -> `bot3` / `generator`
- Stage 4 (`backtest`) -> `bot4` / `backtest`
- Stage 5 (`evaluation`) -> `bot5` / `evaluator`

Target resolution:
- Read `C:\Users\Hu\.openclaw\workspace-evaluator\config\qqbot-c2c-targets.json`
- Use the matching `target` for the bot account
- Send via the official path:
  - `openclaw message send --channel qqbot --account botX --target qqbot:c2c:<openid> --message "..."`

Recommended implementation helper:
- `C:\Users\Hu\.openclaw\workspace-evaluator\scripts\worldquant_stage_notify.py`

Notification timing:
- Only send after the coordinator has validated that the required stage artifacts exist and are non-empty
- If a stage requires host exec approval, that same bot/session should request approval in its own conversation where practical

Suggested minimum payload:
- stage title
- short summary
- `session_id`
- main artifact path

## Minimum user-facing update after each round

The coordinator should summarize:
- what stage finished
- the strongest candidate so far
- whether the workflow will continue, refine, or stop
- what the next step is
